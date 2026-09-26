#!/usr/bin/env python3
"""rv-392 addendum 1 (thought-memory thread, 2026-09-26): per-puzzle day-pass record for one net, report only.

rv-390's and rv-392's result files keep counts, not which puzzles each net left unfinished or hard. This writes, for
each day puzzle of rv-390's and rv-392's grids sets, whether the day pass got it right and its first accepted round
(the same claude_rv390.day_pass the sealed runs use). With the finds files it lets the untrained-net control be
counted on each trained net's own hard puzzles. It changes no mark and trains nothing.

  python -B scripts/claude_rv392_daydump.py --ckpt F --out F.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402

DAYS = [("rv390", ROOT / "artifacts/claude-rv390-20260926/day"), ("rv392", ROOT / "artifacts/claude-rv392-20260926/day")]
SETS = ["grids6", "grids7"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _, R, E = W.mods()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, dev).eval()
    rows = []
    for day, d in DAYS:
        items = W.load(R, d, SETS)
        for name in SETS:
            res = W.day_pass(net, R, E, items[name], dev)
            rows += [{"day": day, "set": name, "idx": i, "right": r["right"], "any_round": r["any_round"]}
                     for i, r in enumerate(res)]
            print(day, name, "n", len(res), "right", sum(r["right"] for r in res),
                  "hard", sum(not r["right"] and r["any_round"] is None for r in res), flush=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows))
    Path(a.out).with_suffix(".sha256.txt").write_text(f"{W.V.sha256(a.ckpt)}  {a.ckpt}\n")


if __name__ == "__main__":
    main()
