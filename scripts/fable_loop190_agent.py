#!/usr/bin/env python3
"""Experiment 190 -- reverse questions by VALUE lookup on loop138g.

loop190 = loop138g + ONE change: the reverse stage in
scripts/fable_fix190_reverse.py (closed shapes E1-E4 over the closed
relation set loop138g can already teach and store; answers from live
taught triples only; clarify actions only, never writes).

Composition: one new ears stage OUTSIDE the unchanged 138g stack
(super().hear() first; only all-clarify results reconsidered, so
forward asks and teaches are byte-identical). No _act override, no
turn() override (the 190 clarifies carry no "didn't understand", so
the 168 grounded-self gate passes them through verbatim). Reasoner,
notebook, sleep, daemon: 138g unchanged.

Ears order (outermost first):
  Reverse190 > Loop138gEars (Frame137g > WhCity158cPort > Tail139eGuard >
  Loop138fEars (Qform158 > Filler157 > Smalltalk156b > Doubt146b >
  Subject150B > Reverse153 > Loop138bEars)).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop190_agent.py --daemon --dir DIR \\
    --config artifacts/fable-reverse190-20260922/loop190-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_fix190_reverse as R190  # noqa: E402 (THE ONE CHANGE)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b/loop138d use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b/loop138d set; no file edited).
A._APOS = L134._APOS_SHOUTED_134


class Loop190Ears(R190.Reverse190Mixin, L138G.Loop138gEars):
    """Loop138gEars + the 190 reverse stage outermost."""

    name = "loop190-reverse"


class Loop190AgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop unchanged (no _act/turn override).

    The 190 stage emits clarify actions only, which _act passes through
    without writing; the clarifies carry no "didn't understand", so the
    168 grounded-self gate in turn() serves them verbatim.
    """


DEFAULT_CONFIG190: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG190["ears"]["stand_in"] = (
    "Loop190Ears (loop138g stack + outermost 190 reverse-value stage: "
    "closed shapes E1-E4 over the closed teachable relation set, "
    "live-taught-triples lookup, clarify-only, never writes)")
DEFAULT_CONFIG190["daemon"]["module"] = "Loop190Daemon (this file)"


def build_agent190(cfg: dict | None = None) -> Loop190AgentLoop:
    """Build the loop138g agent shape with the 190 reverse stage stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG190, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop190Ears(Loop96Ears(chain))
    loop = Loop190AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
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
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep190: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop190: loop138g + reverse-value stage (closed "
                      "shapes E1-E4 over the closed teachable relation "
                      "set; live taught triples only; clarify-only)")
    return loop


class Loop190Daemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 190 agent inside."""

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
        self.loop = build_agent190(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon190(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop190Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 190 reverse loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG190 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG190)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG190)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon190(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent190(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
