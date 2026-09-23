#!/usr/bin/env python3
"""lis-300 key audit: which rows two independent Opus labellers agree on.

A row is AGREED when, after both frames go through the write compiler,
  - the written facts match one-to-one (owner, value, relation exactly, case-insensitive names),
  - both or neither need "whose?",
  - the acts are equal, and
  - for ASK turns, the ask objects match (owner, rel, inverse, via).
Only agreed rows are used for training (or, for a panel, disagreements go to adjudication).

python claude_lis300_agree.py --a A.jsonl --b B.jsonl --out AGREED_IDS.txt [--report REPORT.json]
A rows {"id","turn","prev_reply","frame",...}; B rows {"id","frame"} (turn text taken from A).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_compiler import compile_frame  # noqa: E402
from claude_lis300_score import ask_ok, norm  # noqa: E402


def key(f):
    return (norm(f.get("owner")), f.get("rel"), norm(f.get("value")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    x = ap.parse_args()
    A = {r["id"]: r for r in map(json.loads, Path(x.a).read_text().splitlines()) if r}
    B = {r["id"]: r for r in map(json.loads, Path(x.b).read_text().splitlines()) if r}
    agreed, why = [], Counter()
    fam = Counter()
    for i, ra in A.items():
        rb = B.get(i)
        if not rb or not isinstance(rb.get("frame"), dict):
            why["missing"] += 1
            continue
        t, p = ra["turn"], ra.get("prev_reply", "")
        da, db = compile_frame(ra["frame"], t, p), compile_frame(rb["frame"], t, p)
        reasons = []
        if sorted(map(key, da["write"])) != sorted(map(key, db["write"])):
            reasons.append("writes")
        if bool(da["ask_whose"]) != bool(db["ask_whose"]):
            reasons.append("whose")
        if ra["frame"].get("act") != rb["frame"].get("act"):
            reasons.append("act")
        if ra["frame"].get("act") == "ASK" and rb["frame"].get("act") == "ASK" and \
                not ask_ok(rb["frame"].get("ask"), ra["frame"].get("ask") or {}):
            reasons.append("ask")
        if reasons:
            for r in reasons:
                why[r] += 1
            fam[ra.get("family", "?")] += 1
        else:
            agreed.append(i)
    Path(x.out).write_text("\n".join(agreed) + "\n")
    rep = {"rows": len(A), "agreed": len(agreed), "disagree_reasons": dict(why),
           "disagree_by_family": dict(fam)}
    if x.report:
        Path(x.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
