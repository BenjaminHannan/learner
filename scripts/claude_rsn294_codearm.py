#!/usr/bin/env python3
"""rsn-294 comparison arm: the hand-written reasoner's abilities, re-implemented on frames.

292's reasoner walks notebook facts one hop at a time (up to 3 hops, newest fact wins after a
correction), and 292's reverse / yes-no layers answer "whose R is V?" and "does A's R = V?".
It has no counting, comparing or before/after.  This arm does exactly that on the frame +
notebook rows, so the learned arms can be compared with it on the same items.  It is a
re-implementation of the abilities, not 292's own code path (292 needs English, not frames).

  python claude_rsn294_codearm.py --panel PANEL/items.jsonl --out scores.json
Writes category-level counts only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn294_run as RUN  # noqa: E402


def current(rows, subj, rel):
    hits = [r for r in rows if C._key(r["subject"]) == C._key(subj) and C._key(r["relation"]) == C._key(rel)]
    if not hits:
        return None
    return max(hits, key=lambda r: int(r.get("when", 0)))["value"]


def code_answer(item) -> str:
    rows, fr = item["notebook"], item["frame"]
    k, rels = fr["kind"], fr.get("relations") or []
    who = fr.get("who") or []
    if k == "value" and who and 1 <= len(rels) <= 3:
        cur = who[0]
        for r in rels:
            cur = current(rows, cur, r)
            if cur is None:
                return "UNKNOWN"
        return cur
    if k == "who" and rels and fr.get("value") is not None:
        subs = {r["subject"] for r in rows if C._key(r["relation"]) == C._key(rels[0])
                and C._key(current(rows, r["subject"], rels[0]) or "") == C._key(fr["value"])}
        return subs.pop() if len(subs) == 1 else "UNKNOWN"
    if k == "yesno" and who and rels:
        v = current(rows, who[0], rels[0])
        if v is None:
            return "UNKNOWN"
        return "yes" if C._key(v) == C._key(fr.get("value")) else "no"
    return "UNKNOWN"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--panel", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    items = [json.loads(l) for l in open(a.panel)]
    ans = [(code_answer(it),) * 2 for it in items]
    res = RUN.score(items, ans, "category")
    res.update({"arm": "code (292 abilities, re-implemented)", "items": len(items)})
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res["total"]))
