#!/usr/bin/env python3
"""Experiment 166 -- build the sealed T1/T2 probe case file (Muse).

52 rows, all fictional names:
  F01-F25 (25 first-person rows): teaches+questions across 6 relations
    (mother/father/sister/brother/friend/city), incl. synonym surfaces
    (mom/dad), two-hop questions (F07/F21/F22), corrections (F08/F09/F12),
    duplicate (F11), unknown (F10/F15), mid-chain missing (F16).
  A01-A10 (10 agent-itself rows): "your name"/"who made you" class turns,
    flagged identical_to_base (stored triples AND every reply byte-identical
    to loop162b).
  O01-O17 (17 other rows): third-person teaches/asks, office phrases,
    The-name frames, hearsay/nowrite shapes, chained/malformed turns,
    flagged identical_to_base.

Run once BEFORE sealing (dev): this freezes the registered inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART166 = ROOT / "artifacts" / "fable-me166-20260922"


def frow(pid, teaches, expect, asks, teach_reply="saved"):
    return {"id": pid, "group": "first-person", "teaches": teaches,
            "expect": expect, "teach_reply": teach_reply, "asks": asks}


def ask(q, want):
    return {"q": q, "want": want}


def irow(pid, group, teaches, asks=()):
    return {"id": pid, "group": group, "teaches": list(teaches),
            "identical_to_base": True,
            "asks": [{"q": q, "want": None} for q in asks]}


def main() -> int:
    rows: list[dict] = []
    # ---- F: first-person (stored subject is the reserved USER entity) ----
    U = "USER"
    rows.append(frow("F01", ["My mom is Rita."], [U, "mother", "Rita"],
                     [ask("Who is my mom?", "Rita"),
                      ask("What is my mother?", "Rita")]))
    rows.append(frow("F02", ["My dad is Milo."], [U, "father", "Milo"],
                     [ask("Who is my dad?", "Milo"),
                      ask("Who is my father?", "Milo")]))
    rows.append(frow("F03", ["My sister is Petra."], [U, "sister", "Petra"],
                     [ask("Who is my sister?", "Petra")]))
    rows.append(frow("F04", ["My brother is Hugo."], [U, "brother", "Hugo"],
                     [ask("Who is my brother?", "Hugo")]))
    rows.append(frow("F05", ["My friend is Noor."], [U, "friend", "Noor"],
                     [ask("Who is my friend?", "Noor")]))
    rows.append(frow("F06", ["My city is Lisbon."], [U, "city", "Lisbon"],
                     [ask("Where is my city?", "Lisbon"),
                      ask("What is my city?", "Lisbon")]))
    rows.append(frow("F07", ["My mother is Rita.", "Rita's city is Lisbon."],
                     [[U, "mother", "Rita"], ["Rita", "city", "Lisbon"]],
                     [ask("Where is my mother's city?", "Lisbon"),
                      ask("Where is my mom's city?", "Lisbon")]))
    rows.append(frow("F08", ["My mother is Rita.",
                             "Actually, my mother is Zara."],
                     [U, "mother", "Zara"],
                     [ask("Who is my mother?", "Zara"),
                      ask("Who is my mom?", "Zara")]))
    rows.append(frow("F09", ["My father is Milo.", "No, my father is Felix."],
                     [U, "father", "Felix"],
                     [ask("Who is my father?", "Felix")]))
    rows.append(frow("F10", [], "nowrite",
                     [ask("Who is my father?",
                          "I don't know your father yet.")],
                     teach_reply="any"))
    rows.append(frow("F11", ["My mother is Rita.", "My mother is Rita."],
                     [U, "mother", "Rita"],
                     [ask("Who is my mother?", "Rita")],
                     teach_reply="already"))
    rows.append(frow("F12", ["My sister is Petra.", "My sister is Ada."],
                     [U, "sister", "Ada"],
                     [ask("Who is my sister?", "Ada")]))
    rows.append(frow("F13", ["My mum is Rita."], [U, "mother", "Rita"],
                     [ask("Who is my mum?", "Rita")]))
    rows.append(frow("F14", ["MY DAD IS MILO."], [U, "father", "MILO"],
                     [ask("Who is my dad?", "MILO")]))
    rows.append(frow("F15", [], "nowrite",
                     [ask("Who is my sister?",
                          "I don't know your sister yet.")],
                     teach_reply="any"))
    rows.append(frow("F16", ["My mother is Rita."],
                     [U, "mother", "Rita"],
                     [ask("Where is my mother's city?",
                          "I don't know Rita's city.")]))
    rows.append(frow("F17", ["My brother is Hugo."], [U, "brother", "Hugo"],
                     [ask("Who are my brothers?",
                          "I don't know your brothers yet.")]))
    rows.append(frow("F18", ["My daddy is Milo."], [U, "father", "Milo"],
                     [ask("Who is my daddy?", "Milo")]))
    rows.append(frow("F19", ["My friend is Noor.", "Noor's sister is Ada."],
                     [[U, "friend", "Noor"], ["Noor", "sister", "Ada"]],
                     [ask("Who is my friend's sister?", "Ada")]))
    rows.append(frow("F20", ["My brother is Hugo.",
                             "Actually, my brother is Felix."],
                     [U, "brother", "Felix"],
                     [ask("Who is my brother?", "Felix")]))
    rows.append(frow("F21", ["My brother is Hugo.",
                             "Hugo's friend is Felix."],
                     [[U, "brother", "Hugo"], ["Hugo", "friend", "Felix"]],
                     [ask("Who is my brother's friend?", "Felix")]))
    rows.append(frow("F22", ["My mummy is Rita."], [U, "mother", "Rita"],
                     [ask("Who is my mummy?", "Rita")]))
    rows.append(frow("F23", ["My sister is Ada."], [U, "sister", "Ada"],
                     [ask("What is my sister?", "Ada")]))
    rows.append(frow("F24", ["My husband is Felix."], [U, "husband", "Felix"],
                     [ask("Who is my husband?", "Felix")]))
    rows.append(frow("F25", ["My wife is Noor."], [U, "wife", "Noor"],
                     [ask("Who is my wife?", "Noor")]))
    # ---- A: turns about the agent itself (byte-identical to loop162b) ----
    agent_turns = ["What is your name?", "Who made you?", "Who are you?",
                   "What are you?", "How old are you?",
                   "Who is your mother?", "What is your city?",
                   "Your name is what?", "Are you smart?", "Where are you?"]
    for n, t in enumerate(agent_turns, 1):
        rows.append(irow(f"A{n:02d}", "agent-itself", [t]))
    # ---- O: other turns (byte-identical to loop162b) ----
    other = [
        (["Tom's mother is Rita."], ["Who is Tom's mother?"]),
        (["Rita's city is Lisbon."], ["Where is Rita's city?"]),
        (["The Hobbit's author is Tolkien."],
         ["Who is The Hobbit's author?"]),
        (["The Beatles' founder is Lennon."],
         ["Who is The Beatles' founder?"]),
        (["The mayor of Leeds is Ann."], []),
        (["The president of Zorvia is Mel Ash."], []),
        (["I heard Tom's mother is Rita."], []),
        (["Mary Jane's mother is Rita."], []),
        (["Tom is Rita."], []),
        (["Tom's mother's city is Lisbon."], []),
        (["Who is Tom's mother's city?"],
         ["Who is Tom's mother's city?"]),
        (["What if Tom's mother is Rita?"], []),
        (["USER's mother is Rita."], ["Who is USER's mother?"]),
        (["My mother is Rita?"], []),
        (["My manager is Tom."], []),
        (["Where is my mother city?"], []),
        (["Who is your father's city?"], ["Who is your father's city?"]),
    ]
    for n, (teaches, asks_) in enumerate(other, 1):
        rows.append(irow(f"O{n:02d}", "other", teaches, asks_))
    assert len(rows) == 52, len(rows)
    ART166.mkdir(parents=True, exist_ok=True)
    (ART166 / "cases166.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote {ART166 / 'cases166.json'} n={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
