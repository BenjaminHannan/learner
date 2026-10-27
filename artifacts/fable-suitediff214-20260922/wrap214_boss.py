#!/usr/bin/env python3
"""Exp 214 V3 positive control: scratch-only wrapper around loop138i.

Appends " (test)" to the LAST reply line of every turn whose input text
contains the word "boss" (case-insensitive). Notebook writes are untouched,
so stored triples and verdicts that do not extract from reply text stay
identical; only reply text moves.

Predicted moved cases (pure-function count over suite inputs, written into
PASSMARKS.md BEFORE the registered run): exactly the 13 redteam136 cases
whose input text contains "boss":
  C077 C078 C081 C082 C089 C095 C098 C099 C122 C129 C133 C136 C144
(redteam143 inputs contain no "boss": 0 moves; sessions152 turns contain
no "boss": 0 moves.)

Additive only: this file wraps scripts/fable_loop138i_agent.py read-only.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SCRIPTS = _HERE.parent.parent.parent / "scripts"
if not _SCRIPTS.is_dir():  # fallback: fixed worktree layout
    _SCRIPTS = Path("/Users/ben-hannan/Desktop/projects/beautiful-model"
                    "/.claude/worktrees/card-experiment-handoff-7c5b27"
                    "/scripts")
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (wrapped, read-only)

DEFAULT_CONFIG214: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG214["daemon"]["module"] = "Loop214Daemon (this file)"
DEFAULT_CONFIG214["self"] = dict(DEFAULT_CONFIG214.get("self", {}))

BOSS_TAG = " (test)"


def _wrap_turn(loop):
    orig_turn = loop.turn

    def turn(text: str):
        said = orig_turn(text)
        if "boss" in str(text).lower() and said:
            said = list(said)
            said[-1] = said[-1] + BOSS_TAG
        return said

    loop.turn = turn  # instance attr: NOT rebound, called as turn(text)
    return loop


def build_agent214(cfg: dict | None = None):
    loop = L138I.build_agent138i(cfg)
    return _wrap_turn(loop)


class Loop214Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon with the boss-tagged loop inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 3600.0, **kw) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds, **kw)
        _wrap_turn(self.loop)
