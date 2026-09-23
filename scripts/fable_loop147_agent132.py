#!/usr/bin/env python3
"""Experiment 147 -- mention-walk alignment on loop132 (integration stack).

Same one change as scripts/fable_loop147_agent.py, layered on loop132
instead of loop134: Loop147on132Ears(Align147Mixin, Loop132Ears). The
132 deterministic rewriter keeps running unchanged (it consults the
rewriter only when the aligned base path clarifies, and rewrite
verification goes through the aligned composers, which still verify exact
intact-chain frames). Teach path byte-identical to loop132.

No existing file is edited; everything new lives here +
scripts/fable_align147_compose.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop147_agent132.py --daemon --dir DIR \\
    --config artifacts/fable-align147-20260922/loop147-132-config.json
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
import fable_loop132_agent as L132  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
from fable_align147_compose import (  # noqa: E402 (this experiment's fix)
    Align147Mixin)
from fable_wire51_adapters import (  # noqa: E402 (sleeper, read-only)
    HardGate46Sleeper)


class Loop147on132Ears(Align147Mixin, L132.Loop132Ears):
    """Loop132Ears + mention-walk alignment on the question side."""


class Loop147on132AgentLoop(L132.Loop132AgentLoop):
    """Loop132AgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG147_132: dict = copy.deepcopy(L132.DEFAULT_CONFIG132)
DEFAULT_CONFIG147_132["ears"]["stand_in"] = (
    "Loop147on132Ears (Align147Mixin mention-walk alignment over "
    "Loop132Ears: aligned N-hop/2-hop composers under the unchanged "
    "deterministic relative-clause rewriter) over Loop121Ears teach "
    "coverage over Loop113bEars N-hop router + loop102 fallback")
DEFAULT_CONFIG147_132["daemon"]["module"] = "Loop147on132Daemon (this file)"


def build_agent147_132(cfg: dict | None = None) -> Loop147on132AgentLoop:
    """Build the loop132 agent shape with aligned ears."""
    cfg = dict(DEFAULT_CONFIG147_132, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4132)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop147on132AgentLoop(
        state_dir, ears=Loop147on132Ears(Loop96Ears(chain)), mouth=mouth,
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


class Loop147on132Daemon(L132.Loop132Daemon):
    """Loop132Daemon shape with the aligned agent inside (mailbox identical)."""

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
        self.loop = build_agent147_132(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon147_132(root, cfg: dict | None = None,
                      idle_seconds: float = 30.0) -> int:
    daemon = Loop147on132Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 147 align loop (132)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG147_132 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG147_132)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG147_132)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon147_132(args.dir, cfg=cfg,
                                 idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent147_132(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
