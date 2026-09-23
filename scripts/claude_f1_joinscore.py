#!/usr/bin/env python3
"""Exp F1 joinpanel292t regression scorer (regression only, mechanical).

New file only. Compares two registered arm outputs produced with 292t's
sealed runner (scripts/claude_join292t_run.py panel, read-only):
  <run>/joinpanel-292t.json vs <run>/joinpanel-f1.json
  <run>/joinprobes-292t.json vs <run>/joinprobes-f1.json
plus the F1 mouth log (<run>/joinmouthf1.jsonl, MOUTH241B_LOG).

Bars (regression only):
  - 0 store diffs: per turn ev + triples identical, per dialog stored
    identical, between F1 and 292t.
  - 0 write-count diffs on every turn.
  - every reply diff is a 241b rewrite: the F1 mouth log holds an entry
    with route A mapping the 292t line to the F1 line for that turn.
Prints ids of reply-diff turns and integer counts only; never prints turn
or reply text (blind panel discipline).

Usage:
  uv ... python -B scripts/claude_f1_joinscore.py <run> <out.json>
"""

from __future__ import annotations

import json
import sys


def load(p):
    return json.load(open(p))


def main() -> int:
    run, outp = sys.argv[1], sys.argv[2]
    a = load(f"{run}/joinpanel-292t.json")
    b = load(f"{run}/joinpanel-f1.json")
    ma = {d["id"]: d for d in a}
    mb = {d["id"]: d for d in b}
    mouth = [json.loads(x) for x in
             open(f"{run}/joinmouthf1.jsonl", encoding="utf-8")
             if x.strip()]
    # index mouth entries by (turn, out)
    by_turn: dict[str, list] = {}
    for e in mouth:
        by_turn.setdefault(str(e.get("turn")), []).append(e)
    n_turns = n_diff = n_store = 0
    diff_ids = []
    store_ids = []
    unattributed = []
    for did, da in ma.items():
        db = mb.get(did)
        if db is None:
            store_ids.append(f"{did}:missing-in-f1")
            continue
        if da.get("stored") != db.get("stored"):
            n_store += 1
            store_ids.append(f"{did}:stored")
        for i, (ra, rb) in enumerate(zip(da.get("rows", []),
                                         db.get("rows", []))):
            n_turns += 1
            tid = f"{did}#{i}"
            if ra.get("ev") != rb.get("ev") or \
                    ra.get("triples") != rb.get("triples"):
                n_store += 1
                store_ids.append(tid)
            if str(ra.get("reply", "")) != str(rb.get("reply", "")):
                n_diff += 1
                diff_ids.append(tid)
                ok = any(e.get("route") == "A"
                         and e.get("in") == ra.get("reply")
                         and e.get("out") == rb.get("reply")
                         for e in by_turn.get(str(ra.get("turn")), []))
                if not ok:
                    unattributed.append(tid)
    pa = load(f"{run}/joinprobes-292t.json")
    pb = load(f"{run}/joinprobes-f1.json")
    probe_diff = []
    probe_store = []
    for k in pa:
        if pa.get(k, {}).get("reply") != pb.get(k, {}).get("reply"):
            probe_diff.append(k)
        if pa.get(k, {}).get("writes") != pb.get(k, {}).get("writes") or \
                pa.get(k, {}).get("stored") != pb.get(k, {}).get("stored"):
            probe_store.append(k)
    problems = []
    if n_store:
        problems.append(f"store/ev diffs: {store_ids}")
    if unattributed:
        problems.append(f"reply diffs not route-A rewrites: {unattributed}")
    if probe_store:
        problems.append(f"probe store/write diffs: {probe_store}")
    res = {"n_turns": n_turns, "n_reply_diff_turns": n_diff,
           "diff_ids": diff_ids, "n_store_diff": n_store,
           "store_ids": store_ids, "unattributed": unattributed,
           "probe_reply_diff": probe_diff, "probe_store_diff": probe_store,
           "verdict": "PASS" if not problems else "FAIL",
           "problems": problems}
    json.dump(res, open(outp, "w"), indent=1)
    print(f"turns={n_turns} reply_diff={n_diff} store_diff={n_store} "
          f"unattributed={len(unattributed)} "
          f"probe_diff={len(probe_diff)} probe_store={len(probe_store)} "
          f"VERDICT={res['verdict']}")
    for p in problems:
        print("PROBLEM:", p)
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
