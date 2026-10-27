#!/usr/bin/env python3
"""Exp 252b scorer (read-only).

dev: claude_corr252b_score.py dev <dev252b.jsonl> <mine rows> <252 rows>
  junk write     = a triple present after the turn (or followup) that was not
                   there after setup and is not the item's "new" triple
  wrong removal  = a triple gone after the turn that is not the item's
                   "target" triple
  question write = any store change on a question_tail item
  control        = rows identical to 252's rows (all fields but ms_per_turn)
  Bars: 0 / 0 / 0 and controls identical. Also reports per-family "acted"
  counts (target removed) for information only.
m1: claude_corr252b_score.py m1 <252 panel rows> <252b panel rows>
  every row identical except ms_per_turn, except c252-022 which must have
  stored_after_turn == stored_after_setup and a followup that does not
  contain "that's outdated" (the junk value).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def rows(p):
    return {json.loads(line)["id"]: json.loads(line) for line in
            Path(p).read_text(encoding="utf-8").splitlines() if line.strip()}


def T(xs):
    return {tuple(str(v).lower() for v in x) for x in xs}


def strip(r):
    r = dict(r)
    r.pop("ms_per_turn", None)
    return r


def dev(cases, mine, ref) -> int:
    items = [json.loads(line) for line in
             Path(cases).read_text(encoding="utf-8").splitlines() if line]
    M, R = rows(mine), rows(ref)
    out = {"junk_writes": [], "wrong_removals": [], "question_writes": [],
           "control_diffs": [], "acted": {}, "n": {}}
    for it in items:
        r = M[it["id"]]
        fam = it["family"]
        out["n"][fam] = out["n"].get(fam, 0) + 1
        a = T(r["stored_after_setup"])
        new = T([it["new"]]) if it.get("new") else set()
        tgt = T([it["target"]]) if it.get("target") else set()
        for key in ("stored_after_turn", "stored_after_followup"):
            b = T(r[key])
            if b - a - new:
                out["junk_writes"].append([it["id"], key, sorted(b - a - new)])
            if a - b - tgt:
                out["wrong_removals"].append([it["id"], key,
                                              sorted(a - b - tgt)])
        if fam == "question_tail" and (
                T(r["stored_after_turn"]) != a
                or T(r["stored_after_followup"]) != a):
            out["question_writes"].append(it["id"])
        if fam == "control" and strip(r) != strip(R[it["id"]]):
            out["control_diffs"].append(it["id"])
        if tgt and not (tgt & T(r["stored_after_turn"])):
            out["acted"][fam] = out["acted"].get(fam, 0) + 1
    out["M2_pass"] = not (out["junk_writes"] or out["wrong_removals"]
                          or out["question_writes"] or out["control_diffs"])
    print(json.dumps(out, indent=1))
    return 0


def m1(a, b) -> int:
    A, B = rows(a), rows(b)
    diffs, ok022 = [], None
    for k in A:
        if k == "c252-022":
            r = B[k]
            ok022 = (T(r["stored_after_turn"]) == T(r["stored_after_setup"])
                     and T(r["stored_after_followup"])
                     == T(r["stored_after_setup"])
                     and not re.search(r"that'?s outdated",
                                       r["followup_reply"], re.I))
            continue
        if strip(A[k]) != strip(B.get(k, {})):
            diffs.append(k)
    out = {"rows_252": len(A), "rows_252b": len(B), "other_diffs": diffs,
           "c252_022_ok": ok022,
           "M1_pass": ok022 is True and not diffs and len(A) == len(B)}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    mode = sys.argv[1]
    sys.exit(dev(*sys.argv[2:5]) if mode == "dev" else m1(*sys.argv[2:4]))
