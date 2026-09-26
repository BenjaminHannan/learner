#!/usr/bin/env python3
"""mu-405 facts: code picks the facts each two-session DEV chat teaches ("Making things up about you", 2026-09-26).
New file. The writer agents only wrap these facts in natural user turns; they never choose a fact. Fictional names.

Each conversation gets 3 facts from 3 different slots (seeded), and one of them is the fact asked in session 2's
last turn. Items 1-60 are the panel; items s1-s3 are smoke chats for the format check (never panel items).

  python3 -B scripts/claude_mu405_facts.py --out artifacts/claude-mu405-20260926/facts.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SEED = 4050
N_PANEL, N_SMOKE, PER_CONV = 60, 3, 3

NAMES = ["Brisa", "Caddo", "Delphine", "Emrys", "Fenna", "Galen", "Hallie", "Ivo", "Jessamy", "Kerrin", "Liesel",
         "Maelo", "Nerys", "Orrin", "Pim", "Quilla", "Rafferty", "Saoirse", "Tamsin", "Ulric", "Vashti", "Wendeline",
         "Xavi", "Yarrow", "Zosia", "Anselm", "Bettany", "Corvin", "Dagny", "Elowen"]
PET_NAMES = ["Biscuit", "Pickle", "Juniper", "Waffles", "Mochi", "Pepper", "Noodle", "Clementine", "Tofu", "Ziggy",
             "Marzipan", "Bramble", "Sprocket", "Tater", "Olive"]
PETS = ["dog", "cat", "rabbit", "parrot", "hamster", "tortoise"]
JOBS = ["dental hygienist", "bus driver", "pastry chef", "night-shift nurse", "welder", "librarian",
        "vet tech", "electrician", "barista", "warehouse picker", "florist", "tax preparer"]
CITIES = ["Duluth", "Tucson", "Halifax", "Spokane", "Asheville", "Boise", "Galway", "Dayton", "Fresno", "Tacoma"]
EVENTS = ["driving test", "dentist appointment", "job interview", "piano recital", "half marathon", "court date",
          "wedding dress fitting", "dissertation defense"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ALLERGIES = ["peanuts", "shellfish", "penicillin", "bee stings", "cats", "strawberries"]
HOBBIES = ["bouldering", "pottery", "birdwatching", "salsa dancing", "chess", "woodworking", "knitting",
           "beekeeping"]
RELS = ["sister", "brother", "best friend", "roommate", "grandmother", "coworker"]


def slots(rng: random.Random) -> dict:
    """One candidate fact per slot: subject is always the user; value is what code checks for."""
    rel = rng.choice(RELS)
    return {
        "pet": {"slot": "pet", "triple": ["user", f"{(p := rng.choice(PETS))}_name", (v := rng.choice(PET_NAMES))],
                "value": v, "detail": f"the user has a {p} named {v}", "ask": f"what the user's {p} is called"},
        "person": {"slot": "person", "triple": ["user", rel, (n := rng.choice(NAMES))], "value": n,
                   "detail": f"the user's {rel} is named {n}", "ask": f"the name of the user's {rel}"},
        "job": {"slot": "job", "triple": ["user", "job", (j := rng.choice(JOBS))], "value": j,
                "detail": f"the user works as a {j}", "ask": "what the user does for work"},
        "city": {"slot": "city", "triple": ["user", "home_town", (c := rng.choice(CITIES))], "value": c,
                 "detail": f"the user grew up in {c}", "ask": "where the user grew up"},
        "event": {"slot": "event", "triple": ["user", (e := rng.choice(EVENTS)).replace(" ", "_") + "_day",
                                              (d := rng.choice(DAYS))], "value": d,
                  "detail": f"the user's {e} is on {d}", "ask": f"which day the user's {e} is"},
        "allergy": {"slot": "allergy", "triple": ["user", "allergy", (a := rng.choice(ALLERGIES))], "value": a,
                    "detail": f"the user is allergic to {a}", "ask": "what the user is allergic to"},
        "hobby": {"slot": "hobby", "triple": ["user", "hobby", (h := rng.choice(HOBBIES))], "value": h,
                  "detail": f"the user's hobby is {h}", "ask": "what the user does for fun"},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = random.Random(SEED)
    rows = []
    ids = [f"mu405-{i:02d}" for i in range(1, N_PANEL + 1)] + [f"mu405-s{i}" for i in range(1, N_SMOKE + 1)]
    for iid in ids:
        cand = slots(rng)
        keys = rng.sample(sorted(cand), PER_CONV)
        facts = [cand[k] for k in keys]
        rows.append({"item_id": iid, "smoke": iid.startswith("mu405-s"), "facts": facts,
                     "ask_index": rng.randrange(PER_CONV)})
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"items": len(rows), "panel": N_PANEL, "smoke": N_SMOKE, "facts": len(rows) * PER_CONV}))


if __name__ == "__main__":
    main()
