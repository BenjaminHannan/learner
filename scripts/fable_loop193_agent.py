#!/usr/bin/env python3
"""Experiment 193 -- missing-apostrophe possessives on loop138h (ears only, outermost).

Base: loop138h (scripts/fable_loop138h_agent.py, read-only). ONE CHANGE:
an outermost ears stage. A token that equals, ignoring case, a name
ALREADY IN THE NOTEBOOK plus a trailing "s" (kofis, Kofis, toms, Juans;
also "s'" forms), immediately followed by a relation word the base can
already parse, is read as that name's possessive ("Kofi's city"),
silently (Ben's ruling: typos are fixed silently), then parsed by the
unchanged base. Only when the stem is a known notebook name AND the next
word is a known relation; never for unknown stems; plural real words
("cats", "bus", "Wills" when Will is not in the notebook) untouched;
turns that already parse are untouched.

Stack: ``Loop193Ears(Apos193Mixin, Loop138hEars)`` in this file; the loop,
reasoner, notebook, sleep, and daemon are loop138h unchanged (imported
read-only). Rewritten turns re-enter the full 138h stack (including its
Typo165 stage, which declines apostrophe turns, and the 162b plural
stage, which owns only plural "s'" teaches with the "The " prefix).

No existing file is edited.

Daemons launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop193_agent.py --daemon --dir DIR \\
    --config artifacts/fable-apos193-20260922/loop193-config.json
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
import fable_fix193_apos as F193  # noqa: E402 (apos mixin, this experiment)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop96_agent as L96  # noqa: E402 (inner chain ears, read-only)
import fable_loop138b_agent as L138B  # noqa: E402 (mouth, read-only)
import fable_loop138d_agent as L138D  # noqa: E402 (reasoner, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (wrapped stack, read-only)
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
A._APOS = L138H.L134._APOS_SHOUTED_134


# ------------------------------------------------- ears: 138h + apos fix
class Loop193Ears(F193.Apos193Mixin, L138H.Loop138hEars):
    """Loop138hEars + outermost missing-apostrophe possessive repair.

    Cooperative: only turns with a qualifying known-name + trailing-s
    token before a known relation are rewritten and delegated inward;
    every other turn falls through to the unchanged 138h stack.
    """

    name = "loop193-apos"


# ------------------------------------------- loop: 138h unchanged
class Loop193AgentLoop(L138H.Loop138hAgentLoop):
    """Loop138hAgentLoop unchanged (ears carry the one change)."""


DEFAULT_CONFIG193: dict = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
DEFAULT_CONFIG193["ears"]["stand_in"] = (
    "Loop193Ears (loop138h stack + outermost missing-apostrophe "
    "possessives: known-name + trailing s/s' before a known relation "
    "reads as that name's possessive, silently)")
DEFAULT_CONFIG193["daemon"]["module"] = "Loop193Daemon (this file)"


def build_agent193(cfg: dict | None = None) -> Loop193AgentLoop:
    """Build the loop138h agent shape with the loop193 ears on top."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG193, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138B.Loop138bMouth()
    reasoner = L138D.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop193Ears(L96.Loop96Ears(chain))
    loop = Loop193AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    # 142 teach/chain index patches on the INNER ears (before the sleep
    # wrap replaces loop.ears with its Sleep130Ears delegate).
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
    # L2 live-self state (Self99-shaped logs; the 168-style turn above
    # maintains them -- same shape loop138/loop138b keep).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # 146d doubt store (notebook-side doubts146.json contract, shared by
    # the loop and the inner ears; attached BEFORE the sleep wrap).
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    # 166c display-case overrides (agent-layer only; notebook append-only).
    loop._dc166c = {}
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep193: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop193: loop138h + outermost missing-apostrophe "
                      "possessives (exp-193 ears-only; silent repair, "
                      "known-name + trailing s/s' before a known relation)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop193Daemon(L138H.Loop138hDaemon):
    """Loop138hDaemon shape with the 193 agent inside."""

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
        self.loop = build_agent193(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon193(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop193Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 193 apos possessives")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138h)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG193 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG193)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG193)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon193(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent193(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
