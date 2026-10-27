#!/usr/bin/env python3
"""Experiment 154f -- plain-negation removal (pure helpers, no loop code).

Read-only imports only: FakeEars._relation from scripts/fable_agent_loop.py,
154b sealed forms from scripts/fable_fix154b_multival.py.

Sealed shapes (single hop only):
  * "Rana's language is not Hindi." / "Rana's language isn't Hindi."
    -> {name, relation (key), rel_surface, value}
  * Excluded (None, base path keeps the reply byte-identical):
    - questions (trailing "?"): "Is Rana's language not Hindi?"
    - multi-hop rel surfaces ("The city of Kim's boss is not Oslo."
      fails the single-name anchor; "Kim's boss's city is not Oslo"
      has a possessive inside the relation surface)
    - possessive inside the value ("Rana's sister is not Kim's boss.")
    - correct-not ("No, Rana's language is Tamil, not Hindi.") and
      forget ("Forget ...") shapes (different anchors)
    - pretend/directive prefixes ("Say Rana's language is not Hindi."
      does not anchor on the name)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation map, read-only)

# "Rana's language is not Hindi." Group 1: name, 2: relation surface,
# 3: value. The name anchor must sit at the very start so "Say ...",
# "No, ...", "Actually ..." and question prefixes never match.
_NEGATE154F = re.compile(
    r"^\s*([A-Za-z][A-Za-z'\-]*)\s*'s\s+(.+?)\s+is\s+not\s+(.+?)\s*[.!]*\s*$",
    re.IGNORECASE)

_ISNT154F = re.compile(r"\bisn['\u2019]t\b", re.IGNORECASE)


def relation_key154f(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def parse_negate154f(turn: str) -> dict | None:
    """Parse a plain-negation removal -> {name, relation, value} | None."""
    text = " ".join(str(turn).split())
    if not text or text.rstrip().endswith("?"):
        return None
    text = _ISNT154F.sub("is not", text)
    found = _NEGATE154F.match(text)
    if found is None:
        return None
    name, rel_surface, value = (found.group(1).strip(),
                                found.group(2).strip(),
                                found.group(3).strip())
    if not name or not rel_surface or not value:
        return None
    if re.search(r"['\u2019]s\b", rel_surface):
        return None  # multi-hop relation: not handled, base keeps it
    if re.search(r"['\u2019]s\b", value):
        return None  # possessive value: not handled, base keeps it
    if re.search(r"['\u2019]s\b", name):
        return None  # multi-word/possessive subject, base keeps it
    if " " in name:
        return None  # base one-word-name rule keeps it
    return {"name": name, "relation": relation_key154f(rel_surface),
            "rel_surface": rel_surface, "value": value}
