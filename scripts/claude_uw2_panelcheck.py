#!/usr/bin/env python3
"""uw-2 panel check (artifacts/claude-uw2-20260926/PANEL-SPEC-uw2-addendum.md). Wrong-as-fact thread, 2026-09-26.
New file. Prints COUNTS and ids only, never user text, names or values, so it can run on a TEST-ONLY bank.

  python3 scripts/claude_uw2_panelcheck.py DIR        exit 0 iff every uw-2 check passes
  python3 scripts/claude_uw2_panelcheck.py --selftest

Checks (on top of scripts/claude_sf401_panelcheck.py, which the writer also runs):
  U-a  at least 72 correction turns (corrections.jsonl), each with its old fact a note just before the turn
  U-b  at least 40 earlier-owner corrections: the owner is not the user and neither the owner's full name nor its first
       word is a whole word in the correction message (the uw-2 PASSMARKS definition, claude_uw1_cards grading)
  U-c  every earlier-owner correction's owner is named (whole word) in an earlier user turn of the same life, at least
       2 turns before the correction
  U-d  at least 30 decoy turns and 15 nosave turns (as PANEL-SPEC)
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_uw1_cards as U  # noqa: E402

MIN_CORR, MIN_EO, MIN_DECOY, MIN_NOSAVE = 72, 40, 30, 15


def named(text: str, owner: str) -> bool:
    return U._vmatch(text, owner) or U._vmatch(text, str(owner).split()[0])


def earlier_owner(card: dict) -> bool:
    g = card["gold"]
    return g["type"] == "CHANGE" and g["owner"] != U.USER and not named(card["text"], g["owner"])


def check(d: Path) -> tuple[dict, dict]:
    cards = U.cards_bank(d)
    errs: dict = {}
    c = Counter(group for group in (x["group"] for x in cards))
    corr = [x for x in cards if x["gold"]["type"] == "CHANGE"]
    eo = [x for x in corr if earlier_owner(x)]
    bad_old = [x["card"] for x in corr if not any(v.lower() == x["gold"]["old"].lower() for (_o, _r, v) in x["notes"])]
    far = []
    for x in eo:
        life, i = x["card"].split(":")
        i = int(i)
        before = [y for y in cards if y["card"].split(":")[0] == life and int(y["card"].split(":")[1]) <= i - 2]
        if not any(named(y["text"], x["gold"]["owner"]) for y in before):
            far.append(x["card"])
    counts = {"cards": len(cards), "corrections": len(corr), "earlier_owner": len(eo),
              "user_owned_corrections": sum(x["gold"]["owner"] == U.USER for x in corr),
              "decoy": c["decoy"], "nosave": c["nosave"], "other_cards": len(cards) - len(corr),
              "earlier_owner_by_style": dict(sorted(Counter(x["gold"]["style"] for x in eo).items()))}
    if len(corr) < MIN_CORR:
        errs["U-a corrections"] = len(corr)
    if bad_old:
        errs["U-a old fact not a note"] = bad_old
    if len(eo) < MIN_EO:
        errs["U-b earlier_owner"] = len(eo)
    if far:
        errs["U-c owner not named 2+ turns before"] = far
    if c["decoy"] < MIN_DECOY or c["nosave"] < MIN_NOSAVE:
        errs["U-d decoy/nosave"] = [c["decoy"], c["nosave"]]
    return counts, errs


def selftest() -> None:
    life = [(0, "teach", "my sister Oriel lives in Tamsby"), (1, "smalltalk", "long day"),
            (2, "correct", "oops, she lives in Varn actually"), (3, "correct", "Oriel is 31 btw, not 30"),
            (4, "nosave", "maybe i'll move")]
    turns = [{"life_id": "sf-t-01", "day": 1, "turn_index": i, "user_text": t, "kind": k, "ask_type": None,
              "facts": [], "gold": None, "creative_seed_facts": []} for i, k, t in life]
    truth = [{"fact_id": "f1", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Tamsby",
              "taught_turn": 0, "valid_until_turn": 2},
             {"fact_id": "f2", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Varn",
              "taught_turn": 2, "valid_until_turn": None},
             {"fact_id": "f3", "life_id": "sf-t-01", "owner": "Oriel", "relation": "age", "value": "30",
              "taught_turn": 0, "valid_until_turn": 3},
             {"fact_id": "f4", "life_id": "sf-t-01", "owner": "Oriel", "relation": "age", "value": "31",
              "taught_turn": 3, "valid_until_turn": None}]
    corr = [{"life_id": "sf-t-01", "turn_index": 2, "old_fact": "f1", "new_fact": "f2", "style": 2},
            {"life_id": "sf-t-01", "turn_index": 3, "old_fact": "f3", "new_fact": "f4", "style": 5}]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for name, rows in (("turns", turns), ("truth", truth), ("corrections", corr), ("decoys", [])):
            (d / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        counts, errs = check(d)
    assert counts["corrections"] == 2 and counts["earlier_owner"] == 1 and counts["nosave"] == 1, counts
    assert "U-a old fact not a note" not in errs and "U-c owner not named 2+ turns before" not in errs, errs
    assert "U-a corrections" in errs and "U-b earlier_owner" in errs and "U-d decoy/nosave" in errs, errs
    print("selftest ok")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    counts, errs = check(Path(sys.argv[1]))
    print(json.dumps({"counts": counts, "errors": {k: (v if isinstance(v, int) or len(v) <= 2 else len(v))
                                                   for k, v in errs.items()}}, sort_keys=True))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
