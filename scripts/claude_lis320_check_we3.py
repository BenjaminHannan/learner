#!/usr/bin/env python3
"""lis-320 checks with the plan cue list matched to the plan instruction (reading thread, 2026-09-27; ADDENDUM-10).
New file; claude_lis320_check.py and claude_lis320_check_we2.py stay as sealed.

The seeder tells the writer a plan turn means "the user says this will or may happen in the future; it is not true
yet" (claude_lis320_seed.INTENT_GLOSS["plan"]), but the plan cue list only held will-words (going to, gonna, will,
soon, ...). Luna pilot 7 wrote the "may" half ("Zous might get a cat named Holo", "... in the future", "one day") and
9 of 11 plan turns were dropped for no_cue. The change: the plan cue list also takes might, may, someday, some day,
one day, eventually, in the future, later on, at some point, down the line, sometime. Every other check is check_we2's.
Same flags and outputs as claude_lis320_check.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_check as C  # noqa: E402
import claude_lis320_check_we2 as W2  # noqa: E402

PLAN3 = re.compile(r"\b(going to|gonna|will|next|plan|plans|planning|wants? to|hoping|hopes? to|about to|soon|"
                   r"thinking of|thinking about|might|may|someday|some day|one day|eventually|in the future|later on|"
                   r"at some point|down the line|sometime)\b|'ll\b", re.I)


def install():
    C.CUES["plan"] = PLAN3
    C.check_turn = W2.check_turn_we2


def selftest():
    old = C.CUES["plan"]
    for s in ("i might get a cat and name it Sikin one day", "Tavor may work at Nedel Print in the future",
              "eventually im moving to Lesiby", "gonna start knitting", "i'll be a pilot"):
        assert PLAN3.search(s), s
    for s in ("my cat is Sikin", "i work at Nedel Print"):
        assert not PLAN3.search(s), s
    for s in ("gonna start knitting", "i'll be a pilot", "we plan to move"):
        assert bool(old.search(s)) == bool(PLAN3.search(s)), s        # the old cues still match
    fr = lambda act, facts: {"act": act, "facts": facts, "ask": None}  # noqa: E731
    F = lambda o, r, v, m: {"owner": o, "rel": r, "value": v, "mode": m}  # noqa: E731
    T = lambda k, intent, gold, must, **kw: dict({"k": k, "intent": intent, "gold": gold, "must": must,  # noqa: E731
                                                "first_person": False, "must_not": [], "reply_must_not": [],
                                                "ref": None, "role_words": []}, **kw)
    d = {"dialog_id": "we3-1", "opener": False, "proper_values": ["Dunmere"], "people": [],
         "turns": [T(1, "plan", fr("PLAN", [F("me", "city", "Dunmere", "PLAN")]), ["Dunmere"], first_person=True)]}
    turns = [{"n": 1, "reply_before": "", "user": "i might end up living in Dunmere someday"}]
    install()
    rows, drops, c, fam = C.check_all([d], [{"dialog_id": "we3-1", "parsed": {"turns": turns}}])
    assert fam["plan"] == 1 and not drops, (drops, c)
    C.CUES["plan"] = old
    rows, drops, c, fam = C.check_all([d], [{"dialog_id": "we3-1", "parsed": {"turns": turns}}])
    assert drops and "no_cue" in drops[0]["reasons"], drops           # the old list drops it
    print("check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    install()
    return C.main()


if __name__ == "__main__":
    sys.exit(main())
