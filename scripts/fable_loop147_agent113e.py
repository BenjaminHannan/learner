#!/usr/bin/env python3
"""Experiment 147 -- mention-walk alignment on loop113e (integration stack).

Same one change as scripts/fable_loop147_agent.py, layered on loop113e
instead of loop134: Loop147on113eEars(Align147Mixin, Loop113eEars). The
113e inverse-cue consumption gate keeps running unchanged downstream of
the aligned composers. Teach path byte-identical to loop113e.

No existing file is edited; everything new lives here +
scripts/fable_align147_compose.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop147_agent113e.py --daemon --dir DIR \\
    --config artifacts/fable-align147-20260922/loop147-113e-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_loop113e_agent as L113E  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
from fable_align147_compose import (  # noqa: E402 (this experiment's fix)
    Align147Mixin)
from fable_wire51_adapters import (  # noqa: E402 (sleeper, read-only)
    HardGate46Sleeper)


class Loop147on113eEars(Align147Mixin, L113E.Loop113eEars):
    """Loop113eEars + mention-walk alignment on the question side."""


class Loop147on113eAgentLoop(L113E.Loop113eAgentLoop):
    """Loop113eAgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG147_113E: dict = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
DEFAULT_CONFIG147_113E["ears"]["stand_in"] = (
    "Loop147on113eEars (Align147Mixin mention-walk alignment over "
    "Loop113eEars: aligned N-hop/2-hop composers, unchanged 113e "
    "inverse-cue consumption gate downstream) over Loop102Ears pre-filter "
    "over Loop96Ears = GuardedEars91 over ChainEars; teach path identical "
    "to loop113e")
DEFAULT_CONFIG147_113E["daemon"]["module"] = "Loop147on113eDaemon (this file)"


def build_agent147_113e(cfg: dict | None = None) -> Loop147on113eAgentLoop:
    """Build the loop113e agent shape with aligned ears."""
    cfg = dict(DEFAULT_CONFIG147_113E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop147on113eAgentLoop(
        state_dir, ears=Loop147on113eEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    return loop


class Loop147on113eDaemon(L113E.Loop113eDaemon):
    """Loop113eDaemon shape with the aligned agent inside (mailbox identical)."""

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
        self.loop = build_agent147_113e(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon147_113e(root, cfg: dict | None = None,
                       idle_seconds: float = 30.0) -> int:
    daemon = Loop147on113eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 147 align loop (113e)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG147_113E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG147_113E)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG147_113E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon147_113e(args.dir, cfg=cfg,
                                  idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent147_113e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
