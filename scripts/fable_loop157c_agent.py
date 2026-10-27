#!/usr/bin/env python3
"""Experiment 157c -- loop157c = loop157b + the exp-157c title guard.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix157c_titleguard.py (TitleGuard157cMixin: a capitalised
filler followed directly, no punctuation, by a Capitalised word never
strips; the whole capitalised run is treated as the name via the deep
loop157 parse); this file stacks it onto loop157b at ears level in the
style of scripts/fable_loop157b_agent.py. Values, relation keys,
forget/ask/clarify paths, correction markers, lowercase/comma fillers
and punctuation/lowercase follows are untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop157c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-title157c-20260922/loop157c-config.json
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

import fable_fix157c_titleguard as F157C  # noqa: E402 (this experiment)
import fable_loop157b_agent as L157B  # noqa: E402 (wrapped base, read-only)


class Loop157cEars(F157C.TitleGuard157cMixin, L157B.Loop157bEars):
    """Loop157bEars + exp-157c title guard (filler+Capitalised never strips)."""

    name = "loop157c-titleguard"


class Loop157cAgentLoop(L157B.Loop157bAgentLoop):
    """Loop157bAgentLoop unchanged (title guard lives at ears level)."""


DEFAULT_CONFIG157C: dict = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
DEFAULT_CONFIG157C["ears"]["stand_in"] = (
    "Loop157cEars (loop157b + exp-157c title guard: a capitalised filler "
    "followed directly, no punctuation, by a Capitalised word never "
    "strips; the whole capitalised run is treated as the name via the "
    "deep loop157 parse) over loop157b chain")
DEFAULT_CONFIG157C["daemon"]["module"] = "Loop157cDaemon (this file)"


def build_agent157c(cfg: dict | None = None) -> Loop157cAgentLoop:
    """Build the loop157b agent shape with the 157c title guard in."""
    cfg = dict(DEFAULT_CONFIG157C, **(cfg or {}))
    loop = L157B.build_agent157b(cfg)
    loop.ears.__class__ = Loop157cEars
    loop.ears.name = Loop157cEars.name
    loop.__class__ = Loop157cAgentLoop
    return loop


class Loop157cDaemon(L157B.Loop157bDaemon):
    """Loop157bDaemon shape with the loop157c agent inside (mailbox same)."""

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
        self.loop = build_agent157c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon157c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop157cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 157c title-guard loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop157b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG157C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG157C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG157C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon157c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent157c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
