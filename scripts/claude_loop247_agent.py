"""Exp 247 agent: base 228 (138i + the 228 _src_of guard) + ONE change:
scripts/claude_fix247_apos.py Apos247Mixin stacked OUTERMOST on the 138i
ears (cause C1 of diagnosis 243: missing-apostrophe questions for any
stored relation and multi-word names).

How the ears class is swapped without editing 138i: build_agent138i looks
up the module global ``Loop138iEars`` when it runs, so the builder here
binds that global to Loop247Ears for the duration of the build only and
restores it in ``finally`` (base228 built in the same process is unchanged).
The 228 guard is installed at import and SrcGuardMixin228 is the first
daemon base (copied from scripts/claude_loop228_agent.py).
"""
from __future__ import annotations

import contextlib
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (base agent, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)
from claude_fix247_apos import Apos247Mixin  # noqa: E402 (THE ONE CHANGE)

install_srcguard228()

_BASE_EARS = L138I.Loop138iEars


class Loop247Ears(Apos247Mixin, _BASE_EARS):
    """Loop138iEars with the 247 question-only apostrophe repair outermost."""

    name = "loop247-apos"


@contextlib.contextmanager
def _ears247():
    prev = L138I.Loop138iEars
    L138I.Loop138iEars = Loop247Ears
    try:
        yield
    finally:
        L138I.Loop138iEars = prev


DEFAULT_CONFIG247 = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG247["ears"]["stand_in"] = (
    DEFAULT_CONFIG247["ears"]["stand_in"]
    + " + 247 apos repair outermost (questions only)")
DEFAULT_CONFIG247["daemon"]["module"] = "Loop247Daemon (this file)"


def build_agent247(cfg):
    install_srcguard228()
    with _ears247():
        loop = L138I.build_agent138i(cfg)
    loop.notes.append("loop247: 228 + Apos247Mixin outermost on the ears")
    return loop


class Loop247Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop228Daemon shape; the agent inside is built with Loop247Ears."""

    def __init__(self, *args, **kwargs):
        install_srcguard228()
        with _ears247():
            super().__init__(*args, **kwargs)


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Exp 247 loop247")
    ap.add_argument("--config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None, help="daemon directory")
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--once", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG247)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop247Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        if not args.state_dir:
            ap.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent247(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
