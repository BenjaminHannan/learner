#!/usr/bin/env python3
"""Exp 270 agent: 263 + one outermost text-normaliser layer (one change).

Everything is 263 (scripts/claude_loop263_agent.py, read-only) except the
turn270 wrapper below, which runs the raw user text through
scripts/claude_type270_normalise.py first (THE ONE CHANGE) and hands the
fixed text to the unchanged 263 head. Clean turns pass through
byte-identical, so their replies are 263's replies exactly.

Notebook names: before normalising, subjects and values already stored in
the loop's notebook are collected (lowercase -> stored capitalisation) so
a stored "Will" beats the modal "will".
"""
from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop263_agent as L263  # noqa: E402 (base, read-only)
import claude_type270_normalise as N270  # noqa: E402 (THE ONE CHANGE)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def _notebook_names270(loop) -> dict:
    try:
        triples = L90.notebook_triples(loop.nb)
    except Exception:  # noqa: BLE001
        return {}
    return N270.names_from_triples270(triples)


def install_normaliser270(loop):
    """Install the 270 layer on a built 263 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn263(turn260(...))
    loop.turn270_inner = inner_turn
    loop.type270_log = []

    def turn270(text: str) -> list[str]:
        t = str(text)
        t0 = time.perf_counter()
        fixed = N270.normalise270(t, _notebook_names270(loop))
        dt = (time.perf_counter() - t0) * 1000.0
        if fixed != t:
            loop.type270_log.append({"from": t, "to": fixed,
                                     "norm_ms": round(dt, 4)})
        else:
            loop.type270_log.append({"from": t, "to": None,
                                     "norm_ms": round(dt, 4)})
        return inner_turn(fixed)

    turn270.__name__ = "turn270"
    loop.turn = turn270
    return loop


def _build270(cfg=None):
    loop = L263._build263(cfg)        # 263 build (260 + comma guard)
    install_normaliser270(loop)       # outermost
    return loop


def _with_270(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build270)]):
        return fn(*args, **kwargs)


NOTE270 = ("loop270: loop263 + text normaliser (restore name capitals and "
           "possessive apostrophes on all-lowercase turns, or no-apostrophe "
           "turns with an Xs-relation pattern; check-tails suppressed; "
           "clean turns pass through byte-identical)")

DEFAULT_CONFIG270: dict = copy.deepcopy(L263.DEFAULT_CONFIG263)
DEFAULT_CONFIG270["daemon"]["module"] = (
    "Loop270Daemon (scripts/claude_type270_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG270["self"] = dict(DEFAULT_CONFIG270.get("self", {}))
DEFAULT_CONFIG270["self"]["rule270"] = (
    "270 (scripts/claude_type270_normalise.py): only when a turn has no "
    "capital letters at all (or no apostrophes with an Xs-relation "
    "pattern), restore name capitals (common-English words stay lowercase; "
    "notebook names win) and possessive apostrophes, then hand the fixed "
    "text to the unchanged 263 ear; trailing check-tails pass through; "
    "clean turns pass through byte-identical")
DEFAULT_CONFIG270["exp270"] = {
    "base": "loop263 (scripts/claude_loop263_agent.py)",
    "added": ["270 text normaliser (outermost, instance)"],
    "instance": ["turn270(turn263(turn260(turn224c(turn224(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("270: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("270: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("270: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn270":
        raise RuntimeError("270: turn270 not installed")
    if getattr(loop.turn270_inner, "__name__", "") != "turn263":
        raise RuntimeError("270: turn263 not under turn270")
    loop.notes.append(L138M.NOTE138M)
    loop.notes.append(L263.NOTE263)
    loop.notes.append(NOTE270)


def build_agent270(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG270, **(cfg or {}))
    loop = _with_270(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes270Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    270-installing build swapped in for the build."""


class Loop270Daemon(SrcGuardMixin228, Classes270Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases (228 guard > 220 restart index >
    Loop138jDaemon) with SrcGuardMixin228 first and the 270 build mixin
    (263 + the normaliser) ahead of the 220 mixin, as 263's
    Classes263Mixin sits ahead of Loop138kDaemon."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_270(super().__init__, *args, **kwargs)
        _check(self.loop)


assert [c.__name__ for c in Loop270Daemon.__mro__][:5] == [
    "Loop270Daemon", "SrcGuardMixin228", "Classes270Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 270 (263 + normaliser)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG270)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG270)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop270Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent270(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
