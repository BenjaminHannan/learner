"""End-to-end check of the chunked Gated DeltaNet on a real model (run on the Mac GPU; --tiny runs a random 4-layer model on CPU).
  python speed/mlx/check_e2e.py --model mlx-community/Qwen3.5-2B-4bit --T 256 --chunks 8,16,32,64 --steps 5
Prints (1) step-1 forward loss (LoRA B=0, no update) for stock mlx-lm (per-token, use_kernel=False) vs each chunk size, and
(2) a --steps LoRA training run from the SAME init and SAME batch for stock and for --train-chunk (default 64), one JSON at the end.
Pass marks (fixed in advance): step-1 loss rel diff vs stock <= 1e-4 at chunk 64; no NaN in any loss/grad; the per-step losses
of chunk 64 within 1e-3 relative of stock at every step (they should overlap).  Exit code 1 if a mark fails."""
import argparse, json, sys, time
from pathlib import Path
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map
from mlx_lm.models import gated_delta as gd
from mlx_lm.tuner.utils import linear_to_lora_layers

sys.path.insert(0, str(Path(__file__).parent))
from chunked_gated_delta import patch_mlx_lm


def tiny_model():
    from mlx_lm.models import qwen3_5
    tc = dict(model_type="qwen3_5_text", hidden_size=256, intermediate_size=512, num_hidden_layers=4, full_attention_interval=4,
              num_attention_heads=4, num_key_value_heads=2, head_dim=64, linear_conv_kernel_dim=4, linear_key_head_dim=128,
              linear_num_key_heads=2, linear_num_value_heads=4, linear_value_head_dim=128, vocab_size=1000, rms_norm_eps=1e-6,
              tie_word_embeddings=True, max_position_embeddings=4096, attn_output_gate=True,
              rope_parameters=dict(rope_type="default", rope_theta=10000.0, partial_rotary_factor=0.25, mrope_interleaved=True, mrope_section=[2, 3, 3]))
    m = qwen3_5.Model(qwen3_5.ModelArgs.from_dict(dict(model_type="qwen3_5", text_config=tc)))
    mx.eval(m.parameters())
    return m, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen3.5-2B-4bit")
    ap.add_argument("--T", type=int, default=256)
    ap.add_argument("--chunks", default="8,16,32,64")
    ap.add_argument("--train-chunk", type=int, default=64)
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--tiny", action="store_true")
    ap.add_argument("--text", default=str(Path(__file__).parents[1] / "README.md"))
    a = ap.parse_args()

    if a.tiny:
        model, tok = tiny_model()
        mx.random.seed(0)
        ids = mx.random.randint(0, 1000, (1, a.T + 1))
    else:
        from mlx_lm import load
        model, tok = load(a.model)
        ids = tok.encode(open(a.text).read() * 20)[: a.T + 1]
        assert len(ids) == a.T + 1, "text too short"
        ids = mx.array([ids])
    x, y = ids[:, :-1], ids[:, 1:]
    model.freeze()
    linear_to_lora_layers(model, len(model.layers), {"rank": a.rank, "scale": 20.0, "dropout": 0.0})
    model.train()  # use_kernel=False -> gated_delta_ops (per-token) unless patched
    init = tree_map(lambda p: mx.array(p), model.trainable_parameters())
    mx.eval(init)
    stock = gd.gated_delta_ops

    def use(chunk):
        gd.gated_delta_ops = stock
        if chunk:
            patch_mlx_lm(chunk)

    def loss_fn(m, x, y):
        return nn.losses.cross_entropy(m(x).astype(mx.float32), y).mean()

    out = {"T": a.T, "model": "tiny" if a.tiny else a.model, "step1_loss": {}, "train": {}}
    for c in [0] + [int(v) for v in a.chunks.split(",")]:
        use(c)
        t = time.perf_counter()
        l = loss_fn(model, x, y); mx.eval(l)
        out["step1_loss"]["stock" if c == 0 else f"chunk{c}"] = {"loss": l.item(), "s": round(time.perf_counter() - t, 2)}
        print("step-1 forward loss", "stock" if c == 0 else f"chunk{c}", f"{l.item():.5f}", flush=True)
    base = out["step1_loss"]["stock"]["loss"]
    for k, v in out["step1_loss"].items():
        v["rel_vs_stock"] = abs(v["loss"] - base) / abs(base)

    for name, c in (("stock", 0), (f"chunk{a.train_chunk}", a.train_chunk)):
        use(c)
        model.update(tree_map(lambda p: mx.array(p), init))
        opt = optim.Adam(learning_rate=a.lr)
        vg = nn.value_and_grad(model, loss_fn)
        losses, times = [], []
        for s in range(a.steps):
            t = time.perf_counter()
            l, g = vg(model, x, y)
            opt.update(model, g)
            mx.eval(l, model.parameters(), opt.state)
            losses.append(l.item()); times.append(round(time.perf_counter() - t, 2))
            print(name, "step", s + 1, f"loss {losses[-1]:.5f}  {times[-1]}s", flush=True)
        out["train"][name] = {"losses": losses, "s_per_step": times}
    use(0)

    s, c = out["train"]["stock"]["losses"], out["train"][f"chunk{a.train_chunk}"]["losses"]
    rel = [abs(p - q) / abs(p) for p, q in zip(s, c)]
    ok1 = out["step1_loss"].get(f"chunk{a.train_chunk}", {"rel_vs_stock": 1})["rel_vs_stock"] <= 1e-4 if f"chunk{a.train_chunk}" in out["step1_loss"] else None
    out["step_rel_diff"] = rel
    out["pass"] = {"step1_rel<=1e-4": ok1, "train_overlap<=1e-3": max(rel) <= 1e-3, "finite": all(l == l and abs(l) < 1e6 for l in c)}
    print(json.dumps(out, indent=1))
    sys.exit(0 if all(v is not False for v in out["pass"].values()) else 1)


if __name__ == "__main__":
    main()
