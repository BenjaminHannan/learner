#!/usr/bin/env python3
"""slp-363x: school night with a wider self-check (Fix-sleep thread, 2026-09-25). Follows the slp-363w registered
FAIL: every honest night passed its self-check, yet over a day the reasoner drifted (seed 1: 20 fewer right of 600 on
a fixed panel), answering more and getting more wrong.

ONE CHANGE (to the keep rule only; practice, training and everything else are slp-363w's): besides 363w's check
against the night before, a night is kept only if the trained copy is not worse than the reasoner was BEFORE THE
FIRST NIGHT, on two sets:
  U  tonight's self-check set from the user's taught rows (the start checkpoint is scored on it too), and
  G  a fixed set of GENERAL items from another invented world (claude_slp363_night.world_items, world GENERAL363X),
     built once, never trained on, and never the test panel.
"Not worse" uses 363w's three counts and tolerance (right -TOL, wrong +TOL, answers without a fact +TOL, of the set).
"""
from __future__ import annotations

import json
from pathlib import Path

import claude_slp363_night as N
import claude_slp363w_night as W

GENERAL363X = 9363
N_GENERAL = 400


def _worse(before: dict, after: dict, tol: float) -> list[str]:
    s = tol * before["n"]
    why = []
    if after["checked_right"] < before["checked_right"] - s:
        why.append("fewer right")
    if after["checked_wrong"] > before["checked_wrong"] + s:
        why.append("more wrong")
    if after["raw_answered_without_fact"] > before["raw_answered_without_fact"] + s:
        why.append("more answers without a fact")
    return why


class SchoolNightX(W.SchoolNight):
    def __init__(self, *a, general_world=GENERAL363X, n_general=N_GENERAL, **kw):
        super().__init__(*a, **kw)
        self.start = self.current
        self.general = self.work / "general.jsonl"
        items, _ = N.world_items(general_world, general_world, n_general)
        with open(self.general, "w", encoding="utf-8") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
        self.general_start = self._score(self.start, self.general, self.work / "general-start.json")

    def night(self, loop) -> dict:
        prev = self.current
        rec = super().night(loop)
        if not rec.get("ran") or not rec.get("kept"):
            return rec
        d = self.work / f"night-{rec['night']:03d}"
        try:
            u0 = self._score(self.start, d / "check.jsonl", d / "check-start.json")
            g1 = self._score(self.current, self.general, d / "general-new.json")
            why = [f"U vs start: {w}" for w in _worse(u0, rec["after"], self.tol)] + \
                  [f"G vs start: {w}" for w in _worse(self.general_start, g1, self.tol)]
        except Exception as exc:  # noqa: BLE001  (a failed check keeps the old checkpoint)
            why = [f"check failed: {type(exc).__name__}: {exc}"[:200]]
            u0 = g1 = None
        rec.update({"start_on_check": u0, "general_start": self.general_start, "general_new": g1})
        if why:
            aside = self.work / "aside" / f"night-{rec['night']:03d}"
            aside.parent.mkdir(parents=True, exist_ok=True)
            Path(self.current).parent.replace(aside)
            self.current = prev
            rec.update({"kept": False, "why": why, "aside": str(aside), "current": str(self.current)})
        (d / "record.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return rec


def install_school363x(loop, school: SchoolNightX) -> SchoolNightX:
    return W.install_school363w(loop, school)
