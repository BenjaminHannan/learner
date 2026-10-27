#!/usr/bin/env python3
"""Experiment 146b -- loop146d = loop139b + the exp-146b doubt mixin
(ONE CHANGE vs 146: hearsay/reported-speech refusals never doubt).

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_doubt146b_store.py (Doubt146bMixin over the read-only 146
rule); this file stacks it onto loop139b at both levels (ears hear +
loop _act/_ask) and attaches one shared persisted DoubtStore146 per
daemon dir (same notebook-side doubts146.json contract as 146).

Stacking order (outermost first): Doubt146bMixin, ValueGuard139BMixin,
Loop129bEars/Loop129bAgentLoop.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop146d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-doubt146b-20260922/loop146d-config.json
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
import fable_loop139b_agent as L139B  # noqa: E402 (wrapped base, read-only)


class Loop146dEars(D146B.Doubt146bMixin, L139B.Loop139bEars):
    """Loop139bEars + 146b doubt (hearsay-exempt record + ask screening)."""

    name = "loop146d-doubt-hearsay-exempt-on139b"


class Loop146dAgentLoop(D146B.Doubt146bMixin, L139B.Loop139bAgentLoop):
    """Loop139bAgentLoop + 146b doubt (act-level record/clear, ask backup)."""


DEFAULT_CONFIG146D: dict = copy.deepcopy(L139B.DEFAULT_CONFIG139B)
DEFAULT_CONFIG146D["ears"]["stand_in"] = (
    "Loop146dEars (loop139b + exp-146b refused-correction doubt with "
    "hearsay/reported-speech exemption; doubts146.json notebook-side) "
    "over loop139b value-guard chain")
DEFAULT_CONFIG146D["daemon"]["module"] = "Loop146dDaemon (this file)"


def build_agent146d(cfg: dict | None = None) -> Loop146dAgentLoop:
    """Build the loop139b agent shape with the 146b mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG146D, **(cfg or {}))
    loop = L139B.build_agent139b(cfg)
    loop.ears.__class__ = Loop146dEars
    loop.ears.name = Loop146dEars.name
    loop.__class__ = Loop146dAgentLoop
    state_dir = Path(cfg.get("state_dir", "."))
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    loop.ears.doubt_store146 = store
    return loop


class Loop146dDaemon(L139B.Loop139bDaemon):
    """Loop139bDaemon shape with the loop146d agent inside (mailbox same)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
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
        self.idle_seconds = float(idle_seconds)
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent146d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon146d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop146dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 146b doubt loop (146d)")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop139b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG146D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG146D)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG146D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon146d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent146d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
