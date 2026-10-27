#!/usr/bin/env python3
"""Experiment 154 -- loop154 = loop150 + the exp-154 yes/no stage.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix154_yesno.py (YesNo154Mixin: a yes/no stage that runs ONLY
when the forward path did not understand -- "Is V X's R?" / "Is V the R of
X?" / "Is X's R V?" / "Is X's R1's R2 V?" rewritten into the wh-question
the loop already answers, run through the UNCHANGED forward path, value
compared after the loop's own normalisation; Yes on match, No only on a
single-valued last hop per the sealed code table, "I only know that ..."
on multi-valued relations, the honest forward reply on abstention; never a
write); this file stacks it onto loop150 (loop129b + 139b value guard + 150
subject guard) in the style of scripts/fable_loop140_agent.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop154_agent.py --daemon --dir DIR \\
    --config artifacts/fable-yesno154-20260922/loop154-config.json
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

import fable_fix154_yesno as Y154  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop154Ears(L150.Loop150Ears):
    """Loop150Ears unchanged (the yes/no stage is loop-level only)."""

    name = "loop154-yesno-ears"


class Loop154AgentLoop(Y154.YesNo154Mixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop + the exp-154 yes/no stage on didn't-understand."""


DEFAULT_CONFIG154: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG154["ears"]["stand_in"] = (
    "Loop154Ears (loop150 ears unchanged) over loop150 chain; yes/no is a "
    "loop-level stage (YesNo154Mixin over Loop150AgentLoop): an 'Is ...?' "
    "turn the forward path did not understand is rewritten into the "
    "wh-question the loop already answers and compared after the loop's "
    "own normalisation -- Yes on match, No only on single-valued last "
    "hops, 'I only know that ...' on multi-valued, honest abstain reply "
    "otherwise; never a write")
DEFAULT_CONFIG154["daemon"]["module"] = "Loop154Daemon (this file)"


def build_agent154(cfg: dict | None = None) -> Loop154AgentLoop:
    """Build the loop150 agent shape with the yes/no mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG154, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop154Ears
    loop.ears.name = Loop154Ears.name
    loop.__class__ = Loop154AgentLoop
    return loop


class Loop154Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop154 agent inside (mailbox same)."""

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
        self.loop = build_agent154(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon154(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop154Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154 yes/no loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
