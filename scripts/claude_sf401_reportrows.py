#!/usr/bin/env python3
"""sf-401 report-only rows, written after the run on 2026-09-26. Run from the repo root. Counts only."""
# counts only: edit asks by correction style, decoy-checking asks, per arm (report-only rows of PASSMARKS)
import json, random, sys
from collections import Counter, defaultdict
sys.path.insert(0, "scripts")
import claude_e2e336_score as SC
R = "artifacts/claude-sf401-20260926"
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
turns = ld(f"{R}/panel/turns.jsonl"); tk = {(t["life_id"], t["turn_index"]): t for t in turns}
corr = ld(f"{R}/panel/corrections.jsonl"); dec = ld(f"{R}/panel/decoys.jsonl")
print("types gold/new_fact/checked_by:", Counter(type(t["gold"]).__name__ for t in turns if t["kind"] == "ask"),
      Counter(type(c["new_fact"]).__name__ for c in corr), Counter(type(d["checked_by"]).__name__ for d in dec))
print("gold keys:", Counter(k for t in turns if t["kind"] == "ask" for k in t["gold"]))
fids = {f["fact_id"] for f in ld(f"{R}/panel/truth.jsonl")}
print("new_fact is a fact_id:", sum(c["new_fact"] in fids for c in corr), "of", len(corr),
      "| old_fact is a fact_id:", sum(c["old_fact"] in fids for c in corr))
print("checked_by is an ask turn in the same life:", sum(tk.get((d["life_id"], d["checked_by"]), {}).get("kind") == "ask" for d in dec), "of", len(dec))
from pathlib import Path
import claude_sf401_diag as DG
final = DG.final_verdicts(Path(f"{R}/score"), Path(f"{R}/judges"), Path(f"{R}/judges/j1.jsonl"),
                          Path(f"{R}/judges/j2.jsonl"), Path(f"{R}/judges/j3.jsonl"))
style_of = {c["new_fact"]: str(c["style"]) for c in corr}
out = {}
for arm in ("A", "B"):
    rows = ld(f"{R}/run/arm_{arm}.jsonl")
    conf = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
    mech = {}
    for r in rows:
        t = tk.get((r["life_id"], r["turn_index"]))
        if r["kind"] == "user" and t is not None and t["kind"] == "ask":
            mech[(r["life_id"], r["turn_index"])] = SC.score_ask(t, r, conf.get((r["life_id"], r["turn_index"])))
    by = defaultdict(Counter)
    nostyle = 0
    for (life, ti), m in mech.items():
        t = tk[(life, ti)]
        if t["ask_type"] != "edit":
            continue
        ss = {style_of[f] for f in t["gold"]["uses_facts"] if f in style_of}
        s = ss.pop() if len(ss) == 1 else ("none" if not ss else "multi")
        by[s]["asks"] += 1
        by[s]["right"] += m in ("RIGHT", "RIGHT_CONFIRM")
        by[s]["judged_wrong"] += final.get((arm, life, ti)) == "wrong"
    dk = {(d["life_id"], d["checked_by"]) for d in dec}
    dc = Counter()
    for k in dk:
        m = mech.get(k)
        dc["asks"] += 1
        dc["right"] += m in ("RIGHT", "RIGHT_CONFIRM")
        dc["abstain"] += m == "ABSTAIN"
        dc["judged_wrong"] += final.get((arm,) + k) == "wrong"
    out[arm] = {"edit_by_style": {k: dict(v) for k, v in sorted(by.items())}, "decoy_checking_asks": dict(dc),
                "asks_scored": len(mech)}
print(json.dumps(out, sort_keys=True))
