#!/usr/bin/env python3
"""Experiment 137c -- hypotheticals saved as facts (a WRONG-WRITE class).

Base agent: loop137b (`scripts/fable_loop137b_agent.py`,
`artifacts/fable-discourse137b-20260922/loop137b-config.json`).

Step-1 fact: loop137b strips "Suppose" at
`scripts/fable_loop137b_agent.py:125` (`rest = D137B.strip_first_token(...)`
inside `_upgrade137b`, lines 109-131; phone-fronted "?" strip at lines
163-178): "Suppose Kim's boss is Lee." re-parses as "Kim's boss is Lee."
and SAVES it (director probe 05:16). "Imagine Kim's boss is Lee." saves
too. "What if Kim's boss is Lee?" and "If Kim's boss is Lee then Lee is
busy." are already declined safely on loop137b.

THE ONE CHANGE: `Loop137cEars` subclasses loop137b's ears and checks
`fable_fix137c_hypo.is_hypothetical(turn)` FIRST, before any panel read
(before the unchanged loop137b pipeline runs). A hypothetical turn never
reaches any teach path: it returns a single clarify carrying the exact
sealed reply, so the normal `_act`/mouth path renders it verbatim with
zero writes, zero routing (the text holds no "didn't understand"), and
later questions answer only from real saved facts. Everything else falls
through to `super().hear()` byte-identical (137b "Btw./So/Hi." teaches,
"Say Tom's ..." teaches, bare-"If ..." declines, marker words later in
the sentence never match).

No loop137b file is edited; everything new lives in this file (+
`scripts/fable_fix137c_*.py`, `artifacts/fable-hypo137c-20260922/`,
`design/v3/30-modes/137c-hypo-muse.md`).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop137c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-hypo137c-20260922/loop137c-config.json
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
import fable_fix137c_hypo as H137C  # noqa: E402 (this exp: closed list)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only value source)
import fable_loop137b_agent as L137B  # noqa: E402 (wrapped base, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Same process-wide overrides as loop137b (no file edited).
WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134


class Loop137cEars(L137B.Loop137bEars):
    """Loop137bEars with THE ONE CHANGE: hypothetical openers never write.

    hear() checks the closed-list marker FIRST (before any panel read);
    hypothetical turns return one clarify with the exact sealed reply.
    All other turns run the unchanged loop137b pipeline byte-identical.
    """

    name = "loop137c-hypo"

    def hear(self, turn: str) -> list[dict]:
        if H137C.is_hypothetical(turn):
            try:
                self.last_stage, self.last_score = ("loop137c-hypo", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": H137C.HYPO_REPLY}]
        return super().hear(turn)


class Loop137cMouth(L137B.Loop137bMouth):
    """Loop137bMouth unchanged (mouth texts identical to loop137b)."""

    name = "loop137c-mouth"


class Loop137cAgentLoop(L137B.Loop137bAgentLoop):
    """Loop137bAgentLoop shape with the 137c ears (turn/_act inherited)."""

    pass


DEFAULT_CONFIG137C: dict = copy.deepcopy(L137B.DEFAULT_CONFIG137B)
DEFAULT_CONFIG137C["ears"]["stand_in"] = (
    "Loop137cEars (loop137b + 137c hypothetical guard: turn-initial "
    "closed-list markers suppose/supposing/imagine/pretend/pretend that/"
    "let's say/lets say/hypothetically/in theory/what if/say that, after "
    "optional ok/so/and fillers, never write and reply the exact pretend "
    "sentence; everything else byte-identical to loop137b)")
DEFAULT_CONFIG137C["mouth"]["stand_in"] = (
    "Loop137cMouth (Loop137bMouth unchanged)")
DEFAULT_CONFIG137C["daemon"]["module"] = "Loop137cDaemon (this file)"


def build_agent137c(cfg: dict | None = None) -> Loop137cAgentLoop:
    """Build the loop137b agent shape with the 137c ears swapped in."""
    cfg = dict(DEFAULT_CONFIG137C, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop137cMouth()
    from fable_loop148b_agent import (  # noqa: E402 (read-only wrap)
        ScreenStatusReasoner148b)
    reasoner = ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop137cAgentLoop(
        state_dir, ears=Loop137cEars(Loop96Ears(chain)), mouth=mouth,
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
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep137c: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


class Loop137cDaemon(L137B.Loop137bDaemon):
    """Loop137bDaemon shape with the 137c agent inside (settle inherited)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        self.cfg = dict(cfg or {})
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
        self.loop = build_agent137c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic-write client rule: write tmp in the same dir, then rename."""
    import os as _os
    tmp = Path(str(path) + ".tmp%d" % _os.getpid())
    tmp.write_text(text, encoding="utf-8")
    _os.replace(tmp, path)


def run_daemon137c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop137cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 137c hypo loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop137b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG137C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG137C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG137C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon137c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent137c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
