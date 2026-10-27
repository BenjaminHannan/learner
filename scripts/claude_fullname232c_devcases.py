#!/usr/bin/env python3
"""Exp 232c dev cases (own; written before the 232c blind panel existed).

Same schema as the 232c panel contract: id, family (multi/one/trap/
stated_extra), pair ("pNN" or null), name_words (int), setup [str],
question (str|null), gold (str|null), expect (ANSWER/ABSTAIN/NO_WRITE),
stated_facts [[subject, relation-word-as-written, value]], note.
Every particle in the 232c list gets one multi/one pair; plus multi-word
particle runs, apostrophe/hyphen names, conjunction traps, stated_extra.
Fictional names only. Usage: python -B this.py <out.jsonl>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VERBS = [  # (statement verb, question template, relation word as written)
    ("lives in", "Where does {N} live?", "lives in"),
    ("works at", "Where does {N} work?", "works at"),
    ("works for", "Who does {N} work for?", "works for"),
    ("was born in", "Where was {N} born?", "was born in"),
    ("speaks", "What language does {N} speak?", "speaks"),
]
PLACES = ["Brakmoor", "Quellport", "Tarnby", "Vetherby", "Ashvale",
          "Kelthorn", "Dunmere", "Farrowgate"]
FIRMS = ["Thornwick Mills", "Halden Freight", "Brindlecorp", "Oskel Works"]
BOSSES = ["Hadrin Colbe", "Mera Oskov", "Tull Brannick"]
LANGS = ["Veltish", "Norric", "Kessari", "Ostrenic", "Pellish"]

PARTICLES = ["de", "da", "di", "do", "dos", "das", "del", "della", "delle",
             "degli", "van", "von", "der", "den", "ter", "ten", "te", "le",
             "la", "les", "du", "des", "ben", "bin", "ibn", "bat", "bint",
             "al", "el", "abu", "ap", "mac", "y", "zu"]
FIRSTS = ["Orla", "Tavo", "Senna", "Brisk", "Idra", "Pollo", "Wenna",
          "Corvin", "Maelis", "Tobin", "Ysolde", "Harrow", "Lisset", "Emric"]
LASTS = ["Carvel", "Holm", "Arom", "Tamsin", "Vessel", "Quarry", "Lint",
         "Morrow", "Fosse", "Brannoch", "Ostrey", "Pellam", "Rask", "Doon"]
EXTRA_NAMES = [  # (multi-word name, note)
    ("Bram de la Fosse", "run 'de la'"),
    ("Anneke van der Holt", "run 'van der'"),
    ("Kurt von der Lahn", "run 'von der'"),
    ("Tessaly van den Berg", "run 'van den'"),
    ("Kell O'Brannoch", "apostrophe O'"),
    ("Remy D'Arcy", "apostrophe D'"),
    ("Oona Pell-Rast", "hyphen"),
    ("Maira Ostrey-Vance Holm", "hyphen, 3 words"),
    ("Tomas de la Vega Ruiz", "run + 3 name words"),
    ("Orrin K. Vask", "initial"),
]


def value_for(k: int, verb: str) -> str:
    if verb == "lives in" or verb == "was born in":
        return PLACES[k % len(PLACES)]
    if verb == "works at":
        return FIRMS[k % len(FIRMS)]
    if verb == "works for":
        return BOSSES[k % len(BOSSES)]
    return LANGS[k % len(LANGS)]


def build() -> list[dict]:
    names = []
    for k, p in enumerate(PARTICLES):
        names.append((f"{FIRSTS[k % len(FIRSTS)]} {p} "
                      f"{LASTS[(k * 5) % len(LASTS)]}", f"particle '{p}'"))
    names += EXTRA_NAMES
    out = []
    n = 0
    for k, (multi, note) in enumerate(names):
        verb, q, rel = VERBS[k % len(VERBS)]
        val = value_for(k, verb)
        one = multi.split()[0]
        pid = f"p{k + 1:02d}"
        for fam, name in (("multi", multi), ("one", one)):
            n += 1
            out.append({
                "id": f"d232c-{n:03d}", "family": fam, "pair": pid,
                "name_words": len(name.split()),
                "setup": [f"{name} {verb} {val}."],
                "question": q.format(N=name), "gold": val,
                "expect": "ANSWER",
                "stated_facts": [[name, rel, val]],
                "note": f"{verb}; {note}" if fam == "multi"
                else f"{verb}; one-word twin of {pid}"})
    traps = [
        (["Ana and Bo live in Quellport."], "Where does Ana and Bo live?",
         "conjunction and"),
        (["Ana and Bo lives in Quellport."], "Where does Ana and Bo live?",
         "conjunction and, singular verb"),
        (["Ana & Bo Tran works at Brindlecorp."],
         "Where does Ana & Bo Tran work?", "ampersand"),
        (["Ana with Bo lives in Tarnby."], "Where does Ana with Bo live?",
         "with"),
        (["Ana or Bo speaks Veltish."], "What language does Ana or Bo speak?",
         "or"),
        (["Orrin and Tessaly Vask live in Dunmere."],
         "Where does Orrin and Tessaly Vask live?", "and between full names"),
        (["Pell plus Oda Dray works for Hadrin Colbe."],
         "Who does Pell plus Oda Dray work for?", "plus"),
        (["Maybe Sela ben Arom lives in Quellport."],
         "Where does Sela ben Arom live?", "hedge + particle"),
        (["Sela ben Arom doesn't live in Quellport."],
         "Where does Sela ben Arom live?", "negation + particle"),
        (["Ana de la del le Cruz lives in Ashvale."],
         "Where does Ana de la del le Cruz live?", "4-particle run"),
        (["the de la Cruz family lives in Ashvale."], None,
         "lower-case family subject, no question"),
        ([], "Where does Juan de la Cruz live?", "never taught"),
    ]
    for setup, q, note in traps:
        n += 1
        out.append({"id": f"d232c-{n:03d}", "family": "trap", "pair": None,
                    "name_words": 0, "setup": setup, "question": q,
                    "gold": None,
                    "expect": "NO_WRITE" if q is None else "ABSTAIN",
                    "stated_facts": [], "note": note})
    extras = [
        (["Bram de la Fosse lives in Ashvale."],
         "Where was Bram de la Fosse born?", "Bram de la Fosse", "lives in",
         "Ashvale", "other relation asked"),
        (["Sela ben Arom speaks Kessari."], "Where does Sela ben Tamsin live?",
         "Sela ben Arom", "speaks", "Kessari", "other name asked"),
        (["Ewan mac Lir works at Oskel Works."], "What language does Ewan "
         "mac Lir speak?", "Ewan mac Lir", "works at", "Oskel Works",
         "other relation asked, particle mac"),
    ]
    for setup, q, s, r, v, note in extras:
        n += 1
        same_rel = False
        out.append({"id": f"d232c-{n:03d}", "family": "stated_extra",
                    "pair": None, "name_words": len(s.split()),
                    "setup": setup, "question": q,
                    "gold": v if same_rel else None,
                    "expect": "ANSWER" if same_rel else "ABSTAIN",
                    "stated_facts": [[s, r, v]], "note": note})
    return out


if __name__ == "__main__":
    rows = build()
    Path(sys.argv[1]).write_text("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {len(rows)} dev items to {sys.argv[1]}")
