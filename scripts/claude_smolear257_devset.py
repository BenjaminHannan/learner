#!/usr/bin/env python3
"""Exp 257 -- the dev set for tau and for v3-vs-v4 comparisons (no panel read).

= 235b dev rows tagged base / R1 / R2 / R2s (235 dev split sample + my 235b risk families;
  their templates are not in v4 training)
+ dev257.jsonl (held-out templates for classes C1-C7 + INF, never used in training)
The 235b R3 family is left OUT of the tau set: v4 training uses the same "teaches at /
studies at" verbs (the brief names them), so it is no longer held out. It is still run
and reported separately (tag R3_indist).

python claude_smolear257_devset.py --out DIR   -> DIR/dev_all.jsonl, DIR/dev_tau.jsonl (no R3_indist), DIR/dev_all_turns.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D235B = ROOT / "artifacts/claude-smolear235b-20260922/dev/dev235b.jsonl"
D257 = ROOT / "artifacts/claude-smolear257-20260922/data/dev257.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    for x in D235B.read_text().splitlines():
        if x.strip():
            d = json.loads(x)
            d["id"] = "b" + d["id"]
            if d["tag"] == "R3":
                d["tag"] = "R3_indist"
            rows.append(d)
    for x in D257.read_text().splitlines():
        if x.strip():
            rows.append(json.loads(x))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev_all.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "dev_tau.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows if r["tag"] != "R3_indist"))
    (out / "dev_all_turns.json").write_text(json.dumps([{"id": r["id"], "turn": r["turn"]} for r in rows]))
    from collections import Counter
    print(len(rows), Counter(r["tag"] for r in rows))


if __name__ == "__main__":
    main()
