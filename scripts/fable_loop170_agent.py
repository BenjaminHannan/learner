#!/usr/bin/env python3
"""Experiment 170 -- fast asks in the stacked agent (loop138d + index composers).

Base agent: loop138d (scripts/fable_loop138d_agent.py,
artifacts/fable-agent138d-20260922/loop138d-config.json), imported read-only
and never edited. THE ONE CHANGE lives in scripts/fable_fix170_compose.py:
every per-ask full-notebook scan (notebook_triples rebuild, per-entity
re.compile mentions, per-step triple walks, consumption-gate names build)
reads the incremental per-(subject, relation) index instead. No ears path,
148b screen, 132 rewriter, or decision order is skipped or reordered -- the
same functions are called in the same order; only the scanning leaves run
over the index (with delegation to the saved originals on unknown shapes).

Build: mixin subclass of the 138d loop; install_index170() rebinds the
leaves process-locally (same pattern as WM149.apply_wordmatch).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop170_agent.py --daemon --dir DIR \\
    --config artifacts/fable-speed170-20260922/loop170-config.json
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

import fable_loop138d_agent as L138d  # noqa: E402 (base agent, read-only)
from fable_fix170_compose import install_index170  # noqa: E402 (the fix)

install_index170()

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_loop90_agent as L90  # noqa: E402 (thinker builder, read-only)


class Loop170Ears(L138d.Loop138dEars):
    """Loop138dEars with index-backed scanning leaves (same path, same order)."""

    name = "loop170-stack-index"


class Loop170AgentLoop(L138d.Loop138dAgentLoop):
    """Loop138dAgentLoop with index-backed scanning leaves."""

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        super().__init__(state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
                         sleeper=sleeper, thinker=thinker,
                         sleep_threshold=sleep_threshold)
        self.notes.append("loop170: 138d + index-backed composers "
                          "(notebook_triples cache + whole-word mentions via "
                          "cached sealed patterns + _sro/_srel walks + "
                          "cached consumption names; no path skipped)")


DEFAULT_CONFIG170: dict = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
DEFAULT_CONFIG170["ears"]["stand_in"] = (
    "Loop170Ears (Loop138dEars with index-backed scanning leaves: cached "
    "notebook_triples, whole-word mentions via cached sealed patterns, "
    "_sro/_srel composer walks, cached consumption names)")
DEFAULT_CONFIG170["reasoner"]["class"] = (
    L138d.DEFAULT_CONFIG138D["reasoner"]["class"] + " (unchanged)")
DEFAULT_CONFIG170["daemon"]["module"] = "Loop170Daemon (this file)"


def build_agent170(cfg: dict | None = None) -> Loop170AgentLoop:
    """Build the loop138d agent shape with the 170 ears/loop swapped in."""
    cfg = dict(DEFAULT_CONFIG170, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138d.L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop170Ears(Loop96Ears(chain))
    loop = Loop170AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    from fable_perf142_index import (  # noqa: E402 (read-only, as in 138d)
        _patch_relation, patch_chain142, patch_loop121_teach)
    patch_chain142(chain)
    patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep170: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit, as in 138d)")
    return loop


class Loop170Daemon(L138d.Loop138dDaemon):
    """Loop138dDaemon shape with the 170 agent inside."""

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
        self.loop = build_agent170(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon170(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop170Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 170 stacked loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138d)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG170 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG170)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG170)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon170(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent170(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
