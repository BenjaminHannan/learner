#!/usr/bin/env python3
"""Experiment 222 -- "IS A R OF" ONLY FOR ONE-OF-MANY PERSON RELATIONS.

THE ONE CHANGE (one gate on loop215, which wraps loop138i; both imported
read-only and never edited): the indefinite teach form "X is a/an R of
Y." is rewritten to "Y's R is X." only when R (canonical or alias) is a
person + multi entry of the relation table (see
scripts/fable_fix222_ofteachb.py). Every other indefinite R goes to the
unchanged base path exactly as on 138i. "The" teaches and the question
rewrite stay exactly as in 215.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop222_agent.py --daemon --dir DIR \\
    --config artifacts/fable-ofteachb222-20260922/loop222-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_fix222_ofteachb as F222  # noqa: E402 (the one gate)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_loop215_agent as L215  # noqa: E402 (wrapped fix, read-only)


class Loop222Ears(L215.Loop215Ears):
    """Loop215Ears + the 222 indefinite gate.

    Questions: exact 215 path. Teaches: when 215 would rewrite an
    indefinite ("a"/"an") form whose R is NOT a person+multi table entry,
    skip the 215 mixin and run the unchanged 138i ears instead.
    """

    name = "loop222-ofteachb"

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        text = " ".join(str(turn).split())
        if not text.rstrip().endswith("?"):
            try:
                gated = F222.must_take_base_path222(turn, nb)
            except Exception:
                gated = False
            if gated:
                try:
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop222-basepath", 1.0)
                except AttributeError:
                    pass
                return L138I.Loop138iEars.hear(self, turn)
        return super().hear(turn)


class Loop222AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG222: dict = copy.deepcopy(L215.DEFAULT_CONFIG215)
DEFAULT_CONFIG222["ears"]["stand_in"] = (
    "Loop222Ears (loop215 stack + 222 gate: indefinite 'X is a/an R of Y.' "
    "rewrites to \"Y's R is X.\" only when R is a person+multi entry of "
    "the relation table; every other R takes the unchanged 138i path; "
    "'The' forms and the question rewrite exactly as in 215)")
DEFAULT_CONFIG222["daemon"]["module"] = "Loop222Daemon (this file)"


def build_agent222(cfg: dict | None = None) -> Loop222AgentLoop:
    """Build the loop215 agent shape with the 222 gate stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG222, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop222Ears(Loop96Ears(chain))
    loop = Loop222AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    L138I.patch_chain142(chain)
    L138I.patch_loop121_teach(inner_ears)
    thinker, thinker_module = L138I.L90.build_thinker(loop.nb)
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
    store = L138I.D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop222: loop215 + gate (indefinite 'a/an R of' "
                      "rewrites only for person+multi table R; else 138i "
                      "path; 'The' forms and questions exactly as 215)")
    return loop


class Loop222Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 222 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138I.D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent222(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon222(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop222Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 222 ofteachb loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop215)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG222 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG222)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG222)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon222(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent222(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
