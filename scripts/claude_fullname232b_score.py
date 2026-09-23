#!/usr/bin/env python3
"""Exp 232b scorer: the sealed 232 scorer with ONE corrected definition.

Imports scripts/claude_fullname232_score.py unchanged (sealed in 232) and
replaces only how wrong writes and trap writes are counted:

  * wrong write: a fact the agent ever stored during the item (every taught
    triple in the last turn's cumulative `all` list, active or not) that
    matches NO entry of the item's `stated_facts`. Match = subject and value
    equal case-insensitively (whitespace collapsed, trailing periods
    dropped), and relation equal after the alias map below (the stated verb
    word or the canonical relation 232's code maps it to). An entry with no
    relation matches on subject + value only.
  * trap write (trap items = `pair` empty/None, or `family` starting with
    "trap"): ANY stored fact counts as a trap write, and is not also counted
    as a wrong write.

Everything else is 232's sealed code: right / gold / other-value rules,
missing writes (vs expect_writes), M1b-M1f, pass items, latency (M5),
rerun checks. Usage is identical to the 232 scorer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_fullname232_score as S232  # noqa: E402 (sealed, read-only)

# Stated verb word -> canonical relation 232 stores (city, employer,
# language, place of birth). Added to 232's alias map for this scorer only.
EXTRA_ALIAS_232B = {
    "lives_in": "city", "live_in": "city", "living_in": "city",
    "works_at": "employer", "work_at": "employer", "works_for": "employer",
    "work_for": "employer",
    "speaks": "language", "speak": "language",
    "was_born_in": "place_of_birth", "born_in": "place_of_birth",
    "place_of_birth": "place_of_birth",
}
S232.REL_ALIAS.update(EXTRA_ALIAS_232B)

_orig_judge = S232.judge_item


def is_trap(item) -> bool:
    fam = str(item.get("family") or "").lower()
    return item.get("pair") in (None, "") or fam.startswith("trap")


def judge_item_232b(item, row) -> dict:
    res = _orig_judge(item, row)
    turns = row["turns"]
    ever = turns[-1]["all"] if turns else []
    stated = S232.entries(item.get("stated_facts"))
    if is_trap(item):
        res["trap_writes"] = [list(f) for f in ever]
        res["wrong_writes"] = []
    else:
        res["trap_writes"] = []
        res["wrong_writes"] = [list(f) for f in ever
                               if not any(S232.matches(f, e) for e in stated)]
    res["stated_facts_n"] = len(stated)
    return res


S232.judge_item = judge_item_232b

if __name__ == "__main__":
    sys.exit(S232.main())
