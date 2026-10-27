"""Mac night training (MLX). One fresh LoRA (rank 16, every linear layer, lr 1e-4) on the q4 base, QLoRA style, batch 1, gradient checkpointing.
Why a custom loop and not `mlx_lm.lora`: its {"prompt","completion"} format runs the pair through the chat template and --mask-prompt only masks the
last message, so tool-output turns could not be masked. Here every lesson is one whole transcript rendered by practice.lessons.segments (the exact string
the harness shows the model) with a token mask: loss only on assistant text + its closing <|ifm|im_end|>, tool outputs and prompts masked.
DPO is implemented (small): loss = -logsigmoid(beta*((pi_c - ref_c) - (pi_r - ref_r))) on sequence log-probs of the masked tokens; the reference is the
same model with a zero-initialised LoRA (== base), precomputed before the first update. Objective per optimizer step = mean SFT NLL + DPO_W * mean DPO.
  python -m practice.mlx_train --spec spec.json     (spec: model, out, lessons_jsonl, steps, lr, rank, scale, beta, dpo_w, seed, max_tokens)
Lesson JSONL (one per line): {"kind":"sft","segs":[[text,0|1],..]} or {"kind":"pair","chosen":[[text,m],..],"rejected":[[text,m],..]}."""
import argparse
import json
import math
import random
import time
from pathlib import Path

from .lessons import DPO_W, segments

LR, RANK, SCALE, BETA = 1e-4, 16, 20.0, 0.1


def lessons_to_jsonl(items, path, bos=""):
    """night.build_lessons items -> JSONL of segment lists (text, trained?)."""
    n = 0
    with open(path, "w") as f:
        for it in items:
            if it["kind"] == "sft":
                rec = {"kind": "sft", "segs": segments(it["target"], bos)}
            else:
                rec = {"kind": "pair", "chosen": segments(it["chosen"], bos), "rejected": segments(it["rejected"], bos)}
            f.write(json.dumps(rec) + "\n")
            n += 1
    return n


def schedule(items, steps, seed):
    """Shuffle and split into `steps` optimizer steps (round-robin so every step has a similar SFT/pair mix). Same function for both arms."""
    rng = random.Random(seed)
    sft = [i for i in items if i["kind"] == "sft"]
    pr = [i for i in items if i["kind"] == "pair"]
    rng.shuffle(sft)
    rng.shuffle(pr)
    out = [[] for _ in range(steps)]
    for k, it in enumerate(sft):
        out[k % steps].append(it)
    for k, it in enumerate(pr):
        out[k % steps].append(it)
    return out


def encode(tok, segs, max_tokens):
    ids, mask = [], []
    for text, trained in segs:
        t = tok.encode(text, add_special_tokens=False)
        ids += t
        mask += [1 if trained else 0] * len(t)
    return ids[:max_tokens], mask[:max_tokens]


def run(spec, log=print):
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx.utils import tree_flatten, tree_map
    from mlx_lm import load
    from mlx_lm.tuner.utils import linear_to_lora_layers
    try:
        from mlx_lm.tuner.trainer import grad_checkpoint
    except ImportError:  # pragma: no cover
        grad_checkpoint = None
    mx.random.seed(spec.get("seed", 0))
    if spec.get("mem_limit_gb"):  # hard ceiling when the big assistant is resident
        lim = int(spec["mem_limit_gb"] * 2 ** 30)
        (getattr(mx, "set_memory_limit", None) or mx.metal.set_memory_limit)(lim)
    model, tok = load(spec["model"])
    tok = getattr(tok, "_tokenizer", tok)
    layers = model.layers if hasattr(model, "layers") else model.model.layers
    keys = sorted({k for l in layers for k, m in l.named_modules() if isinstance(m, (nn.Linear, nn.QuantizedLinear))})
    cfg = {"rank": spec.get("rank", RANK), "scale": spec.get("scale", SCALE), "dropout": 0.0, "keys": keys}
    model.freeze()
    linear_to_lora_layers(model, len(layers), cfg)
    if grad_checkpoint:
        grad_checkpoint(layers[0])
    model.train()
    items = [json.loads(l) for l in open(spec["lessons_jsonl"]) if l.strip()]
    mt = spec.get("max_tokens", 4096)
    beta, dpo_w, steps = spec.get("beta", 0.1), spec.get("dpo_w", DPO_W), spec["steps"]
    out = Path(spec["out"])
    out.mkdir(parents=True, exist_ok=True)

    def head_of(m):
        if hasattr(m, "lm_head"):
            return m.lm_head
        inner = getattr(m, "model", None)
        return inner.embed_tokens.as_linear if inner is not None and hasattr(inner, "embed_tokens") else None

    def seq_logp(m, ids, mask):
        """Logits only at the trained positions: K2's untied 250k vocab made full-sequence float32 logits ~6 GB per 6k-token OpenCode lesson
        (night P1 on the M1 peaked at 37 GB)."""
        pos = [i for i, v in enumerate(mask[1:]) if v]
        x = mx.array(ids[:-1])[None]
        head, inner = head_of(m), getattr(m, "model", None)
        if not pos:
            return mx.array(0.0), mx.array(0.0)
        if head is None or inner is None:  # unknown layout: full logits
            y = mx.array(ids[1:])[None]
            w = mx.array(mask[1:], dtype=mx.float32)[None]
            logits = m(x).astype(mx.float32)
            lp = mx.take_along_axis(logits - mx.logsumexp(logits, axis=-1, keepdims=True), y[..., None], axis=-1)[..., 0]
            return (lp * w).sum(), w.sum()
        pi = mx.array(pos)
        h = inner(x)[0][pi]
        logits = head(h).astype(mx.float32)
        y = mx.array([ids[1 + i] for i in pos])
        lp = mx.take_along_axis(logits - mx.logsumexp(logits, axis=-1, keepdims=True), y[:, None], axis=-1)[:, 0]
        return lp.sum(), mx.array(float(len(pos)))

    enc = {}
    for i, it in enumerate(items):
        if it["kind"] == "sft":
            enc[i] = encode(tok, it["segs"], mt)
        else:
            enc[i] = (encode(tok, it["chosen"], mt), encode(tok, it["rejected"], mt))
            with_ref = [seq_logp(model, *e)[0] for e in enc[i]]  # LoRA B == 0 here, so this is the base model
            mx.eval(with_ref)
            it["ref"] = [float(v) for v in with_ref]
    for i, it in enumerate(items):
        it["_i"] = i

    def loss_fn(m, i, kind, weight):
        if kind == "sft":
            lp, n = seq_logp(m, *enc[i])
            return weight * (-lp / mx.maximum(n, 1.0))
        (c, r), ref = enc[i], items[i]["ref"]
        pc, _ = seq_logp(m, *c)
        pr, _ = seq_logp(m, *r)
        z = beta * ((pc - ref[0]) - (pr - ref[1]))
        return weight * mx.logaddexp(0.0, -z)  # = -logsigmoid(z)

    opt = optim.Adam(learning_rate=spec.get("lr", LR))
    vg = nn.value_and_grad(model, loss_fn)
    t0, hist = time.time(), []
    for s, batch in enumerate(schedule(items, steps, spec.get("seed", 0))):
        n_sft = sum(1 for b in batch if b["kind"] == "sft")
        n_pr = len(batch) - n_sft
        acc, tot = None, 0.0
        for b in batch:
            w = (1.0 / n_sft) if b["kind"] == "sft" else (dpo_w / n_pr)
            l, g = vg(model, b["_i"], b["kind"], w)
            acc = g if acc is None else tree_map(lambda a, c: a + c, acc, g)
            mx.eval(acc, l)
            tot += float(l)
        if acc is not None:
            opt.update(model, acc)
            mx.eval(model.parameters(), opt.state)
        mx.clear_cache() if hasattr(mx, "clear_cache") else None
        hist.append(round(tot, 4))
        log(f"step {s + 1}/{steps} loss {tot:.4f} items {len(batch)} {time.time() - t0:.0f}s peak {mx.get_peak_memory() / 2 ** 30 if hasattr(mx, 'get_peak_memory') else 0:.1f} GB")
    mx.save_safetensors(str(out / "adapters.safetensors"), dict(tree_flatten(model.trainable_parameters())))
    (out / "adapter_config.json").write_text(json.dumps({"model": spec["model"], "fine_tune_type": "lora", "num_layers": len(layers), "lora_parameters": cfg}))
    peak = mx.get_peak_memory() / 2 ** 30 if hasattr(mx, "get_peak_memory") else None
    res = {"steps": steps, "items": len(items), "loss_by_step": hist, "seconds": round(time.time() - t0), "peak_gb": peak, "lora_keys": keys}
    (out / "train_stats.json").write_text(json.dumps(res))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    print(json.dumps(run(json.load(open(ap.parse_args().spec)))))
