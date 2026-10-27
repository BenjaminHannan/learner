#!/usr/bin/env python3
"""rsn-358i2 (sleep research thread, 2026-09-26): rsn-358i's loop arm with ONE change, a bug repair: bf16 autocast
runs with its weight cache OFF.

Why (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md; the Thread manager's audit,
/mnt/project-files/thread-manager/loop-training-audit-2026-09-26.md, Test A): the loop's free rounds run under
torch.no_grad() inside the same `with amp:` block as its graded rounds (scripts/claude_rsn358a_run.py:118-121, :286).
On torch 2.8 autocast caches the bf16 copy of each Linear weight the first time it is cast; a copy made under
no_grad has no gradient link, and the graded rounds reuse it, so the loop's layer weights get no gradient on every
step with at least one free round (about 85% of steps). Plain never runs a free round and is unaffected. Newer torch
(2.11, 2.14) does not show it. cache_enabled=False removes the cache on every version; the forward numbers are the
same (the same bf16 casts, made again each time instead of reused).
Nothing else changes: 358i's data, sizes, steps, schedule, stop rule v2, tests. Added logging only (no effect on
training): torch/CUDA versions, GPU name, and gradient checks in train_summary.json:
  steps_block_nograd = how many optimizer steps had any block Linear weight with no or all-zero gradient (should be 0)
  grad_norms = per-block gradient norm every 2,500 steps.

  python -B scripts/claude_rsn358i2_run.py train --arm loop --seed S --out DIR
  python -B scripts/claude_rsn358i2_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_rsn358i2_run.py selftest | smoke | check-mask
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i_run as I  # noqa: E402  (358i: legend grids + v2 stop rule + half-narrow heads)

R, E = I.R, I.E
NORM_EVERY = 2500


class NoCacheAutocast(torch.autocast):
    """torch.autocast with the weight cache off unless a caller asks otherwise; the only training change"""

    def __init__(self, *args, **kw):
        kw.setdefault("cache_enabled", False)
        super().__init__(*args, **kw)


torch.autocast = NoCacheAutocast

_STATS = {"net": None, "steps": 0, "steps_block_nograd": 0, "grad_norms": []}
_init = R.Net.__init__


def _net_init(self, *a, **k):
    _init(self, *a, **k)
    _STATS["net"] = self


R.Net.__init__ = _net_init
_clip = torch.nn.utils.clip_grad_norm_


def _block_mats(net):
    return [(n, p) for n, p in net.named_parameters() if n.startswith("blocks.") and p.dim() == 2
            and not n.endswith((".br", ".bc"))]


def _clip_and_check(params, *a, **k):
    net = _STATS["net"]
    if net is not None and net.training:
        _STATS["steps"] += 1
        mats = _block_mats(net)
        if any(p.grad is None or not bool(p.grad.detach().abs().sum()) for _, p in mats):
            _STATS["steps_block_nograd"] += 1
        if _STATS["steps"] == 1 or _STATS["steps"] % NORM_EVERY == 0:
            by_block = {}
            for n, p in mats:
                b = n.split(".")[1]
                by_block[b] = by_block.get(b, 0.0) + (0.0 if p.grad is None else float(p.grad.detach().float().norm()) ** 2)
            _STATS["grad_norms"].append({"step": _STATS["steps"], **{f"block{b}": round(v ** 0.5, 6) for b, v in by_block.items()}})
    return _clip(params, *a, **k)


torch.nn.utils.clip_grad_norm_ = _clip_and_check
_train = R.train


def train(a):
    _STATS.update(steps=0, steps_block_nograd=0, grad_norms=[])
    _train(a)
    f = Path(a.out) / "train_summary.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d.update({"torch": torch.__version__, "cuda": torch.version.cuda, "python": platform.python_version(),
              "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "autocast_cache": False, "steps_seen": _STATS["steps"],
              "steps_block_nograd": _STATS["steps_block_nograd"], "grad_norms": _STATS["grad_norms"]})
    f.write_text(json.dumps(d, indent=1), encoding="utf-8")


R.train = train


def selftest():
    """the stage 0 check through this file's autocast: no block Linear weight is left without gradient"""
    import random
    torch.manual_seed(0)
    rng = random.Random(0)
    items = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(8)]
    t, s, y, env = R.tensors(items, "cpu")
    net = R.Net("loop")
    with torch.autocast("cpu", dtype=torch.bfloat16):
        outs = net.loop_train(t, s, env, 3, 2)
        loss = sum(R.ce_and_exact(lg, s, y)[0] + q.float().mean() for lg, q in outs)
    loss.backward()
    mats = _block_mats(net)
    none = sum(p.grad is None or not bool(p.grad.abs().sum()) for _, p in mats)
    assert len(mats) == 8 and none == 0, (len(mats), none)
    assert torch.autocast is NoCacheAutocast
    print(f"selftest ok: torch {torch.__version__}, cache off, 0/8 block Linear weights without gradient after 3 free + 2 graded rounds")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["check-mask"]:
        I.check_mask()
    else:
        R.main()
