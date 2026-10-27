#!/usr/bin/env python3
"""lis-318 panel scorer (counts only; never prints panel text).

Panel rows (readpanel318): {"id","prev_reply","turn","kind","facts":[{"owner","relation","value"}],"nosave_reason"}.
Reads: claude_lis300_read.py output {"id","frame","conf","raw","ms"} for one arm.
Per-fact release (lis-315 semantics): a greedy fact is SAVED if it passes the live structural check
(claude_lis300_compiler.check_fact) and conf >= T. Saved facts are RIGHT if owner + value match a gold fact
of that row (owner USER <-> me; else full or first name, any case; value any case), else WRONG.
Counts:
  R0            gold facts found in the greedy read with mode ASSERT/CORRECT (no gate, no check)
  saved_right   gold facts saved at T
  saved_wrong / wrong_turns    saved facts matching no gold fact / rows with >= 1
  nofact_rows_with_save        nosave + smalltalk rows (75) with any saved fact
  held_right    R0 facts not saved at T (what confirm-at-use could still recover)
  parse_fail, ms median
python claude_lis318_score.py --panel panel.jsonl --reads reads.jsonl --threshold T [--out OUT.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis317_gates import e2e_match  # noqa: E402

WRITABLE = {"ASSERT", "CORRECT"}


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def score(panel, reads, T):
    rd = {r["id"]: r for r in reads}
    c, per_kind, ms = Counter(), Counter(), []
    for row in panel:
        r = rd.get(row["id"])
        c["rows"] += 1
        if r is None:
            c["missing"] += 1
            continue
        if "ms" in r:
            ms.append(r["ms"])
        fr = r.get("frame")
        if fr is None:
            c["parse_fail"] += 1
            fr = {}
        facts = [f for f in (fr.get("facts") or []) if isinstance(f, dict)]
        confs = r.get("conf") or []
        gold = row["facts"]
        saved = [f for i, f in enumerate(facts)
                 if CMP.check_fact(f, row["turn"], row.get("prev_reply", "")) is None
                 and (confs[i] if i < len(confs) else 0.0) >= T]
        for g in gold:
            c["gold"] += 1
            per_kind[row.get("kind", "all") + ":gold"] += 1
            if any(e2e_match(f, g) and str(f.get("mode", "")).upper() in WRITABLE for f in facts):
                c["R0"] += 1
                per_kind[row.get("kind", "all") + ":R0"] += 1
                if any(e2e_match(f, g) for f in saved):
                    c["saved_right"] += 1
                    per_kind[row.get("kind", "all") + ":saved_right"] += 1
                else:
                    c["held_right"] += 1
        wrong = [f for f in saved if not any(e2e_match(f, g) for g in gold)]
        c["saved_wrong"] += len(wrong)
        c["wrong_turns"] += bool(wrong)
        if wrong:
            per_kind[row.get("kind", "all") + ":wrong_turns"] += 1
        if not gold and saved:
            c["nofact_rows_with_save"] += 1
    out = dict(c)
    out["threshold"] = T
    out["ms_median"] = round(statistics.median(ms), 1) if ms else None
    out["per_kind"] = dict(sorted(per_kind.items()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = score(load(a.panel), load(a.reads), a.threshold)
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
