#!/usr/bin/env python3
"""lis-320 group-speaker check, narrowed (reading thread, 2026-09-27; ADDENDUM-8). New file; claude_lis320_check_we.py
stays as sealed.

Pilot 5 failed PILOT-THRESHOLDS item 1 (someone_else kept 3 of 8 turns, under 40%). One of the five lost turns was a
false drop by check_we's bare "me and" words: "someone told me and im just repeating it". The one change: "me and" and
"and me" count only when joined to a person, as in check_we's "and i" rule: "me and my roommate", "me and Nuroa",
"Nuroa and me", "my wife and me". Every other group word (we, our, us, ...) and every other check is unchanged.
Same flags and outputs as claude_lis320_check.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_check as C  # noqa: E402
import claude_lis320_check_cr as CR  # noqa: E402

GROUP2 = re.compile(r"\b(we|our|ours|us|ourselves|we're|weve|we've|we'd|we'll|both of us)\b", re.I)
MY_JOINT = re.compile(r"\bmy \w+(?:'s)? and (?:i|me)\b|\b(?:i|me) and (?:my|his|her|their)\b", re.I)


def group_speaker(text, names=()):
    t = (text or "").replace("’", "'")
    if GROUP2.search(t) or MY_JOINT.search(t):
        return True
    return any(re.search(rf"\b{re.escape(n)} and (?:i|me)\b|\b(?:i|me) and {re.escape(n)}\b", t, re.I)
               for n in names if n)


def check_turn_we2(d, parsed, i):
    row, why = CR.check_turn_cr(d, parsed, i)
    if group_speaker(parsed[i].get("user"), [p.get("name") for p in d.get("people", [])]):
        return None, ([] if row is not None else list(why)) + ["group_speaker"]
    return row, why


def selftest():
    names = ["Nuroa", "Fenelle"]
    for s in ("Nuroa is a chef and we live in Lotirmoor", "Nuroa and me actually live in Junzocombe",
              "our cat is named gani", "so me and my roommate tirald have been talking", "we’re moving",
              "weve got a dog", "my husband and i moved", "what if fenelle and i just packed up", "my wife and me",
              "me and Nuroa share a flat"):
        assert group_speaker(s, names), s
    for s in ("someone told me and im just repeating it", "latex and me dont get along", "me and dumplings are close",
              "my sister Mira is a nurse", "i went to the well", "were you there", "the wed date is set",
              "im a baker and i live in Dunmere", "she asked me and then left"):
        assert not group_speaker(s, names), s
    fr = lambda act, facts: {"act": act, "facts": facts, "ask": None}  # noqa: E731
    F = lambda o, r, v, m: {"owner": o, "rel": r, "value": v, "mode": m}  # noqa: E731
    T = lambda k, intent, gold, must, **kw: dict({"k": k, "intent": intent, "gold": gold, "must": must,  # noqa: E731
                                                "first_person": False, "must_not": [], "reply_must_not": [],
                                                "ref": None, "role_words": []}, **kw)
    d = {"dialog_id": "we2-1", "opener": False, "proper_values": ["Dunmere"],
         "people": [{"name": "Mira", "gender": "f", "role": "wife"}],
         "turns": [T(1, "teach", fr("STATE", [F("me", "wife", "Mira", "ASSERT")]), ["Mira"], first_person=True,
                     role_words=[["wife"]]),
                   T(2, "teach", fr("STATE", [F("Mira", "city", "Dunmere", "ASSERT")]), ["Mira", "Dunmere"])]}
    turns = [{"n": 1, "reply_before": "", "user": "my wife is Mira"},
             {"n": 2, "reply_before": "ok", "user": "Mira and me live in Dunmere"}]
    C.check_turn = check_turn_we2
    rows, drops, c, fam = C.check_all([d], [{"dialog_id": "we2-1", "parsed": {"turns": turns}}])
    assert [r["id"].rsplit("-", 1)[-1] for r in rows] == ["t1"], rows
    assert drops[0]["k"] == 2 and "group_speaker" in drops[0]["reasons"], drops
    print("check_we2 selftest OK: 1 kept, 1 dropped (group_speaker); bare 'me and' no longer drops")


def main():
    C.check_turn = check_turn_we2
    if "--selftest" in sys.argv:
        return selftest()
    return C.main()


if __name__ == "__main__":
    sys.exit(main())
