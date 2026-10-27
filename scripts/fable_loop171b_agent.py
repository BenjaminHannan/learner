#!/usr/bin/env python3
"""Experiment 171b -- THE ONE CHANGE vs loop171: word-names save.

loop171b = loop171 + NameVal171BMixin (scripts/fable_fix171b_nameval.py):
a name-relation value of ONLY 1-3 Title-case tokens counts as name-shaped
(saved like any real name) even when its lowercase form is a dictionary
word, except the sealed closed list (state/place/time words), which stays
refused exactly as in 171. Everything else is the loop171 code path
literally.

Base loop171 (scripts/fable_loop171_agent.py) is imported read-only and
never edited; everything new lives in this file + scripts/fable_fix171b_*.py
+ artifacts/fable-nameval171b-20260922/loop171b-config.json + the design doc
design/v3/30-modes/171b-word-names-muse.md.

Composition: ears NameVal171B > Loop171Ears (explicit-super bypass: the
inner 171 guard is skipped exactly once, the 138d chain underneath decides
first, then the 171b screen rewrites refused name-value teaches to the
same sealed clarify). Loop _act: NameVal171B re-check > 171/138d guards.
Reasoner, notebook, sleeper, thinker, daemon shape: inherited from 171.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop171b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-nameval171b-20260922/loop171b-config.json
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
import fable_fix171b_nameval as N171B  # noqa: E402 (the one change)
import fable_loop171_agent as L171  # noqa: E402 (wrapped base, read-only)


class Loop171bEars(N171B.NameVal171BMixin, L171.Loop171Ears):
    """Loop171Ears + the word-name exception (outermost, super-first)."""

    name = "loop171b-wordnames"


class Loop171bAgentLoop(N171B.NameVal171BMixin, L171.Loop171AgentLoop):
    """Loop171AgentLoop + the word-name exception on _act.

    __init__/_save/turn() are inherited verbatim (they never name the ears
    class); build_agent171b passes the Loop171bEars instance in.
    """


DEFAULT_CONFIG171B: dict = copy.deepcopy(L171.DEFAULT_CONFIG171)
DEFAULT_CONFIG171B["ears"]["stand_in"] = (
    "Loop171bEars (NameVal171BMixin + loop171 stack: 171 name-shaped-value "
    "guard with the 171b word-name exception + loop138d stack, outermost "
    "first)")
DEFAULT_CONFIG171B["daemon"]["module"] = "Loop171bDaemon (this file)"
DEFAULT_CONFIG171B["notes"] = ("loop171b: loop171 + exp-171b word-name "
                               "exception (Title-case-only 1-3 token values "
                               "on the 21 sealed name keys save as names; "
                               "sealed closed list stays refused)")


def build_agent171b(cfg: dict | None = None) -> Loop171bAgentLoop:
    """Build the loop171 agent shape with the 171b exception swapped in."""
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    from fable_perf142_index import (  # noqa: E402 (read-only)
        patch_chain142, patch_loop121_teach)
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    cfg = dict(DEFAULT_CONFIG171B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    import fable_loop138b_agent as L138b  # noqa: E402 (read-only)
    mouth = L138b.Loop138bMouth()
    from fable_loop138d_agent import Reasoner138d  # noqa: E402 (read-only)
    reasoner = Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop171bEars(Loop96Ears(chain))
    loop = Loop171bAgentLoop(
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
    loop.notes.append("sleep171b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop171b: loop171 + exp-171b word-name exception "
                      "(Title-case-only 1-3 token name values save; sealed "
                      "closed list still clarifies)")
    return loop


class Loop171bDaemon(L171.Loop171Daemon):
    """Loop171Daemon shape with the 171b agent inside.

    Settle gate + exactly-once process_file are inherited unchanged; only
    the build call changes. Name ends in Daemon / starts with Loop so the
    marks123 loader picks this class.
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
        self.loop = build_agent171b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon171b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop171bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 171b word-name loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop171)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG171B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG171B)
        out["thinker"]["module"] = "fable_webfix89_thinking"
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG171B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon171b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent171b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
