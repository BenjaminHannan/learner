#!/usr/bin/env python3
"""Experiment 154c -- allow-list of multi-valued relations (pure helpers).

Read-only imports only: SINGLE_VALUED_154 from scripts/fable_fix154_yesno.py
(sealed 154 table) and FakeEars._relation from scripts/fable_agent_loop.py
(the base parser's relation mapping, read-only).

THE ONE RULE: the add-a-second-value path fires ONLY for relation keys in
MULTI_VALUED_154C below. Every other relation -- including every relation
that 154b treated as multi-valued but that is NOT listed here -- behaves
byte-identically to loop138b (change-prompt / replace). Everything listed
here behaves byte-identically to loop154b (sealed 154b reply forms).

The base parser's relation mapping is trivial
(scripts/fable_agent_loop.py FakeEars._relation: lowercase + underscores),
so the only "surface variants" that can ever reach the loop as distinct
keys are spacing/punctuation variants; those included are listed with
reasons. Nothing about citizenship, language, speaks, country, occupation,
job, employer, position, league, team, religion, genre, headquarters,
capital, city, or any place/organisation relation is listed.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation map, read-only)

# Sealed allow-list: relations where several current values are normal for
# people in everyday English. A re-teach on any OTHER relation replaces
# (loop138b change-prompt), exactly as before.
MULTI_VALUED_154C = frozenset({
    "sister",       # people normally have several sisters
    "brother",      # people normally have several brothers
    "sibling",      # several siblings is the normal case
    "friend",       # people normally have many friends
    "child",        # people normally have several children
    "son",          # several sons is normal (child surface variant)
    "daughter",     # several daughters is normal (child surface variant)
    "pet",          # people normally have several pets
    "dog",          # several dogs is normal (pet surface variant)
    "cat",          # several cats is normal (pet surface variant)
    "cousin",       # people normally have many cousins
    "grandchild",   # people normally have several grandchildren
    "grand_child",  # spaced surface "grand child" -> distinct parser key
    "grand_son",    # spaced surface "grand son" -> distinct parser key
    "grand_daughter",  # spaced surface "grand daughter" -> distinct key
    "aunt",         # people normally have several aunts
    "uncle",        # people normally have several uncles
    "colleague",    # people normally have many colleagues
    "coworker",     # people normally have many coworkers
    "co_worker",    # spaced surface "co worker" -> distinct parser key
    "co-worker",    # hyphenated surface "co-worker" -> distinct parser key
    "notable_work",  # creators normally have several notable works
})


def relation_key154c(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def is_multi154c(key: str) -> bool:
    """True iff the relation key takes the 154b add-a-second-value path."""
    return key in MULTI_VALUED_154C
