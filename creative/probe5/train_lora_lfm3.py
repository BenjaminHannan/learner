"""Probe-3's test-writer SFT on LFM3-1.7B (Probe-5 PREREG.md): torch + peft, on MPS where there is one (frozen base fp16, LoRA weights and the loss fp32, as sleepmlx's lfm3_mps profile).
Same recipe as probe3/train_lora.py / train_mlx.py: LoRA r16, alpha 32, dropout .05 on attention q/k/v/o, short-conv in/out and feed-forward w1/w2/w3 (regex from LFM3-FACTS.md), AdamW lr 1e-4 (no weight decay),
cosine with 3% warmup, 2 epochs, effective batch 16 = 16 micro-batches of 1 accumulated, grad clip 1.0, seed 0, gradient checkpointing, loss on the answer tokens only (token mean over the effective batch),
the lm_head sees only the answer positions. Prompt = the chat template with thinking off (generation prompt ends <think></think>), target = reply + <|im_end|>: exactly what llama-server is given at test time.
The model comes from the vendored LiquidAI code (vendor/) and a LOCAL weights dir: no trust_remote_code, no network.
Prints and logs the val loss before training and after every epoch (the last one is "after"). Keeps the LAST state (no checkpoint picking). PEFT adapter -> OUT/adapter (adapter_model.safetensors + adapter_config.json).
Usage: train_lora_lfm3.py --model ~/learner-ops/models/lfm3-1.7b-hf --data DIR(train.jsonl, val.jsonl from probe3/build_data.py) --out DIR [--mps-gb 12]
Resumable: a checkpoint (LoRA weights + optimizer + step) is written every --save-every steps to OUT/ckpt.pt; rerun the same command. Exit 75 = ASSISTANT_RUNNING appeared (checkpoint saved).
Smoke (CPU, no weights): --tiny --tokenizer DIR --limit-train 4 --limit-val 2 --max-steps 2 --batch 2"""
import argparse, json, math, os, random, resource, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C
import lfm3_load as L
import mlx_common as M    # probe3/mlx: constants (R, ALPHA, DROPOUT, LR, WARMUP, EPOCHS, BATCH, SEED), lr_at, epoch_orders (plain python, no mlx needed)

R, ALPHA, DROPOUT, LR, WARMUP, EPOCHS, BATCH, SEED = M.R, M.ALPHA, M.DROPOUT, M.LR, M.WARMUP, M.EPOCHS, M.BATCH, M.SEED
END_OF_TURN = "<|im_end|>"


# ---------- data ----------
def encode(tok, prompt, target, max_len=None):
    """-> (input_ids, labels): labels -100 on the generation prompt, the token ids of target + <|im_end|> after it; None if longer than max_len."""
    p = tok.apply_chat_template([dict(role="user", content=prompt)], add_generation_prompt=True, tokenize=False, enable_thinking=False)
    pi = tok(p, add_special_tokens=False)["input_ids"]       # the template writes <|startoftext|> itself
    ai = tok(target + END_OF_TURN, add_special_tokens=False)["input_ids"]
    ids = pi + ai
    return None if max_len and len(ids) > max_len else (ids, [-100] * len(pi) + ai)


# ---------- dropout that survives gradient checkpointing ----------
class KeyedDropout:
    """LoRA input dropout whose mask depends only on (SEED_BOX[0], uid), via a private generator: under gradient checkpointing the backward re-runs the forward, and the global RNG of some devices (MPS)
    is not restored, which would give the recomputation a different mask than the forward used."""
    SEED_BOX = [0]
    _gens = {}

    @classmethod
    def build(cls, p, uid):
        import torch

        class _D(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.p, self.uid = p, uid

            def forward(self, x):
                if not self.training or self.p == 0:
                    return x
                key = zlib.crc32(f"{cls.SEED_BOX[0]}|{self.uid}".encode()) % 2**31
                g = cls._gens.get(x.device.type)
                if g is None:
                    try:
                        g = torch.Generator(device=x.device)
                    except Exception:  # noqa  (a device without private generators: fall back to the global one)
                        g = False
                    cls._gens[x.device.type] = g
                if g is False:
                    keep = torch.rand(x.shape, device=x.device) >= self.p
                else:
                    g.manual_seed(key)
                    keep = torch.rand(x.shape, device=x.device, generator=g) >= self.p
                return x * keep.to(x.dtype) * (1.0 / (1.0 - self.p))
        return _D()


def use_keyed_dropout(peft_model):
    n = 0
    for _, m in peft_model.named_modules():
        d = getattr(m, "lora_dropout", None)
        if d is not None and "default" in d:
            d["default"] = KeyedDropout.build(DROPOUT, n)
            n += 1
    return n


# ---------- loss ----------
def collate(items, pad_id):
    import torch
    n = max(len(i) for i, _ in items)
    ids = torch.full((len(items), n), pad_id, dtype=torch.long)
    lab = torch.full((len(items), n), -100, dtype=torch.long)
    att = torch.zeros((len(items), n), dtype=torch.long)
    for k, (i, l) in enumerate(items):
        ids[k, :len(i)], lab[k, :len(l)], att[k, :len(i)] = torch.tensor(i), torch.tensor(l), 1
    return ids, att, lab


def answer_loss(lm, ids, att, lab):
    """-> (summed CE over the answer tokens in fp32, their number). lm = the peft model; the lm_head only sees the answer rows."""
    import torch.nn.functional as F
    base = lm.get_base_model() if hasattr(lm, "get_base_model") else lm
    h = base.model(input_ids=ids, attention_mask=att, use_cache=False).last_hidden_state[:, :-1]
    tgt = lab[:, 1:].to(h.device)
    m = tgt != -100
    logits = base.lm_head(h[m]).float()
    return F.cross_entropy(logits, tgt[m], reduction="sum"), int(m.sum())


def val_loss(lm, data, pad_id, dev):
    import torch
    lm.eval()
    tot = n = 0
    with torch.no_grad():
        for ex in data:
            s, k = answer_loss(lm, *(x.to(dev) for x in collate([ex], pad_id)))
            tot, n = tot + float(s), n + k
    lm.train()
    return tot / max(n, 1)


# ---------- memory / device ----------
def pick_device(torch):
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    return "mps" if mps is not None and mps.is_available() else "cpu"


def set_mps_cap(torch, gb):
    total = None
    f = getattr(torch.mps, "recommended_max_memory", None)
    if f:
        try:
            total = float(f())
        except Exception:  # noqa
            total = None
    if total is None:
        try:
            import psutil
            total = float(psutil.virtual_memory().total)
        except Exception:  # noqa
            total = 32e9
    frac = max(0.05, min(1.0, gb * 1e9 / total))
    torch.mps.set_per_process_memory_fraction(frac)
    return frac


def mem_gb(torch, dev):
    """(device memory in use now, driver-allocated, process peak RSS) in GB."""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (2**30 if sys.platform == "darwin" else 2**20)
    if dev == "mps":
        return torch.mps.current_allocated_memory() / 2**30, torch.mps.driver_allocated_memory() / 2**30, rss
    if dev == "cuda":
        return torch.cuda.memory_allocated() / 2**30, torch.cuda.max_memory_allocated() / 2**30, rss
    return 0.0, 0.0, rss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir with train.jsonl, val.jsonl (probe3/build_data.py)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=os.path.expanduser("~/learner-ops/models/lfm3-1.7b-hf"), help="local HF snapshot of LiquidAI/LFM3-1.7B (weights + tokenizer files)")
    ap.add_argument("--tokenizer", default=None, help="tokenizer dir if different from --model (smoke tests)")
    ap.add_argument("--dtype", default="auto", choices=["auto", "float16", "bfloat16", "float32"], help="frozen base dtype; auto: fp16 on MPS/CUDA, fp32 on CPU")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-len", type=int, default=8192, help="examples longer than this are dropped (reported)")
    ap.add_argument("--tiny", action="store_true", help="smoke test: random-init tiny model of the same architecture (needs --tokenizer)")
    ap.add_argument("--limit-train", type=int, default=0)
    ap.add_argument("--limit-val", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (smoke test)")
    ap.add_argument("--batch", type=int, default=BATCH, help="effective batch (16 = the prereg; other values are for smoke tests only)")
    ap.add_argument("--save-every", type=int, default=5)
    ap.add_argument("--mps-gb", type=float, default=0, help="cap this process's MPS memory at about this many GB (0 = no cap)")
    ap.add_argument("--no-grad-checkpoint", action="store_true")
    ap.add_argument("--no-pause-flag", action="store_true")
    a = ap.parse_args()
    import torch
    from transformers import AutoTokenizer
    from peft import LoraConfig, get_peft_model
    os.makedirs(a.out, exist_ok=True)
    final = os.path.join(a.out, "adapter")
    if os.path.exists(os.path.join(final, "adapter_config.json")):
        print("final adapter already exists:", final, "(delete OUT/adapter to retrain)")
        return 0
    bad = L.check_hashes()
    assert not bad, f"vendored model files differ from the pinned revision: {bad}"
    random.seed(SEED), torch.manual_seed(SEED)
    dev = pick_device(torch) if a.device == "auto" else a.device
    dt = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(a.dtype) or (torch.float16 if dev in ("mps", "cuda") else torch.float32)
    if dev == "mps" and a.mps_gb:
        print(f"MPS memory cap: fraction {set_mps_cap(torch, a.mps_gb):.3f} (~{a.mps_gb} GB)", flush=True)
    tok = AutoTokenizer.from_pretrained(a.tokenizer or a.model, trust_remote_code=False)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    data = {}
    for nm, lim in (("train", a.limit_train), ("val", a.limit_val)):
        rows = C.read_jsonl(os.path.join(a.data, nm + ".jsonl"))[:lim or None]
        enc = [encode(tok, r["prompt"], r["target"], a.max_len) for r in rows]
        data[nm] = [e for e in enc if e]
        print(f"{nm}: {len(data[nm])} examples ({len(enc) - len(data[nm])} dropped > {a.max_len} tokens), {sum(len(i) for i, _ in data[nm])} tokens, "
              f"{sum(sum(x != -100 for x in l) for _, l in data[nm])} answer tokens, longest {max(len(i) for i, _ in data[nm])}", flush=True)
    t0 = time.time()
    if a.tiny:
        modeling, _ = L.vendored()
        net = modeling.Lfm3ForCausalLM(L.tiny_config(len(tok))).to(dt)
    else:
        net = L.load_model(a.model, dtype=dt)
    net.config.use_cache = False
    if not a.no_grad_checkpoint:
        net.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        net.enable_input_require_grads()
    lm = get_peft_model(net, LoraConfig(r=R, lora_alpha=ALPHA, lora_dropout=DROPOUT, target_modules=L.TARGET_REGEX, bias="none", task_type="CAUSAL_LM"))
    for p in lm.parameters():       # fp32 adapter weights over a half-precision frozen base
        if p.requires_grad:
            p.data = p.data.float()
    lm.to(dev).train()
    nk = use_keyed_dropout(lm)
    names = [n for n, p in lm.named_parameters() if p.requires_grad]
    assert names and all("lora_" in n for n in names), "only LoRA tensors may train"
    kinds = {k for k in L.MODULE_KINDS if any(f".{k}.lora_A" in n for n in names)}
    assert kinds == set(L.MODULE_KINDS), f"LoRA missing on module kinds: {sorted(set(L.MODULE_KINDS) - kinds)}"
    ntrain = sum(p.numel() for p in lm.parameters() if p.requires_grad)
    nall = sum(p.numel() for p in lm.parameters())
    print(f"model ready in {time.time() - t0:.0f}s on {dev} ({dt}); LoRA on {nk} modules, trainable {ntrain:,} of {nall:,} ({100 * ntrain / nall:.3f}%), dtypes {sorted({str(p.dtype) for p in lm.parameters()})}", flush=True)
    params = [p for p in lm.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0)
    n = len(data["train"])
    per_epoch = math.ceil(n / a.batch)
    sched_total = EPOCHS * per_epoch
    total = a.max_steps or sched_total
    warm = math.ceil(WARMUP * sched_total)
    orders = M.epoch_orders(n, EPOCHS)
    ckpt = os.path.join(a.out, "ckpt.pt")
    start = 0
    if os.path.exists(ckpt):
        st = torch.load(ckpt, map_location="cpu")
        sd = dict(lm.named_parameters())
        with torch.no_grad():
            for k, v in st["lora"].items():
                sd[k].copy_(v)
        opt.load_state_dict(st["opt"])
        start = st["step"]
        print(f"resuming from step {start}", flush=True)
    log_path = os.path.join(a.out, "train_log.jsonl")
    logged = {r["epoch"] for r in (C.read_jsonl(log_path)) if r.get("event") == "val"}
    log = open(log_path, "a")
    peak = dict(driver=0.0, rss=0.0)

    def emit(**r):
        print(json.dumps(r), flush=True), log.write(json.dumps(r) + "\n"), log.flush()

    def maybe_val(ep):
        if ep not in logged:
            t = time.time()
            v = val_loss(lm, data["val"], pad, dev)
            now, drv, rss = mem_gb(torch, dev)
            emit(event="val", epoch=ep, val_loss=v, n_val=len(data["val"]), sec=round(time.time() - t, 1), mem_gb=round(now, 2))
            logged.add(ep)

    def save_ckpt(step):
        sd = dict(lm.named_parameters())
        torch.save(dict(step=step, lora={k: sd[k].detach().cpu() for k in names}, opt=opt.state_dict()), ckpt + ".tmp")
        os.replace(ckpt + ".tmp", ckpt)

    emit(event="start", steps=total, per_epoch=per_epoch, warmup_steps=warm, resumed_from=start, device=dev, dtype=str(dt), n_train=n, torch=torch.__version__)
    t_train = time.time()
    for step in range(start, total):
        ep = step // per_epoch + 1
        if step % per_epoch == 0:
            maybe_val(step // per_epoch)
        if not a.no_pause_flag and C.assistant_running():
            save_ckpt(step)
            emit(event="paused", step=step, reason=f"{C.flag_path()} exists")
            print(f"PAUSED at step {step}: assistant running. Checkpoint saved; rerun the same command to resume.", flush=True)
            return C.EXIT_PAUSED
        g = step % per_epoch
        grp = [data["train"][i] for i in orders[ep - 1][g * a.batch:(g + 1) * a.batch]]
        ntok = sum(sum(x != -100 for x in l[1:]) for _, l in grp)
        t = time.time()
        tot = 0.0
        for j, ex in enumerate(grp):
            KeyedDropout.SEED_BOX[0] = (SEED * 100003 + step) * BATCH + j      # masks depend on (step, micro-batch) only: a resumed run matches an uninterrupted one
            s, _ = answer_loss(lm, *(x.to(dev) for x in collate([ex], pad)))
            (s / ntok).backward()
            tot += float(s.detach())
            del s
        gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        lr = M.lr_at(step, warm, sched_total)
        for grp_ in opt.param_groups:
            grp_["lr"] = lr
        opt.step()
        opt.zero_grad(set_to_none=True)
        if dev == "mps":
            torch.mps.empty_cache()
        sec = time.time() - t
        now, drv, rss = mem_gb(torch, dev)
        peak["driver"], peak["rss"] = max(peak["driver"], drv), max(peak["rss"], rss)
        emit(event="step", step=step + 1, epoch=ep, loss=tot / ntok, grad_norm=gn, lr=lr, s_per_step=round(sec, 1), mem_gb=round(now, 2), driver_gb=round(drv, 2), rss_peak_gb=round(rss, 2),
             eta_min=round((total - step - 1) * sec / 60, 1))
        if (step + 1) % a.save_every == 0 and step + 1 < total:
            save_ckpt(step + 1)
    maybe_val(math.ceil(total / per_epoch))
    lm.save_pretrained(final)
    vals = [r for r in C.read_jsonl(log_path) if r.get("event") == "val"]
    summ = dict(val_loss_before=vals[0]["val_loss"], val_loss_after=vals[-1]["val_loss"], steps=total, train_wall_s=round(time.time() - t_train), device=dev, dtype=str(dt),
                peak_driver_gb=round(peak["driver"], 2), peak_rss_gb=round(peak["rss"], 2), n_train=n, n_val=len(data["val"]), vendored_revision=L.PINNED_REVISION, trainable_params=ntrain)
    C.atomic_write(os.path.join(a.out, "train_summary.json"), json.dumps(summ, indent=1))
    if os.path.exists(ckpt):
        os.remove(ckpt)
    print(f"val loss before {summ['val_loss_before']:.4f} -> after {summ['val_loss_after']:.4f}; saved adapter -> {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
