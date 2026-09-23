#!/usr/bin/env python3
"""Experiment 139c -- sealed T1 probe cases (written before any run).

60 cases: 30 tail (every closed-list word >= 1, 8 relations, corrections
with yes, 2-hop questions afterwards) + 15 Title-case names/titles ending
in a list word (differential vs loop138b) + 15 other teaches/questions
(differential vs loop138b). Writes artifacts/.../cases139c.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "fable-tailwords139c-20260922"


def tail(cid, dialog, expect, prompt_clean=None, prompt_dirty=None,
         final_contains=None):
    return {"id": cid, "group": "tail", "mode": "tail", "dialog": dialog,
            "expect": expect, "prompt_clean": prompt_clean,
            "prompt_dirty": prompt_dirty, "final_contains": final_contains}


def diff(cid, dialog):
    return {"id": cid, "group": "title" if cid.startswith("N") else "other",
            "mode": "diff", "dialog": dialog, "expect": None,
            "prompt_clean": None, "prompt_dirty": None,
            "final_contains": None}


def build() -> list[dict]:
    c = []
    # -- tail: the 8 director examples -------------------------------------
    c.append(tail("T01", ["Tom's boss is Ann too."],
                  [["Tom", "boss", "Ann"]]))
    c.append(tail("T02", ["Tom's city is Oslo actually."],
                  [["Tom", "city", "Oslo"]]))
    c.append(tail("T03", ["Mia's pet is Rex as well."],
                  [["Mia", "pet", "Rex"]]))
    c.append(tail("T04", ["Mia's school is Hill High though."],
                  [["Mia", "school", "Hill High"]]))
    c.append(tail("T05", ["Mia's coach is Dan lol."],
                  [["Mia", "coach", "Dan"]]))
    c.append(tail("T06", ["Mia's town is Leeds btw."],
                  [["Mia", "town", "Leeds"]]))
    c.append(tail("T07", ["Mia's teacher is Max again."],
                  [["Mia", "teacher", "Max"]]))
    c.append(tail("T08", ["Rex's color is red.",
                           "Rex's color is black now.", "yes."],
                  [["Rex", "color", "black"]],
                  prompt_clean="change it to black?",
                  prompt_dirty="black now",
                  final_contains="black"))
    # -- tail: remaining list words ----------------------------------------
    c.append(tail("T09", ["Mia's town is Leeds tho."],
                  [["Mia", "town", "Leeds"]]))
    c.append(tail("T10", ["Mia's coach is Dan lmao."],
                  [["Mia", "coach", "Dan"]]))
    c.append(tail("T11", ["Mia's pet is Rex haha."],
                  [["Mia", "pet", "Rex"]]))
    c.append(tail("T12", ["Tom's boss is Ann also."],
                  [["Tom", "boss", "Ann"]]))
    c.append(tail("T13", ["Tom's city is Oslo i guess."],
                  [["Tom", "city", "Oslo"]]))
    c.append(tail("T14", ["Mia's school is Hill High anyway."],
                  [["Mia", "school", "Hill High"]]))
    c.append(tail("T15", ["Mia's teacher is Max then."],
                  [["Mia", "teacher", "Max"]]))
    c.append(tail("T16", ["Tom's city is Oslo.",
                           "Tom's city is Paris instead.", "yes."],
                  [["Tom", "city", "Paris"]],
                  prompt_clean="change it to Paris?",
                  prompt_dirty="Paris instead",
                  final_contains="Paris"))
    c.append(tail("T17", ["Mia's pet is Rex rn."],
                  [["Mia", "pet", "Rex"]]))
    c.append(tail("T18", ["Tom's boss is Ann right."],
                  [["Tom", "boss", "Ann"]]))
    c.append(tail("T19", ["Mia's school is Hill High ok."],
                  [["Mia", "school", "Hill High"]]))
    c.append(tail("T20", ["Mia's teacher is Max okay."],
                  [["Mia", "teacher", "Max"]]))
    c.append(tail("T21", ["Tom's boss is Ann.",
                           "Tom's boss is Sue actually.", "yes."],
                  [["Tom", "boss", "Sue"]],
                  prompt_clean="change it to Sue?",
                  prompt_dirty="Sue actually",
                  final_contains="Sue"))
    c.append(tail("T22", ["Mia's town is Leeds now."],
                  [["Mia", "town", "Leeds"]]))
    c.append(tail("T23", ["Tom's city is Oslo, too."],
                  [["Tom", "city", "Oslo"]]))
    # -- tail: question afterwards ------------------------------------------
    c.append(tail("T24", ["Mia's pet is Rex as well.",
                           "Rex's color is black.",
                           "What is Rex's color?"],
                  [["Mia", "pet", "Rex"], ["Rex", "color", "black"]],
                  final_contains="black"))
    c.append(tail("T25", ["Tom's boss is Ann too.",
                           "Who is Tom's boss?"],
                  [["Tom", "boss", "Ann"]], final_contains="Ann"))
    c.append(tail("T26", ["Tom's boss is Ann too.",
                           "Ann's city is Oslo btw.",
                           "What is Tom's boss's city?"],
                  [["Tom", "boss", "Ann"], ["Ann", "city", "Oslo"]],
                  final_contains="Oslo"))
    c.append(tail("T27", ["Tom's city is Oslo too lol."],
                  [["Tom", "city", "Oslo"]]))
    c.append(tail("T28", ["Mia's town is Leeds btw haha."],
                  [["Mia", "town", "Leeds"]]))
    c.append(tail("T29", ["Rex's color is red.",
                           "Rex's color is black now.", "yes.",
                           "What is Rex's color?"],
                  [["Rex", "color", "black"]],
                  prompt_clean="change it to black?",
                  prompt_dirty="black now",
                  final_contains="black"))
    c.append(tail("T30", ["Mia's pet is Rex as well.",
                           "Rex's color is red.",
                           "Rex's color is green instead.", "yes.",
                           "What is Rex's color?"],
                  [["Mia", "pet", "Rex"], ["Rex", "color", "green"]],
                  prompt_clean="change it to green?",
                  prompt_dirty="green instead",
                  final_contains="green"))
    c.append(tail("T31", ["Mia's pet is Rex as well haha though."],
                  [["Mia", "pet", "Rex"]]))
    # -- title: Title-case names/titles ending in a list word (diff) -------
    c.append(diff("N01", ["Tom's boss is Take That."]))
    c.append(diff("N02", ["Mia's song is Let It Be."]))
    c.append(diff("N03", ["Mia's film is Home Alone."]))
    c.append(diff("N04", ["Mia's song is Say It Again."]))
    c.append(diff("N05", ["Tom's band is Right Said Fred."]))
    c.append(diff("N06", ["Mia's song is Do It Again."]))
    c.append(diff("N07", ["Tom's motto is All Right."]))
    c.append(diff("N08", ["Mia's song is Right Now."]))
    c.append(diff("N09", ["Mia's song is Me Too."]))
    c.append(diff("N10", ["Tom's book is Until Then."]))
    c.append(diff("N11", ["Mia's song is Not Now."]))
    c.append(diff("N12", ["Tom's motto is Try Again."]))
    c.append(diff("N13", ["Mia's pet is Okay."]))
    c.append(diff("N14", ["Mia's pet is Lol."]))
    c.append(diff("N15", ["Tom's book is Think Again."]))
    # -- other: plain teaches/questions (diff) ------------------------------
    c.append(diff("O01", ["Tom's boss is Ann."]))
    c.append(diff("O02", ["Tom's city is Oslo."]))
    c.append(diff("O03", ["Mia's pet is Rex."]))
    c.append(diff("O04", ["Mia's school is Hill High."]))
    c.append(diff("O05", ["Tom's boss is Ann.", "Who is Tom's boss?"]))
    c.append(diff("O06", ["Tom's city is Oslo.", "What is Tom's city?"]))
    c.append(diff("O07", ["Tom's boss is Ann.", "Ann's city is Oslo.",
                            "What is Tom's boss's city?"]))
    c.append(diff("O08", ["Who is Zoe's boss?"]))
    c.append(diff("O09", ["Tom's boss is Ann.", "Tom's boss is Sue.",
                            "yes."]))
    c.append(diff("O10", ["Mia's pet is Rex.", "Rex's color is black.",
                            "What is Rex's color?"]))
    c.append(diff("O11", ["Mia's town is Leeds.", "Mia's coach is Dan.",
                            "Who is Mia's coach?"]))
    c.append(diff("O12", ["Rex's color is red.", "Rex's color is black.",
                            "yes.", "What is Rex's color?"]))
    c.append(diff("O13", ["Mia's teacher is Max.",
                            "Who is Mia's teacher?"]))
    c.append(diff("O14", ["Tom's city is Oslo.", "Tom's city is Paris.",
                            "yes.", "What is Tom's city?"]))
    c.append(diff("O15", ["Mia's pet is Rex.", "Who is Mia's pet?"]))
    return c


def main() -> int:
    cases = build()
    assert len(cases) == 61, len(cases)
    tails = [x for x in cases if x["mode"] == "tail"]
    assert len(tails) == 31
    ART.mkdir(parents=True, exist_ok=True)
    dest = ART / "cases139c.json"
    dest.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {dest} n={len(cases)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
