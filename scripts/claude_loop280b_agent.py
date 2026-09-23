#!/usr/bin/env python3
"""Exp 280b agent: 280 + one outermost general-question layer.

Everything is 280 (scripts/claude_loop280_agent.py, read-only) except
scripts/claude_fix280b_general.py install_general280b, which wraps the
whole built turn outside 280's turn280 (a caught turn gets exactly the
sealed CAN280 text with 0 writes; anything else passes through
byte-identical).

It is installed inside the build (like 280), so the daemon's boot
reconcile already runs through it. The daemon keeps SrcGuardMixin228
first, exactly where 280 has it.
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

import claude_fix280b_general as F280B  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop280_agent as L280  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build280b(cfg=None):
    loop = L280._build280(cfg)        # 280 build (260 + 280)
    F280B.install_general280b(loop)   # outermost
    return loop


def _with_280b(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build280b)]):
        return fn(*args, **kwargs)


NOTE280B = ("loop280b: loop280 + 280b general ability-question rule "
            "(outermost turn layer serving the sealed CAN280 text)")


def _base_config280b() -> dict:
    cfg = copy.deepcopy(L280.DEFAULT_CONFIG280)
    cfg["daemon"]["module"] = (
        "Loop280bDaemon (scripts/claude_loop280b_agent.py) over "
        "Loop138kDaemon with the 138m classes")
    cfg["self"]["rule280b"] = (
        "280b (scripts/claude_fix280b_general.py): question-shaped turns "
        "addressing the assistant with an ability cue and no named "
        "entity/relation get the sealed CAN280 text (0 writes); "
        "'Can you <specific>?' keeps 280's reply; everything else "
        "byte-identical to 280; never writes")
    cfg["exp280b"] = {
        "base": "loop280 (scripts/claude_loop280_agent.py)",
        "added": ["280b general ability-question rule (outermost, instance)"],
        "instance": ["turn280b(turn280(turn260(turn224c(turn224(class turn))))"],
    }
    return cfg


DEFAULT_CONFIG280B: dict = _base_config280b()


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("280b: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("280b: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("280b: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn280b":
        raise RuntimeError("280b: turn280b not installed")
    if getattr(loop.turn280b_inner, "__name__", "") != "turn280":
        raise RuntimeError("280b: 280 not under turn280b")
    if getattr(loop.turn280_inner, "__name__", "") != "turn260":
        raise RuntimeError("280b: 260 not under turn280")
    loop.notes.append(L280.NOTE280)
    loop.notes.append(NOTE280B)


def build_agent280b(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG280B, **(cfg or {}))
    loop = _with_280b(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes280bMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    280b-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_280b(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop280bDaemon(SrcGuardMixin228, Classes280bMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 280b
    build mixin ahead of the 220 mixin, exactly as 280 stacks its own."""


assert [c.__name__ for c in Loop280bDaemon.__mro__][:5] == [
    "Loop280bDaemon", "SrcGuardMixin228", "Classes280bMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 280b (280 + generals)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG280B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG280B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop280bDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent280b(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
