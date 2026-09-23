#!/usr/bin/env python3
"""Experiment 215 -- marks123 per-case diff vs sealed marks138i rows (Muse).

Compares /tmp pilot (or registered) marks123 output dir against
artifacts/fable-agent138i-20260922/marks138i. Volatile fields ignored:
`seconds` timings, l6 `replied_before_kill` kill-timing counts, sleep
SKIP reason agent filename. Prints per-suite move lists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

NEW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/tmp/o215-pilot/marks123")
BASE = Path("artifacts/fable-agent138i-20260922/marks138i")

VOLATILE = {"seconds", "total_seconds"}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def norm_reply(s) -> str:
    return str(s or "").strip()


moves_total = 0
def strip_seconds(o):
    if isinstance(o, dict):
        return {k: ("VOLATILE" if k in VOLATILE else strip_seconds(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [strip_seconds(v) for v in o]
    return o


print("=== p2 ===")
n2, b2 = load(NEW / "p2-report.json"), load(BASE / "p2-report.json")
nrows = {r["id"]: r for r in n2.get("rows", n2.get("cases", []))}
brows = {r["id"]: r for r in b2.get("rows", b2.get("cases", []))}
m = [i for i in nrows if i in brows and json.dumps(
    {k: v for k, v in nrows[i].items() if k not in VOLATILE}, sort_keys=True)
    != json.dumps({k: v for k, v in brows[i].items() if k not in VOLATILE},
                  sort_keys=True)]
only = [i for i in nrows if i not in brows] + [i for i in brows
                                               if i not in nrows]
print(f"p2 rows {len(nrows)}/{len(brows)} moves={len(m)} only-one-side={only}")
for i in m[:20]:
    print(f"  {i}: 138i={json.dumps(brows[i])[:150]}")
    print(f"  {i}: 215 ={json.dumps(nrows[i])[:150]}")
moves_total += len(m) + len(only)

print("=== p4 ===")
n4, b4 = load(NEW / "p4-report.json"), load(BASE / "p4-report.json")
for key in ("false_refusals", "nonpass", "non_pass", "rows", "cases"):
    if key in n4 or key in b4:
        nv, bv = n4.get(key), b4.get(key)
        print(f"p4.{key}: same={json.dumps(nv, sort_keys=True) == json.dumps(bv, sort_keys=True)}")
        if json.dumps(nv, sort_keys=True) != json.dumps(bv, sort_keys=True):
            moves_total += 1
            print(f"  138i={json.dumps(bv)[:300]}")
            print(f"  215 ={json.dumps(nv)[:300]}")

print("=== rt110 ===")
n1, b1 = load(NEW / "rt110-report.json"), load(BASE / "rt110-report.json")
for key in ("ok_to_bug", "still_bug", "harness_errors", "rows", "cases",
            "bugs", "ok_to_bug_ids", "still_bug_ids"):
    if key in n1 or key in b1:
        nv, bv = n1.get(key), b1.get(key)
        same = json.dumps(nv, sort_keys=True) == json.dumps(bv, sort_keys=True)
        print(f"rt110.{key}: same={same}")
        if not same:
            moves_total += 1
            print(f"  138i={json.dumps(bv)[:300]}")
            print(f"  215 ={json.dumps(nv)[:300]}")

print("=== q1/q4 ===")
for f in ("q1-report.json", "q4-report.json"):
    nv, bv = load(NEW / f), load(BASE / f)
    nv2 = {k: v for k, v in nv.items() if k not in VOLATILE}
    bv2 = {k: v for k, v in bv.items() if k not in VOLATILE}
    same = json.dumps(nv2, sort_keys=True) == json.dumps(bv2, sort_keys=True)
    print(f"{f}: same={same}")
    if not same:
        moves_total += 1
        print(f"  138i={json.dumps(bv2)[:400]}")
        print(f"  215 ={json.dumps(nv2)[:400]}")

print("=== bench rows ===")
for split in ("fable_edit_200", "s2fresh_4hop"):
    nf = [json.loads(l) for l in
          (NEW / f"bench-rows-{split}.jsonl").read_text(
              encoding="utf-8").splitlines() if l.strip()]
    bf = [json.loads(l) for l in
          (BASE / f"bench-rows-{split}.jsonl").read_text(
              encoding="utf-8").splitlines() if l.strip()]
    nb = {r["id"]: r for r in nf}
    bb = {r["id"]: r for r in bf}
    mm = [i for i in nb if i in bb and nb[i].get("verdict")
          != bb[i].get("verdict")]
    nw = sum(1 for i in mm if bb[i].get("verdict") != "wrong"
             and nb[i].get("verdict") == "wrong")
    print(f"{split}: n={len(nf)}/{len(bf)} verdict-moves={len(mm)} "
          f"new_wrong={nw}")
    for i in mm[:30]:
        print(f"  {i}: 138i={bb[i].get('verdict')} "
              f"215={nb[i].get('verdict')}")
    moves_total += len(mm)

print("=== rt81 ===")
n8, b8 = load(NEW / "rt81-report.json"), load(BASE / "rt81-report.json")
n82 = {k: v for k, v in n8.items() if k not in VOLATILE}
b82 = {k: v for k, v in b8.items() if k not in VOLATILE}
same = json.dumps(n82, sort_keys=True) == json.dumps(b82, sort_keys=True)
print(f"rt81: same={same}")
if not same:
    moves_total += 1
    for k in sorted(set(n82) | set(b82)):
        if json.dumps(n82.get(k), sort_keys=True) != json.dumps(
                b82.get(k), sort_keys=True):
            print(f"  .{k}: 138i={json.dumps(b82.get(k))[:300]}")
            print(f"  .{k}: 215 ={json.dumps(n82.get(k))[:300]}")

print("=== p3/soak/sleep ===")
for f in ("p3-report.json", "soak-report.json", "sleep-report.json"):
    nv, bv = load(NEW / f), load(BASE / f)
    if f == "sleep-report.json":
        nv = dict(nv)
        bv = dict(bv)
        nv["reason"] = str(nv.get("reason", "")).replace(
            "fable_loop215_agent.py", "AGENT")
        bv["reason"] = str(bv.get("reason", "")).replace(
            "fable_loop138i_agent.py", "AGENT")
    nv2 = strip_seconds(nv)
    bv2 = strip_seconds(bv)
    if f == "p3-report.json":
        for rep in (nv2, bv2):
            marks = (rep.get("marks") or {}).get("l6") or {}
            if isinstance(marks, dict) and "replied_before_kill" in marks:
                marks = dict(marks)
                marks["replied_before_kill"] = "VOLATILE"
                rep["marks"]["l6"] = marks
    same = json.dumps(nv2, sort_keys=True) == json.dumps(bv2, sort_keys=True)
    print(f"{f}: same={same}")
    if not same:
        moves_total += 1
        print(f"  138i={json.dumps(bv2)[:500]}")
        print(f"  215 ={json.dumps(nv2)[:500]}")

print(f"MOVES_TOTAL={moves_total}")
