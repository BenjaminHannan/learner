#!/usr/bin/env python3
"""Exp 64 helper (NOT the registered selector): dump rung-1 per-sentence scores.

Rung-1 score-*.json files hold only aggregate counts, so this helper re-runs the
frozen rung-1 ears (runs/<arm>-<seed>/ear.pt) over panels/{cal,t_seen,t_new,t_hard}.json
with the rung-1 decoder imported READ-ONLY from fable_ears45_score.py, and writes one
small JSON per (arm, panel) with the fields the numpy-only selector needs.

No threshold is chosen here; no label guides any choice here. Output rows:
  n, fam, gold (gold act or None), s (ensemble min-conf over 3 ears),
  cand (would-write at tau=0: ensemble EXECUTE and item act in WRITE_ACTS),
  ok (decoded item == gold item), s123/cand123/ok123 (single-ear reference).

Usage (needs torch; Mac CPU):
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
    scripts/fable_abstain64_dump.py --arms tape,bigru --outdir artifacts/fable-abstain64-20260921
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE  # noqa: E402  (read-only)
import fable_ears45_data as D  # noqa: E402
import fable_ears45_model as M  # noqa: E402
import fable_ears45_score as S  # noqa: E402  (decoder + forward, read-only)
import fable_ears45_train as T  # noqa: E402

SEEDS = (4301, 4302, 4303)
PANELS = ("cal", "t_seen", "t_new", "t_hard")


def dump_panel(arm: str, panel: str, runs_dir: Path, panels_dir: Path) -> list[dict]:
    rows = json.loads((panels_dir / f"{panel}.json").read_text())
    split, pools, lex, gen = D.load_all()
    rng = random.Random(9000 + D.PANEL_SEEDS[panel])
    encs, keep = [], []
    for ex in rows:
        e = D.encode(ex, lex, rng, False, hash_names=(arm == "names"))
        if e is None:
            continue
        e["idx"] = len(encs)
        encs.append(e)
        keep.append(ex)
    packs = T.to_tensors(encs)
    models = []
    for s in SEEDS:
        ck = torch.load(runs_dir / f"{arm}-{s}" / "ear.pt", weights_only=False)
        m = M.Ears(ck["vocab"], arm)
        m.load_state_dict(ck["state"])
        m.eval()
        models.append(m)
    parses = []
    for m in models:
        probs = S.run_ear(m, packs)
        parses.append([S.decode(keep[i], encs[i], probs[i]) for i in range(len(encs))])
    out = []
    for k, ex in enumerate(keep):
        ps = [parses[q][k] for q in range(3)]
        v, item = S.verdict_ensemble(ps, 0.0)
        s = min(p["conf"] for p in ps)
        g = S.gold_of(ex)
        out.append({
            "n": ex["n"],
            "fam": ex["family"],
            "gold": (g.get("act") if isinstance(g, dict) else None),
            "s": round(float(s), 6),
            "cand": bool(v == "EXECUTE" and item is not None
                         and item.get("act") in LE.WRITE_ACTS),
            "ok": bool(S.same_item(item, g)),
            "s123": [round(float(p["conf"]), 6) for p in ps],
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="tape,bigru")
    ap.add_argument("--runs", default="artifacts/fable-ears45-20260921/runs")
    ap.add_argument("--panels", default="artifacts/fable-ears45-20260921/panels")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for arm in a.arms.split(","):
        for panel in PANELS:
            rows = dump_panel(arm, panel, Path(a.runs), Path(a.panels))
            # progress only: shapes, never labels/errors/confidence stats
            print(f"{arm}/{panel}: {len(rows)} rows dumped", flush=True)
            (outdir / f"per_sentence_{arm}_{panel}.json").write_text(json.dumps(rows))


if __name__ == "__main__":
    main()
