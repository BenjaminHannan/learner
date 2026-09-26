#!/usr/bin/env python3
"""rv-392 addendum 1 (thought-memory thread, 2026-09-26): write an UNTRAINED loop net as a control checkpoint.

Why: the GUESS arms have hand-written parts (the checker, and on grids the guess candidates skip symbols already in the
cell's row or column). A smoke on practice grids showed an untrained net solving some puzzles through them. Running the
sealed rv-390 and rv-392 code on this net, exactly as on the trained nets, shows what the code parts solve alone. The
net is 358i's loop architecture (Net("loop"), the arch R.load builds) with its default random init under a fixed seed,
saved in the same format as a trained checkpoint. Report only; it changes no mark.

  python -B scripts/claude_rv392_randnet.py --out DIR/loop-r0.pt [--seed 0]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    _, R, _ = W.mods()
    torch.manual_seed(a.seed)
    net = R.Net("loop")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"arm": "loop", "seed": -1 - a.seed, "state": net.state_dict()}, a.out)
    back = R.load(a.out, "cpu")
    assert all(torch.equal(x, y) for x, y in zip(net.state_dict().values(), back.state_dict().values()))
    h = hashlib.sha256()
    for k, v in net.state_dict().items():
        h.update(k.encode())
        h.update(v.detach().cpu().contiguous().numpy().tobytes())
    # the file's sha256 changes from save to save; the weights' hash is the same for the same seed and torch build
    print("untrained loop net", a.out, "init seed", a.seed, "weights", sum(p.numel() for p in net.parameters()),
          "weights_sha256", h.hexdigest(), "file_sha256", W.V.sha256(a.out))


if __name__ == "__main__":
    main()
