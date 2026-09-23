#!/usr/bin/env python3
"""Experiment 139d -- sealed T1 probe cases (written before any run).

65 cases (62 sealed + D1's 3 base-identity locks): 28 unknown-tail (words NOT in 139c's list, 8 relations incl. 5
corrections + 1 honest wrong-question edge "Pad thai") + 16 same-shape
(connector-ending / lowercase-start / Title-case values, differential vs
loop139c) + 18 other teaches/questions (differential vs loop139c).
Writes artifacts/fable-tail139d-20260922/cases139d.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "fable-tail139d-20260922"


def CL(clean: str) -> str:
    return ('Did you mean "%s"? Please say it again without the extra '
            'words.') % clean


def tailu(cid, dialog, stored, clean, note=""):
    return {"id": cid, "group": "tailu", "mode": "tailu", "dialog": dialog,
            "expect_stored": stored, "expect_reply": CL(clean), "note": note}


def diff(cid, dialog):
    group = "same" if cid.startswith("S") else "other"
    return {"id": cid, "group": group, "mode": "diff", "dialog": dialog,
            "expect_stored": None, "expect_reply": None, "note": ""}


def build() -> list[dict]:
    c = []
    # -- unknown tails: single teaches (director probes first) -------------
    c.append(tailu("U01", ["Kim's city is Rome honestly."], [], "Rome"))
    c.append(tailu("U02", ["Kim's mother is Rose tbh."], [], "Rose"))
    c.append(tailu("U03", ["Tom's boss is Ann fr."], [], "Ann"))
    c.append(tailu("U04", ["Mia's coach is Dan ngl."], [], "Dan"))
    c.append(tailu("U05", ["Mia's pet is Rex lowkey."], [], "Rex"))
    c.append(tailu("U06", ["Tom's city is Oslo obviously."], [], "Oslo"))
    c.append(tailu("U07", ["Mia's school is Hill High basically."],
                   [], "Hill High"))
    c.append(tailu("U08", ["Mia's teacher is Max yeah."], [], "Max"))
    c.append(tailu("U09", ["Mia's town is Leeds hello."], [], "Leeds"))
    c.append(tailu("U10", ["Tom's boss is Sue idk."], [], "Sue"))
    c.append(tailu("U11", ["Mia's pet is Rex imo."], [], "Rex"))
    c.append(tailu("U12", ["Mia's coach is Dan omg."], [], "Dan"))
    c.append(tailu("U13", ["Tom's city is Paris yeah."], [], "Paris"))
    c.append(tailu("U14", ["Mia's school is Hill High yep."], [],
                   "Hill High"))
    c.append(tailu("U15", ["Mia's teacher is Max nope."], [], "Max"))
    c.append(tailu("U16", ["Tom's boss is Ann today."], [], "Ann"))
    c.append(tailu("U17", ["Mia's town is Leeds yesterday."], [], "Leeds"))
    c.append(tailu("U18", ["Kim's city is Rome please."], [], "Rome"))
    c.append(tailu("U19", ["Kim's mother is Rose sorry."], [], "Rose"))
    c.append(tailu("U20", ["Tom's boss is Ann thanks."], [], "Ann"))
    c.append(tailu("U21", ["Mia's coach is Dan hello."], [], "Dan"))
    c.append(tailu("U22", ["Mia's pet is Rex bye."], [], "Rex"))
    # -- unknown tails: corrections (no write, no correction prompt) -------
    c.append(tailu("U23", ["Mia's pet is Rex.",
                           "Mia's pet is Spot honestly."],
                   [["Mia", "pet", "Rex"]], "Spot"))
    c.append(tailu("U24", ["Tom's boss is Ann.",
                           "Tom's boss is Sue tbh."],
                   [["Tom", "boss", "Ann"]], "Sue"))
    c.append(tailu("U25", ["Tom's city is Oslo.",
                           "Tom's city is Paris ngl."],
                   [["Tom", "city", "Oslo"]], "Paris"))
    c.append(tailu("U26", ["Mia's pet is Rex.",
                           "Mia's pet is Spot lowkey."],
                   [["Mia", "pet", "Rex"]], "Spot"))
    c.append(tailu("U27", ["Kim's city is Paris.",
                           "Kim's city is Rome honestly tbh."],
                   [["Kim", "city", "Paris"]], "Rome"))
    # -- honest wrong-question edge: real value, tail-shaped ending --------
    c.append(tailu("U28", ["Mia's food is Pad thai."], [], "Pad",
                   note="HONEST-EDGE: real dish wrongly questioned"))
    # -- same-shape: connector-ending / lowercase-start / Title-case -------
    c.append(diff("S01", ["Mia's hero is Leonardo da Vinci."]))
    c.append(diff("S02", ["Mia's film is House of Wax."]))
    c.append(diff("S03", ["Mia's book is Lord of the Rings."]))
    c.append(diff("S04", ["Mia's town is Salt Lake City."]))
    c.append(diff("S05", ["Tom's band is Take That."]))
    c.append(diff("S06", ["Mia's song is Let It Be."]))
    c.append(diff("S07", ["Mia's song is Say It Again."]))
    c.append(diff("S08", ["Tom's band is Right Said Fred."]))
    c.append(diff("S09", ["Rex's color is black."]))
    c.append(diff("S10", ["Mia's food is pizza."]))
    c.append(diff("S11", ["Mia's drink is green tea."]))
    c.append(diff("S12", ["Mia's lunch is cold pizza."]))
    c.append(diff("S13", ["Tom's book is House of Cards."]))
    c.append(diff("S14", ["Mia's hero is Joan of Arc."]))
    c.append(diff("S15", ["Mia's hero is Vincent van Gogh."]))
    c.append(diff("S16", ["Mia's hero is Charles de Gaulle."]))
    # -- other: plain teaches/questions (differential vs loop139c) ---------
    c.append(diff("O01", ["Tom's boss is Ann."]))
    c.append(diff("O02", ["Tom's city is Oslo."]))
    c.append(diff("O03", ["Mia's pet is Rex."]))
    c.append(diff("O04", ["Tom's boss is Ann too."]))
    c.append(diff("O05", ["Mia's teacher is Max again."]))
    c.append(diff("O06", ["Tom's motto is all right."]))
    c.append(diff("O07", ["Tom's boss is Ann.", "Who is Tom's boss?"]))
    c.append(diff("O08", ["Tom's city is Oslo.", "What is Tom's city?"]))
    c.append(diff("O09", ["Tom's boss is Ann.", "Ann's city is Oslo.",
                          "What is Tom's boss's city?"]))
    c.append(diff("O10", ["Who is Zoe's boss?"]))
    c.append(diff("O11", ["Tom's boss is Ann.", "Tom's boss is Sue.",
                          "yes."]))
    c.append(diff("O12", ["Mia's pet is Rex.", "Rex's color is black.",
                          "What is Rex's color?"]))
    c.append(diff("O13", ["Rex's color is red.", "Rex's color is black.",
                          "yes.", "What is Rex's color?"]))
    c.append(diff("O14", ["Mia's town is Leeds.", "Mia's coach is Dan.",
                          "Who is Mia's coach?"]))
    c.append(diff("O15", ["Tom's city is Oslo.", "Tom's city is Paris.",
                          "yes.", "What is Tom's city?"]))
    c.append(diff("O16", ["Mia's pet is Rex.", "Who is Mia's pet?"]))
    c.append(diff("O17", ["Mia's teacher is Max.",
                          "Who is Mia's teacher?"]))
    c.append(diff("O18", ["Tom's boss is Ann too.",
                          "Who is Tom's boss?"]))
    # -- D1 locks: base-identical non-teach paths for tail-shaped inputs ---
    c.append(diff("O19", ["Mia's teacher is Max maybe."]))
    c.append(diff("O20", ["Mia's town is Leeds probably."]))
    c.append(diff("O21", ["Rex's color is red.",
                          "Rex's color is black honestly."]))
    return c


def main() -> int:
    cases = build()
    assert len(cases) == 65, len(cases)
    tailu = [x for x in cases if x["mode"] == "tailu"]
    assert len(tailu) == 28, len(tailu)
    assert len([x for x in cases if x["group"] == "same"]) == 16
    assert len([x for x in cases if x["group"] == "other"]) == 21
    ART.mkdir(parents=True, exist_ok=True)
    dest = ART / "cases139d.json"
    dest.write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {dest} n={len(cases)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
