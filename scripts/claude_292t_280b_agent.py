#!/usr/bin/env python3
"""Exp 292t single-layer arm: 292 + 280 ability table + 280b general layer.

New file only. Reuses the shared 292t builders in
scripts/claude_loop292t_agent.py (piece files imported read-only there);
this file only selects the 280b arm so the sealed runner can load one arm
per process (the 268 guard rebinds a module global; never mix arms in one
process).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_fix252b_screen as F252B  # noqa: E402 (read-only)
import claude_fix268_nhopdir as G268  # noqa: E402 (read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only, _Swap)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only)
import claude_loop292_agent as L292  # noqa: E402 (read-only)
import claude_loop292t_agent as T292  # noqa: E402 (shared builders)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _with_292_280b(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", L292.Loop292Ears),
                      (L138J, "Loop138jAgentLoop", L292.Loop292AgentLoop),
                      (L138J, "build_agent138j", T292._build292_280b)]):
        return fn(*args, **kwargs)


DEFAULT_CONFIG292T280B: dict = copy.deepcopy(T292.DEFAULT_CONFIG292T)
DEFAULT_CONFIG292T280B["daemon"]["module"] = (
    "Loop292t280bDaemon (scripts/claude_292t_280b_agent.py) over "
    "Loop138kDaemon with the 292 classes + 280/280b layers")
DEFAULT_CONFIG292T280B["exp292t280b"] = {
    "base": "loop292 (scripts/claude_loop292_agent.py)",
    "added": ["280 ability table + 280b general-question layer "
              "(outermost, instance, in order)"],
    "instance": ["turn280b(turn280(turn291(turn260(turn224c(turn224("
                 "class turn))))))"],
}


def _check(loop):
    T292._check_292_base(loop, "292t280b")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn280b":
        raise RuntimeError("292t280b: turn280b not outermost")
    if getattr(loop.turn280b_inner, "__name__", "") != "turn280":
        raise RuntimeError("292t280b: 280 not under turn280b")
    if getattr(loop.turn280_inner, "__name__", "") != "turn291":
        raise RuntimeError("292t280b: 291 not under turn280")
    loop.notes.append(L292.NOTE292)
    loop.notes.append("loop292t280b: 292 + 280/280b layers "
                      "(turn280b outermost)")


def build_agent292t280b(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG292T280B, **(cfg or {}))
    loop = _with_292_280b(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes292t280bMixin:
    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        F252B.install_screen252b()
        _with_292_280b(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop292t280bDaemon(SrcGuardMixin228, Classes292t280bMixin,
                         L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with the 292+280/280b build mixin."""


assert [c.__name__ for c in Loop292t280bDaemon.__mro__][:5] == [
    "Loop292t280bDaemon", "SrcGuardMixin228", "Classes292t280bMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 292t arm 292+280/280b")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG292T280B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG292T280B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop292t280bDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent292t280b(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
