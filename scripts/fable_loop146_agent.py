#!/usr/bin/env python3
"""Experiment 146 -- loop146 = loop129b + the exp-146 refused-correction
doubt mixin (ONE CHANGE).

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_doubt146_store.py (DoubtStore146 + Doubt146Mixin); this file
stacks it onto loop129b at both levels (ears hear + loop _act/_ask) and
attaches one shared persisted DoubtStore146 per daemon dir.

Doubt rule: a refused teach (clarify reply) naming a notebook-known subject
with an existing-parser relation cue records a doubt on (subject,
relation); questions whose answer walk uses it abstain ("could not store,
say it again as one fact"); a later successful teach clears it. The store
is notebook-side (doubts146.json), never weights, never edits old facts.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop146_agent.py --daemon --dir DIR \\
    --config artifacts/fable-doubt146-20260922/loop146-config.json
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

import fable_doubt146_store as D146  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop146Ears(D146.Doubt146Mixin, L129b.Loop129bEars):
    """Loop129bEars + refused-correction doubt (record + ask screening)."""

    name = "loop146-doubt"


class Loop146AgentLoop(D146.Doubt146Mixin, L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop + doubt (act-level record/clear, ask backup)."""


DEFAULT_CONFIG146: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG146["ears"]["stand_in"] = (
    "Loop146Ears (loop129b + exp-146 refused-correction doubt: refused "
    "known-subject teach records (subject, relation); doubted answer walks "
    "abstain; later successful teach clears; doubts146.json notebook-side) "
    "over loop129b chain")
DEFAULT_CONFIG146["daemon"]["module"] = "Loop146Daemon (this file)"


def build_agent146(cfg: dict | None = None) -> Loop146AgentLoop:
    """Build the loop129b agent shape with the doubt mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG146, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop146Ears
    loop.ears.name = Loop146Ears.name
    loop.__class__ = Loop146AgentLoop
    state_dir = Path(cfg.get("state_dir", "."))
    store = D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    loop.ears.doubt_store146 = store
    return loop


class Loop146Daemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop146 agent inside (mailbox same)."""

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
        self.loop = build_agent146(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon146(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop146Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 146 doubt loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG146 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG146)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG146)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon146(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent146(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
