#!/usr/bin/env python3
"""lis-317 (report only): build reader input rows for the e2e DEV bank.

One row per DEV user turn: {"id", "turn", "prev_reply", "kind", "ask_type", "facts", "gold"}.
prev_reply = the reply the 330a_chat arm gave just before this turn in the rent-330-dev run
(artifacts/claude-e2e330-dev-20260924/run/arm_330a_chat.jsonl on builder-outbox), so the reader
sees the same context it saw live. DEV data only (fine to read); no TEST-ONLY bank is touched.

Usage: python scripts/claude_lis317_rows.py --bank artifacts/claude-e2e331-dev-20260924 \
         --arm ARM_330a_chat.jsonl --out artifacts/claude-lis317-20260925/rows_e2edev.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    turns = load(Path(a.bank) / "turns.jsonl")
    rows = load(a.arm)
    by = defaultdict(list)
    for r in rows:
        by[r["life_id"]].append(r)
    out = []
    for t in turns:
        seq = by[t["life_id"]]
        idx = next(i for i, r in enumerate(seq) if r["turn_index"] == t["turn_index"] and r["kind"] == "user")
        prev = seq[idx - 1]["reply"] if idx > 0 else ""
        out.append({"id": f'{t["life_id"]}:{t["turn_index"]}', "turn": t["user_text"], "prev_reply": prev,
                    "kind": t["kind"], "ask_type": t["ask_type"], "facts": t["facts"], "gold": t["gold"]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print("rows", len(out))


if __name__ == "__main__":
    main()
