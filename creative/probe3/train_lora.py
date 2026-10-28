"""Probe-3 SFT (PREREG.md): LoRA r16/a32/drop .05 on all attention+MLP projections of K2-Horizon-3.7B, lr 1e-4 cosine (3% warmup), 2 epochs, effective batch 16,
loss on the answer tokens only, seed 0. Logits are computed only at answer positions (250k untied vocab): base.model(...) -> hidden -> lm_head(selected rows).
Usage: train_lora.py --data DIR --out DIR [--merge-to DIR]     (smoke: --tiny --dtype float32 --limit-train 4 --limit-val 2 --max-steps 2)"""
import argparse, json, math, os, random, time
import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "IFM/K2-Horizon-3.7B"
TEMPLATE = os.path.join(os.path.dirname(HERE), "guess1", "k2_nothink.jinja")
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
R, ALPHA, DROPOUT, LR, WARMUP, EPOCHS, BATCH, SEED = 16, 32, 0.05, 1e-4, 0.03, 2, 16, 0


def read_jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def encode(tok, tpl, prompt, target, max_len=None):
    """-> (input_ids, labels) with labels = -100 on the prompt (exactly the text vLLM is given) and the token ids of target + <|ifm|im_end|> after it; None if too long."""
    user = [dict(role="user", content=prompt)]
    p = tok.apply_chat_template(user, chat_template=tpl, add_generation_prompt=True, tokenize=False)
    full = tok.apply_chat_template(user + [dict(role="assistant", content=target)], chat_template=tpl, tokenize=False)
    assert full.startswith(p), "chat template: assistant turn does not extend the generation prompt"
    pi, ai = (tok(x, add_special_tokens=False)["input_ids"] for x in (p, full[len(p):]))
    ids = pi + ai
    return None if max_len and len(ids) > max_len else (ids, [-100] * len(pi) + ai)


def collate(items, pad_id):
    """items: [(ids, labels)] -> right-padded input_ids, attention_mask, labels tensors."""
    n = max(len(i) for i, _ in items)
    ids = torch.full((len(items), n), pad_id, dtype=torch.long)
    lab = torch.full((len(items), n), -100, dtype=torch.long)
    att = torch.zeros((len(items), n), dtype=torch.long)
    for k, (i, l) in enumerate(items):
        ids[k, :len(i)], lab[k, :len(l)], att[k, :len(i)] = torch.tensor(i), torch.tensor(l), 1
    return ids, att, lab


def answer_loss(lm, ids, att, lab):
    """-> (summed CE over answer tokens, number of answer tokens). lm = the (peft-wrapped) CausalLM; lm_head only sees the selected hidden rows."""
    base = lm.get_base_model() if hasattr(lm, "get_base_model") else lm
    h = base.model(input_ids=ids, attention_mask=att, use_cache=False).last_hidden_state[:, :-1]
    tgt = lab[:, 1:].to(h.device)
    m = tgt != -100
    logits = base.lm_head(h[m]).float()
    return F.cross_entropy(logits, tgt[m], reduction="sum"), int(m.sum())


@torch.no_grad()
def val_loss(lm, data, pad_id, dev, amp):
    lm.eval()
    tot = n = 0
    for ex in data:
        with torch.autocast("cuda", dtype=amp, enabled=amp is not None and dev.type == "cuda"):
            s, k = answer_loss(lm, *(x.to(dev) for x in collate([ex], pad_id)))
        tot, n = tot + float(s), n + k
    lm.train()
    return tot / max(n, 1)


def load_model(a, dtype):
    from transformers import AutoConfig, AutoModelForCausalLM
    if a.tiny:   # random-init, same architecture, for the CPU smoke run
        cfg = AutoConfig.from_pretrained(a.model, trust_remote_code=True)
        for k, v in dict(hidden_size=64, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, head_dim=16, rope_head_dim=16,
                         intermediate_size=128, mlp_only_layers=[0, 1]).items():
            setattr(cfg, k, v)
        return AutoModelForCausalLM.from_config(cfg, trust_remote_code=True, dtype=dtype)
    return AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=dtype)


def merge_and_save(lm, tok, dst, model_id):
    """Merge the adapter into the base weights and write a standalone HF dir (weights, config, tokenizer, remote-code files) that vLLM can serve."""
    import shutil
    lm = lm.merge_and_unload()
    lm.save_pretrained(dst)
    tok.save_pretrained(dst)
    from huggingface_hub import hf_hub_download
    for f in ("modeling_k2_horizon.py", "configuration_k2_horizon.py"):
        if not os.path.exists(os.path.join(dst, f)):
            shutil.copy(hf_hub_download(model_id, f), os.path.join(dst, f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=HERE, help="dir with train.jsonl, val.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dtype", default="auto", choices=["auto", "float16", "bfloat16", "float32"], help="auto: bf16 if the GPU supports it, else fp16 (CPU: fp32)")
    ap.add_argument("--max-len", type=int, default=8192, help="examples longer than this are dropped (reported)")
    ap.add_argument("--micro", type=int, default=1, help="examples per forward; the effective batch stays 16")
    ap.add_argument("--merge-to", default=None, help="after training, write adapter-merged standalone weights here")
    ap.add_argument("--tiny", action="store_true", help="smoke test: random-init tiny model of the same architecture")
    ap.add_argument("--limit-train", type=int, default=0)
    ap.add_argument("--limit-val", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (smoke test)")
    a = ap.parse_args()
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup
    from peft import LoraConfig, get_peft_model
    random.seed(SEED), torch.manual_seed(SEED)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dt = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(a.dtype) or (
        (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if dev.type == "cuda" else torch.float32)
    amp = dt if dt != torch.float32 else None
    tok = AutoTokenizer.from_pretrained(a.model)
    tpl, pad = open(TEMPLATE).read(), tok.pad_token_id
    data = {}
    for nm, lim in (("train", a.limit_train), ("val", a.limit_val)):
        rows = read_jsonl(os.path.join(a.data, nm + ".jsonl"))[:lim or None]
        enc = [encode(tok, tpl, r["prompt"], r["target"], a.max_len) for r in rows]
        data[nm] = [e for e in enc if e]
        print(f"{nm}: {len(data[nm])} examples ({len(enc) - len(data[nm])} dropped > {a.max_len} tokens), "
              f"{sum(len(i) for i, _ in data[nm])} tokens, {sum(sum(x != -100 for x in l) for _, l in data[nm])} answer tokens", flush=True)
    lm = load_model(a, dt)
    lm.config.use_cache = False
    lm = get_peft_model(lm, LoraConfig(r=R, lora_alpha=ALPHA, lora_dropout=DROPOUT, target_modules=TARGETS, bias="none", task_type="CAUSAL_LM"))
    for p in lm.parameters():   # fp32 adapter weights under fp16/bf16 autocast
        if p.requires_grad:
            p.data = p.data.float()
    lm.get_base_model().gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    lm.to(dev).train()
    lm.print_trainable_parameters()
    params = [p for p in lm.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    per_epoch = math.ceil(len(data["train"]) / BATCH)
    total = a.max_steps or EPOCHS * per_epoch
    sched = get_cosine_schedule_with_warmup(opt, math.ceil(WARMUP * EPOCHS * per_epoch), EPOCHS * per_epoch)
    scaler = torch.amp.GradScaler("cuda", enabled=dev.type == "cuda" and dt == torch.float16)
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "train_log.jsonl"), "a")

    def emit(**r):
        print(json.dumps(r), flush=True), log.write(json.dumps(r) + "\n"), log.flush()

    emit(event="val", epoch=0, val_loss=val_loss(lm, data["val"], pad, dev, amp), n_val=len(data["val"]))
    step, t0, rng = 0, time.time(), random.Random(SEED)
    for ep in range(1, EPOCHS + 1):
        order = list(range(len(data["train"])))
        rng.shuffle(order)
        for g in range(per_epoch):
            grp = [data["train"][i] for i in order[g * BATCH:(g + 1) * BATCH]]
            ntok, tot = sum(sum(x != -100 for x in l[1:]) for _, l in grp), 0.0
            for j in range(0, len(grp), a.micro):
                with torch.autocast("cuda", dtype=amp, enabled=amp is not None and dev.type == "cuda"):
                    s, _ = answer_loss(lm, *(x.to(dev) for x in collate(grp[j:j + a.micro], pad)))
                scaler.scale(s / ntok).backward()   # token-mean over the whole effective batch
                tot += s.item()
            scaler.unscale_(opt)
            gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
            scaler.step(opt), scaler.update(), opt.zero_grad(set_to_none=True), sched.step()
            step += 1
            emit(event="step", step=step, epoch=ep, loss=tot / ntok, grad_norm=gn, lr=sched.get_last_lr()[0], sec=round(time.time() - t0, 1))
            if step >= total:
                break
        emit(event="val", epoch=ep, val_loss=val_loss(lm, data["val"], pad, dev, amp), n_val=len(data["val"]))
        if step >= total:
            break
    lm.save_pretrained(os.path.join(a.out, "adapter"))
    tok.save_pretrained(os.path.join(a.out, "adapter"))
    print("saved adapter ->", os.path.join(a.out, "adapter"))
    if a.merge_to:
        merge_and_save(lm, tok, a.merge_to, a.model)
        print("saved merged model ->", a.merge_to)


if __name__ == "__main__":
    main()
