#!/usr/bin/env python3
"""lis-317 (report only): score the reader's raw reads on the e2e DEV bank, before any gate.

Inputs: rows_e2edev.jsonl (claude_lis317_rows.py) and the GPU output of claude_lis317_sample.py.
Counts (all integers; DEV data):
  R0      gold teach/correct facts found in the greedy read with a writable mode (ASSERT/CORRECT),
          owner + value matching (owner: USER <-> me; else full or first name, any case; value any case).
  R0rel   the same, also requiring rel == the bank's relation (the bank uses free relation words,
          so this is a lower bound).
  RT      R0 facts whose lis-300 confidence clears T = 0.995 (the live gate).
  W0      writable facts in greedy reads that match no gold fact of that turn (every turn, incl.
          nosave / smalltalk / ask turns): candidate wrong saves with no gate.
  agree   for every greedy writable fact, how many of the K samples contain the same
          (owner, value) with a writable mode; recall / wrong counts at each agreement level.
  ask     for ask turns: greedy act is ASK; ask owner matches a used fact's owner.
Decision rule (fixed in PLAN.md before the GPU run) is printed at the end.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

WRITABLE = {"ASSERT", "CORRECT"}
USER = {"user", "me", "i", "you", "my"}
T = 0.995


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def own_ok(gold, got):
    g, s = str(gold).strip().lower(), str(got).strip().lower()
    if g == "user":
        return s in USER
    return s == g or s == g.split()[0] or g == s.split()[0] if s else False


def val_ok(gold, got):
    return str(gold).strip().lower() == str(got).strip().lower()


def writable(fr):
    return [f for f in ((fr or {}).get("facts") or []) if str(f.get("mode", "ASSERT")).upper() in WRITABLE]


def matches(gf, f):
    return own_ok(gf["owner"], f.get("owner", "")) and val_ok(gf["value"], f.get("value", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = {r["id"]: r for r in load(a.rows)}
    reads = {r["id"]: r for r in load(a.reads)}
    c = Counter()
    agree_right, agree_wrong = Counter(), Counter()
    k_max = 0
    for rid, row in rows.items():
        rd = reads.get(rid)
        if rd is None:
            c["missing_read"] += 1
            continue
        fr = rd["frame"]
        if fr is None:
            c["unparsed"] += 1
        wf = writable(fr)
        allf = (fr or {}).get("facts") or []
        confs = rd.get("conf") or []
        samples = rd.get("samples") or []
        k_max = max(k_max, len(samples))
        gold = row["facts"] if row["kind"] in ("teach", "correct") else []
        for gf in gold:
            c["gold"] += 1
            hit = [i for i, f in enumerate(allf) if matches(gf, f)
                   and str(f.get("mode", "ASSERT")).upper() in WRITABLE]
            anyhit = [f for f in allf if matches(gf, f)]
            if hit:
                c["R0"] += 1
                i = hit[0]
                if str(allf[i].get("rel", "")).lower() == gf["relation"].lower():
                    c["R0rel"] += 1
                if i < len(confs) and confs[i] >= T:
                    c["RT"] += 1
                if str(allf[i].get("owner", "")).lower() in ("he", "she", "they", "her", "his", "him", "them"):
                    c["R0_pronoun_owner"] += 1
            elif anyhit:
                c["found_not_writable_mode:" + str(anyhit[0].get("mode"))] += 1
            else:
                c["not_found"] += 1
        for f in wf:
            right = any(matches(gf, f) for gf in gold)
            c["W_total"] += 1
            if not right:
                c["W0"] += 1
                c["W0_kind:" + row["kind"]] += 1
            n = sum(1 for s in samples if any(
                str(sf.get("owner", "")).lower() == str(f.get("owner", "")).lower() and val_ok(sf.get("value", ""), f.get("value", ""))
                for sf in writable(s)))
            (agree_right if right else agree_wrong)[n] += 1
        if row["kind"] == "ask":
            c["ask_turns"] += 1
            if fr and fr.get("act") == "ASK":
                c["ask_act_ASK"] += 1
    lines = [f"{k}: {v}" for k, v in sorted(c.items())]
    lines.append(f"agreement (K={k_max}): level -> right writable facts kept / wrong writable facts kept")
    for lvl in range(k_max + 1):
        r = sum(v for n, v in agree_right.items() if n >= lvl)
        w = sum(v for n, v in agree_wrong.items() if n >= lvl)
        lines.append(f"  >= {lvl}/{k_max}: right {r}, wrong {w}")
    g = c["gold"] or 1
    lines.append(f"R0 = {c['R0']}/{c['gold']} = {100 * c['R0'] / g:.1f}%   RT = {c['RT']}/{c['gold']}   W0 = {c['W0']}")
    if c["R0"] >= 0.80 * g:
        lines.append("DECISION (PLAN.md rule): R0 >= 80% -> the reader reads chat; lead fix = the gate.")
    elif c["R0"] < 0.60 * g:
        lines.append("DECISION (PLAN.md rule): R0 < 60% -> the reader misreads chat; lead fix = retrain the reader on chatty turns.")
    else:
        lines.append("DECISION (PLAN.md rule): 60-80% -> both; the gate first (no training).")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
