#!/usr/bin/env python3
"""Experiment 192 -- loop192 = loop167e + correct-reply (mouth/reply only).

Thin wrapper only (no existing file edited -- in particular no 167e
file, no 167c file, no agent-loop/contract/listening file): the
behaviour change lives in scripts/fable_fix192_correctreply.py
(CorrectReply192Mixin: outermost _listening_tick post-processing that
replaces the Saved confirmation with the sealed "Updated: X's R is N
(it was O)." template on exactly those turns that appended a
superseding FACT; reply text only, events byte-identical).

Stacking (same style as scripts/fable_loop167e_agent.py):

  loop192 = build_agent150(...) with ears/loop classes swapped in and
  loop.mouth wrapped in Label167cMouth + Label167eMouth (literally
  loop167e's mouth chain), plus CorrectReply192Mixin outermost on the
  loop class.

Ears, reasoner, sleeper, notebook, matching, stored keys, and records
are literally loop167e's -- only the outgoing English sentence can
change, and only on replacement turns. Non-replacement behaviour and
non-replacement replies are byte-identical by construction.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop192_agent.py --daemon --dir DIR \\
    --config artifacts/fable-correctreply192-20260922/loop192-config.json
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
import fable_fix167e_label as L167E  # noqa: E402 (label wrapper, read-only)
import fable_fix192_correctreply as F192  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (builder base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (loop class donor, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (daemon base, read-only)
import fable_loop167e_agent as L167EB  # noqa: E402 (base agent, read-only)


class Loop192Ears(L167EB.Loop167eEars):
    """Loop167eEars unchanged (the 192 change is reply-side only)."""

    name = "loop192-correctreply"


class Loop192AgentLoop(F192.CorrectReply192Mixin,
                       L167EB.Loop167eAgentLoop):
    """Loop167eAgentLoop + outermost 192 correct-reply post-processing."""


DEFAULT_CONFIG192: dict = copy.deepcopy(L167EB.DEFAULT_CONFIG167E)
DEFAULT_CONFIG192["ears"]["stand_in"] = (
    "Loop192Ears (loop167e ears literally; exp-192 reply-side correct-"
    "reply: turns that replace a single-valued current value reply "
    "\"Updated: X's R is N (it was O).\" naming both values; stored "
    "facts, keys, events, and matching byte-identical to loop167e) "
    "over loop150 chain")
DEFAULT_CONFIG192["daemon"]["module"] = "Loop192Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent192(cfg: dict | None = None) -> Loop192AgentLoop:
    """Build the loop167e shape with the 192 correct-reply stacked on."""
    cfg = dict(DEFAULT_CONFIG192, **(cfg or {}))
    loop = _swap_loop(L150.build_agent150(cfg), Loop192Ears,
                      Loop192AgentLoop)
    inner = loop.mouth
    if not isinstance(inner, C167C.Label167cMouth):
        loop.mouth = C167C.Label167cMouth(inner)
        inner = loop.mouth
    if not isinstance(inner, L167E.Label167eMouth):
        loop.mouth = L167E.Label167eMouth(inner)
    return loop


class _DaemonBase192(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 192 agent inside."""

    _builder = staticmethod(build_agent192)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop192Daemon(_DaemonBase192):
    """Loop150Daemon shape with the loop192 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent192)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 192 correct-reply loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop167e)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG192 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG192)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG192)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop192Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent192(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
