#!/usr/bin/env python3
"""Experiment 135 -- loop129b + the exp-135 officeholder guard mixin.

loop135 = loop129b + fable_fix135_office.OfficeholderGuardMixin, subclass and
class-swap only. No existing file is edited; everything new lives in this
file (+ scripts/fable_fix135_office.py).

  Loop135Ears(OfficeholderGuardMixin, Loop129bEars): the mixin's hear() runs
    the exact loop129b/loop121 teach logic with bench73's catch-all
    "The (.+?) is (.+?)" guarded -- officeholder triples whose head phrase is
    not a table-derived office title return None, so the sentence takes the
    loop's unparsed-sentence path (clarify, no write). Question side, guards,
    relation keys, punctuation sanitize: identical to loop129b.
  Loop135AgentLoop(Loop129bAgentLoop): unchanged acts (kept as a subclass so
    the marks123 harness finds the loop135 names).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop135_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix135-20260922/loop135-config.json
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

import fable_fix135_office as F135  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop135Ears(F135.OfficeholderGuardMixin, L129b.Loop129bEars):
    """Loop129bEars + officeholder catch-all guard (stackable mixin first)."""

    name = "loop135-office-guard"


class Loop135AgentLoop(L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG135: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG135["ears"]["stand_in"] = (
    "Loop135Ears (loop129b teach coverage + exp-129 punctuation strip + "
    "exp-135 officeholder catch-all guard: officeholder writes only for "
    "table-derived office heads, else the unparsed clarify path) over "
    "loop129b chain")
DEFAULT_CONFIG135["daemon"]["module"] = "Loop135Daemon (this file)"


def build_agent135(cfg: dict | None = None) -> Loop135AgentLoop:
    """Build the loop129b agent shape with Loop135Ears/Loop swapped in."""
    cfg = dict(DEFAULT_CONFIG135, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop135Ears
    loop.ears.name = Loop135Ears.name
    loop.__class__ = Loop135AgentLoop
    return loop


class Loop135Daemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop135 agent inside (mailbox same)."""

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
        self.loop = build_agent135(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon135(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop135Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 135 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG135 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG135)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG135)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon135(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent135(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
