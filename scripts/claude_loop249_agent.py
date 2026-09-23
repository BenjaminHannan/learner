#!/usr/bin/env python3
"""Experiment 249 -- first-person twins (cause D of diagnosis 243) on loop228.

loop249 = loop228 (scripts/claude_loop228_agent.py = 138i + 228 guard,
read-only) + ONE change: FirstPerson249Mixin
(scripts/claude_fix249_firstperson.py) OUTERMOST on the ears (outside
ChainOf174). Question turns about the user ("Where do I live?", "Who am I
married to?", "What's my city?", "Where do I work?" ...) are rewritten to
the "my" form Me166 already answers, only when the target relation is stored
for the user; otherwise the original turn is heard unchanged.

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

import claude_loop228_agent as L228  # noqa: E402 (base agent, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (ears class, read-only)
import fable_loop90_agent as L90  # noqa: E402 (thinker module name)
from claude_fix249_firstperson import (  # noqa: E402 (THE ONE CHANGE)
    FirstPerson249Mixin, Render249Mixin)


class Loop249Ears(FirstPerson249Mixin, L138I.Loop138iEars):
    """Loop138iEars with the 249 first-person stage outermost."""

    name = "loop249-firstperson"


DEFAULT_CONFIG249: dict = copy.deepcopy(L228.DEFAULT_CONFIG228)
DEFAULT_CONFIG249["ears"]["stand_in"] = (
    L228.DEFAULT_CONFIG228["ears"]["stand_in"]
    + "; 249 first-person twins outermost (question turns only)")
DEFAULT_CONFIG249["daemon"]["module"] = (
    "Loop249Daemon (scripts/claude_loop249_agent.py)")


def _upgrade249(loop):
    ears, hops = loop.ears, 0
    while type(ears) is not L138I.Loop138iEars:  # walk wrappers (Sleep130Ears)
        ears, hops = getattr(ears, "inner", None), hops + 1
        if ears is None or hops > 8:
            raise RuntimeError("Loop138iEars not found under loop.ears")
    ears.__class__ = Loop249Ears  # subclass, no new state
    ears.last249 = None
    base_cls = type(loop)
    loop.__class__ = type("Loop249AgentLoop", (Render249Mixin, base_cls), {})
    loop._ears249 = ears
    loop.notes.append("loop249: loop228 + FirstPerson249Mixin outermost "
                      "(question turns only; writes untouched)")
    return loop


def build_agent249(cfg: dict | None = None):
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG249, **(cfg or {}))
    return _upgrade249(L228.build_agent228(cfg))


class Loop249Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon + 228 guard (as Loop228Daemon) + the 249 ears stage."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _upgrade249(self.loop)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 249 first-person twins")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG249)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG249)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if not args.dir:
        ap.error("--daemon needs --dir")
    d = Loop249Daemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
    return d.run()


if __name__ == "__main__":
    sys.exit(main())
