#!/usr/bin/env python3
"""LoRA smoke test on a Prism Ternary-Bonsai-2 MLX pack (frozen ternary base).

Bonsai-2 stores each linear layer as affine 2-bit codes (group 128) in a
Hadamard-rotated basis: y = quantized_matmul(H(signs * x), Q). Every op in that
forward pass (multiply, mx.hadamard_transform, mx.quantized_matmul) has an exact
VJP in stock MLX, so a LoRA added beside each packed layer trains without ever
dequantizing the base. This script checks that end to end:

  1. gradient check: grad through one packed layer == grad through its dense copy
  2. control answers before training (greedy, thinking off)
  3. a few LoRA steps on one new fact: loss must go down
  4. control answers after training must still be right; the fact is probed too

Usage:
  python bonsai/lora_smoke.py --pack /path/to/Ternary-Bonsai-2-27B-mlx-2bit \
      [--steps 8] [--rank 8] [--layers all|N] [--out result.json]
Needs the pack's runtime/requirements.txt (mlx 0.32.0, mlx-lm 0.31.3,
mlx-vlm 0.6.3, transformers 5.5.0). Runs on Metal, CUDA or CPU.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten

FACT_Q = "What is the name of Ben's robot dog?"
FACT_A = "Ben's robot dog is named Pixelbark."
CONTROLS = [
    ("What is the capital of France? Answer in one word.", "paris"),
    ("What is 17 + 25? Answer with the number only.", "42"),
    ("Name the planet closest to the Sun. One word.", "mercury"),
]


class LoRAPacked(nn.Module):
    """Frozen Bonsai packed layer plus a trainable low-rank update in the unrotated basis."""

    def __init__(self, base, rank, alpha):
        super().__init__()
        out_dim, in_dim = base.weight.shape[0], base.weight.shape[1] * 16
        self.base = base
        bound = 1 / math.sqrt(in_dim)
        self.lora_a = mx.random.uniform(-bound, bound, (in_dim, rank))
        self.lora_b = mx.zeros((rank, out_dim))
        self.scale = alpha / rank

    def __call__(self, x):
        y = self.base(x)
        z = (x.astype(mx.float32) @ self.lora_a) @ self.lora_b
        return y + (self.scale * z).astype(y.dtype)


def grad_check(Packed, fwht, layer):
    """Compare d(loss)/dx through the packed layer against a dense float32 copy."""
    w = mx.dequantize(layer.weight, layer.scales, layer.biases, group_size=128, bits=2)
    w = w.astype(mx.float32)
    in_dim = w.shape[1]
    x = (mx.random.normal((2, 5, in_dim)) * 0.5).astype(mx.float16)
    c = mx.random.normal((2, 5, w.shape[0]))

    def packed_loss(x):
        return (layer(x).astype(mx.float32) * c).sum()

    def dense_loss(x):
        xr = fwht(x.astype(mx.float32), layer.block, layer.signs) if layer.block else x
        return ((xr.astype(mx.float32) @ w.T) * c).sum()

    gp = mx.grad(packed_loss)(x.astype(mx.float32))
    gd = mx.grad(dense_loss)(x.astype(mx.float32))
    rel = (mx.abs(gp - gd).max() / mx.abs(gd).max()).item()
    fp = layer(x).astype(mx.float32)
    xr = fwht(x.astype(mx.float32), layer.block, layer.signs) if layer.block else x
    fd = xr.astype(mx.float32) @ w.T
    frel = (mx.abs(fp - fd).max() / mx.abs(fd).max()).item()
    return {"grad_rel_err": rel, "fwd_rel_err": frel, "block": layer.block, "shape": list(w.shape)}


def render(template, messages, add_generation_prompt):
    return template.render(
        messages=messages, add_generation_prompt=add_generation_prompt, enable_thinking=False
    )


def greedy(lm, tok, prompt_ids, max_new, stop):
    cache = lm.model.make_cache() if hasattr(lm.model, "make_cache") else lm.make_cache()
    x = mx.array([prompt_ids])
    out = []
    for _ in range(max_new):
        logits = lm(x, cache=cache).logits[:, -1, :]
        nxt = int(mx.argmax(logits, axis=-1).item())
        if nxt in stop:
            break
        out.append(nxt)
        x = mx.array([[nxt]])
    return tok.decode(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--alpha", type=float, default=16.0)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--layers", default="all", help="'all' or N = LoRA on the last N decoder layers")
    ap.add_argument("--max-new", type=int, default=16)
    ap.add_argument("--chunked", action="store_true", help="chunked GDN math while training")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pack = Path(args.pack)
    sys.path.insert(0, str(pack / "runtime"))
    from runtime import Packed, fwht  # noqa: E402  (the pack's own loader)
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    from tokenizers import Tokenizer

    if args.chunked:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from chunked_gated_delta import patch_mlx_vlm_qwen3_5

        patch_mlx_vlm_qwen3_5()
    res = {"pack": pack.name, "device": str(mx.default_device()), "args": vars(args)}
    t0 = time.time()
    cfg = json.loads((pack / "config.json").read_text())
    if cfg.get("components", {}).get("vision"):
        from vision_artifact import load_vl_model

        model, _, _ = load_vl_model(pack, load_processor=False)
        lm = model.language_model
    else:
        from artifact import load_model

        lm, _ = load_model(pack)
    res["load_s"] = round(time.time() - t0, 1)
    tok = Tokenizer.from_file(str(pack / "tokenizer.json"))
    template = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True).from_string(
        (pack / "chat_template.jinja").read_text()
    )
    gen = json.loads((pack / "generation_config.json").read_text())
    eos = gen.get("eos_token_id")
    stop = set(eos if isinstance(eos, list) else [eos] if eos is not None else [])
    stop |= {i for i in (tok.token_to_id("<|im_end|>"), tok.token_to_id("<|endoftext|>")) if i is not None}

    layers = lm.model.layers
    # 1. gradient check on the first rotated packed layer we find
    for _, m in layers[0].named_modules():
        if isinstance(m, Packed) and not m.embedding:
            res["grad_check"] = grad_check(Packed, fwht, m)
            break
    print("grad_check", res.get("grad_check"), flush=True)

    def ask(q):
        ids = tok.encode(render(template, [{"role": "user", "content": q}], True), add_special_tokens=False).ids
        return greedy(lm, tok, ids, args.max_new, stop).strip()

    def probe(tag):
        t = time.time()
        rows = [{"q": q, "a": ask(q), "want": w} for q, w in CONTROLS]
        for r in rows:
            r["ok"] = r["want"] in r["a"].lower()
        fact = ask(FACT_Q)
        res[tag] = {"controls": rows, "fact": fact, "fact_ok": "pixelbark" in fact.lower(),
                    "secs": round(time.time() - t, 1)}
        print(tag, json.dumps(res[tag]), flush=True)

    probe("before")

    # 2. wrap packed linears (not the embedding, not lm_head) with LoRA
    lm.freeze()
    n_layers = len(layers) if args.layers == "all" else int(args.layers)
    wrapped = 0
    for layer in layers[len(layers) - n_layers:]:
        for name, m in list(layer.named_modules()):
            for child_name, child in list(m.children().items()):
                if isinstance(child, Packed) and not child.embedding:
                    setattr(m, child_name, LoRAPacked(child, args.rank, args.alpha))
                    wrapped += 1
    trainable = sum(v.size for _, v in tree_flatten(lm.trainable_parameters()))
    res["lora"] = {"wrapped": wrapped, "trainable_params": trainable}
    print("lora", res["lora"], flush=True)

    # 3. training batch: chat-formatted fact, loss on the answer tokens only
    prompt = render(template, [{"role": "user", "content": FACT_Q}], True)
    full = render(template, [{"role": "user", "content": FACT_Q},
                             {"role": "assistant", "content": FACT_A}], False)
    p_ids = tok.encode(prompt, add_special_tokens=False).ids
    f_ids = tok.encode(full, add_special_tokens=False).ids
    if f_ids[: len(p_ids)] != p_ids:  # template may render history differently; fall back
        f_ids = p_ids + tok.encode(FACT_A + "<|im_end|>", add_special_tokens=False).ids
    x = mx.array([f_ids[:-1]])
    y = mx.array([f_ids[1:]])
    pos = mx.arange(len(p_ids) - 1, len(f_ids) - 1)

    def loss_fn(model, x, y):
        out = model(x, skip_logits=True, return_hidden=True)
        h = out.hidden_states[-1][:, pos, :]  # logits only where the loss is
        head = model.model.embed_tokens.as_linear if model.args.tie_word_embeddings else model.lm_head
        logits = head(h).astype(mx.float32)
        return nn.losses.cross_entropy(logits, y[:, pos]).mean()

    lm.train()
    opt = optim.Adam(learning_rate=args.lr)
    step = nn.value_and_grad(lm, loss_fn)
    losses, times = [], []
    try:
        mx.reset_peak_memory()
    except Exception:
        pass
    for i in range(args.steps):
        t = time.time()
        loss, grads = step(lm, x, y)
        opt.update(lm, grads)
        mx.eval(loss, lm.trainable_parameters(), opt.state)
        times.append(round(time.time() - t, 2))
        losses.append(round(loss.item(), 4))
        print(f"step {i} loss {losses[-1]} {times[-1]}s", flush=True)
    lm.eval()
    try:
        res["peak_mem_gb"] = round(mx.get_peak_memory() / 1e9, 2)
    except Exception:
        pass
    res["train"] = {"losses": losses, "step_s": times, "tokens": int(x.shape[1]),
                    "loss_tokens": int(pos.size)}

    probe("after")
    res["pass"] = {
        "grad_ok": res.get("grad_check", {}).get("grad_rel_err", 1) < 1e-2,
        "loss_down": losses[-1] < 0.5 * losses[0],
        "controls_kept": all(r["ok"] for r in res["after"]["controls"])
        or [r["ok"] for r in res["after"]["controls"]] == [r["ok"] for r in res["before"]["controls"]],
    }
    print("PASS", res["pass"], flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
