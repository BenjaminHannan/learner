#!/usr/bin/env python3
"""Exp 237 M2 dev scorer: right = every 'contains' string in the reply and no
'absent' string; also counts question writes. Usage: devscore.py rows.jsonl"""
import json, sys
from collections import Counter
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
tot, ok, w = Counter(), Counter(), 0
for r in rows:
    low = r["reply"].lower()
    good = all(c.lower() in low for c in r["contains"]) and not any(a.lower() in low for a in r["absent"])
    tot[r["family"]] += 1; ok[r["family"]] += good; w += bool(r["question_wrote"])
    print(("OK  " if good else "MISS"), r["id"], r["family"], repr(r["question"]), "->", repr(r["reply"]))
print({f: f"{ok[f]}/{tot[f]}" for f in tot}, "total", f"{sum(ok.values())}/{sum(tot.values())}", "writes", w)
