#!/usr/bin/env python3
"""Experiment 220 -- loop138i with the restart-index fix (ONE change).

loop220 = loop138i + FixedIndexedLoopNotebook
(scripts/fable_fix220_restartindex.py) in place of IndexedLoopNotebook.
No existing file is edited. The swap is a process-local runtime patch of
the single construction site every loop138 lineage __init__ resolves to
(L138d.Loop138dAgentLoop.__init__ reads the global IndexedLoopNotebook in
scripts/fable_loop138d_agent.py; Loop138f/138g/138h/138i define no
__init__ of their own) -- the same process-wide override pattern
loop134/loop138b/loop138d already use for WM149/the _APOS rule. The patch
is applied only while build_agent220 constructs the loop and is restored
before returning, so base builds in the same process are untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop220_agent.py --daemon --dir DIR \\
    --config artifacts/fable-restartindex220-20260922/loop220-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (patch site, read-only)
import fable_loop138i_agent as L138i  # noqa: E402 (wrapped base, read-only)
from fable_fix220_restartindex import (  # noqa: E402 (the one change)
    FixedIndexedLoopNotebook,
)

DEFAULT_CONFIG220: dict = copy.deepcopy(L138i.DEFAULT_CONFIG138I)
DEFAULT_CONFIG220["notebook"]["class"] = (
    "FixedIndexedLoopNotebook (scripts/fable_fix220_restartindex.py: "
    "IndexedLoopNotebook with _load indexing each event exactly once)")
DEFAULT_CONFIG220["daemon"]["module"] = "Loop220Daemon (this file)"


def build_agent220(cfg: dict | None = None):
    """Build the loop138i agent shape with the fixed notebook inside."""
    cfg = dict(DEFAULT_CONFIG220, **(cfg or {}))
    orig = L138d.IndexedLoopNotebook
    L138d.IndexedLoopNotebook = FixedIndexedLoopNotebook  # type: ignore[method-assign]
    try:
        loop = L138i.build_agent138i(cfg)
    finally:
        L138d.IndexedLoopNotebook = orig  # type: ignore[method-assign]
    loop.notes.append("loop220: FixedIndexedLoopNotebook in place of "
                      "IndexedLoopNotebook (exp-220 single change: after a "
                      "load every event is indexed exactly once)")
    return loop


class Loop220Daemon(L138i.Loop138iDaemon):
    """Loop138iDaemon shape with the fixed-notebook agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
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
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent220(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon220(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop220Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (thinker module, read-only)
    parser = argparse.ArgumentParser(description="Exp 220 fixed-index loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG220 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG220)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG220)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon220(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent220(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
