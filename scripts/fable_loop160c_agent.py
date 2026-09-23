#!/usr/bin/env python3
"""Experiment 160c -- loop160c = loop160b + the exp-160c two-hop mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix160c_twohp.py (TwoHop160cMixin: after a previous reply that
stated a chain of >= 2 facts, a bare correction writes nothing and replies
with the chain's facts as options; otherwise byte-identical to loop160b).
Stacked outside LastStated160bMixin at the loop _act/_listening_tick level
(ears hear tag untouched, inherited from loop160b).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop160c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-twohop160c-20260922/loop160c-config.json
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

import fable_fix160c_twohp as C160c  # noqa: E402 (this experiment)
import fable_loop160b_agent as L160b  # noqa: E402 (wrapped base, read-only)


class Loop160cEars(L160b.Loop160bEars):
    """Loop160bEars unchanged (bare-correction tag identical to 160b)."""

    name = "loop160c-twohop"


class Loop160cAgentLoop(C160c.TwoHop160cMixin, L160b.Loop160bAgentLoop):
    """Loop160bAgentLoop + 160c two-hop clarify-before-write."""


DEFAULT_CONFIG160C: dict = copy.deepcopy(L160b.DEFAULT_CONFIG160B)
DEFAULT_CONFIG160C["ears"]["stand_in"] = (
    "Loop160cEars (loop160b + exp-160c two-hop rule: after a >= 2-fact chain "
    "answer a bare correction writes nothing and asks which fact is wrong; "
    "else byte-identical to loop160b) over loop150 chain")
DEFAULT_CONFIG160C["daemon"]["module"] = "Loop160cDaemon (this file)"


def build_agent160c(cfg: dict | None = None) -> Loop160cAgentLoop:
    """Build the loop160b agent shape with the 160c mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG160C, **(cfg or {}))
    loop = L160b.build_agent160b(cfg)
    loop.ears.__class__ = Loop160cEars
    loop.ears.name = Loop160cEars.name
    loop.__class__ = Loop160cAgentLoop
    if getattr(loop, "_chain160c", None) is None:
        loop._chain160c = None
    if getattr(loop, "_last_stated160b", None) is None:
        loop._last_stated160b = None
    return loop


class Loop160cDaemon(L160b.Loop160bDaemon):
    """Loop160bDaemon shape with the loop160c agent inside (mailbox same)."""

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
        self.loop = build_agent160c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon160c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop160cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 160c two-hop loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop160b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG160C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG160C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG160C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon160c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent160c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
