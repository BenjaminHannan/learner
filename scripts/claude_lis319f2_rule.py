#!/usr/bin/env python3
"""lis-319f2: FORMER as a save-time hold rule instead of retraining (reading thread, 2026-09-26). Fallback for lis-319f.

A fact the reader saves (mode ASSERT/CORRECT) is HELD when claude_lis319f_data.is_former(fact, turn) is true: the same
code rule that relabelled lis-319f's training data (past cue in the value's clause, no present cue, value does not carry
time itself). Held = confidence set to 0.0, so no scorer at any bar saves it. No retraining; the reader is unchanged.

hold: python claude_lis319f2_rule.py hold --reads R --rows ROWS --out R_F2.jsonl   (ROWS: id, turn; counts only)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis319_fullclaim import load  # noqa: E402
from claude_lis319f_data import is_former  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hold"])
    ap.add_argument("--reads", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    turn = {r["id"]: r["turn"] for r in load(a.rows)}
    c, out = Counter(), []
    for r in load(a.reads):
        facts = ((r.get("frame") or {}).get("facts") or [])
        confs = list(r.get("conf") or [])
        for i, f in enumerate(facts):
            if isinstance(f, dict) and i < len(confs) and is_former(f, turn.get(r["id"], "")):
                c[f"held:{f.get('rel')}"] += 1
                confs[i] = 0.0
        out.append(dict(r, conf=confs))
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps({"reads": len(out), "held": sum(c.values())} | dict(sorted(c.items()))))


if __name__ == "__main__":
    main()
