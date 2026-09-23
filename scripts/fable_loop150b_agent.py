#!/usr/bin/env python3
"""Experiment 150b -- loop150b = loop150 + the exp-150b clause-in-subject mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix150b_subject150b.py (Subject150BMixin: refuse with the
existing SPLIT reply any teach/correct whose subject span contains a
relation cue from the loop's own relation tables or a lower-case finite
verb/copula; capitalised title words never fire); this file stacks it onto
loop150 at both levels (ears hear + loop _act just before the write).
Values, relation keys, forget/ask/clarify paths untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop150b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-subject150b-20260922/loop150b-config.json
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

import fable_fix150b_subject150b as S150b  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop150bEars(S150b.Subject150BMixin, L150.Loop150Ears):
    """Loop150Ears + 150b clause-in-subject guard on outgoing teach/correct."""

    name = "loop150b-clausesubject"


class Loop150bAgentLoop(S150b.Subject150BMixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop + 150b clause-in-subject guard before the write."""


DEFAULT_CONFIG150B: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG150B["ears"]["stand_in"] = (
    "Loop150bEars (loop150 + exp-150b clause-in-subject guard: refuse with "
    "existing SPLIT reply any teach/correct whose subject span holds a "
    "relation cue from the loop tables or a lower-case finite verb; "
    "capitalised titles exempt) over loop150 chain")
DEFAULT_CONFIG150B["daemon"]["module"] = "Loop150bDaemon (this file)"


def build_agent150b(cfg: dict | None = None) -> Loop150bAgentLoop:
    """Build the loop150 agent shape with the 150b guard mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG150B, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop150bEars
    loop.ears.name = Loop150bEars.name
    loop.__class__ = Loop150bAgentLoop
    return loop


class Loop150bDaemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop150b agent inside (mailbox same)."""

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
        self.loop = build_agent150b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon150b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop150bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 150b clause-subject loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG150B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG150B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG150B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon150b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent150b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
