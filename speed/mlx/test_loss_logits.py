"""CPU test: make_loss == mlx_lm default_loss (value + LoRA-style grads), tied/untied, padded lengths, chunked head.
Run: python speed/mlx/test_loss_logits.py   (also runs on the Mac GPU)"""
import sys
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm.models.llama import Model, ModelArgs
from mlx_lm.tuner.trainer import default_loss

sys.path.insert(0, str(Path(__file__).parent))
from loss_logits import make_loss

TOL = 1e-5  # fp32, relative


def rel(a, b):
    return (mx.max(mx.abs(a - b)) / (mx.max(mx.abs(b)) + 1e-12)).item()


def check(tie, chunk_rows):
    mx.random.seed(1)
    args = ModelArgs(model_type="llama", hidden_size=32, num_hidden_layers=2, intermediate_size=64, num_attention_heads=4,
                     num_key_value_heads=2, rms_norm_eps=1e-5, vocab_size=101, tie_word_embeddings=tie)
    m = Model(args)
    mx.eval(m.parameters())
    B, T = 3, 17
    batch = mx.random.randint(0, 101, (B, T))
    lengths = mx.array([[5, 17], [0, 9], [3, 12]])  # (prompt_len, total_len): loss only on steps in [l0, l1]
    out = {}
    for name, fn in (("stock", default_loss), ("gather", make_loss(chunk_rows=chunk_rows))):
        vg = nn.value_and_grad(m, fn)
        (l, n), g = vg(m, batch, lengths)
        mx.eval(l, n, g)
        out[name] = (l, n, dict(tree_flatten(g)))
    (l0, n0, g0), (l1, n1, g1) = out["stock"], out["gather"]
    assert n0.item() == n1.item(), (n0, n1)
    errs = {"loss": rel(l1, l0), "grad": max(rel(g1[k], g0[k]) for k in g0)}
    assert set(g0) == set(g1) and all(v < TOL for v in errs.values()), errs
    print(f"ok tie={tie} chunk_rows={chunk_rows} ntoks={n0.item()} {errs}")


if __name__ == "__main__":
    for tie in (False, True):
        for cr in (None, 4):
            check(tie, cr)
    print("all passed on", mx.default_device())
