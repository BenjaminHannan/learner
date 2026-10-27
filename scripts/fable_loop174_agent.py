#!/usr/bin/env python3
"""Experiment 174 -- loop138f + the exp-174 "of"-question rewrite (ONE CHANGE).

loop174 = clean base loop138f (scripts/fable_loop138f_agent.py, read-only)
with ONE added outermost ears stage: ChainOf174Mixin (scripts/
fable_fix174_chainof.py, read-only) -- the question-frame rewrite "What/Who
is the R of X's S?" -> "What/Who is X's S's R?" and "What/Who is the R of
X?" -> "What/Who is X's R?" for closed-list R/S + name X, else passthrough.
Statements are never rewritten. Everything else (teaches, guards, reasoner,
notebook, sleep, daemon settle) is loop138f unchanged.

Composition:
  Ears (outermost first): ChainOf174 > Loop138fEars (138f stack unchanged).
  Loop _act / turn(): inherited verbatim from loop138f (via Loop138fAgentLoop).
  Reasoner / Notebook / Sleeper / Thinker: built by build_agent138f pieces.

No existing file is edited; everything new lives in this file (+ scripts/
fable_fix174_*.py drivers + artifacts/fable-chainof174-20260922/ +
design/v3/30-modes/174-chainof-muse.md).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop174_agent.py --daemon --dir DIR \\
    --config artifacts/fable-chainof174-20260922/loop174-config.json
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
import fable_fix174_chainof as C174  # noqa: E402 (the one change, read-only)
import fable_loop138f_agent as L138f  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b/loop138d/loop138f
# use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b/loop138d/loop138f set; no file edited).
import fable_loop134_agent as L134  # noqa: E402 (read-only)
A._APOS = L134._APOS_SHOUTED_134


# ------------------------------------------------------------ ears: 138f + one outermost stage
class Loop174Ears(C174.ChainOf174Mixin, L138f.Loop138fEars):
    """Loop138fEars + outermost "of"-question rewrite (statements untouched)."""

    name = "loop174-chainof"


# ------------------------------------------------------------ loop: 138f shape, 174 ears
class Loop174AgentLoop(L138f.Loop138fAgentLoop):
    """Loop138fAgentLoop behaviour with Loop174Ears inside.

    _act / turn() are inherited verbatim from loop138f. __init__/_save
    mirror Loop138fAgentLoop (IndexedLoopNotebook + torn-tail repair +
    Listening + _patch_relation + tail-200 persist) via the 138d donor.
    """


DEFAULT_CONFIG174: dict = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
DEFAULT_CONFIG174["ears"]["stand_in"] = (
    "Loop174Ears (ChainOf174 outermost: What/Who is the R of X's S? -> "
    "X's S's R? and the R of X? -> X's R? for closed-list R/S + name X, "
    "questions only; loop138f stack unchanged beneath)")
DEFAULT_CONFIG174["daemon"]["module"] = "Loop174Daemon (this file)"


def build_agent174(cfg: dict | None = None) -> Loop174AgentLoop:
    """Build the loop138f agent shape with the 174 rewrite outermost."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG174, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138f.L138b.Loop138bMouth()
    reasoner = L138f.L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop174Ears(Loop96Ears(chain))
    loop = Loop174AgentLoop(
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
    # L2 live-self state (Self99-shaped logs; the inherited loop138 turn
    # maintains them -- same shape loop138/loop138b/loop138f keep).
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
    import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep174: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop174: loop138f + ChainOf174 outermost "
                      "of-question rewrite (ears only, statements never "
                      "rewritten)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop174Daemon(L138f.Loop138fDaemon):
    """Loop138fDaemon shape with the 174 agent inside.

    141 settle gate + exactly-once process_file are inherited unchanged.
    __init__ mirrors Loop138fDaemon.__init__ line for line except the
    build call. Name ends in Daemon / starts with Loop so the marks123
    loader picks this class.
    """

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
        self.loop = build_agent174(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon174(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop174Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 174 stacked loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138f)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG174 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG174)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG174)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon174(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent174(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
