#!/usr/bin/env python3
"""Exp 252b held-out safety dev (own wordings, fictional names; nothing
copied from any panel). Writes artifacts/claude-correct252b-20260922/
dev252b.jsonl in the corrpanel252 item shape plus:
  "target": the denied / corrected stored triple [S, R, Y] (or null)
  "new":    the intended new triple [S, R, Z] for a correction (or null)
Families: deny_tail, correct_tail (denials / corrections ending in a
trailing clause, with apostrophe and punctuation variants), question_tail,
control (turns 252 already gets right)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("artifacts/claude-correct252b-20260922/dev252b.jsonl")
E, CI, L, PB = "employer", "city", "language", "place_of_birth"

TAILS = [", that's outdated", ", which is old news", ", it's wrong now",
         " - that's changed", "; that isn't true anymore",
         ", thats outdated", " -- that's old", ", that’s changed",
         ", which isn't right anymore", " (that's stale)",
         ", that's no longer true", "... that's out of date"]


def item(fam, setup, turn, follow, target, new, note):
    return {"family": fam, "setup": setup, "turn": turn, "followup": follow,
            "stated_facts": [target] if target else [],
            "expect_gone": [target] if target and fam != "control" else [],
            "expect_store": [new] if new else [], "gold_followup": None,
            "note": note, "target": target, "new": new}


I = []
# ---- denials with a trailing clause (18)
den = [
    ("Arlo", E, "Brimwell", "Arlo works at Brimwell.",
     "Arlo doesn't work at Brimwell{t}.", "Where does Arlo work?"),
    ("Beska", CI, "Faldon", "Beska lives in Faldon.",
     "Beska doesn't live in Faldon{t}.", "Where does Beska live?"),
    ("Cyril", "boss", "Mott", "Cyril's boss is Mott.",
     "Mott isn't Cyril's boss{t}.", "Who is Cyril's boss?"),
    ("Dagny", L, "Pellic", "Dagny speaks Pellic.",
     "Dagny does not speak Pellic{t}.", "What language does Dagny speak?"),
    ("Evard", "manager", "Sill", "Evard's manager is Sill.",
     "Evard's manager is not Sill{t}.", "Who is Evard's manager?"),
    ("Fliss", PB, "Wendover", "Fliss was born in Wendover.",
     "Fliss wasn't born in Wendover{t}.", "Where was Fliss born?"),
]
for n, (s, r, y, setup, turn, fq) in enumerate(den):
    for k in range(3):
        t = TAILS[(n * 3 + k) % len(TAILS)]
        I.append(item("deny_tail", [setup], turn.format(t=t), fq,
                      [s, r, y], None, f"tail {t!r}"))
# ---- corrections with a trailing clause (16)
cor = [
    ("Gideon", E, "Tarrow", "Kelby", "Gideon works at Tarrow.",
     "Gideon doesn't work at Tarrow, he works at Kelby{t}.",
     "Where does Gideon work?"),
    ("Hesta", CI, "Umbry", "Lowick", "Hesta lives in Umbry.",
     "Actually, Hesta lives in Lowick, not Umbry{t}.",
     "Where does Hesta live?"),
    ("Isak", "boss", "Varn", "Olet", "Isak's boss is Varn.",
     "Isak's boss isn't Varn, it's Olet{t}.", "Who is Isak's boss?"),
    ("Jolie", L, "Mirric", "Tavish", "Jolie speaks Mirric.",
     "No, Jolie speaks Tavish, not Mirric{t}.",
     "What language does Jolie speak?"),
]
for n, (s, r, y, z, setup, turn, fq) in enumerate(cor):
    for k in range(4):
        t = TAILS[(n * 4 + k + 5) % len(TAILS)]
        I.append(item("correct_tail", [setup], turn.format(t=t), fq,
                      [s, r, y], [s, r, z], f"tail {t!r}"))
# ---- contextual turns with a trailing clause after an answer (4)
ctx = [
    ("Kasia", E, "Norbeck", "Kasia works at Norbeck.", "Where does Kasia work?",
     "That's wrong, that's old news.", None),
    ("Linus", CI, "Pardale", "Linus lives in Pardale.", "Where does Linus live?",
     "No, it's Quarry, that's outdated.", "Quarry"),
    ("Mavis", "sister", "Nell", "Mavis's sister is Nell.",
     "Who is Mavis's sister?", "Nope - it's Opal; that isn't true anymore.",
     "Opal"),
    ("Nico", L, "Dorric", "Nico speaks Dorric.",
     "What language does Nico speak?", "That's not right, it's wrong now.",
     None),
]
for s, r, y, setup, q, turn, z in ctx:
    I.append(item("correct_tail" if z else "deny_tail", [setup, q], turn, q,
                  [s, r, y], [s, r, z] if z else None, "contextual + tail"))
# ---- questions with a trailing clause (6): must write nothing
qs = [
    ("Otis", E, "Hallam", "Otis works at Hallam.",
     "Doesn't Otis work at Hallam, or is that outdated?"),
    ("Pia", CI, "Sorrel", "Pia lives in Sorrel.",
     "Isn't Pia living in Sorrel, that's old news?"),
    ("Quade", "boss", "Rhee", "Quade's boss is Rhee.",
     "Is it true that Rhee isn't Quade's boss anymore, that's changed?"),
    ("Rosamund", L, "Ettic", "Rosamund speaks Ettic.",
     "rosamund doesn't speak ettic, does she - that's outdated?"),
    ("Saul", PB, "Coombe", "Saul was born in Coombe.",
     "Wasn't Saul born in Coombe; that isn't true anymore?"),
    ("Tilde", "manager", "Ungar", "Tilde's manager is Ungar.",
     "Why is Ungar not Tilde's manager, which is old news?"),
]
for s, r, y, setup, turn in qs:
    I.append(item("question_tail", [setup], turn, f"Who is {s}?" if False
                  else ("Where does %s work?" % s if r == E else
                        "Where does %s live?" % s if r == CI else
                        "What language does %s speak?" % s if r == L else
                        "Where was %s born?" % s if r == PB else
                        "Who is %s's %s?" % (s, r)),
                  [s, r, y], None, "question + tail"))
    I[-1]["expect_gone"] = []
    I[-1]["expect_store"] = [[s, r, y]]
# ---- controls 252 already gets right (12)
ctl = [
    (["Ursa works at Bellgate."], "Ursa doesn't work at Bellgate.",
     "Where does Ursa work?", ["Ursa", E, "Bellgate"], None),
    (["Vail lives in Crane Hollow."], "Vail doesn't live in Crane Hollow.",
     "Where does Vail live?", ["Vail", CI, "Crane Hollow"], None),
    (["Wynn's boss is Hask."], "Hask isn't Wynn's boss.",
     "Who is Wynn's boss?", ["Wynn", "boss", "Hask"], None),
    (["Xavi lives in Merrow.", "Where does Xavi live?"], "That's wrong.",
     "Where does Xavi live?", ["Xavi", CI, "Merrow"], None),
    (["Yara works at Dunstan.", "Where does Yara work?"], "No, it's Ellery.",
     "Where does Yara work?", ["Yara", E, "Dunstan"], ["Yara", E, "Ellery"]),
    (["Zeke lives in Fairholm."],
     "Actually, Zeke lives in Gorsey, not Fairholm.",
     "Where does Zeke live?", ["Zeke", CI, "Fairholm"],
     ["Zeke", CI, "Gorsey"]),
    (["Amos's teacher is Brisk."], "Correction: Amos's teacher is Calloway.",
     "Who is Amos's teacher?", ["Amos", "teacher", "Brisk"],
     ["Amos", "teacher", "Calloway"]),
    (["Bea works at Harrowby."], "Doesn't Bea work at Harrowby?",
     "Where does Bea work?", ["Bea", E, "Harrowby"], None),
    (["Cole lives in Ivel."], "Cole doesn't live in Jessop.",
     "Where does Cole live?", ["Cole", CI, "Ivel"], None),
    (["Dina speaks Korric.", "Dina speaks Lunnish.",
      "What language does Dina speak?"], "That's wrong.",
     "What language does Dina speak?", ["Dina", L, "Korric"], None),
    (["Egan works at Marlowe."], "Where does Egan work?",
     "Whose employer is Marlowe?", ["Egan", E, "Marlowe"], None),
    (["Faye lives in Nettle."], "No, Faye lives in Oxley.",
     "Where does Faye live?", ["Faye", CI, "Nettle"], ["Faye", CI, "Oxley"]),
]
for setup, turn, fq, target, new in ctl:
    I.append(item("control", setup, turn, fq, target, new, "252 handles"))


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.dumps({"id": f"b252-{n:03d}", **d}, ensure_ascii=False)
            for n, d in enumerate(I, 1)]
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    fams: dict[str, int] = {}
    for d in I:
        fams[d["family"]] = fams.get(d["family"], 0) + 1
    print(len(I), fams)
    return 0


if __name__ == "__main__":
    sys.exit(main())
