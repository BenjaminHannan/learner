"""Mac bench: stock default_loss vs loss_logits.make_loss on K2-Horizon-3.7B shapes (llama-like random weights, LoRA r8 on all layers).
K2-3.7B: 36 layers, hidden 2560, mlp 10240, 32 heads / 8 kv, head_dim 128, vocab 250,624 untied (HF config).
Run: python speed/mlx/bench_loss.py [--batch 1,4] [--seq 1024,2048] [--frac 0.25] [--out f.json]   (~7.4 GB bf16 weights)
     python speed/mlx/bench_loss.py --quick     (tiny config, CPU smoke)
Exits at once if ~/learner-ops/PAUSE_OTHERS or ASSISTANT_RUNNING exists. frac = share of positions that are loss targets (rest = prompt).
"""
import argparse, json, sys, time
from pathlib import Path

OPS = Path.home() / "learner-ops"
for flag in ("PAUSE_OTHERS", "ASSISTANT_RUNNING"):
    if (OPS / flag).exists():
        print(f"{OPS / flag} exists: Mac is busy with other work, not benchmarking. Remove it or wait.")
        sys.exit(0)

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm.models.llama import Model, ModelArgs
from mlx_lm.tuner.trainer import default_loss
from mlx_lm.tuner.utils import linear_to_lora_layers

sys.path.insert(0, str(Path(__file__).parent))
from loss_logits import make_loss

K2 = dict(hidden_size=2560, num_hidden_layers=36, intermediate_size=10240, num_attention_heads=32, num_key_value_heads=8,
          head_dim=128, vocab_size=250624, rms_norm_eps=1e-6, rope_theta=1e7, tie_word_embeddings=False)
TINY = dict(hidden_size=64, num_hidden_layers=2, intermediate_size=128, num_attention_heads=4, num_key_value_heads=2,
            head_dim=16, vocab_size=5000, rms_norm_eps=1e-6, tie_word_embeddings=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="1,4"); ap.add_argument("--seq", default="1024,2048")
    ap.add_argument("--frac", type=float, default=0.25); ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--chunk-rows", type=int, default=4096); ap.add_argument("--quick", action="store_true"); ap.add_argument("--hidden", type=int, help="override hidden size (CPU)"); ap.add_argument("--dtype", default="bfloat16"); ap.add_argument("--layers", type=int, help="override body depth (CPU: 2)"); ap.add_argument("--out")
    a = ap.parse_args()
    cfg = TINY if a.quick else K2
    if a.quick:
        a.batch, a.seq, a.iters, a.chunk_rows = "2", "128", 1, 64
    if a.layers:
        cfg = {**cfg, "num_hidden_layers": a.layers}
    if a.hidden:
        cfg = {**cfg, "hidden_size": a.hidden, "intermediate_size": 4 * a.hidden, "head_dim": a.hidden // cfg["num_attention_heads"]}
    mx.random.seed(0)
    m = Model(ModelArgs(model_type="llama", **cfg))
    m.set_dtype(getattr(mx, a.dtype))  # CPU: use float32 (bf16 matmul is very slow there)
    m.freeze()
    linear_to_lora_layers(m, cfg["num_hidden_layers"], {"rank": 8, "scale": 20.0, "dropout": 0.0, "keys": None})
    mx.eval(m.parameters())
    losses = {"stock": default_loss, "gather": make_loss(), f"gather_chunk{a.chunk_rows}": make_loss(chunk_rows=a.chunk_rows)}
    out = {"device": str(mx.default_device()), "cfg": cfg, "rows": []}
    for B in map(int, a.batch.split(",")):
        for T in map(int, a.seq.split(",")):
            batch = mx.random.randint(0, cfg["vocab_size"], (B, T + 1))
            p = int(T * (1 - a.frac))
            lengths = mx.array([[p, T]] * B)
            ref = None
            for name, fn in losses.items():
                row = {"B": B, "T": T, "frac": a.frac, "method": name}
                try:
                    vg = nn.value_and_grad(m, fn)
                    def once():
                        (l, n), g = vg(m, batch, lengths)
                        mx.eval(l, n, g)
                        return l.item(), g
                    once(); base = mx.get_active_memory(); mx.reset_peak_memory(); ts = []
                    for _ in range(a.iters):
                        t = time.perf_counter(); l, g = once(); ts.append(time.perf_counter() - t)
                    row.update(ms=1e3 * sorted(ts)[len(ts) // 2], peak_gb=(mx.get_peak_memory() - base) / 2**30, loss=l)
                    gf = dict(tree_flatten(g))
                    if ref is None: ref = (l, gf)
                    else:
                        row["rel_loss"] = abs(l - ref[0]) / abs(ref[0])
                        row["rel_grad_max"] = max((mx.max(mx.abs(gf[k].astype(mx.float32) - ref[1][k].astype(mx.float32))) / (mx.max(mx.abs(ref[1][k].astype(mx.float32))) + 1e-12)).item() for k in ref[1])
                except Exception as e:  # OOM
                    row["error"] = repr(e)[:200]
                out["rows"].append(row); print(json.dumps(row), flush=True); mx.clear_cache()
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1)); print("wrote", a.out)


if __name__ == "__main__":
    main()
