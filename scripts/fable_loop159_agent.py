#!/usr/bin/env python3
"""Experiment 159 -- loop150 + the exp-159 hop-through-known-names bridge.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix159_hop.py (Hop159Reasoner77: the fix77 hop loop verbatim
except mid-chain literals continue iff they exactly name one live taught
subject); this file stacks it onto loop150 by swapping the reasoner after
the standard loop150 build (ears, mouth, sleeper, thinker, notebook, daemon
mailbox all inherited unchanged).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop159_agent.py --daemon --dir DIR \\
    --config artifacts/fable-hop159-20260922/loop159-config.json
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

import fable_fix159_hop as H159  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop159AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop with the hop-159 reasoner (swapped in at build)."""


DEFAULT_CONFIG159: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG159["reasoner"]["stand_in"] = (
    "Hop159Reasoner77 (QualifierAwareReasoner77 + exp-159 bridge: mid-chain "
    "literal continues iff it exactly names one live taught subject)")
DEFAULT_CONFIG159["reasoner"]["module"] = "scripts/fable_fix159_hop.py"
DEFAULT_CONFIG159["daemon"]["module"] = "Loop159Daemon (this file)"


def build_agent159(cfg: dict | None = None) -> Loop159AgentLoop:
    """Build the loop150 agent shape with the hop-159 reasoner swapped in."""
    cfg = dict(DEFAULT_CONFIG159, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    old = loop.reasoner
    new = H159.Hop159Reasoner77()
    if hasattr(old, "words"):
        try:
            new.words = old.words
        except Exception:  # noqa: BLE001 -- _sync rebuilds from nb anyway
            pass
    loop.reasoner = new
    try:
        loop.parts90["reasoner"] = new
    except (AttributeError, KeyError, TypeError):
        pass
    loop.__class__ = Loop159AgentLoop
    return loop


class Loop159Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop159 agent inside (mailbox same)."""

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
        self.loop = build_agent159(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon159(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop159Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 159 hop-through loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG159 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG159)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG159)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon159(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent159(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
