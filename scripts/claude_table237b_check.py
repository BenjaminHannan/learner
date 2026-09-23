#!/usr/bin/env python3
"""Exp 237b table checks (no agent): pattern count, surface collisions,
v1.1 rows kept, reading time, and readings for a list of questions.
Usage: check.py [questions.txt]"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_fix221_tableask as T
import claude_loop237_agent as L237
ROOT = Path(__file__).resolve().parent.parent
V11 = ROOT / "artifacts/claude-table237-20260922/relation_table_v1_1.json"
V12 = ROOT / "artifacts/claude-table237b-20260922/relation_table_v1_2.json"
t11, t12 = T.Table221(V11), T.Table221(V12)
print(f"v1.1 relations={len(t11.rels)} patterns={len(t11.patterns)}")
print(f"v1.2 relations={len(t12.rels)} patterns={len(t12.patterns)}")
# every v1.1 key still maps to the same relation
bad = [k for k, r in t11.key2rel.items() if t12.key2rel.get(k) != r]
print("v1.1 keys remapped:", bad)
# surfaces claimed by two relations
seen = {}
coll = []
for r in json.loads(V12.read_text())["relations"]:
    for s in [r["name"]] + [T.key221(a) for a in r["aliases"]] + r.get("storage_keys", []):
        k = T.key221(s)
        if k in seen and seen[k] != r["name"]:
            coll.append((k, seen[k], r["name"]))
        seen.setdefault(k, r["name"])
print("surface collisions:", coll)
qs = [l.strip() for l in open(sys.argv[1])] if len(sys.argv) > 1 else []
qs = [q for q in qs if q and not q.startswith("#")]
for tb, nm in ((t11, "v1.1"), (t12, "v1.2")):
    t0 = time.perf_counter(); n = 0
    for _ in range(3):
        for q in qs or ["Who is the landlord for Kim Vale?"]:
            L237.table_readings237(q, tb); n += 1
    print(f"{nm} ms/question (readings only) = {(time.perf_counter()-t0)*1000/n:.3f}")
for q in qs:
    rd = L237.table_readings237(q, t12)
    out = [(r["rel"], r["kind"], r["X"] or r["Y"]) for r in rd]
    print(("AMBIG " if len(rd) > 1 else "NONE  " if not rd else "ok    ") + f"{q!r} -> {out}")
