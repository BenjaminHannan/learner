#!/usr/bin/env python3
"""Experiment 154g -- "No," corrections on multi-valued relations: pure helpers.

Read-only imports only: FakeEars._relation + PERSON_RELATIONS from
scripts/fable_agent_loop.py, 154b multival readers, the 154e allow-list.
No 154e/154c/154b/138b file is edited; everything new lives here.

LINEAGE of the correction prefixes (where each already appears):
  * scripts/fable_agent_loop.py:95  `_CORRECTION` -- "actually" / "no,".
  * scripts/fable_loop102_agent.py:92-95 `_CORRECTION_PREFIX_RE` --
    "actually," / "actually " / "no," / "correction:" / "sorry, i meant".
  * scripts/fable_fix154b_multival.py:83-86 `_NOT154B` -- "actually" /
    "no," / "correction:" / "sorry," (the "X is Y, not Z" shape).
  * scripts/fable_fix160_barecorrect.py docstring -- "actually," /
    "actually " / "no," / "correction:" / "sorry[ ,] i meant".
154g seals exactly three of those: "No," / "Actually," / "Correction:".

SEALED 154g RULE (one change vs loop154e):
  <prefix> X's R is Y.  (prefix in {No, / Actually, / Correction:},
  single-hop possessive, one-word name, R multi-valued per is_multi154e)
  * exactly ONE current value          -> REPLACE it (single-valued
    correction mechanics; reply names the old value).
  * TWO OR MORE current values         -> 0 writes + one fixed question
    "Which one should {Y} replace: {A} or {B}?" (3+: "A, B or C").
    The next turn naming exactly one listed value replaces THAT value;
    any other next turn cancels (0 writes) and is processed normally.
  * NO current value                    -> fall through (plain teach).
Plain teaches without a prefix keep the 154e add path unchanged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation map, read-only)
import fable_fix154b_multival as M154  # noqa: E402 (readers, read-only)
import fable_fix154e_allowlist as M154E  # noqa: E402 (allow-list, read-only)

# The three sealed prefixes (case-insensitive; comma/colon as in lineage).
_PREFIX154G = r"(?:no\s*,|actually\s*,|correction\s*:)"
_CORR154G = re.compile(
    r"^\s*(" + _PREFIX154G + r")\s*(.+)$", re.IGNORECASE | re.DOTALL)

_APOS154G = r"['\u2019]s\b\s*"


def _chain154g(text: str) -> list[str]:
    return [p.strip() for p in re.split(_APOS154G, text.strip())
            if p.strip()]


def parse_bare_correction154g(turn: str) -> dict | None:
    """Parse '<prefix> X's R is Y.' -> {prefix, name, relation, rel_key,
    value} | None.

    Guards (fall through to the base path when any fails): the ", not Z"
    correct-not shape (154e owns it), "?" questions, multi-hop
    possessives, multi-word names (the base one-word rule), empty names /
    relations / values. Subject screens and the known-name check live in
    the ears layer (needs the notebook).
    """
    text = " ".join(str(turn).split())
    found = _CORR154G.match(text)
    if found is None:
        return None
    prefix, rest = found.group(1), found.group(2).strip()
    if not rest or rest.rstrip().endswith("?"):
        return None
    if M154.parse_correct_not154b(text) is not None:
        return None  # the "Y, not Z" shape stays on the 154e path
    stmt = re.match(r"^\s*(.+?)\s+is\s+(.+?)\s*[.!]*\s*$", rest,
                    re.IGNORECASE | re.DOTALL)
    if stmt is None:
        return None
    left, value = stmt.group(1).strip(), stmt.group(2).strip()
    if not value:
        return None
    parts = _chain154g(left)
    if len(parts) != 2:
        return None
    name, rel_surface = parts[0].strip(), parts[1].strip()
    if not name or not rel_surface or " " in name:
        return None
    key = A.FakeEars._relation(rel_surface)
    if not M154E.is_multi154e(key):
        return None  # single-valued: the base path owns it, byte-identical
    return {"prefix": prefix, "name": name, "relation": rel_surface,
            "rel_key": key, "value": value}


def replace_question154g(new: str, values: list[str]) -> str:
    """The one fixed sealed question (2+: no Oxford comma, 'or')."""
    vals = list(values)
    if len(vals) <= 2:
        listed = " or ".join(vals)
    else:
        listed = ", ".join(vals[:-1]) + " or " + vals[-1]
    return f"Which one should {new} replace: {listed}?"


def match_single_candidate154g(turn: str, candidates: list[str]) -> str | None:
    """The pending answer names exactly one listed value -> that value.

    Normalise: collapse whitespace, strip one trailing "." / "!" (never
    "?": a question always cancels). Match is exact against the stored
    displays; naming zero or two+ candidates -> None (cancel).
    """
    text = " ".join(str(turn).split()).strip()
    if not text or text.rstrip().endswith("?"):
        return None
    norm = text.rstrip(".!").strip()
    if not norm:
        return None
    hits = [c for c in candidates if norm == c]
    return hits[0] if len(hits) == 1 else None


def relation_key154g(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)
