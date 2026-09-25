#!/usr/bin/env python3
"""bm-395 report-only analysis (benchmarks thread, 2026-09-25): how often the lines shown held an evidence turn,
and F1 split by found / not found, for E and E20 (from their "turns" field) and Rb / Rb2 (from bm-393's BM25 flags,
which reproduced Rb's shown turns 497 of 497). Not part of the verdict. Counts and scores only.

  python -B scripts/claude_bm395_found_split.py --data DATA --per SCOREDIR/per_question.json \
      --runs RUNDIR --bm393 artifacts/claude-bm393-20260925/evrecall_per_question.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402


def evidence_positions(data: Path) -> dict:
    ev = {}
    for conv in B.load_locomo(data, ""):
        pos = {}
        for _date, turns in B.sessions(conv):
            for t in turns:
                pos[t.get("dia_id")] = len(pos)
        for i, qa in enumerate(conv["qa"]):
            ev[f"{conv['sample_id']}#{i}"] = {pos[e] for e in qa.get("evidence", []) if e in pos}
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--per", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--bm393", required=True)
    a = ap.parse_args()
    ev = evidence_positions(Path(a.data))
    per = json.loads(Path(a.per).read_text(encoding="utf-8"))
    bm = {}
    for x in Path(a.bm393).read_text(encoding="utf-8").splitlines():
        if x.strip():
            r = json.loads(x)
            if r["n_ev"]:
                bm[r["qid"]] = r["bm25_any@10"]
    out = {"label": "after using LoCoMo for development"}
    for arm in ("E", "E20", "Rb2", "Rb"):
        if arm not in per or "locomo" not in per[arm]:
            continue
        f1 = per[arm]["locomo"]
        if arm.startswith("E"):
            shown = {}
            for x in (Path(a.runs) / f"locomo_{arm}.jsonl").read_text(encoding="utf-8").splitlines():
                if x.strip():
                    r = json.loads(x)
                    shown[r["qid"]] = set(r["turns"])
            found = {q: int(bool(ev[q] & shown[q])) for q in shown if ev.get(q)}
        else:
            found = dict(bm)
        ids = [q for q in found if q in f1 and f1[q]["cat"] in (1, 2, 3, 4)]
        yes = [f1[q]["f1"] for q in ids if found[q]]
        no = [f1[q]["f1"] for q in ids if not found[q]]
        out[arm] = {"questions": len(ids), "found": len(yes), "found_pct": round(100 * len(yes) / max(1, len(ids)), 1),
                    "f1_found": round(100 * sum(yes) / max(1, len(yes)), 2),
                    "f1_not_found": round(100 * sum(no) / max(1, len(no)), 2)}
        print(json.dumps({arm: out[arm]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
