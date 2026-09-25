#!/usr/bin/env python3
"""lis-317 part 3 (report only, CPU): compare "am I sure?" gates on the same reader output.

Per-fact release (lis-315 semantics): a greedy fact is SAVED if it passes the live structural
check (claude_lis300_compiler.check_fact) and the gate. A saved fact is RIGHT if it matches a
gold fact of that turn, else WRONG. Gates compared:
  min   lis-300 confidence (min token probability over act + fact JSON) >= t   (live: t = 0.995)
  agree the same (owner, value) comes back with mode ASSERT/CORRECT in >= a of the K samples
  both  agree >= a AND min >= t
Gold:
  --set lis   lis-301 dev (dev.jsonl gold frames): match = lis-300 scorer's match() (owner, value,
              same or narrower relation), gold facts that pass check_fact one at a time (per-fact, as lis-302 arm B).
  --set e2e   e2e DEV rows (rows_e2edev.jsonl): owner + value (USER <-> me, first name ok),
              relation ignored (the bank uses free relation words).
Prints right / wrong facts and wrong turns for every gate setting. Selection rule (PLAN.md):
the agreement level is chosen on lis dev only, as the lowest a whose wrong turns are no more
than the live gate's on lis dev; e2e DEV is then read at that level.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis300_score import match as lis_match  # noqa: E402

WRITABLE = {"ASSERT", "CORRECT"}
USER = {"user", "me", "i", "you", "my"}


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def n(x):
    return " ".join(str(x or "").lower().split())


def e2e_match(f, g):
    go, fo = n(g["owner"]), n(f.get("owner"))
    own = (fo in USER) if go == "user" else (fo == go or fo == go.split()[0] or (fo and go == fo.split()[0]))
    return bool(own) and n(f.get("value")) == n(g["value"])


def agree_count(f, samples):
    k = 0
    for s in samples or []:
        for sf in ((s or {}).get("facts") or []):
            if (isinstance(sf, dict) and str(sf.get("mode", "")).upper() in WRITABLE
                    and n(sf.get("owner")) == n(f.get("owner")) and n(sf.get("value")) == n(f.get("value"))):
                k += 1
                break
    return k


def facts_table(set_name, rows_path, reads_path):
    reads = {r["id"]: r for r in load(reads_path)}
    out = []   # (turn_id, right(bool), minconf, agree)
    gold_total = 0
    for row in load(rows_path):
        rd = reads.get(row["id"])
        if rd is None:
            continue
        turn, prev = row.get("turn", ""), row.get("prev_reply", "")
        if set_name == "lis":
            gw = [g for g in (row["frame"].get("facts") or [])      # per fact, as lis-315 releases
                  if isinstance(g, dict) and CMP.check_fact(g, turn, prev) is None]
            gold_total += len(gw)
            is_right = lambda f: any(lis_match(f, g) == "hit" for g in gw)  # noqa: E731
        else:
            gw = row["facts"] if row["kind"] in ("teach", "correct") else []
            gold_total += len(gw)
            is_right = lambda f: any(e2e_match(f, g) for g in gw)  # noqa: E731
        fr = rd.get("frame") or {}
        confs = rd.get("conf") or []
        for i, f in enumerate(fr.get("facts") or []):
            if not isinstance(f, dict) or CMP.check_fact(f, turn, prev) is not None:
                continue
            if set_name == "lis" and not is_right(f) and any(lis_match(f, g) == "broader" for g in gw):
                continue   # true but vague: neither a hit nor a wrong save (lis-300 rule)
            c = confs[i] if i < len(confs) else 0.0
            out.append((row["id"], is_right(f), c, agree_count(f, rd.get("samples"))))
    return out, gold_total


def tally(tab, keep):
    right = sum(1 for t in tab if t[1] and keep(t))
    wrong = [t for t in tab if not t[1] and keep(t)]
    return right, len(wrong), len({t[0] for t in wrong})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["lis", "e2e"], required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--k", type=int, default=8)
    a = ap.parse_args()
    tab, gold = facts_table(a.set, a.rows, a.reads)
    print(f"[{a.set}] gold writable facts {gold}; structurally writable greedy facts {len(tab)}")
    print("gate                       right  wrong_facts  wrong_turns")
    for t in (0.0, 0.9, 0.98, 0.99, 0.995, 0.999):
        r, w, wt = tally(tab, lambda x, t=t: x[2] >= t)
        print(f"min >= {t:<6}               {r:5d}  {w:11d}  {wt:11d}")
    for k in range(a.k + 1):
        r, w, wt = tally(tab, lambda x, k=k: x[3] >= k)
        print(f"agree >= {k}/{a.k}               {r:5d}  {w:11d}  {wt:11d}")
    for k in range(a.k - 3, a.k + 1):
        for t in (0.9, 0.98):
            r, w, wt = tally(tab, lambda x, k=k, t=t: x[3] >= k and x[2] >= t)
            print(f"agree >= {k}/{a.k} & min >= {t:<5} {r:5d}  {w:11d}  {wt:11d}")


if __name__ == "__main__":
    main()
