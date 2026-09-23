#!/usr/bin/env python3
"""Experiment 171 -- THE ONE CHANGE vs loop138d: refuse description values
on name-valued relations (no write + one sealed clarify).

loop171 = loop138d + NameVal171Mixin (scripts/fable_fix171_nameval.py):
for relations whose value must be a NAME (mother, father, mom, dad, mum,
daddy, sister, brother, sibling, boss, friend, spouse, wife, husband,
child, son, daughter, teacher, colleague, dog, cat), a teach/correct whose
value is not name-shaped (first word a common English word per sealed
wordlist171.txt, or a sealed article/determiner, or a sealed place/time
adverb) writes nothing and replies with the one sealed clarify, e.g.
"That sounds like a description, not a name, so I didn't save it. What is
Kim's mother's name?". Name-shaped values (Rita, ana, priya, ...) and all
non-name relations (job, pet, city, colour, food, ...) take the loop138d
code path literally (byte-identical by construction: the mixin only claims
teach/correct actions on the 21 sealed name keys with refused values).

Base loop138d (scripts/fable_loop138d_agent.py) is imported read-only and
never edited; everything new lives in this file + scripts/fable_fix171_*.py
+ artifacts/fable-nameval171-20260922/loop171-config.json + the design doc
design/v3/30-modes/171-name-shaped-values-muse.md.

Composition: ears NameVal171 > Loop138dEars (super-first: the inner 138d
chain decides first, the mixin only rewrites refused name-value teaches to
clarify). Loop _act: NameVal171 re-check > 138d guards (covers structured
paths). Reasoner, notebook, sleeper, thinker, daemon shape: inherited from
138d unchanged.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop171_agent.py --daemon --dir DIR \\
    --config artifacts/fable-nameval171-20260922/loop171-config.json
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
import fable_fix171_nameval as N171  # noqa: E402 (the one change)
import fable_loop138d_agent as L138d  # noqa: E402 (wrapped base, read-only)


class Loop171Ears(N171.NameVal171Mixin, L138d.Loop138dEars):
    """Loop138dEars + the name-shaped-value guard (outermost, super-first)."""

    name = "loop171-nameval"


class Loop171AgentLoop(N171.NameVal171Mixin, L138d.Loop138dAgentLoop):
    """Loop138dAgentLoop + the name-shaped-value guard on _act.

    __init__/_save/turn() are inherited verbatim (they never name the ears
    class); build_agent171 passes the Loop171Ears instance in.
    """


DEFAULT_CONFIG171: dict = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
DEFAULT_CONFIG171["ears"]["stand_in"] = (
    "Loop171Ears (NameVal171Mixin + loop138d stack: 158 qform + 157 filler "
    "+ 156b smalltalk + 146d hearsay-exempt doubt + 150b clause-subject "
    "guard + 155 inverted frames (x135) + 153 reverse questions, "
    "outermost first)")
DEFAULT_CONFIG171["daemon"]["module"] = "Loop171Daemon (this file)"
DEFAULT_CONFIG171["notes"] = ("loop171: loop138d + exp-171 name-shaped-value "
                              "guard (description values on the 21 sealed "
                              "name keys write nothing + sealed clarify)")


def build_agent171(cfg: dict | None = None) -> Loop171AgentLoop:
    """Build the loop138d agent shape with the 171 guard swapped in."""
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    from fable_perf142_index import (  # noqa: E402 (read-only)
        patch_chain142, patch_loop121_teach)
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    cfg = dict(DEFAULT_CONFIG171, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    import fable_loop138b_agent as L138b  # noqa: E402 (read-only)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop171Ears(Loop96Ears(chain))
    loop = Loop171AgentLoop(
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
    loop.notes.append("sleep171: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop171: loop138d + exp-171 name-shaped-value guard "
                      "(description values on name keys: no write + sealed "
                      "clarify)")
    return loop


class Loop171Daemon(L138d.Loop138dDaemon):
    """Loop138dDaemon shape with the 171 agent inside.

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
        self.loop = build_agent171(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon171(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop171Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 171 guarded loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138d)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG171 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG171)
        out["thinker"]["module"] = "fable_webfix89_thinking"
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG171)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon171(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent171(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
