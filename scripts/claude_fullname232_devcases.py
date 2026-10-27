#!/usr/bin/env python3
"""Exp 232 dev cases (own, written before the blind panel was opened).

Panel-format JSONL: id, family, pair, name_words, setup[], question,
expect_writes [[subject, relation, value], ...], expect_nowrite (bool),
gold (str, list of str, or "" = must abstain), notes. Fictional names only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# (pair id, family, one-word name, multi-word name, setup templates,
#  question template, expected writes (N = subject), gold, notes)
PAIRS = [
    ("P01", "lives_in", "Orrin", "Orrin Vask",
     ["{N} lives in Quellmoor."], "Where does {N} live?",
     [["{N}", "city", "Quellmoor"]], "Quellmoor", "basic"),
    ("P02", "works_at", "Tessaly", "Tessaly Marrow-Fen",
     ["{N} works at Brindlecorp."], "Where does {N} work?",
     [["{N}", "employer", "Brindlecorp"]], "Brindlecorp", "hyphen surname"),
    ("P03", "works_at", "Pell", "Pell Oskin Dray",
     ["{N} works for Hollowmere."], "Who does {N} work for?",
     [["{N}", "employer", "Hollowmere"]], "Hollowmere", "works for, 3 words"),
    ("P04", "speaks", "Juno", "Juno de Carvel",
     ["{N} speaks Veltish."], "What language does {N} speak?",
     [["{N}", "language", "Veltish"]], "Veltish", "particle de"),
    ("P05", "mixed", "Idris", "Idris Varn",
     ["{N} was born in Farrowgate."], "Where was {N} born?",
     [["{N}", "place_of_birth", "Farrowgate"]], "Farrowgate", "born in"),
    ("P06", "lives_in", "Brisa", "Brisa Holloway",
     ["{N} lives in Quellmoor.", "Actually, {N} lives in Dunmere."],
     "Where does {N} live?", [["{N}", "city", "Dunmere"]], "Dunmere",
     "correction"),
    ("P07", "speaks", "Sefa", "Sefa Oldenbrook",
     ["{N} speaks Veltish.", "{N} speaks Norric."],
     "What languages does {N} speak?",
     [["{N}", "language", "Veltish"], ["{N}", "language", "Norric"]],
     ["Veltish", "Norric"], "two languages (154e multi-add)"),
    ("P08", "lives_in", "Kell", "Kell Ashdown",
     ["{N} lives in a flat."], "Where does {N} live?", [], "",
     "167b value screen refuses"),
    ("P09", "lives_in", "Mira", "Mira van Doss",
     ["{N} lives in Quellmoor now."], "Where does {N} live?",
     [["{N}", "city", "Quellmoor"]], "Quellmoor", "tail strip, particle van"),
    ("P10", "mixed", "Ander", "Ander Quist",
     ["{N} works at Brindlecorp."], "What is {N}'s employer?",
     [["{N}", "employer", "Brindlecorp"]], "Brindlecorp",
     "verb teach, possessive ask"),
    ("P11", "mixed", "Oona", "Oona Pell-Rast",
     ["{N}'s city is Tillmarsh."], "Where does {N} live?",
     [["{N}", "city", "Tillmarsh"]], "Tillmarsh",
     "possessive teach, verb ask"),
    ("P12", "lives_in", "Wren", "Wren Talbot",
     [], "Where does {N} live?", [], "", "never taught"),
    ("P13", "lives_in", "Cato", "Cato Ferrier",
     ["{N} lives in Quellmoor.", "{N} lives in Dunmere."],
     "Where does {N} live?", [["{N}", "city", "Quellmoor"]], "Quellmoor",
     "conflicting re-teach asks before changing"),
    ("P14", "mixed", "Ibbet", "Ibbet Crane",
     ["Anselm's boss is {N}.", "{N} lives in Tillmarsh."],
     "Where does {N} live?",
     [["Anselm", "boss", "{N}"], ["{N}", "city", "Tillmarsh"]], "Tillmarsh",
     "name taught as a value first"),
    ("P15", "works_at", "Lune", "Lune Ostrava",
     ["{N} works at Brindlecorp.", "No, {N} works at Halden Mills."],
     "Where does {N} work?", [["{N}", "employer", "Halden Mills"]],
     "Halden Mills", "No, correction"),
    ("P16", "works_at", "Anna", "Anna van der Holt",
     ["{N} works at Brindlecorp."], "Where does {N} work?",
     [["{N}", "employer", "Brindlecorp"]], "Brindlecorp", "4 words"),
    ("P17", "lives_in", "Rook", "Rook J. Amsel",
     ["{N} lives in Farrowgate."], "Where does {N} live?",
     [["{N}", "city", "Farrowgate"]], "Farrowgate", "initial"),
    ("P18", "lives_in", "Tamsin", "Tamsin Grey",
     ["{N} lives in Quellmoor."], "where does {N} live",
     [["{N}", "city", "Quellmoor"]], "Quellmoor", "lowercase q, no ?"),
    ("P19", "lives_in", "Faro", "Faro Lint",
     ["{N} doesn't live in Quellmoor."], "Where does {N} live?", [], "",
     "negation declines"),
    ("P20", "speaks", "Nell", "Nell Umber",
     ["{N} speaks Veltish.", "{N} lives in Dunmere."],
     "What language does {N} speak?",
     [["{N}", "language", "Veltish"], ["{N}", "city", "Dunmere"]],
     "Veltish", "two facts, right one answered"),
]

TRAPS = [
    ("T01", "Maybe Orrin Vask lives in Quellmoor.", "Where does Orrin Vask live?"),
    ("T02", "I think Tessaly Marrow works at Brindlecorp.",
     "Where does Tessaly Marrow work?"),
    ("T03", "Someone told me Juno Carvel speaks Veltish.",
     "What language does Juno Carvel speak?"),
    ("T04", "Honestly Pell Dray lives in Quellmoor.",
     "Where does Pell Dray live?"),
    ("T05", "My friend Idris Varn lives in Quellmoor.",
     "Where does Idris Varn live?"),
    ("T06", "orrin vask lives in quellmoor.", "Where does Orrin Vask live?"),
    ("T07", "The Vask family lives in Quellmoor.",
     "Where does the Vask family live?"),
    ("T08", "Orrin Tel Vask Brin Oda lives in Quellmoor.",
     "Where does Orrin Tel Vask Brin Oda live?"),
    ("T09", "Orrin and Tessaly live in Quellmoor.", "Where does Orrin live?"),
    ("T10", "Everyone in Quellmoor speaks Veltish.",
     "What language does Everyone speak?"),
    ("T11", "Orrin Vask used to live in Quellmoor.",
     "Where does Orrin Vask live?"),
    ("T12", "Orrin Vask probably lives in Quellmoor.",
     "Where does Orrin Vask live?"),
    ("T13", "Rumor has it Brisa Holloway works at Brindlecorp.",
     "Where does Brisa Holloway work?"),
    ("T14", "Orrin Vask lives in a small flat.",
     "Where does Orrin Vask live?"),
]


def sub(x, n):
    if isinstance(x, list):
        return [sub(y, n) for y in x]
    return x.replace("{N}", n)


def build() -> list[dict]:
    out = []
    for pid, fam, one, multi, setup, q, writes, gold, notes in PAIRS:
        for tag, name in (("a", one), ("b", multi)):
            out.append({"id": f"dev-{pid}{tag}", "family": fam, "pair": pid,
                        "name_words": len(name.split()),
                        "setup": sub(setup, name), "question": sub(q, name),
                        "expect_writes": sub(writes, name),
                        "expect_nowrite": not writes, "gold": gold,
                        "clear": True, "notes": notes})
    for tid, s, q in TRAPS:
        out.append({"id": f"dev-{tid}", "family": "trap", "pair": None,
                    "name_words": None, "setup": [s], "question": q,
                    "expect_writes": [], "expect_nowrite": True, "gold": "",
                    "clear": True, "notes": "no-write trap"})
    return out


if __name__ == "__main__":
    path = Path(sys.argv[1])
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                            for r in build()), encoding="utf-8")
    print(f"wrote {len(build())} dev items to {path}")
