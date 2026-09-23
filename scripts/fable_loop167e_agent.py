#!/usr/bin/env python3
"""Experiment 167e -- loop167e = loop167c + every-template label render.

Thin wrapper only (no existing file edited -- in particular no 167c
file, no 167b file, no agent-loop/contract/listening file): the
behaviour change lives in scripts/fable_fix167e_label.py
(Label167eMouth: delegate to the loop's own mouth, then render the
relation slot of EVERY reply template that prints a relation key --
Saved (already spaced by the inner loop167c mouth, idempotent here),
CONFLICT change-prompt, MISSING_FACT "I don't know", BROKEN_CHAIN,
Forgotten -- with the answer path's own `replace("_", " ")` surface
rule for every relation key containing an underscore). This file stacks
it onto loop167c in the style of scripts/fable_loop167c_agent.py:

  loop167e = build_agent167c(...) with loop.mouth wrapped in Label167eMouth

Ears, reasoner, sleeper, notebook, matching, stored keys, and records
are literally loop167c's -- only the outgoing English sentence can
change, and only on relation-key replies. Non-key behaviour and
non-key replies are byte-identical by construction.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop167e_agent.py --daemon --dir DIR \\
    --config artifacts/fable-label167e-20260922/loop167e-config.json
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

import fable_fix167c_label as C167C  # noqa: E402 (Saved wrapper, read-only)
import fable_fix167e_label as L167E  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (builder base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (loop class donor, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (daemon base, read-only)
import fable_loop167c_agent as L167C  # noqa: E402 (base agent, read-only)


class Loop167eEars(L167C.Loop167cEars):
    """Loop167cEars unchanged (the 167e change is mouth-side only)."""

    name = "loop167e-label"


class Loop167eAgentLoop(L167C.Loop167cAgentLoop):
    """Loop167cAgentLoop (acts/ears unchanged); mouth wrapped by builder."""


DEFAULT_CONFIG167E: dict = copy.deepcopy(L167C.DEFAULT_CONFIG167C)
DEFAULT_CONFIG167E["ears"]["stand_in"] = (
    "Loop167eEars (loop167c ears literally; exp-167e mouth-side label "
    "render: every reply template that prints a relation key (Saved, "
    "CONFLICT change-prompt, MISSING_FACT I-don't-know, BROKEN_CHAIN, "
    "Forgotten) shows the answer path's spaced relation surface for "
    "every underscore relation key; stored facts, keys, and matching "
    "byte-identical to loop167c) over loop150 chain")
DEFAULT_CONFIG167E["daemon"]["module"] = "Loop167eDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent167e(cfg: dict | None = None) -> Loop167eAgentLoop:
    """Build the loop167c shape with the 167e label mouth wrapped on."""
    cfg = dict(DEFAULT_CONFIG167E, **(cfg or {}))
    loop = _swap_loop(L150.build_agent150(cfg), Loop167eEars,
                      Loop167eAgentLoop)
    inner = loop.mouth
    if not isinstance(inner, C167C.Label167cMouth):
        loop.mouth = C167C.Label167cMouth(inner)
        inner = loop.mouth
    if not isinstance(inner, L167E.Label167eMouth):
        loop.mouth = L167E.Label167eMouth(inner)
    return loop


class _DaemonBase167e(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 167e agent inside."""

    _builder = staticmethod(build_agent167e)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop167eDaemon(_DaemonBase167e):
    """Loop150Daemon shape with the loop167e agent inside (mailbox same)."""

    _builder = staticmethod(build_agent167e)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 167e label loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop167c)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG167E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG167E)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG167E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop167eDaemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent167e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
