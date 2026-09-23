#!/usr/bin/env python3
"""Experiment 154e -- allow-list delta: language becomes multi-valued.

Base: loop154c (scripts/fable_loop154c_agent.py +
scripts/fable_fix154c_allowlist.py), read-only. No 154c/154b/138b file
is edited; everything new lives here.

THE ONE CHANGE versus loop154c: the add-a-second-value path fires for
MULTI_VALUED_154C plus exactly one more key: "language". Citizenship
and every other deny-listed relation stay single-valued, unchanged
(loop138b change-prompt path, byte-identical).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation map, read-only)
import fable_fix154c_allowlist as M154C  # noqa: E402 (base table, read-only)

# Exactly one delta vs 154c: language joins the allow-list.
MULTI_VALUED_154E = frozenset(set(M154C.MULTI_VALUED_154C) | {"language"})


def relation_key154e(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    return A.FakeEars._relation(surface)


def is_multi154e(key: str) -> bool:
    """True iff the relation key takes the multi add-a-second-value path."""
    return key in MULTI_VALUED_154E
