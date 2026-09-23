#!/usr/bin/env python3
"""Experiment 162b -- build the sealed T1/T2 probe case file (Muse).

Reads artifacts/fable-thename162-20260922/cases162.json READ-ONLY and copies
the 26 must-write (W01-W26), 12 office (O01-O12), 11 must-not-write (N01-N11)
and 2 chain (C1-C2) rows VERBATIM, then prepends 24 NEW plural rows
(P01-P24: 8 table relations x 3 plural names, each with teach + Who + What +
of-form asks) and appends 1 NEW plural chain (C3). Total 76 rows.

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
ART162 = ROOT / "artifacts" / "fable-thename162-20260922"
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"

# 8 table relations (the same 8 as 162's W set) x 3 plural names.
PLURAL_SPECS = [
    ("founder", [("The Beatles", "Lennon"), ("The Rolling Stones", "Jagger"),
                 ("The Supremes", "Ross")]),
    ("author", [("The Beatles", "Asimov"), ("The Rolling Stones", "Clarke"),
                ("The Times", "Herbert")]),
    ("genre", [("The Beatles", "rock"), ("The Supremes", "soul"),
               ("The Temptations", "funk")]),
    ("performer", [("The Beatles", "Lennon"), ("The Supremes", "Ross"),
                   ("The Temptations", "Kendricks")]),
    ("manufacturer", [("The Beatles", "Boeing"), ("The Rolling Stones", "Ford"),
                      ("The Times", "Cook")]),
    ("headquarters location", [("The Beatles", "London"),
                               ("The Rolling Stones", "Denver"),
                               ("The Times", "Littlehampton")]),
    ("official language", [("The Beatles", "English"),
                           ("The Supremes", "French"),
                           ("The Temptations", "Spanish")]),
    ("employer", [("The Beatles", "Parlophone"), ("The Supremes", "Trust"),
                  ("The Temptations", "EMI")]),
]


def plural_row(pid: str, rel: str, name: str, val: str) -> dict:
    key = "_".join(rel.split())
    return {
        "id": pid,
        "group": "plural",
        "teach": f"{name}' {rel} is {val}.",
        "expect": [name, key, val],
        "reply": "saved",
        "asks": [
            {"q": f"Who is {name}' {rel}?", "want": val},
            {"q": f"What is {name}' {rel}?", "want": val},
            {"q": f"Who is the {rel} of {name}?", "want": val},
        ],
    }


def main() -> int:
    base = json.loads((ART162 / "cases162.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in base}
    rows: list[dict] = []
    n = 0
    for rel, triples in PLURAL_SPECS:
        for name, val in triples:
            n += 1
            rows.append(plural_row(f"P{n:02d}", rel, name, val))
    assert n == 24, n
    for wid in [f"W{i:02d}" for i in range(1, 27)]:
        rows.append(by_id[wid])
    for oid in [f"O{i:02d}" for i in range(1, 13)]:
        row = dict(by_id[oid])
        row["identical_to_base"] = True
        rows.append(row)
    for nid in [f"N{i:02d}" for i in range(1, 12)]:
        row = dict(by_id[nid])
        row["identical_to_base"] = True
        rows.append(row)
    rows.append(by_id["C1"])
    rows.append(by_id["C2"])
    rows.append({
        "id": "C3",
        "group": "chain",
        "teaches": ["The Supremes' founder is Ross.",
                    "Ross's mother is Judy."],
        "expect": [["The Supremes", "founder", "Ross"],
                   ["Ross", "mother", "Judy"]],
        "reply": "saved",
        "asks": [
            {"q": "Who is The Supremes' founder's mother?", "want": "Judy"},
            {"q": "Who is the mother of The Supremes' founder?",
             "want": "Judy"},
        ],
    })
    ART162B.mkdir(parents=True, exist_ok=True)
    dest = ART162B / "cases162b.json"
    dest.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    groups: dict[str, int] = {}
    for r in rows:
        groups[r["group"]] = groups.get(r["group"], 0) + 1
    print(f"wrote {dest} n={len(rows)} groups={groups}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
