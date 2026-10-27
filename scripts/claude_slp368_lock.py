#!/usr/bin/env python3
"""slp-368: SLEEP WRITE LOCK (Fix-sleep thread, 2026-09-25; follows the slp-364 FAIL, P364.4).

slp-364 found that code running inside a sleep can still write rows labelled "taught" to the main notebook by
calling loop.nb.assert_fact directly (actor "listening" is only a label). slp-360 only moves guessed sources
(sleep-derived, inferred) to the scrap layer, and slp-361 never copies the main notebook back, so such rows stay.

ONE CHANGE: install_lock368(loop) wraps loop.sleeper.sleep. While it runs, every main-notebook object reachable
from the loop (loop.nb and its inner .nb) refuses to append to its log: Notebook._append (the single place a
notebook writes its log, fable_notebook_contract.py) raises Locked368 before any byte is written. The sleeper
call is aborted and reports {"accepted": False, "attempted": False, "reason": "slp-368: ..."}; with slp-361/364
installed the night is then undone. Writes to the scrap layer (slp-360) are separate files and are not locked.
Outside a sleep nothing changes. A second check compares the main log's bytes before and after the sleeper call
(catches a writer that opened its own notebook object on the same folder); a change is reported, not repaired.
"""
from __future__ import annotations

import functools
import hashlib
from pathlib import Path


class Locked368(RuntimeError):
    """A main-notebook write was attempted during sleep."""


def _targets(loop) -> list:
    out, seen = [], set()
    for obj in (loop.nb, getattr(loop.nb, "nb", None)):
        if obj is not None and hasattr(obj, "_append") and id(obj) not in seen:
            out.append(obj)
            seen.add(id(obj))
    return out


def _log_path(loop):
    for obj in _targets(loop):
        p = getattr(obj, "path", None)
        if p is not None:
            return Path(p)
    return None


def _digest(path) -> str | None:
    if path is None or not Path(path).exists():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_lock368(loop) -> dict:
    st = {"locked": False, "blocked": 0, "nights": 0, "aborted": 0, "log_changed": 0, "last": None}
    loop.lock368 = st
    for obj in _targets(loop):
        inner_append = obj._append

        def _append368(event, _inner=inner_append):
            if st["locked"]:
                st["blocked"] += 1
                raise Locked368(f"slp-368: main notebook write refused during sleep ({event.get('kind')})")
            return _inner(event)

        obj._append = _append368
    inner_sleep = loop.sleeper.sleep

    @functools.wraps(inner_sleep)
    def sleep368(experience, notebook):
        path = _log_path(loop)
        before = _digest(path)
        blocked0 = st["blocked"]
        st["nights"] += 1
        st["locked"] = True
        err = None
        try:
            out = inner_sleep(experience, notebook)
        except Locked368 as exc:
            err = str(exc)
            out = None
        finally:
            st["locked"] = False
        changed = _digest(path) != before
        tries = st["blocked"] - blocked0
        st["last"] = {"blocked": tries, "log_changed": changed, "aborted": err is not None}
        if changed:
            st["log_changed"] += 1
        if err is not None or tries or changed:
            st["aborted"] += int(err is not None)
            why = err or (f"slp-368: {tries} main notebook write(s) refused during sleep" if tries
                          else "slp-368: main notebook log changed during sleep")
            base = dict(out) if isinstance(out, dict) else {}
            base.update({"accepted": False, "reason": why, "locked368": dict(st["last"])})
            base.setdefault("recipe", {"attempted": False, "reason": why})
            if isinstance(base.get("recipe"), dict) and err is not None:
                base["recipe"] = dict(base["recipe"], attempted=False, reason=why)
            return base
        return out

    loop.sleeper.sleep = sleep368
    loop.notes.append("slp-368: the main notebook refuses every write while the sleeper runs")
    return st
