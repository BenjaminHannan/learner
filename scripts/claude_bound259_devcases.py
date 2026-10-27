#!/usr/bin/env python3
"""Exp 259 dev set (own wordings, fictional names; nothing copied from any
panel). Writes artifacts/claude-boundary259-20260922/dev259.jsonl.

Item shape = corrpanel shape (setup, turn, followup, stated_facts, target,
expect_gone, expect_store, gold_followup, note) + dev-only fields:
  "restart": true  -> the daemon is rebuilt between turn and followup
  "extra": [[question, must_not_contain, must_contain], ...]
  "pred": predicted outcome on 259 ("right", or "miss:<why>")
Families:
  tail_denial   explicit denial of a stored fact + trailing clause
  near_miss     the denied value only shares a prefix with the stored one
  unstored_tail denial with a tail of a fact that is not stored
  question_tail question with a tail: nothing may change
  keep          must-not-change turns: rows byte-identical to 252b's
  pronoun       pronoun denial with a tail (after a one-fact answer)
  restart       tail denial, daemon restart, followup + reverse lookup
stated_facts are the triples the base stores after setup (checked in the
pilot); expect_store / expect_gone follow the corrtail258 rules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("artifacts/claude-boundary259-20260922/dev259.jsonl")
E, CI, L, B, T, PB, MG = ("employer", "city", "language", "boss", "teacher",
                          "place_of_birth", "manager")

NELL = ["Nell", E, "Garrow"]
OSS = ["Ossian", CI, "Pellam"]
QUI = ["Quilla", L, "Vessic"]
RUNE = ["Rune", B, "Tolly"]
SAB = ["Sabra", T, "Wick"]
TAVI = ["Tavi", PB, "Hollin"]
S_NELL, S_OSS, S_QUI = ("Nell works at Garrow.", "Ossian lives in Pellam.",
                        "Quilla speaks Vessic.")
S_RUNE, S_SAB, S_TAVI = ("Rune's boss is Tolly.", "Sabra's teacher is Wick.",
                         "Tavi was born in Hollin.")
Q_NELL, Q_OSS, Q_QUI = ("Where does Nell work?", "Where does Ossian live?",
                        "What language does Quilla speak?")
Q_RUNE, Q_SAB, Q_TAVI = ("Who is Rune's boss?", "Who is Sabra's teacher?",
                         "Where was Tavi born?")

I: list[dict] = []


def add(fam, setup, turn, follow, stated, target, gone, store, gold, note,
        pred="right", **kw):
    it = {"family": fam, "setup": setup, "turn": turn, "followup": follow,
          "stated_facts": stated, "target": target, "expect_gone": gone,
          "expect_store": store, "gold_followup": gold, "note": note,
          "pred": pred}
    it.update(kw)
    I.append(it)


def deny(setup, fact, turn, q, note, pred="right", fam="tail_denial", **kw):
    add(fam, [setup], turn, q, [fact], fact, [fact], [], None, note, pred,
        **kw)


# ---- tail_denial (22): explicit denial of a stored fact + trailing clause
deny(S_NELL, NELL, "Nell doesn't work at Garrow, that's old news.", Q_NELL,
     "that-clause after comma")
deny(S_NELL, NELL, "Nell doesn't work at Garrow, which was years ago.",
     Q_NELL, "which-clause after comma")
deny(S_NELL, NELL, "Nell doesn't work at Garrow, it's wrong now.", Q_NELL,
     "', it's wrong now'")
deny(S_NELL, NELL, "Nell doesn't work at Garrow, not anymore.", Q_NELL,
     "', not anymore'", pred="miss:ears cannot read the clause (unchanged)")
deny(S_NELL, NELL, "Nell doesn't work at Garrow - she quit.", Q_NELL,
     "' - she quit'")
deny(S_NELL, NELL, "Nell doesn't work at Garrow lol", Q_NELL,
     "' lol' (no punctuation; 252b already right)")
deny(S_NELL, NELL, "Nell doesn't work at Garrow btw", Q_NELL,
     "' btw' (no punctuation; 252b already right)")
deny(S_NELL, NELL, "Nell doesn't work at Garrow, sadly.", Q_NELL,
     "', sadly' (252b junk write via the two-clause correction path)",
     pred="miss:junk write 'sadly' stays (not the denial path)")
deny(S_OSS, OSS, "Ossian doesn't live in Pellam (he moved away).", Q_OSS,
     "bracket clause")
deny(S_OSS, OSS, "Ossian doesn't live in Pellam; that was last spring.",
     Q_OSS, "semicolon that-clause", pred="miss:base ears cannot read the sentence; unchanged from 252b")
deny(S_OSS, OSS, "Ossian no longer lives in Pellam, that's outdated.", Q_OSS,
     "'no longer' + that-clause", pred="miss:base ears cannot read the sentence; unchanged from 252b")
deny(S_OSS, OSS, "Ossian doesn't live in Pellam — that's stale.", Q_OSS,
     "em dash clause", pred="miss:base ears cannot read the sentence; unchanged from 252b")
deny(S_QUI, QUI, "Quilla doesn't speak Vessic, that isn't true anymore.",
     Q_QUI, "that-isn't clause")
deny(S_QUI, QUI, "Quilla does not speak Vessic (that's an old note).", Q_QUI,
     "'does not' + bracket")
deny(S_RUNE, RUNE, "Rune's boss isn't Tolly, that's changed.", Q_RUNE,
     "possessive form + that's (252 path)", pred="miss:base ears cannot read the sentence; unchanged from 252b")
deny(S_RUNE, RUNE, "Rune's boss is not Tolly, which is out of date.", Q_RUNE,
     "possessive form + which-clause (154f-owned shape)")
deny(S_RUNE, RUNE, "Tolly isn't Rune's boss (that was last year).", Q_RUNE,
     "reversed form, tail lands in the relation")
deny(S_RUNE, RUNE, "Tolly is not Rune's boss anymore, which was ages ago.",
     Q_RUNE, "reversed form + anymore + which-clause")
deny(S_SAB, SAB, "Sabra's teacher isn't Wick - he retired.", Q_SAB,
     "possessive form + dash clause (154f-owned shape)")
deny(S_SAB, SAB, "Sabra's teacher is not Wick, sadly.", Q_SAB,
     "possessive form + ', sadly' (154f-owned shape)")
deny(S_TAVI, TAVI, "Tavi wasn't born in Hollin, that's a mix-up.", Q_TAVI,
     "born-in + that-clause")
deny(S_NELL, NELL, "nell doesn't work at garrow, that's old news.", Q_NELL,
     "lowercase names")

# ---- near_miss (9): the value only shares a prefix: nothing may change
def near(setup, fact, turn, q, gold, note, pred="right", **kw):
    add("near_miss", [setup], turn, q, [fact], None, [], [fact], gold, note,
        pred, **kw)


near(S_NELL, NELL, "Nell doesn't work at Garrow Hall.", Q_NELL, "Garrow",
     "longer value, no tail (byte-identical to 252b)")
near(S_NELL, NELL, "Nell doesn't work at Garrow Hall, that's wrong.", Q_NELL,
     "Garrow", "longer value + tail")
near(S_NELL, NELL, "Nell doesn't work at Garrowby, that's old.", Q_NELL,
     "Garrow", "prefix-sharing single word")
near("Nell works at Garrow Hall.", ["Nell", E, "Garrow Hall"],
     "Nell doesn't work at Garrow, that's old news.", Q_NELL, "Garrow Hall",
     "stored value is LONGER than the denied one")
near(S_OSS, OSS, "Ossian doesn't live in Pellam Cross (that's wrong).",
     Q_OSS, "Pellam", "two-word value + bracket")
near(S_QUI, QUI, "Quilla doesn't speak Vessican, that's outdated.", Q_QUI,
     "Vessic", "suffix-extended value")
near(S_RUNE, RUNE, "Rune's boss isn't Tollyson, that's changed.", Q_RUNE,
     "Tolly", "prefix-sharing boss")
near(S_NELL, NELL, "Nell doesn't work at Garrow-on-Hythe, that's old.",
     Q_NELL, "Garrow", "hyphen without spaces is not a boundary")
near(S_SAB, SAB, "Sabra's teacher is not Wickham - he retired.", Q_SAB,
     "Wick", "prefix-sharing, 154f-owned shape")

# ---- unstored_tail (7): nothing may change, reply may not claim a change
def unst(setup, fact, turn, q, gold, note, pred="right", **kw):
    add("unstored_tail", [setup], turn, q, [fact], None, [], [fact], gold,
        note, pred, **kw)


unst(S_NELL, NELL, "Nell doesn't work at Brackley, that's old news.", Q_NELL,
     "Garrow", "known person, other value")
unst(S_NELL, NELL, "Bexley doesn't work at Garrow, that's outdated.",
     "Where does Bexley work?", None, "unknown person")
unst(S_OSS, OSS, "Ossian doesn't live in Marrow (that was ages ago).", Q_OSS,
     "Pellam", "known person, other value, bracket")
unst(S_RUNE, RUNE, "Rune's boss isn't Pimm, which is old news.", Q_RUNE,
     "Tolly", "154f-owned shape, other value")
unst(S_QUI, QUI, "Quilla doesn't speak Orvish - that's changed.", Q_QUI,
     "Vessic", "dash clause, other value")
unst(S_NELL, NELL, "Corvin's manager is not Dale, that was never true.",
     "Who is Corvin's manager?", None, "unknown person, possessive form")
unst(S_NELL, NELL, "Nell doesn't live in Garrow, that's wrong.", Q_NELL,
     "Garrow", "value stored under ANOTHER relation (employer, not city)")

# ---- question_tail (6): nothing may change
def ques(setup, fact, turn, q, gold, note, pred="right"):
    add("question_tail", [setup], turn, q, [fact], None, [], [fact], gold,
        note, pred)


ques(S_NELL, NELL, "Doesn't Nell work at Garrow, or is that old news?",
     Q_NELL, "Garrow", "negative question + or-clause")
ques(S_NELL, NELL, "Nell works at Garrow, is that still right?", Q_NELL,
     "Garrow", "statement + tag question")
ques(S_NELL, NELL, "Is Garrow still Nell's employer, or has that changed?",
     Q_NELL, "Garrow", "yes/no + or-clause")
ques(S_RUNE, RUNE, "Rune's boss isn't Tolly anymore, is it?", Q_RUNE,
     "Tolly", "negative statement + tag question")
ques(S_OSS, OSS, "Does Ossian still live in Pellam (or is that stale)?",
     Q_OSS, "Pellam", "question + bracket")
ques(S_QUI, QUI, "Why doesn't Quilla speak Vessic, that's odd?", Q_QUI,
     "Vessic", "why-question + that-clause")

# ---- keep (15): must be byte-identical to 252b (replies and stores)
def keep(setup, turn, q, note, pred="right", **kw):
    add("keep", setup, turn, q, [], None, [], [], None, note, pred, **kw)


keep([S_NELL], "Wren works at Lusk, which is a bakery.", "Where does Wren work?",
     "teach with which-appositive")
keep([S_NELL], "Wren lives in Hobb, that's near the coast.",
     "Where does Wren live?", "teach with that-appositive")
keep([S_NELL], "Nell doesn't work at Garrow.", Q_NELL, "plain denial (252)")
keep([S_RUNE], "Rune's boss isn't Tolly.", Q_RUNE, "plain 154f denial")
keep([S_RUNE], "Tolly isn't Rune's boss.", Q_RUNE, "plain reversed denial")
keep([S_NELL, Q_NELL], "That's wrong.", Q_NELL, "contextual denial")
keep([S_NELL, Q_NELL], "No, it's Brackley.", Q_NELL,
     "contextual correction")
keep([S_NELL], "Actually, Nell works at Brackley, not Garrow.", Q_NELL,
     "explicit correction")
keep([S_NELL], "Thanks, that's helpful.", Q_NELL, "chat with that-clause")
keep([S_NELL], "Where does Nell work?", "Who works at Garrow?",
     "plain question + reverse lookup")
keep(["My boss is Tolly."], "My boss isn't Tolly, that's outdated.",
     "Who is my boss?", "user fact denial with tail (confirm flow)")
keep(["I work at Garrow."], "I don't work at Garrow anymore, that's old news.",
     "Where do I work?", "first-person denial with tail")
keep([S_NELL, Q_NELL], "She doesn't work there.", Q_NELL,
     "pronoun denial, no tail")
keep([S_NELL, Q_NELL], "That's wrong, that's old news.", Q_NELL,
     "pure contextual denial + that-clause (258's job)")
keep([S_RUNE, "Tolly lives in Pellam.", "Where does Rune's boss live?"],
     "That's wrong, which is old news.", "Where does Rune's boss live?",
     "inferred answer disputed with tail")

# ---- pronoun (2): after a one-fact answer, pronoun denial + tail
add("pronoun", [S_NELL, Q_NELL], "She doesn't work at Garrow, that's old news.",
    Q_NELL, [NELL], NELL, [NELL], [], None,
    "pronoun denial + that-clause (goes through 252's named-denial step)")
add("pronoun", [S_OSS, Q_OSS], "He doesn't live in Pellam (he moved).",
    Q_OSS, [OSS], OSS, [OSS], [], None, "pronoun denial + bracket")

# ---- restart (5): tail denial, daemon rebuilt, followup + reverse lookup
deny(S_NELL, NELL, "Nell doesn't work at Garrow, that's old news.", Q_NELL,
     "restart after tail denial + reverse lookup", fam="restart",
     restart=True, extra=[["Whose employer is Garrow?", ["Nell"], []]])
deny(S_RUNE, RUNE, "Rune's boss is not Tolly, which is out of date.", Q_RUNE,
     "restart, 154f-owned shape + reverse lookup", fam="restart",
     restart=True, extra=[["Whose boss is Tolly?", ["Rune"], []]])
deny(S_RUNE, RUNE, "Tolly isn't Rune's boss (that was last year).", Q_RUNE,
     "restart, reversed form + reverse lookup", fam="restart",
     restart=True, extra=[["Whose boss is Tolly?", ["Rune"], []]])
add("restart", [S_NELL], "Nell doesn't work at Garrow Hall, that's wrong.",
    Q_NELL, [NELL], None, [], [NELL], "Garrow", "restart after near miss",
    restart=True, extra=[["Whose employer is Garrow?", [], ["Nell"]]])
add("restart", [S_NELL, "Ossian works at Garrow."],
    "Nell doesn't work at Garrow - she quit.", "Whose employer is Garrow?",
    [NELL, ["Ossian", E, "Garrow"]], NELL, [NELL], [["Ossian", E, "Garrow"]],
    "Ossian", "restart, two people share the value; only Nell goes",
    restart=True, extra=[["Where does Ossian work?", [], ["Garrow"]]])


def main() -> int:
    for k, it in enumerate(I, 1):
        it["id"] = f"v259-{k:03d}"
    fams = {}
    for it in I:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    turns = [it["family"] + "|" + it["turn"] + "|" + "|".join(it["setup"]) for it in I]
    assert len(set(turns)) == len(turns), "duplicate item"
    need = {"tail_denial": 15, "near_miss": 8, "unstored_tail": 6,
            "keep": 12, "question_tail": 6}
    for f, n in need.items():
        assert fams.get(f, 0) >= n, (f, fams.get(f))
    assert fams.get("restart", 0) >= 4
    assert len(I) >= 50
    OUT.parent.mkdir(parents=True, exist_ok=True)
    order = ["id", "family", "setup", "turn", "followup", "stated_facts",
             "target", "expect_gone", "expect_store", "gold_followup", "note",
             "pred", "restart", "extra"]
    OUT.write_text("".join(json.dumps({k: it[k] for k in order if k in it},
                                      ensure_ascii=False) + "\n"
                           for it in I), encoding="utf-8")
    print(len(I), fams)
    return 0


if __name__ == "__main__":
    sys.exit(main())
