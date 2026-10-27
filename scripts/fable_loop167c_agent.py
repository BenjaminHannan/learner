#!/usr/bin/env python3
"""Experiment 167c -- loop167c = loop167b + Saved-label render (mouth only).

Thin wrapper only (no existing file edited -- in particular no 167b file,
no 167 file, no agent-loop/contract file): the behaviour change lives in
scripts/fable_fix167c_label.py (Label167cMouth: delegate to the loop's own
mouth, then render the relation slot of `Saved: X's REL is V.` fact
confirmations with the answer path's own `replace("_", " ")` surface rule
for every relation key containing an underscore). This file stacks it onto
loop167b in the style of scripts/fable_loop167b_agent.py:

  loop167c = build_agent167b(...) with loop.mouth wrapped in Label167cMouth

Ears, reasoner, sleeper, notebook, matching, stored keys, and records are
literally loop167b's -- only the outgoing English sentence can change, and
only on Saved confirmations with underscore relations. Non-verb behaviour
and non-Saved replies are byte-identical by construction.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop167c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-label167c-20260922/loop167c-config.json
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

import fable_fix167c_label as L167C  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (builder base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (loop class donor, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (daemon base, read-only)
import fable_loop167b_agent as L167B  # noqa: E402 (base agent, read-only)


class Loop167cEars(L167B.Loop167bEars):
    """Loop167bEars unchanged (the 167c change is mouth-side only)."""

    name = "loop167c-label"


class Loop167cAgentLoop(L167B.Loop167bAgentLoop):
    """Loop167bAgentLoop (acts/ears unchanged); mouth wrapped by builder."""


DEFAULT_CONFIG167C: dict = copy.deepcopy(L167B.DEFAULT_CONFIG167B)
DEFAULT_CONFIG167C["ears"]["stand_in"] = (
    "Loop167cEars (loop167b ears literally; exp-167c mouth-side Saved-label "
    "render: Saved fact confirmations show the answer path's spaced relation "
    "surface for every underscore relation key; stored facts, keys, and "
    "matching byte-identical to loop167b) over loop150 chain")
DEFAULT_CONFIG167C["daemon"]["module"] = "Loop167cDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent167c(cfg: dict | None = None) -> Loop167cAgentLoop:
    """Build the loop167b shape with the 167c Saved-label mouth wrapped on."""
    cfg = dict(DEFAULT_CONFIG167C, **(cfg or {}))
    loop = _swap_loop(L150.build_agent150(cfg), Loop167cEars,
                      Loop167cAgentLoop)
    inner = loop.mouth
    if not isinstance(inner, L167C.Label167cMouth):
        loop.mouth = L167C.Label167cMouth(inner)
    return loop


class _DaemonBase167c(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 167c agent inside."""

    _builder = staticmethod(build_agent167c)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop167cDaemon(_DaemonBase167c):
    """Loop150Daemon shape with the loop167c agent inside (mailbox same)."""

    _builder = staticmethod(build_agent167c)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 167c label loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop167b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG167C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG167C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG167C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop167cDaemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent167c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
