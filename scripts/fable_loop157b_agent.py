#!/usr/bin/env python3
"""Experiment 157b -- loop157b = loop157 + the exp-157b capitalised-filler mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix157b_capfiller.py (CapFiller157bMixin: strip up to TWO
leading fillers from the same closed list as 157, any capitalisation,
each optionally comma-followed, only when the remainder parses as a
complete teach or question by the unchanged loop157 chain); this file
stacks it onto loop157 at ears level in the style of
scripts/fable_loop157_agent.py. Values, relation keys, forget/ask/
clarify paths, correction markers, and titles are untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop157b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-filler157b-20260922/loop157b-config.json
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

import fable_fix157b_capfiller as F157B  # noqa: E402 (this experiment's mixin)
import fable_loop157_agent as L157  # noqa: E402 (wrapped base, read-only)


class Loop157bEars(F157B.CapFiller157bMixin, L157.Loop157Ears):
    """Loop157Ears + exp-157b capitalised/stacked filler strip."""

    name = "loop157b-capfiller"


class Loop157bAgentLoop(L157.Loop157AgentLoop):
    """Loop157AgentLoop unchanged (filler strip lives at ears level)."""


DEFAULT_CONFIG157B: dict = copy.deepcopy(L157.DEFAULT_CONFIG157)
DEFAULT_CONFIG157B["ears"]["stand_in"] = (
    "Loop157bEars (loop157 + exp-157b capitalised/stacked filler strip: "
    "up to TWO fillers from the same closed list, any capitalisation, "
    "only when the remainder parses as a complete teach or question by "
    "the unchanged loop157 chain) over loop157 chain")
DEFAULT_CONFIG157B["daemon"]["module"] = "Loop157bDaemon (this file)"


def build_agent157b(cfg: dict | None = None) -> Loop157bAgentLoop:
    """Build the loop157 agent shape with the 157b cap-filler mixin in."""
    cfg = dict(DEFAULT_CONFIG157B, **(cfg or {}))
    loop = L157.build_agent157(cfg)
    loop.ears.__class__ = Loop157bEars
    loop.ears.name = Loop157bEars.name
    loop.__class__ = Loop157bAgentLoop
    return loop


class Loop157bDaemon(L157.Loop157Daemon):
    """Loop157Daemon shape with the loop157b agent inside (mailbox same)."""

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
        self.loop = build_agent157b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon157b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop157bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 157b cap-filler loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop157)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG157B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG157B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG157B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon157b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent157b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
