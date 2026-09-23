#!/usr/bin/env python3
"""Experiment 96 -- CLOSE THE GAPS in the integrated loop (exp 90).

Gap 1: loop90's ears chain ends in plain FakeEars, which has two known
silent wrong writes (red team 81: "Mira's city is Lisbon?" saves "Lisbon?";
"...Lisbon and Mira's pet is a cat." saves one packed literal). Exp 91 built
scripts/fable_earsguard91.py GuardedEars(inner) fixing them, but loop90 does
not use it.

Gap 2: loop90's Z3 re-ran the OLD red-team probes against the OLD classes,
so it reproduced the sealed 64/3/2 and 53/1/2 tallies -- nothing checked
that the loop ITSELF resists those attacks.

This file changes exactly one thing: the ears of the loop90 agent become
GuardedEars(the loop90 ears chain). Notebook, reasoner, mouth, thinker,
sleeper, mailbox, tau-hat gate are untouched (same classes, same config).

Additive only: every other module is imported read-only and wrapped here.
Nothing outside this file is edited.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop96_agent.py --daemon --dir DIR \\
    --config artifacts/fable-loop96-20260921/loop96-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_loop90_agent as L90  # noqa: E402 (whole loop90 build, read-only)
from fable_earsguard91 import GuardedEars  # noqa: E402 (the exp-91 fix, read-only)


class Loop96Ears(GuardedEars):
    """GuardedEars around the loop90 ChainEars, with chain introspection.

    GuardedEars(inner) already implements the Ears protocol; this subclass
    only adds bind() delegation (the chain binds the notebook) and attribute
    passthrough so daemon logs still see last_stage / last_score / stage_names.
    """

    name = "guarded-chain"

    def bind(self, nb) -> None:
        inner = self.__dict__.get("inner")
        if inner is not None and hasattr(inner, "bind"):
            inner.bind(nb)

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(self.__dict__["inner"], name)


DEFAULT_CONFIG96: dict = copy.deepcopy(L90.DEFAULT_CONFIG)
DEFAULT_CONFIG96["ears"]["stand_in"] = (
    "Loop96Ears = GuardedEars91 over ChainEars(bench73 template + FakeEars "
    "templates); risky values clarify, everything else passes through")
DEFAULT_CONFIG96["ears"]["guard"] = (
    "scripts/fable_earsguard91.py GuardedEars: '?' -> clarify, packed "
    "second fact / >6 words -> split clarify; doorway guarantees untouched")
DEFAULT_CONFIG96["daemon"]["module"] = "Loop96Daemon (this file)"


def build_agent96(cfg: dict | None = None) -> L90.Loop90AgentLoop:
    """Build the loop90 agent, then wrap its ears chain in GuardedEars.

    The chain object is already bound to the loop notebook inside
    build_agent; wrapping after binding keeps the same notebook.
    """
    loop = L90.build_agent(dict(DEFAULT_CONFIG96, **(cfg or {})))
    chain = loop.ears
    loop.ears = Loop96Ears(chain)
    loop.parts90["ears"] = loop.ears
    loop.parts90["ears_chain_stages"] = list(
        getattr(chain, "stage_names", []))
    return loop


class Loop96Daemon(L90.Loop90Daemon):
    """Loop90Daemon with the loop96 (guarded-ears) agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent96(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon96(root, cfg: dict | None = None,
                 idle_seconds: float = 30.0) -> int:
    daemon = Loop96Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 96 gap-closed loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop90)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG96 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG96)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG96)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon96(args.dir, cfg=cfg,
                            idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent96(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
