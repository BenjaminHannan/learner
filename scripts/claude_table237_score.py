#!/usr/bin/env python3
"""Exp 237 M1 scorer (sealed rules). The panel's field NAMES are unknown at
seal time, so they come from a small map file written after the seal
(map keys: id, family, question, setup, gold, gold_sep, abstain_golds,
base_id, base_reply). The scoring RULES below are fixed:

  values(r)   = the value (3rd) of every triple stored before the question,
                minus any that appear in the question text itself.
  gold        = gold field split on gold_sep; a gold in abstain_golds
                (case-insensitive) or family 'trap' means "no value".
  wrong value = a value in values(r) that is not a gold value appears in the
                reply (case-insensitive substring).
  right       = synonym/new_relation/date: every gold value appears in the
                reply AND no wrong value.
  trap right  = no value from values(r) appears in the reply.
  control     = reply byte-identical (after strip) to base221.jsonl reply.
  writes      = stored triples before != after the question.
Usage: score.py rows237.jsonl base221.jsonl map.json out.json
"""
import json
import sys
from collections import Counter, defaultdict

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
base = [json.loads(l) for l in open(sys.argv[2]) if l.strip()]
mp = json.load(open(sys.argv[3]))
bid = {str(b[mp["base_id"]]): b for b in base}
ab = {a.lower() for a in mp.get("abstain_golds", [])}
tot = Counter(); right = Counter(); out = []
wrong_total = 0; writes = 0
for r in rows:
    fam = r[mp["family"]]; rid = str(r[mp["id"]])
    reply = r["reply"]; low = reply.lower(); q = r["question"].lower()
    g = r.get(mp["gold"])
    golds = g if isinstance(g, list) else [x.strip() for x in str(g or "").split(mp.get("gold_sep", ";")) if x.strip()]
    no_value = fam == "trap" or not golds or all(x.lower() in ab for x in golds)
    vals = {str(t[2]).strip().rstrip(".") for t in (r.get("stored_before") or [])}
    vals = {v for v in vals if v and v.lower() not in q}
    gl = {x.lower() for x in golds}
    wrong = sorted(v for v in vals if v.lower() not in gl and v.lower() in low)
    if no_value:
        given = sorted(v for v in vals if v.lower() in low)
        ok = not given
        wrong = given
    else:
        ok = all(x.lower() in low for x in golds) and not wrong
    if fam == "control":
        b = bid.get(rid)
        ok = b is not None and str(b[mp["base_reply"]]).strip() == reply.strip()
    wrong_total += len(wrong)
    writes += int(bool(r.get("question_wrote")))
    tot[fam] += 1; right[fam] += int(ok)
    out.append({"id": rid, "family": fam, "question": r["question"],
                "reply": reply, "gold": golds, "right": ok,
                "wrong_values": wrong, "question_wrote": r.get("question_wrote")})
summ = {"per_family": {f: [right[f], tot[f]] for f in tot},
        "wrong_values_total": wrong_total, "question_writes": writes,
        "cases": out}
json.dump(summ, open(sys.argv[4], "w"), indent=1, ensure_ascii=False)
for f in tot:
    print(f"{f}: {right[f]}/{tot[f]} = {100*right[f]/tot[f]:.1f}%")
print(f"wrong values {wrong_total}; question writes {writes}")
