#!/usr/bin/env python3
"""Experiment 146b -- loop146c = loop129b + the exp-146b doubt mixin
(ONE CHANGE vs 146: hearsay/reported-speech refusals never doubt).

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_doubt146b_store.py (Doubt146bMixin over the read-only 146
rule); this file stacks it onto loop129b at both levels (ears hear +
loop _act/_ask) and attaches one shared persisted DoubtStore146 per
daemon dir (same notebook-side doubts146.json contract as 146).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop146c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-doubt146b-20260922/loop146c-config.json
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

import fable_doubt146b_store as D146B  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop146cEars(D146B.Doubt146bMixin, L129b.Loop129bEars):
    """Loop129bEars + 146b doubt (hearsay-exempt record + ask screening)."""

    name = "loop146c-doubt-hearsay-exempt"


class Loop146cAgentLoop(D146B.Doubt146bMixin, L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop + 146b doubt (act-level record/clear, ask backup)."""


DEFAULT_CONFIG146C: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG146C["ears"]["stand_in"] = (
    "Loop146cEars (loop129b + exp-146b refused-correction doubt with "
    "hearsay/reported-speech exemption: refused first-person known-subject "
    "teach records (subject, relation); hearsay/quoted refusals never "
    "record; doubted answer walks abstain; later successful teach clears; "
    "doubts146.json notebook-side) over loop129b chain")
DEFAULT_CONFIG146C["daemon"]["module"] = "Loop146cDaemon (this file)"


def build_agent146c(cfg: dict | None = None) -> Loop146cAgentLoop:
    """Build the loop129b agent shape with the 146b mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG146C, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop146cEars
    loop.ears.name = Loop146cEars.name
    loop.__class__ = Loop146cAgentLoop
    state_dir = Path(cfg.get("state_dir", "."))
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    loop.ears.doubt_store146 = store
    return loop


class Loop146cDaemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop146c agent inside (mailbox same)."""

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
        self.loop = build_agent146c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon146c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop146cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 146b doubt loop (146c)")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG146C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG146C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG146C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon146c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent146c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
