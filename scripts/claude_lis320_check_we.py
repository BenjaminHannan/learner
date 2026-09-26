#!/usr/bin/env python3
"""lis-320 code checks plus one group-speaker check (reading thread, 2026-09-26; ADDENDUM-7). New file;
claude_lis320_check.py and claude_lis320_check_cr.py run unchanged underneath.

Pilot 4's hand read found 3 of 20 kept labels wrong, all one flaw: GLM worded a one-owner plan fact as a shared one
("we live in Lotirmoor", "Nuroa and me actually live in Junzocombe", "our cat is named gani"), so the text states a
second owner's fact that the plan label leaves out. The one change: a turn in which the user speaks for a group is
dropped with reason "group_speaker". Group words: we, our, ours, us, ourselves, we're, we've, we'd, we'll (with or
without the apostrophe where that is not another word), "both of us", "me and", "and me", and "and i" / "i and" joined to a
person of the dialog or to "my <word>" ("fenelle and i", "my wife and i"). Every other check is as before.
Same flags and outputs as claude_lis320_check.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_check as C  # noqa: E402
import claude_lis320_check_cr as CR  # noqa: E402

GROUP = re.compile(r"\b(we|our|ours|us|ourselves|we're|weve|we've|we'd|we'll|both of us|me and|and me)\b", re.I)


MY_AND_I = re.compile(r"\bmy \w+(?:'s)? and i\b|\bi and my\b", re.I)


def group_speaker(text, names=()):
    t = (text or "").replace("’", "'")
    if GROUP.search(t) or MY_AND_I.search(t):
        return True
    return any(re.search(rf"\b{re.escape(n)} and i\b|\bi and {re.escape(n)}\b", t, re.I) for n in names if n)


def check_turn_we(d, parsed, i):
    row, why = CR.check_turn_cr(d, parsed, i)
    if group_speaker(parsed[i].get("user"), [p.get("name") for p in d.get("people", [])]):
        return None, ([] if row is not None else list(why)) + ["group_speaker"]
    return row, why


def selftest():
    for s in ("Nuroa is a chef and we live in Lotirmoor", "Nuroa and me actually live in Junzocombe",
              "our cat is named gani", "me and my sister share a flat", "we’re moving", "weve got a dog"):
        assert group_speaker(s), s
    for s in ("my sister Mira is a nurse", "i went to the well", "she used to own a bus", "were you there",
              "the wed date is set", "use the ourt", "im a baker and i live in Dunmere"):
        assert not group_speaker(s, ["Mira"]), s
    for s in ("my husband and i moved", "what if fenelle and i just packed up", "i and Mira"):
        assert group_speaker(s, ["Fenelle", "Mira"]), s
    fr = lambda act, facts: {"act": act, "facts": facts, "ask": None}  # noqa: E731
    F = lambda o, r, v, m: {"owner": o, "rel": r, "value": v, "mode": m}  # noqa: E731
    T = lambda k, intent, gold, must, **kw: dict({"k": k, "intent": intent, "gold": gold, "must": must,  # noqa: E731
                                                "first_person": False, "must_not": [], "reply_must_not": [],
                                                "ref": None, "role_words": []}, **kw)
    d = {"dialog_id": "we-1", "opener": False, "proper_values": ["Dunmere"],
         "people": [{"name": "Mira", "gender": "f", "role": "wife"}],
         "turns": [T(1, "teach", fr("STATE", [F("me", "wife", "Mira", "ASSERT")]), ["Mira"], first_person=True,
                     role_words=[["wife"]]),
                   T(2, "teach", fr("STATE", [F("Mira", "city", "Dunmere", "ASSERT")]), ["Mira", "Dunmere"])]}
    turns = [{"n": 1, "reply_before": "", "user": "my wife is Mira"},
             {"n": 2, "reply_before": "ok", "user": "Mira and me live in Dunmere"}]
    C.check_turn = check_turn_we
    rows, drops, c, fam = C.check_all([d], [{"dialog_id": "we-1", "parsed": {"turns": turns}}])
    assert [r["id"].rsplit("-", 1)[-1] for r in rows] == ["t1"], rows
    assert drops[0]["k"] == 2 and "group_speaker" in drops[0]["reasons"], drops
    assert c["drop:group_speaker"] == 1, c
    print("check_we selftest OK: 1 kept, 1 dropped (group_speaker)")


def main():
    C.check_turn = check_turn_we
    if "--selftest" in sys.argv:
        return selftest()
    return C.main()


if __name__ == "__main__":
    sys.exit(main())
