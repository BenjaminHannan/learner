#!/usr/bin/env python3
"""Experiment 222 -- gate the 215 indefinite rewrite on the relation table.

THE ONE CHANGE (on loop215, which wraps loop138i read-only): the
indefinite teach form "X is a/an R of Y." is rewritten to "Y's R is X."
ONLY when R (as a canonical name or alias, case-insensitive) is listed in
artifacts/claude-relationtable-20260922/relation_table_v1.json with
value_kind == "person" AND cardinality == "multi". For every other R the
turn goes to the unchanged base path exactly as on 138i.

"The" teaches and the question rewrite stay exactly as in 215.

This module only loads the table (read-only) and exposes the gate; the
ears subclass lives in scripts/fable_loop222_agent.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop215_agent as L215  # noqa: E402 (read-only)

TABLE_PATH = (SCRIPTS.parent / "artifacts" / "claude-relationtable-20260922"
              / "relation_table_v1.json")


def _load_allowed222() -> frozenset:
    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    allowed: set[str] = set()
    for rel in table.get("relations", []):
        if (rel.get("value_kind") == "person"
                and rel.get("cardinality") == "multi"):
            allowed.add(str(rel["name"]).strip().lower())
            for alias in rel.get("aliases", []):
                allowed.add(str(alias).strip().lower())
    return frozenset(allowed)


ALLOWED222: frozenset = _load_allowed222()


def rel_allowed222(rel: str) -> bool:
    """True iff the R surface form is a person+multi table entry/alias."""
    return " ".join(str(rel).split()).lower() in ALLOWED222


def must_take_base_path222(turn: str, nb=None) -> bool:
    """True iff 215 WOULD rewrite this teach but 222 must not.

    I.e. the 215 teach rewrite fires, the article is indefinite (a/an),
    and R is not a person+multi table entry. Everything else returns
    False (caller runs the exact 215 path).
    """
    try:
        cand = L215.rewrite_teach215(turn, nb)
    except Exception:
        return False
    if cand is None:
        return False
    try:
        text = " ".join(str(turn).split())
        work = text.replace("\u2019", "'")
        prefix_match = L215._CORRECTION_PREFIX_RE.match(work)
        if prefix_match is not None:
            work = prefix_match.group(2).strip()
        stem = work.strip()
        if not stem.endswith("."):
            return False
        core = stem[:-1].strip()
        match = L215._TEACH_RE.match(core)
        if match is None:
            return False
        article = match.group("art").lower()
        if article not in ("a", "an"):
            return False
        mid = " ".join(match.group("mid").split())
        split = L215.split_middle215(mid, nb)
        if split is None:
            return False
        rel, _who = split
        return not rel_allowed222(rel)
    except Exception:
        return False
