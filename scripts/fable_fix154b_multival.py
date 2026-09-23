#!/usr/bin/env python3
"""Experiment 154b -- multi-valued relations: pure helpers (no loop code).

Read-only imports only: SINGLE_VALUED_154 from scripts/fable_fix154_yesno.py,
FakeEars._relation + PERSON_RELATIONS from scripts/fable_agent_loop.py.

Sealed rules (see PASSMARKS.md):
  * multi-valued = relation key NOT in SINGLE_VALUED_154.
  * list form (single-hop ask over 2+ values, oldest first):
      "Omar's sister is Priya and Lena." / 3+: "A, B and C".
  * add reply: "Saved: Omar's sister is Lena. (I also have Priya.)"
  * mid-chain clarify: "Omar's sister is Priya and Lena. Which one do you mean?"
  * correct-not reply: "Saved: Omar's sister is Lena." (+ remainers
    parenthetical when values remain; " (I didn't have {old}.)" when the
    named old value was not current).
  * forget-one reply: "Forgotten: Omar's sister Priya." / miss:
    "I don't have Omar's sister Priya."
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation map + person set, read-only)
from fable_fix154_yesno import SINGLE_VALUED_154  # noqa: E402 (sealed table, read-only)


def relation_key154b(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def is_single154b(key: str) -> bool:
    """True iff the relation key is single-valued per the sealed 154 table."""
    return key in SINGLE_VALUED_154


def join_and154b(items: list[str]) -> str:
    """Sealed list join: 'A and B', 'A, B and C'."""
    items = list(items)
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def display154b(nb, value: dict) -> str:
    """Value display (entity name or literal text)."""
    if "entity" in value:
        return str(nb.entities.get(value["entity"], value["entity"]))
    return str(value.get("literal", ""))


def taught_current154b(nb, entity_id: str, relation: str) -> list[dict]:
    """Active taught rows for (entity, relation), oldest fact first."""
    rows = [fact for fact_id, fact in nb.facts.items()
            if fact.get("subject") == entity_id
            and fact.get("relation") == relation
            and fact.get("source") == "taught"
            and nb.active(fact_id)]
    rows.sort(key=lambda f: f["n"])
    return rows


def current_values154b(nb, entity_id: str, relation: str) -> list[str]:
    """Distinct current displays, oldest first."""
    seen: list[str] = []
    for row in taught_current154b(nb, entity_id, relation):
        shown = display154b(nb, row["value"])
        if shown not in seen:
            seen.append(shown)
    return seen


# "No, Omar's sister is Lena, not Priya." (single hop only; the name part
# must not itself contain a possessive). Group 1: prefix, 2: name,
# 3: relation surface, 4: new value, 5: old value.
_NOT154B = re.compile(
    r"^\s*(?:actually\s*,?|actually\s+|no\s*,|correction\s*:|sorry\s*,?)\s*"
    r"([A-Za-z][A-Za-z'\-]*)\s*'s\s+(.+?)\s+is\s+(.+?)\s*,\s*not\s+(.+?)\s*[.?!]*\s*$",
    re.IGNORECASE)


def parse_correct_not154b(turn: str) -> dict | None:
    """Parse the named-value correction shape -> {name, relation, new, old}."""
    text = " ".join(str(turn).split())
    if text.rstrip().endswith("?"):
        return None
    found = _NOT154B.match(text)
    if found is None:
        return None
    name, rel_surface, new, old = (found.group(1).strip(), found.group(2).strip(),
                                  found.group(3).strip(), found.group(4).strip())
    if not name or not rel_surface or not new or not old:
        return None
    if re.search(r"['\u2019]s\b", rel_surface):
        return None  # multi-hop: not handled, base path keeps it
    if " " in name:
        return None  # base one-word-name rule keeps it
    return {"name": name, "relation": relation_key154b(rel_surface),
            "rel_surface": rel_surface, "new": new, "old": old}


# "Forget Omar's sister Priya." Split of the tail into relation + value is
# resolved against the notebook's current values (exact display match).
_FORGET154B = re.compile(r"^\s*forget\s+(\S+?)'s\s+(.+?)\s*[.?!]*\s*$",
                         re.IGNORECASE)


def parse_forget_one154b(turn: str, nb) -> dict | None:
    """Parse a named-value forget -> {name, relation, value} | None.

    A split fires when the relation key is non-single-valued AND (the
    value matches a current taught value OR the relation is already a
    declared notebook relation). Otherwise None, so the base whole-slot
    path (and unknown-relation turns) stay byte-identical.
    """
    text = " ".join(str(turn).split())
    found = _FORGET154B.match(text)
    if found is None:
        return None
    name, tail = found.group(1).strip(), found.group(2).strip()
    words = tail.split()
    if len(words) < 2:
        return None
    resolved = nb.resolve(name)
    if resolved.status != "OK":
        return None
    entity_id = resolved.detail["entity_id"]
    known = {e["relation"] for e in nb.events if e["kind"] == "RELATION"}
    for cut in range(1, len(words)):
        rel_surface = " ".join(words[:cut])
        value = " ".join(words[cut:])
        key = relation_key154b(rel_surface)
        if is_single154b(key):
            continue  # single-valued forgets stay on the base path
        if value in current_values154b(nb, entity_id, key) or key in known:
            return {"name": name, "relation": key, "rel_surface": rel_surface,
                    "value": value, "entity_id": entity_id}
    return None
