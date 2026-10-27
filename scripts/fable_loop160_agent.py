#!/usr/bin/env python3
"""Experiment 160 -- loop160 = loop150 + the exp-160 bare-correction mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix160_barecorrect.py (BareCorrect160Mixin: bare corrections
"no wait, it's V" / "wait, it's V" / "sorry, it's V" / "I meant V" /
"no, V" apply to the triple taught in the IMMEDIATELY previous user turn
through the existing correction machinery; otherwise the sealed clarify
with 0 writes). Stacked onto loop150 at both levels (ears hear tag + loop
_act resolve + _listening_tick previous-triple bookkeeping). Guards,
values, relation keys, forget/ask/clarify paths untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop160_agent.py --daemon --dir DIR \\
    --config artifacts/fable-correct160-20260922/loop160-config.json
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

import fable_fix160_barecorrect as B160  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop160Ears(B160.BareCorrect160Mixin, L150.Loop150Ears):
    """Loop150Ears + 160 bare-correction tag on single clarifies."""

    name = "loop160-barecorrect"


class Loop160AgentLoop(B160.BareCorrect160Mixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop + 160 bare-correct resolve + previous-triple memory."""


DEFAULT_CONFIG160: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG160["ears"]["stand_in"] = (
    "Loop160Ears (loop150 + exp-160 bare corrections against the previous "
    "taught triple: no wait,/wait,/sorry, + it's V, I meant V, no, V; "
    "else the sealed Which-fact clarify, 0 writes) over loop150 chain")
DEFAULT_CONFIG160["daemon"]["module"] = "Loop160Daemon (this file)"


def build_agent160(cfg: dict | None = None) -> Loop160AgentLoop:
    """Build the loop150 agent shape with the 160 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG160, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop160Ears
    loop.ears.name = Loop160Ears.name
    loop.__class__ = Loop160AgentLoop
    if getattr(loop, "_last_teach160", None) is None:
        loop._last_teach160 = None
    return loop


class Loop160Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop160 agent inside (mailbox same)."""

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
        self.loop = build_agent160(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon160(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop160Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 160 bare-correct loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG160 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG160)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG160)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon160(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent160(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
