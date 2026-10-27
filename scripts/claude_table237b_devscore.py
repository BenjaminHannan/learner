#!/usr/bin/env python3
"""Exp 237b M2 dev scorer. Usage: devscore.py rows237b.jsonl rows221.jsonl
right (synonym/new_relation/date) = every 'contains' string in the reply
  (case-insensitive) and the reply does not start with I don't know /
  I do not know;
trap right = no 'absent' value in the reply (whole word, case-insensitive);
control right = reply byte-identical (after strip) to the loop221 arm;
writes = stored triples changed by the question turn."""
import json, re, sys
from collections import Counter
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
base = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2]) if l.strip()}
def has(v, text):
    return re.search(r"(?<!\w)" + re.escape(v.lower()) + r"(?!\w)", text.lower()) is not None
tot, ok, w = Counter(), Counter(), 0
for r in rows:
    rep, fam = r["reply"].strip(), r["family"]
    if fam == "trap":
        good = not any(has(a, rep) for a in r["absent"])
    elif fam == "control":
        good = rep == base[r["id"]]["reply"].strip()
    else:
        good = all(c.lower() in rep.lower() for c in r["contains"]) and not rep.lower().startswith(("i don't know", "i do not know"))
    tot[fam] += 1; ok[fam] += good; w += bool(r["question_wrote"])
    b = base[r["id"]]["reply"]
    print(("OK  " if good else "MISS"), r["id"], fam, repr(r["question"]), "->", repr(rep), "" if b == rep else f"| 221: {b!r}")
print({f: f"{ok[f]}/{tot[f]}" for f in tot}, "total", f"{sum(ok.values())}/{sum(tot.values())}", "writes", w)
