#!/usr/bin/env python3
"""Experiment 163 -- loop163 = loop150 + the exp-163 lowercase mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix163_lowercase.py (Lowercase163Mixin: entity-layer
display-form names -- all-lowercase ask/teach spans that resolve to exactly
one known entity use its display form; all-lowercase NEW teach spans are
stored capitalised per token; inner-capital/mixed-case spans untouched;
person-relation values only, literals untouched; ambiguous spans untouched);
this file stacks it onto loop150 at both levels (ears hear + loop _act just
before the write) in the style of scripts/fable_loop140_agent.py. Values
apart from person-relation names, relation keys, forget/alias/person/quote/
answer/clarify paths untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop163_agent.py --daemon --dir DIR \\
    --config artifacts/fable-lowercase163-20260922/loop163-config.json
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

import fable_fix163_lowercase as L163  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop163Ears(L163.Lowercase163Mixin, L150.Loop150Ears):
    """Loop150Ears + 163 entity-layer display-form names."""

    name = "loop163-lowercase"


class Loop163AgentLoop(L163.Lowercase163Mixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop + 163 display-form names just before the write."""


DEFAULT_CONFIG163: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG163["ears"]["stand_in"] = (
    "Loop163Ears (loop150 + exp-163 lowercase mixin: all-lowercase ask "
    "owners and person-relation teach spans resolve to the stored display "
    "form, new lowercase person-name spans stored capitalised, other "
    "relations / inner-capitals / ambiguous spans untouched) over loop150 "
    "chain")
DEFAULT_CONFIG163["daemon"]["module"] = "Loop163Daemon (this file)"


def build_agent163(cfg: dict | None = None) -> Loop163AgentLoop:
    """Build the loop150 agent shape with the 163 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG163, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop163Ears
    loop.ears.name = Loop163Ears.name
    loop.__class__ = Loop163AgentLoop
    return loop


class Loop163Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop163 agent inside (mailbox same)."""

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
        self.loop = build_agent163(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon163(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop163Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 163 lowercase loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG163 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG163)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG163)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon163(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent163(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
