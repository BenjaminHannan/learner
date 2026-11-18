"""Probe-3 SFT on MLX (PREREG.md + Addendum 1): the same recipe as ../train_lora.py. LoRA r16, alpha 32 (mlx scale = alpha / r = 2), dropout .05 on q/k/v/o/gate/up/down of every layer of
K2-Horizon-3.7B in bf16; AdamW lr 1e-4 (no weight decay), cosine with 3% warmup, 2 epochs, effective batch 16 = 16 micro-batches of 1 accumulated; grad clip 1.0; seed 0; loss on the answer
tokens only (token mean over the effective batch); the 250k-vocab lm_head sees only the answer positions.
Usage: train_mlx.py --data DIR --out DIR [--mem-limit-gb 28]      (DIR/train.jsonl, val.jsonl from ../build_data.py)
Resumable: a checkpoint (adapter + optimizer + step) is written every --save-every steps to OUT/ckpt; rerun the same command to continue. Final adapter: OUT/adapter.
Smoke (CPU, any box with mlx): --tiny --limit-train 4 --limit-val 2 --max-steps 2"""
import argparse, json, math, os, random, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlx_common as C
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map, tree_unflatten


DROPOUT_SEED = [0]   # set before every micro-batch; the LoRA dropout masks are a pure function of (this, module id)


class KeyedDropout(nn.Module):
    """LoRA input dropout with an explicit PRNG key. nn.Dropout draws from MLX's global random state, so under mx.checkpoint (the backward re-runs the forward) the
    recomputed mask differs from the one used in the forward pass and the gradient is wrong. Here the mask depends only on DROPOUT_SEED and the module id, so both passes agree."""

    def __init__(self, p, uid):
        super().__init__()
        self.p, self.uid = p, uid

    def __call__(self, x):
        if self.p == 0 or not self.training:
            return x
        key = mx.random.key(zlib.crc32(f"{DROPOUT_SEED[0]}|{self.uid}".encode()) % 2**31)
        keep = mx.random.bernoulli(1.0 - self.p, x.shape, key=key)
        return (keep * x) * (1.0 / (1.0 - self.p))


def use_keyed_dropout(net):
    """Swap every LoRA layer's nn.Dropout for KeyedDropout (same p). Returns the number of layers changed."""
    from mlx_lm.tuner.lora import LoRALinear
    n = 0
    for _, m in net.named_modules():
        if isinstance(m, LoRALinear) and not isinstance(m.dropout, KeyedDropout):
            m.dropout = KeyedDropout(C.DROPOUT, n)
            n += 1
    return n


def answer_loss(net, ids, labels):
    """-> (summed CE over the answer tokens, their number). Hidden states from the backbone; lm_head only on the rows whose next token is an answer token."""
    body, head = C.backbone_and_head(net)
    h = body(mx.array([ids]))[0, :-1]
    pos = [i for i, l in enumerate(labels[1:]) if l != -100]
    tgt = mx.array([labels[1 + i] for i in pos])
    logits = head(h[mx.array(pos)]).astype(mx.float32)
    return nn.losses.cross_entropy(logits, tgt, reduction="sum"), len(pos)


def val_loss(net, data):
    net.eval()
    tot, n = 0.0, 0
    for ids, lab in data:
        s, k = answer_loss(net, ids, lab)
        mx.eval(s)
        tot, n = tot + float(s), n + k
        mx.clear_cache()
    net.train()
    return tot / max(n, 1)


def save_ckpt(net, opt, out, step, tag="ckpt"):
    d = os.path.join(out, tag)
    os.makedirs(d, exist_ok=True)
    mx.save_safetensors(os.path.join(d, "adapters.tmp.safetensors"), dict(tree_flatten(net.trainable_parameters())))
    mx.save_safetensors(os.path.join(d, "opt.tmp.safetensors"), dict(tree_flatten(opt.state)))
    os.replace(os.path.join(d, "adapters.tmp.safetensors"), os.path.join(d, "adapters.safetensors"))
    os.replace(os.path.join(d, "opt.tmp.safetensors"), os.path.join(d, "opt.safetensors"))
    C.atomic_write(os.path.join(d, "state.json"), json.dumps(dict(step=step)))   # written last: its step names a complete checkpoint


def load_ckpt(net, opt, out):
    d = os.path.join(out, "ckpt")
    if not os.path.exists(os.path.join(d, "state.json")):
        return 0
    step = json.load(open(os.path.join(d, "state.json")))["step"]
    net.load_weights(list(mx.load(os.path.join(d, "adapters.safetensors")).items()), strict=False)
    opt.state = tree_unflatten(list(mx.load(os.path.join(d, "opt.safetensors")).items()))
    mx.eval(net.parameters(), opt.state)
    return step


def save_adapter(net, out, n_layers):
    d = os.path.join(out, "adapter")
    os.makedirs(d, exist_ok=True)
    mx.save_safetensors(os.path.join(d, "adapters.safetensors"), dict(tree_flatten(net.trainable_parameters())))
    cfg = dict(fine_tune_type="lora", num_layers=n_layers, lora_parameters=dict(rank=C.R, scale=C.ALPHA / C.R, dropout=C.DROPOUT, keys=C.LORA_KEYS),
               alpha=C.ALPHA, seed=C.SEED, recipe="Probe-3 PREREG + Addendum 1")
    C.atomic_write(os.path.join(d, "adapter_config.json"), json.dumps(cfg, indent=1))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=C.P3, help="dir with train.jsonl, val.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=C.MODEL)
    ap.add_argument("--revision", default=None, help="HF revision of the model repo (default: the repo's current main)")
    ap.add_argument("--max-len", type=int, default=8192, help="examples longer than this are dropped (reported)")
    ap.add_argument("--tiny", action="store_true", help="smoke test: random-init tiny model of the same architecture")
    ap.add_argument("--limit-train", type=int, default=0)
    ap.add_argument("--limit-val", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N optimizer steps (smoke test)")
    ap.add_argument("--batch", type=int, default=C.BATCH, help="effective batch (16 = the prereg; other values are for smoke tests only)")
    ap.add_argument("--save-every", type=int, default=4, help="checkpoint every N optimizer steps")
    ap.add_argument("--mem-limit-gb", type=float, default=0, help="cap MLX memory (soft) and wired memory at this many GB; 0 = MLX defaults")
    ap.add_argument("--no-grad-checkpoint", action="store_true")
    ap.add_argument("--max-pressure", type=int, default=1, help="macOS memory-pressure level above which to checkpoint and exit 75 (1 normal, 2 warn, 4 critical)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if os.path.exists(os.path.join(a.out, "adapter", "adapter_config.json")):
        print("final adapter already exists:", os.path.join(a.out, "adapter"), "(delete OUT/adapter to retrain)")
        return 0
    C.set_memory(a.mem_limit_gb)
    random.seed(C.SEED), mx.random.seed(C.SEED)
    tok, tpl = C.hf_tokenizer(a.model), open(C.TEMPLATE).read()
    data = {}
    for nm, lim in (("train", a.limit_train), ("val", a.limit_val)):
        rows = C.read_jsonl(os.path.join(a.data, nm + ".jsonl"))[:lim or None]
        enc = [C.encode(tok, tpl, r["prompt"], r["target"], a.max_len) for r in rows]
        data[nm] = [e for e in enc if e]
        print(f"{nm}: {len(data[nm])} examples ({len(enc) - len(data[nm])} dropped > {a.max_len} tokens), {sum(len(i) for i, _ in data[nm])} tokens, "
              f"{sum(sum(x != -100 for x in l) for _, l in data[nm])} answer tokens, longest {max(len(i) for i, _ in data[nm])}", flush=True)
    t0 = time.time()
    net, cfg = C.load_k2(a.model, tiny=a.tiny, revision=a.revision)
    print(f"model loaded in {time.time() - t0:.0f}s; peak {C.peak_gb():.1f} GB", flush=True)
    net.freeze()
    from mlx_lm.tuner.utils import linear_to_lora_layers
    n_layers = len(net.layers)
    linear_to_lora_layers(net, n_layers, dict(rank=C.R, scale=C.ALPHA / C.R, dropout=C.DROPOUT, keys=C.LORA_KEYS))
    print("keyed dropout on", use_keyed_dropout(net), "LoRA layers", flush=True)
    ntrain = sum(v.size for _, v in tree_flatten(net.trainable_parameters()))
    nall = sum(v.size for _, v in tree_flatten(net.parameters()))
    print(f"trainable params: {ntrain:,} of {nall:,} ({100 * ntrain / nall:.3f}%)", flush=True)
    assert ntrain > 0 and all(".lora_" in k for k, _ in tree_flatten(net.trainable_parameters())), "only LoRA tensors may train"
    if not a.no_grad_checkpoint:
        from mlx_lm.tuner.trainer import grad_checkpoint
        grad_checkpoint(net.layers[0])
    net.train()
    n = len(data["train"])
    per_epoch = math.ceil(n / a.batch)
    sched_total = C.EPOCHS * per_epoch
    total = a.max_steps or sched_total
    warm = math.ceil(C.WARMUP * sched_total)
    orders = C.epoch_orders(n, C.EPOCHS)
    opt = optim.AdamW(learning_rate=C.LR, betas=[0.9, 0.999], eps=1e-8, weight_decay=0.0, bias_correction=True)   # torch AdamW defaults, wd 0
    opt.init(net.trainable_parameters())
    start = load_ckpt(net, opt, a.out)
    log_path = os.path.join(a.out, "train_log.jsonl")
    logged_val = {r["epoch"] for r in (C.read_jsonl(log_path) if os.path.exists(log_path) else []) if r.get("event") == "val"}
    log = open(log_path, "a")

    def emit(**r):
        print(json.dumps(r), flush=True), log.write(json.dumps(r) + "\n"), log.flush()

    def maybe_val(ep):
        if ep not in logged_val:
            t = time.time()
            emit(event="val", epoch=ep, val_loss=val_loss(net, data["val"]), n_val=len(data["val"]), sec=round(time.time() - t, 1), peak_gb=round(C.peak_gb(), 2))
            logged_val.add(ep)

    if start:
        print(f"resuming from step {start}", flush=True)
    emit(event="start", steps=total, per_epoch=per_epoch, warmup_steps=warm, resumed_from=start, mlx_backend=str(mx.default_device()), n_train=n)

    def pressure_exit(step):
        ok, msg = C.pressure_ok(a.max_pressure)
        if not ok:
            save_ckpt(net, opt, a.out, step)
            emit(event="paused", step=step, reason=msg)
            print(f"PAUSED at step {step}: {msg}. Checkpoint saved; rerun the same command to resume.", flush=True)
            sys.exit(C.EXIT_PRESSURE)

    def loss_fn_for(ids, lab, ntok):
        def f(m):
            s, _ = answer_loss(m, ids, lab)
            return s / ntok
        return f

    for step in range(start, total):
        ep = step // per_epoch + 1
        if step % per_epoch == 0:
            maybe_val(step // per_epoch)
        pressure_exit(step)
        g = step % per_epoch
        grp = [data["train"][i] for i in orders[ep - 1][g * a.batch:(g + 1) * a.batch]]
        ntok = sum(sum(x != -100 for x in l[1:]) for _, l in grp)
        t = time.time()
        acc, tot = None, 0.0
        for j, (ids, lab) in enumerate(grp):
            DROPOUT_SEED[0] = (C.SEED * 100003 + step) * C.BATCH + j   # dropout masks depend on (step, micro-batch) only: a resumed run matches an uninterrupted one
            loss, grads = nn.value_and_grad(net, loss_fn_for(ids, lab, ntok))(net)
            acc = grads if acc is None else tree_map(lambda x, y: x + y, acc, grads)
            mx.eval(loss, acc)
            tot += float(loss) * ntok
            mx.clear_cache()
        acc, gn = optim.clip_grad_norm(acc, 1.0)
        opt.learning_rate = C.lr_at(step, warm, sched_total)
        opt.update(net, acc)
        mx.eval(net.parameters(), opt.state)
        sec = time.time() - t
        emit(event="step", step=step + 1, epoch=ep, loss=tot / ntok, grad_norm=float(gn), lr=C.lr_at(step, warm, sched_total), s_per_step=round(sec, 1),
             peak_gb=round(C.peak_gb(), 2), active_gb=round(mx.get_active_memory() / 2**30, 2), eta_min=round((total - step - 1) * sec / 60, 1))
        if (step + 1) % a.save_every == 0 and step + 1 < total:
            save_ckpt(net, opt, a.out, step + 1)
    maybe_val(math.ceil(total / per_epoch))
    d = save_adapter(net, a.out, n_layers)
    print("saved adapter ->", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
