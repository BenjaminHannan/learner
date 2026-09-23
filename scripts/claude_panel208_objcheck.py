#!/usr/bin/env python3
"""Director add-on scorer for the sealed exp-208 natural panel (reads a run jsonl; changes nothing sealed).
G1 cannot see wrong-valued saves (e.g. "Rosa's dad is called Callum." stored as value 'called Callum').
This check compares every newly stored triple on a SAVE turn with the expected fact by SUBJECT and OBJECT
(case-insensitive; relation names differ between panel and notebook, so they are not compared) and on
non-SAVE turns flags any write. Usage: python3 claude_panel208_objcheck.py <run.jsonl>"""
import json, sys
bad, good, missed = [], 0, 0
for line in open(sys.argv[1]):
    r = json.loads(line)
    new = r.get("new_triples") or []
    if r.get("exp") != "SAVE":
        for t in new: bad.append((r["id"], r["text"], t, "write on a non-SAVE turn"))
        continue
    exp = [e for e in (r.get("expect_fact"), r.get("expect_fact2")) if e]
    if not new: missed += 1; continue
    for t in new:
        ok = any(t[0].lower() == e[0].lower() and str(t[2]).lower() == str(e[2]).lower() for e in exp)
        if ok: good += 1
        else: bad.append((r["id"], r["text"], t, f"expected one of {exp}"))
print(f"SAVE turns: stored-and-matching {good}, stored nothing {missed}; junk/wrong-valued or stray writes {len(bad)}")
for b in bad: print("  JUNK", b[0], repr(b[1]), "->", b[2], "|", b[3])
