#!/usr/bin/env python3
"""Exp 263 agent: 260 + one outermost comma write-guard layer (one change).

Everything is 260 (scripts/claude_loop260_agent.py, read-only) except
scripts/claude_fix263_comma.py install_comma263, which wraps the whole
built turn outside turn260 (so a retry runs through the entire head
exactly as if typed alone) and blocks any teach/correct whose subject
contains a comma at the inner ears and at _act.

It is installed inside the build, so the daemon's boot reconcile already
runs through it. The daemon keeps SrcGuardMixin228 first.
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

import claude_fix263_comma as F263  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop260_agent as L260  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build263(cfg=None):
    loop = L260._build260(cfg)            # 260 build (138m + openers)
    F263.install_comma263(loop)           # outermost
    return loop


def _with_263(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build263)]):
        return fn(*args, **kwargs)


NOTE263 = ("loop263: loop260 + comma write guard (no stored subject may "
           "contain a comma; retry after the last comma of the leading "
           "segment, else the head's save-failure reply with 0 writes)")

DEFAULT_CONFIG263: dict = copy.deepcopy(L260.DEFAULT_CONFIG260)
DEFAULT_CONFIG263["daemon"]["module"] = (
    "Loop263Daemon (scripts/claude_loop263_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG263["self"] = dict(DEFAULT_CONFIG263.get("self", {}))
DEFAULT_CONFIG263["self"]["rule263"] = (
    "263 (scripts/claude_fix263_comma.py): no teach/correct may store a "
    "subject containing a comma (blocked at the inner ears and at _act); "
    "a blocked teach retries once on the text after the last comma of the "
    "leading segment through the same head, and is otherwise answered with "
    "the head's save-failure reply with 0 writes; values keep commas; "
    "questions never write")
DEFAULT_CONFIG263["exp263"] = {
    "base": "loop260 (scripts/claude_loop260_agent.py)",
    "added": ["263 comma write guard (outermost, instance)"],
    "instance": ["turn263(turn260(turn224c(turn224(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("263: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("263: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("263: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn263":
        raise RuntimeError("263: turn263 not installed")
    if getattr(loop.turn263_inner, "__name__", "") != "turn260":
        raise RuntimeError("263: turn260 not under turn263")
    loop.notes.append(L138M.NOTE138M)
    loop.notes.append(L260.NOTE260)
    loop.notes.append(NOTE263)


def build_agent263(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG263, **(cfg or {}))
    loop = _with_263(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes263Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    263-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_263(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop263Daemon(SrcGuardMixin228, Classes263Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases (228 guard > 220 restart index >
    Loop138jDaemon) with SrcGuardMixin228 first and the 263 build mixin
    (260 + the comma guard) ahead of the 220 mixin, as 260's
    Classes260Mixin sits ahead of Loop138kDaemon."""


assert [c.__name__ for c in Loop263Daemon.__mro__][:5] == [
    "Loop263Daemon", "SrcGuardMixin228", "Classes263Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 263 (260 + comma guard)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG263)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG263)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop263Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent263(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
