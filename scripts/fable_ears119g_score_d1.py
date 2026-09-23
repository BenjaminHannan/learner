#!/usr/bin/env python3
"""Director scorer-only fix D1 for Exp 119g (2026-09-22 11:07). No rule, mark,
model, training or data change; the sealed scorer is imported unchanged.

Bug (crashed at wave step 0, before any training or score was produced):
score_panel_multi passes decode_all_k1's FLAT list (one parse dict per row)
to score_k, which iterates each row as a LIST of frames -> TypeError
"string indices must be integers". score47g needs the flat form, so the fix
applies inside score_panel_multi ONLY: K=1 parses are wrapped as one-frame
lists ([parse]), exactly what the K=chosen path already returns per row.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119g_score as G  # noqa: E402

_orig_k1 = G.decode_all_k1
_orig_panel = G.score_panel_multi


def _k1_rows(*a, **k):
    return [[p] for p in _orig_k1(*a, **k)]


def score_panel_multi_d1(*a, **k):
    G.decode_all_k1 = _k1_rows
    try:
        return _orig_panel(*a, **k)
    finally:
        G.decode_all_k1 = _orig_k1


G.score_panel_multi = score_panel_multi_d1

if __name__ == "__main__":
    G.main()
