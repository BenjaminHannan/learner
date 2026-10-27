#!/usr/bin/env python3
"""Exp 119h — scorer: 119g scorer with the D1 fix built in (Muse BUILD).

    python fable_ears119h_score.py --score47g --runs <runs> \\
        --panels47 <panels> --snapshot <scibert> --out report47h.json \\
        --taus-out taus119h.json --k 3 --floor 0.10
    python fable_ears119h_score.py --score-panel --runs <runs> \\
        --taus <taus119h.json> --snapshot <scibert> --panel <panel.jsonl> \\
        --panel-tag 94b --k 3 --floor 0.10 --out report119h_94b_K3.json

Everything is 119g verbatim by import (K=1 verbatim old decode, K=chosen
relation-conditioned multi-decode, 47 tau rule, 106 normaliser, RelCondEars
loader) EXCEPT the D1 fix, which is built in here instead of living in a
separate wrapper file: inside score_panel_multi only, the flat per-row
K=1 parses from decode_all_k1 are wrapped as one-frame lists before scoring
(score47g keeps the flat form it needs). No step 0: the 119g registered
numbers are the baseline. No test.pt anywhere; panels are scoring-only.

Additive only: 119g scorer imported read-only, never edited.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119g_score as G119  # noqa: E402  (everything by import)

SEEDS = list(G119.SEEDS)
assert tuple(SEEDS) == (11911, 11912, 11913), SEEDS


def score_panel_multi(runs: Path, taus: dict, snapshot: str, out: Path,
                      device, panel_path: Path, panel_tag: str,
                      K: int, FLOOR: float) -> dict:
    """119g score_panel_multi with the D1 fix built in (K=1 rows wrapped)."""
    orig_k1 = G119.decode_all_k1

    def _k1_rows(*a, **k):
        return [[p] for p in orig_k1(*a, **k)]

    G119.decode_all_k1 = _k1_rows  # pyright: ignore[reportAttributeAccessIssue]
    try:
        return G119.score_panel_multi(runs, taus, snapshot, out, device,
                                      panel_path, panel_tag, K, FLOOR)
    finally:
        G119.decode_all_k1 = orig_k1  # pyright: ignore[reportAttributeAccessIssue]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score47g", action="store_true")
    ap.add_argument("--score-panel", action="store_true")
    ap.add_argument("--runs", default=None)
    ap.add_argument("--panels47", default=None)
    ap.add_argument("--taus", default=None)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--taus-out", default=None)
    ap.add_argument("--panel", default=None)
    ap.add_argument("--panel-tag", default="94b")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--floor", type=float, default=0.10)
    a = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.score47g:
        assert a.runs and a.panels47 and a.taus_out, \
            "--score47g needs --runs --panels47 --taus-out"
        G119.score47g(Path(a.runs), Path(a.panels47), a.snapshot,
                      Path(a.out), Path(a.taus_out), device, a.k, a.floor)
    elif a.score_panel:
        assert a.runs and a.taus and a.panel, \
            "--score-panel needs --runs --taus --panel"
        taus = json.loads(Path(a.taus).read_text(encoding="utf-8"))
        score_panel_multi(Path(a.runs), taus, a.snapshot, Path(a.out),
                          device, Path(a.panel), a.panel_tag, a.k, a.floor)
    else:
        raise SystemExit("need --score47g or --score-panel (no step 0 in 119h)")


if __name__ == "__main__":
    main()
