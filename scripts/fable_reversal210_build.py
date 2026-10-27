#!/usr/bin/env python3
"""Experiment 210 -- build a TRUE reversal split (benchmark repair, no agent change).

Writes data/open/reversal210/fable_reversal210.jsonl (+ manifest).

Design (from pilots on loop138i, scratch/rev210pilot):
- 50 reversal facts, each taught with ONE sentence only (one direction).
  S_FIRST teach:  "PERSON is the ROLE of WORK."   (loop stores it)
  O_FIRST teach:  "WORK's ROLE is PERSON."        (loop stores it)
  (Verb-form teaches like "X composed Y" are rejected by the loop's ears,
  and passive "The ROLE of WORK is PERSON" is rejected too -- piloted.)
- Reversal questions are verb-form, grammatical, gold never in question:
  S_FIRST taught -> "Who PAST WORK?"        (gold PERSON)
  O_FIRST taught -> "What did PERSON BASE?" (gold WORK)
- 20 controls taught one direction, asked in the TAUGHT direction:
  S_FIRST taught -> "What did PERSON BASE?" (gold WORK, forward)
  O_FIRST taught -> "Who PAST WORK?"        (gold PERSON, forward)
- All persons and all works unique across the 70 items (unambiguous).
- Fictional names only.

Run: python -B scripts/fable_reversal210_build.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
OUTDIR = ROOT / "data" / "open" / "reversal210"

# (base, past, past-participle, role noun)
VERBS = [
    ("compose", "composed", "composed", "composer"),
    ("write", "wrote", "written", "author"),
    ("discover", "discovered", "discovered", "discoverer"),
    ("found", "founded", "founded", "founder"),
    ("paint", "painted", "painted", "painter"),
    ("direct", "directed", "directed", "director"),
    ("invent", "invented", "invented", "inventor"),
    ("design", "designed", "designed", "designer"),
]

PEOPLE = [
    "Damon Moonrake", "Marisol Underbough", "Rosalind Aldercroft",
    "Dunstan Ashdown", "Keziah Thornwhistle", "Barnaby Quillfeather",
    "Odette Larkspur", "Caspian Holloway", "Imogen Starling",
    "Percival Grimsbane", "Lavinia Crowmarsh", "Ambrose Nightingale",
    "Cordelia Frostbound", "Leander Wolfhart", "Seraphina Brightmoor",
    "Quentin Ironwood", "Evangeline Mistral", "Horace Bramblewick",
    "Prudence Silverthwaite", "Gideon Emberfall", "Beatrix Hollowmere",
    "Silas Copperfield", "Wren Halloway", "Tobias Fenwick",
    "Algernon Blackbriar", "Delphine Ravensworth", "Edmund Grayshore",
    "Fiona Amberline", "Gareth Stonebridge", "Harriet Willowsong",
    "Ivor Duskendale", "Jemima Lightfoot", "Kester Oakenshield",
    "Lydia Marshbank", "Milo Copperpot", "Nerissa Wavecrest",
    "Orson Blackmoor", "Petra Goldfinch", "Quillan Frost", "Rowan Ashford",
    "Sylvia Thornbury", "Tamara Vell", "Ulric Stone", "Vera Nightshade",
    "Wesley Brook", "Xanthe Marlowe", "Yorick Fenn", "Zelda Harrow",
    "Anselm Crow", "Bridget Sable", "Cyprian Vale", "Delia Moss",
    "Edwin Lark", "Farah Quinn", "Giles Reed", "Hester Bly",
    "Ivan Marsh", "Juniper Cole", "Kelvin Hart", "Liora Wren",
    "Marek Dune", "Nadia Frost", "Otto Vane", "Paloma Skye",
    "Rufus Gale", "Sable Quinn", "Tamsin Rook", "Ulfric Bain",
    "Vesper Lane", "Willa Dorn",
]

WORKS = [
    "Gilded Mirrors", "Oaken Melodies", "Woven Compasses",
    "Silver Feasts", "Crimson Lanterns", "Velvet Harbors",
    "Marble Echoes", "Golden Thistles", "Silent Caravans",
    "Ivory Tides", "Copper Skies", "Jade Labyrinths",
    "Amber Chronicles", "Bronze Gardens", "Crystal Voyages",
    "Ebony Sonatas", "Scarlet Mazes", "Opal Windows",
    "Rustic Hymns", "Hollow Crowns", "Luminous Riddles",
    "Frozen Bells", "Hidden Stairways", "Burnished Drums",
    "Quiet Masks", "Paper Moons", "Iron Ballads", "Glass Orchards",
    "Tin Stars", "Leaden Rivers", "Amber Wicks", "Salt Psalms",
    "Fern Canticles", "Moss Tablets", "Pebble Odes", "Reed Ghazals",
    "Slate Elegies", "Thorn Epics", "Willow Sestinas", "Yew Limericks",
    "Ashen Villanelles", "Birch Haikus", "Cedar Sonnets",
    "Driftwood Odes", "Elder Fables", "Flint Parables",
    "Granite Allegories", "Heather Myths", "Indigo Legends",
    "Juniper Tales", "Kelp Stories", "Linen Ballads",
    "Maple Ditties", "Nettle Rhymes", "Obsidian Verses",
    "Pine Refrains", "Quartz Choruses", "Rowan Rounds",
    "Spruce Shanties", "Teak Anthems", "Umber Carols",
    "Vine Serenades", "Wheat Nocturnes", "Xenon Lullabies",
    "Yarrow Dirges", "Zinc Fanfares", "Almond Requiems",
    "Basalt Preludes", "Coral Fugues", "Dune Sonatas",
]


def teach_s_first(person: str, role: str, work: str) -> str:
    return f"{person} is the {role} of {work}."


def teach_o_first(person: str, role: str, work: str) -> str:
    return f"{work}'s {role} is {person}."


def q_who(past: str, work: str) -> str:
    return f"Who {past} {work}?"


def q_what(person: str, base: str) -> str:
    return f"What did {person} {base}?"


def main() -> int:
    assert len(PEOPLE) >= 70 and len(WORKS) >= 70
    assert len(set(PEOPLE)) == len(PEOPLE)
    assert len(set(WORKS)) == len(WORKS)
    items: list[dict] = []
    # 50 reversal: alternate S_FIRST / O_FIRST; verb cycles through VERBS.
    for i in range(50):
        person, work = PEOPLE[i], WORKS[i]
        base, past, _part, role = VERBS[i % len(VERBS)]
        if i % 2 == 0:
            taught = teach_s_first(person, role, work)
            tdir = "S_FIRST"
            question = q_who(past, work)
            gold = person
            asked = "WHO_REV"
        else:
            taught = teach_o_first(person, role, work)
            tdir = "O_FIRST"
            question = q_what(person, base)
            gold = work
            asked = "WHAT_REV"
        cue = work if gold == person else person
        items.append({
            "id": f"rev210-{i + 1:03d}",
            "type": "reversal", "expected": "answer",
            "source": "reversal210-fictional",
            "person": person, "work": work,
            "verb_base": base, "verb_past": past, "role": role,
            "taught": [{"sentence_en": taught, "subject": person,
                        "relation": role, "object": work, "dir": tdir}],
            "taught_dir": tdir,
            "question": question, "asked": asked,
            "gold": [gold], "gold_aliases": [],
            "cue": cue,
        })
    # 20 controls: asked in the TAUGHT direction.
    for j in range(20):
        k = 50 + j
        person, work = PEOPLE[k], WORKS[k]
        base, past, _part, role = VERBS[k % len(VERBS)]
        if j % 2 == 0:
            taught = teach_s_first(person, role, work)
            tdir = "S_FIRST"
            question = q_what(person, base)
            gold = work
            asked = "WHAT_FWD"
        else:
            taught = teach_o_first(person, role, work)
            tdir = "O_FIRST"
            question = q_who(past, work)
            gold = person
            asked = "WHO_FWD"
        cue = work if gold == person else person
        items.append({
            "id": f"rev210-c{j + 1:02d}",
            "type": "control", "expected": "answer",
            "source": "reversal210-fictional",
            "person": person, "work": work,
            "verb_base": base, "verb_past": past, "role": role,
            "taught": [{"sentence_en": taught, "subject": person,
                        "relation": role, "object": work, "dir": tdir}],
            "taught_dir": tdir,
            "question": question, "asked": asked,
            "gold": [gold], "gold_aliases": [],
            "cue": cue,
        })
    OUTDIR.mkdir(parents=True, exist_ok=True)
    data_p = OUTDIR / "fable_reversal210.jsonl"
    data_p.write_text("\n".join(
        json.dumps(it, ensure_ascii=False, sort_keys=True)
        for it in items) + "\n", encoding="utf-8")
    (OUTDIR / "fable_reversal210_build_manifest.json").write_text(
        json.dumps({"n": len(items),
                    "n_reversal": 50, "n_control": 20,
                    "verbs": [v[0] for v in VERBS],
                    "note": "one taught sentence per item; "
                            "reversal asked opposite dir, control same dir"},
                   indent=1), encoding="utf-8")
    print(f"wrote {data_p} n={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
