#!/usr/bin/env python3
"""Exp 218 C2 plant: scratch-only wrapper around loop138i.

Rewrites "capital" -> "capitol" and "Capital" -> "Capitol" in the INPUT
text before loop138i's turn (director plant). Notebook writes are
untouched by this file; the misspelt input makes the agent fail to save
the fact on the capital-shaped cases.

Predicted moved cases (written into PASSMARKS.md BEFORE the registered
run): exactly 6 rt136 moves -- C002 C105 C118 = "lost OK"
(OK with the save -> MISSED with nothing saved), C075 C096 C121 =
"reply-only move" (verdict and stored triples identical, only the reply
text changed); sessions152 0 moves; GATE NOT clean (lost OK 3).

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

DEFAULT_CONFIG218: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG218["daemon"]["module"] = "Loop218Daemon (this file)"
DEFAULT_CONFIG218["self"] = dict(DEFAULT_CONFIG218.get("self", {}))


def plant_text(text: str) -> str:
    return str(text).replace("capital", "capitol").replace("Capital",
                                                            "Capitol")


def _wrap_turn(loop):
    orig_turn = loop.turn

    def turn(text: str):
        return orig_turn(plant_text(text))

    loop.turn = turn  # instance attr: NOT rebound, called as turn(text)
    return loop


def build_agent218(cfg: dict | None = None):
    loop = L138I.build_agent138i(cfg)
    return _wrap_turn(loop)


class Loop218Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon with the capitol-plant loop inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 3600.0, **kw) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds, **kw)
        _wrap_turn(self.loop)
