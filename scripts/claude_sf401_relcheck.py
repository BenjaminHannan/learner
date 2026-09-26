#!/usr/bin/env python3
"""sf-401 after the verdict: relation-name agreement for BLAME-after-verdict.md (report only, counts only). Run from the repo root."""
import json, sys
from collections import Counter, defaultdict
sys.path.insert(0, "scripts")
import claude_e2e336_score as SC
import claude_sf401_blame as BL
R = "artifacts/claude-sf401-20260926"
ld = BL.ld
turns = ld(f"{R}/panel/turns.jsonl"); tk = {(t["life_id"], t["turn_index"]): t for t in turns}
truth = {f["fact_id"]: f for f in ld(f"{R}/panel/truth.jsonl")}
old_of = {c["new_fact"]: c["old_fact"] for c in ld(f"{R}/panel/corrections.jsonl")}
rows = ld(f"{R}/run/arm_B.jsonl")
conf = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
by_life = defaultdict(list)
for r in rows: by_life[r["life_id"]].append(r)
# global: of stored triples matching a truth fact's owner+value, how often is the relation string equal?
g = Counter()
for life, rs in by_life.items():
    last = [r for r in rs if r.get("stored_triples") is not None][-1]
    for (a, rel, v) in {tuple(x) for x in last["stored_triples"]}:
        fs = [f for f in truth.values() if f["life_id"] == life and SC.owner_match(a, f["owner"]) and str(v).lower() == str(f["value"]).lower()]
        if fs:
            g["owner_value_match"] += 1
            g["relation_equal"] += any(str(rel).strip().lower() == str(f["relation"]).strip().lower() for f in fs)
print("global", dict(g))
c = Counter()
for (life, ti), t in tk.items():
    if t["kind"] != "ask" or t["ask_type"] != "edit": continue
    news = [f for f in t["gold"]["uses_facts"] if f in old_of]
    if len(news) != 1: continue
    row = next(r for r in by_life[life] if r["turn_index"] == ti and r["kind"] == "user")
    mech = SC.score_ask(t, row, conf.get((life, ti)))
    before = [r for r in by_life[life] if r["turn_index"] < ti and r.get("stored_triples") is not None]
    stored = {tuple(x) for x in before[-1]["stored_triples"]} if before else set()
    f = truth[news[0]]
    if BL.held(stored, f) and not BL.held(stored, truth[old_of[news[0]]]) and mech not in ("RIGHT", "RIGHT_CONFIRM"):
        rel_ok = any(SC.owner_match(a, f["owner"]) and str(v).lower() == str(f["value"]).lower() and str(r_).strip().lower() == str(f["relation"]).strip().lower() for (a, r_, v) in stored)
        c[f"new_only_not_right_relation_{'equal' if rel_ok else 'differs'}_{mech}"] += 1
print(dict(sorted(c.items())))
