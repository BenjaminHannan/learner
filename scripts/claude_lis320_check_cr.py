#!/usr/bin/env python3
"""lis-320 code checks with the correct_ref intent (reading thread, 2026-09-26; ADDENDUM-5). New file;
claude_lis320_check.py is sealed by y1t and runs unchanged for every other intent.

A correct_ref turn (claude_lis320_seed_cr.py) is checked exactly as a backref turn: owner not in the turn or the reply,
owner named in the visible history, the ref word present, the pronoun unique or the role link visible, no hedge, not
read as former; plus the generic must / must_not checks (new value, and the old value named or not as asked). Its label
is the gold CORRECT frame with the owner as typed in the history. Kept rows carry family "correct_ref".
Same flags and outputs as claude_lis320_check.py.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_check as C  # noqa: E402

_BASE = C.check_turn


def check_turn_cr(d, parsed, i):
    t = d["turns"][i]
    if t["intent"] != "correct_ref":
        return _BASE(d, parsed, i)
    d2 = dict(d, turns=list(d["turns"]))
    d2["turns"][i] = dict(t, intent="backref")
    row, why = _BASE(d2, parsed, i)
    if row is not None:
        row["family"] = "correct_ref"
    return row, why


def selftest():
    fr = lambda act, facts: {"act": act, "facts": facts, "ask": None}  # noqa: E731
    F = lambda o, r, v, m, old=None: dict({"owner": o, "rel": r, "value": v, "mode": m}, **({"old": old} if old else {}))  # noqa: E731
    T = lambda k, intent, gold, must, **kw: dict({"k": k, "intent": intent, "gold": gold, "must": must,  # noqa: E731
                                                "first_person": False, "must_not": [], "reply_must_not": [],
                                                "ref": None, "role_words": []}, **kw)
    ref = {"kind": "pronoun", "gender": "f", "words": ["she", "her", "hers"]}
    d = {"dialog_id": "cr-1", "opener": False, "proper_values": [],
         "people": [{"name": "Mira", "gender": "f", "role": "sister"}, {"name": "Tovan", "gender": "m", "role": "boss"}],
         "turns": [
             T(1, "teach", fr("STATE", [F("me", "sister", "Mira", "ASSERT"), F("Mira", "occupation", "nurse", "ASSERT")]),
               ["Mira", "nurse"], first_person=True, role_words=[["sister"]]),
             T(2, "correct_ref", fr("CORRECT", [F("Mira", "occupation", "midwife", "CORRECT", "nurse")]),
               ["midwife", "nurse"], must_not=["Mira"], reply_must_not=["Mira"], ref=ref),
             T(3, "correct_ref", fr("CORRECT", [F("Mira", "occupation", "doctor", "CORRECT")]),
               ["doctor"], must_not=["Mira", "midwife"], reply_must_not=["Mira"], ref=ref)]}
    turns = [{"n": 1, "reply_before": "", "user": "my sister Mira is a nurse"},
             {"n": 2, "reply_before": "nice", "user": "oops she's not a nurse, she's a midwife"},
             {"n": 3, "reply_before": "ok", "user": "actually Mira is a doctor now"}]
    rows, drops, c, fam = C.check_all([d], [{"dialog_id": "cr-1", "parsed": {"turns": turns}}])
    assert fam["correct_ref"] == 1, fam
    r = next(x for x in rows if x["family"] == "correct_ref")
    f = r["frame"]["facts"][0]
    assert r["frame"]["act"] == "CORRECT" and f["owner"] == "Mira" and f["value"] == "midwife" and f["old"] == "nurse", r
    dr = next(x for x in drops if x["k"] == 3)
    assert dr["intent"] == "correct_ref" and "forbidden_in_turn" in dr["reasons"], dr
    print("check_cr selftest OK: 1 kept (owner from history), 1 dropped (owner named)")


def main():
    C.check_turn = check_turn_cr
    if "--selftest" in sys.argv:
        return selftest()
    return C.main()


if __name__ == "__main__":
    sys.exit(main())
