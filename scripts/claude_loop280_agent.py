#!/usr/bin/env python3
"""Exp 280 agent: 260 + one outermost honesty layer for ability questions.

Everything is 260 (scripts/claude_loop260_agent.py, read-only) except
scripts/claude_fix280_capab.py install_capab280, which wraps the whole
built turn outside 260's turn260 (so a substituted reply is exactly the
sealed CAN280 text) and swaps C24-shaped head replies for it.

It is installed inside the build (like 260), so the daemon's boot
reconcile already runs through it. The daemon keeps SrcGuardMixin228
first, exactly where 260 has it.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_fix280_capab as F280  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop260_agent as L260  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build280(cfg=None):
    loop = L260._build260(cfg)        # 260 build (138m + 224/224c + 260)
    F280.install_capab280(loop)       # outermost
    return loop


def _with_280(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build280)]):
        return fn(*args, **kwargs)


NOTE280 = ("loop280: loop260 + 280 honest ability list (outermost turn "
           "layer rendering self-description replies from a sealed table)")

DEFAULT_CONFIG280: dict = copy.deepcopy(L260.DEFAULT_CONFIG260)
DEFAULT_CONFIG280["daemon"]["module"] = (
    "Loop280Daemon (scripts/claude_loop280_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG280["self"] = dict(DEFAULT_CONFIG280.get("self", {}))
DEFAULT_CONFIG280["self"]["rule280"] = (
    "280 (scripts/claude_fix280_capab.py): general ability questions and "
    "any C24-shaped head reply are answered with the sealed CAN280 text "
    "(6 table-backed abilities, 3 dropped); everything else byte-identical "
    "to 260; never writes")
DEFAULT_CONFIG280["exp280"] = {
    "base": "loop260 (scripts/claude_loop260_agent.py)",
    "added": ["280 honest ability list (outermost, instance)"],
    "instance": ["turn280(turn260(turn224c(turn224(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("280: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("280: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("280: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn280":
        raise RuntimeError("280: turn280 not installed")
    if getattr(loop.turn280_inner, "__name__", "") != "turn260":
        raise RuntimeError("280: 260 not under turn280")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("280: 224c not under turn260")
    loop.notes.append(L260.NOTE260)
    loop.notes.append(NOTE280)


def build_agent280(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG280, **(cfg or {}))
    loop = _with_280(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes280Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    280-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_280(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop280Daemon(SrcGuardMixin228, Classes280Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 280
    build mixin ahead of the 220 mixin, exactly as 260 stacks its own."""


assert [c.__name__ for c in Loop280Daemon.__mro__][:5] == [
    "Loop280Daemon", "SrcGuardMixin228", "Classes280Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 280 (260 + honest abilities)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG280)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG280)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop280Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent280(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
