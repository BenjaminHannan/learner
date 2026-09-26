#!/usr/bin/env python3
"""ch-404 DEV probe scorer (everyday-chat thread, 2026-09-26). New file only. DEV data only (readable): the ch-403
rental's DEVOUT rows on artifacts/claude-chatdev-20260926 for X, X403, X404, X404g and T.

packets  per-arm counts (ch-403's arm_counts plus 338's guard counts: G4 = samples rejected as too long,
         kept_all_failed = turns where every sample failed and the give-up line stayed) and blind judge packets:
           pair_p  X404 vs X403, only conversations that differ     pair_q  X403 vs T      pair_r  X404 vs T
           pair_s  X404g vs X403, only conversations that differ    pair_t  X404g vs T
         sides shuffled per conversation (seeds 4041-4045), files of 15, keys in DIR/key_{p..t}.json.
           python3 scripts/claude_ch404_dev.py packets --panel-dir DD --dev DEVOUT --out DIR
tally    applies the keys to the judges' files (JUDGE-BRIEF.md format) and prints wins, ties and made-up counts.
           python3 scripts/claude_ch404_dev.py tally --out DIR --judged JDIR
Nothing here is a registered mark: it decides whether ch-404 (length) or ch-404g (greedy first) goes to a sealed
panel (rule: artifacts/claude-ch404-20260926/NEXT.md).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ch403_run as R  # noqa: E402

PAIRS = (("p", "X404", "X403", 4041, True), ("q", "X403", "T", 4042, False), ("r", "X404", "T", 4043, False),
         ("s", "X404g", "X403", 4044, True), ("t", "X404g", "T", 4045, False))


def packets(a) -> None:
    items = {it["item_id"]: it for it in R.load_panel(Path(a.panel_dir))}
    dev, out = Path(a.dev), Path(a.out)
    arms = {x: R.load(dev / f"chat_{x}.jsonl") for x in ("X", "X403", "X404", "X404g", "T") if (dev / f"chat_{x}.jsonl").exists()}
    summ = {"items": len(items), "arms": sorted(arms)}
    for x, rows in arms.items():
        c = R.arm_counts(rows, items)
        g = Counter()
        for r in rows:
            g.update(r.get("c338") or {})
        c["c338"] = {k: g[k] for k in ("gave_up", "replaced", "kept_all_failed", "G1", "G2", "G3", "G4")}
        summ[x] = c
    jd = out / "judge"
    jd.mkdir(parents=True, exist_ok=True)
    for tag, first, other, seed, only_diff in PAIRS:
        if first not in arms or other not in arms:
            continue
        pk, key, same = R.packets(first, other, arms, items, seed, only_diff)
        for i in range(0, len(pk), R.PACKET):
            (jd / f"pair_{tag}{i // R.PACKET + 1}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk[i:i + R.PACKET]), encoding="utf-8")
        (out / f"key_{tag}.json").write_text(json.dumps({"key": key, "identical": same}, indent=1), encoding="utf-8")
        summ[f"pair_{tag}"] = {"arms": [first, other], "judged": len(pk), "identical": len(same),
                               "files": math.ceil(len(pk) / R.PACKET)}
    (out / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def tally(a) -> None:
    out, jdir = Path(a.out), Path(a.judged)
    res = {}
    for tag, first, other, _, _ in PAIRS:
        kf = out / f"key_{tag}.json"
        if kf.exists():
            j = R.judged(jdir, tag, json.loads(kf.read_text(encoding="utf-8")))
            res[f"{first}_vs_{other}"] = j
    (out / "tally.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["packets", "tally"])
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--dev", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--judged", default="")
    a = ap.parse_args()
    {"packets": packets, "tally": tally}[a.cmd](a)


if __name__ == "__main__":
    main()
