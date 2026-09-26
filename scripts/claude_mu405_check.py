#!/usr/bin/env python3
"""mu-405 panel check (counts only, prints no chat text): every chat matches facts.jsonl, session 1 states all 3 fact
values, session 2 has the 5 kinds in order and contains no value ("Making things up about you", 2026-09-26).

  python3 -B scripts/claude_mu405_check.py --panel artifacts/claude-mu405-20260926/panel/items.jsonl \
      --facts artifacts/claude-mu405-20260926/facts.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

KINDS2 = ["smalltalk", "feelings", "advice", "followup", "ask"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--facts", required=True)
    a = ap.parse_args()
    fx = {r["item_id"]: r for r in map(json.loads, Path(a.facts).read_text(encoding="utf-8").splitlines())}
    rows = [json.loads(x) for x in Path(a.panel).read_text(encoding="utf-8").splitlines()]
    bad = Counter()
    ids = [r["item_id"] for r in rows]
    if len(ids) != len(set(ids)):
        bad["duplicate_ids"] += 1
    if set(ids) != set(fx):
        bad["ids_differ_from_facts"] += 1
    for r in rows:
        f = fx.get(r["item_id"])
        if f is None:
            continue
        vals = [x["value"].lower() for x in f["facts"]]
        s1 = " ".join(t["text"] for t in r["session1"]).lower()
        if not 3 <= len(r["session1"]) <= 4:
            bad["session1_length"] += 1
        bad["value_missing_in_session1"] += sum(1 for v in vals if v not in s1)
        if [t["kind"] for t in r["session2"]] != KINDS2:
            bad["session2_kinds"] += 1
        bad["value_in_session2"] += sum(1 for t in r["session2"] for v in vals if v in t["text"].lower())
    out = {"chats": len(rows), "panel": sum(1 for r in rows if not fx.get(r["item_id"], {}).get("smoke")),
           "smoke": sum(1 for r in rows if fx.get(r["item_id"], {}).get("smoke")),
           "session1_turns": sum(len(r["session1"]) for r in rows),
           "session2_turns": sum(len(r["session2"]) for r in rows),
           "problems": {k: v for k, v in bad.items() if v}}
    print(json.dumps(out))
    raise SystemExit(1 if out["problems"] else 0)


if __name__ == "__main__":
    main()
