#!/usr/bin/env python3
"""Experiment 250 agent: base 228 (138i + 228 guard) + ONE change.

The change (scripts/claude_fix250_verbsubj.py): VerbSubj250Mixin takes
Verb167Mixin's slot in the 138i ears stack (same position, same neighbours),
so verb questions with a lowercase or multi-word subject that resolves to
exactly one stored entity get their possessive twin. Everything else is
byte-identical 228.

The 228 _src_of guard is installed at import and by the daemon mixin
(SrcGuardMixin228 first in the daemon bases).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import claude_loop228_agent as L228  # noqa: E402 (base, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_fix167_verb as V167  # noqa: E402 (read-only)
from claude_fix250_verbsubj import VerbSubj250Mixin  # noqa: E402 (THE ONE CHANGE)


def _bases250():
    bases = list(L138I.Loop138iEars.__bases__)
    idx = bases.index(V167.Verb167Mixin)
    bases[idx] = VerbSubj250Mixin
    return tuple(bases)


Loop250Ears = type("Loop250Ears", _bases250(), {
    "__doc__": "Loop138iEars with Verb167Mixin's slot taken by "
               "VerbSubj250Mixin (a Verb167Mixin subclass).",
    "__module__": __name__,
    "name": "loop250-verbsubj",
})

DEFAULT_CONFIG250 = copy.deepcopy(L228.DEFAULT_CONFIG228)
DEFAULT_CONFIG250["ears"]["stand_in"] = (
    L228.DEFAULT_CONFIG228["ears"]["stand_in"]
    + "; 250 verb-question subjects: case-insensitive, multi-word, "
      "notebook-resolved (Verb167 slot)")
DEFAULT_CONFIG250["daemon"]["module"] = (
    "Loop250Daemon (scripts/claude_loop250_agent.py)")


def _upgrade250(loop):
    ears, hops = loop.ears, 0
    while type(ears) is not L138I.Loop138iEars:  # walk Sleep130Ears wrapper
        if type(ears) is Loop250Ears:
            return loop
        ears, hops = getattr(ears, "inner", None), hops + 1
        if ears is None or hops > 8:
            raise RuntimeError("Loop138iEars not found under loop.ears")
    ears.__class__ = Loop250Ears  # same state, one mixin swapped
    loop.notes.append("loop250: 228 + VerbSubj250Mixin in Verb167's slot "
                      "(question turns only; writes untouched)")
    return loop


def build_agent250(cfg: dict | None = None):
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG250, **(cfg or {}))
    return _upgrade250(L228.build_agent228(cfg))


class Loop250Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon with the 228 guard and the 250 ears swap."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _upgrade250(self.loop)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 250 verb-question subjects")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG250)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG250)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if not args.dir:
        ap.error("--daemon needs --dir")
    d = Loop250Daemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
    return d.run()


if __name__ == "__main__":
    sys.exit(main())
