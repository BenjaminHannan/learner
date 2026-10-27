#!/usr/bin/env python3
"""Experiment 139e -- loop139c + THE ONE CHANGE: relation-gated tail clarify.

Subclasses loop139c (no loop139c/139d file edited; 139d/139c code reused by
import only). Step-1 locations:
  139c's strip: scripts/fable_fix139c_tail.py:46 (strip_chat_tail),
    applied in scripts/fable_loop139c_agent.py:66 (ears hear) and :82
    (loop _act, before super()._act()).
  value extraction: scripts/fable_agent_loop.py:136 (FakeEars possessive
    path raw value span; loop138b wraps it with the exp-140 cleaner).
  139b value guard: scripts/fable_fix139b_valueguard.py:99
    (screen_value_139b), per-action at :118/:131.
  139d trigger+reply: scripts/fable_fix139d_tail.py (unknown_tail_split,
    clarify_text, CONNECTORS -- imported read-only, never redefined).

THE ONE CHANGE vs 139d: the same trigger and reply, but ONLY when the
teach/correct action's relation is in the closed listed set fixed in
scripts/fable_fix139e_tail.py (LISTED_RELATIONS: person-valued mother,
father, sister, brother, sibling, spouse, husband, wife, boss, friend,
teacher, coach, pet, dog; place-valued city, town, hometown/home_town,
country, birthplace/place_of_birth, school). Everything else is
byte-identical to loop139c.

Applied at TWO levels so every teach path is covered:
  * ears hear(): super().hear() (full 139c chain) then the 139e guard
    (teach/correct with unknown tails on listed relations become clarify);
  * loop _act(): 139c sanitize first, then the 139e relation-gated check;
    on trigger return {"kind": "clarify", ...} with no write (covers the
    inner-chain delegate path that bypasses ears).

turn() is inherited verbatim; no loop139c file is edited.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop139e_agent.py --daemon --dir DIR \\
    --config artifacts/fable-tail139e-20260922/loop139e-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_fix139c_tail as T139c  # noqa: E402 (139c strip runs first, read-only)
import fable_fix139e_tail as T139e  # noqa: E402 (THE ONE CHANGE, this exp)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop96_agent as L96  # noqa: E402 (ears wrap, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (base stack, read-only)
import fable_loop139c_agent as L139c  # noqa: E402 (wrapped base, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen reasoner/mouth)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper, read-only)
    HardGate46Sleeper)


class Loop139eEars(T139e.RelationGatedTailMixin, L139c.Loop139cEars):
    """Loop139cEars + relation-gated unknown-tail clarify on teaches."""

    name = "loop139e-tailclarify-gated"

    def hear(self, turn: str) -> list[dict]:
        actions = super().hear(turn)
        return T139e.guard_actions(actions)


class Loop139eMouth(L139c.Loop139cMouth):
    name = "loop139e-mouth"


class Loop139eAgentLoop(T139e.RelationGatedTailMixin, L139c.Loop139cAgentLoop):
    """Loop139cAgentLoop + relation-gated unknown-tail clarify.

    turn() is inherited VERBATIM through loop139c/loop138b from loop138
    (L2 router + Self99 live answers + decline rule unchanged).
    """

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            action = T139c.sanitize_action(action)
            msg = T139e.check_value(action.get("value", ""),
                                    action.get("relation", ""))
            if msg is not None:
                self.counters["clarifications"] += 1
                return {"kind": "clarify", "text": msg}
        return super()._act(action)


DEFAULT_CONFIG139E: dict = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
DEFAULT_CONFIG139E["ears"]["stand_in"] = (
    "Loop139eEars (loop139c + 139e relation-gated unknown-tail clarify "
    "after the 139c strip, listed relations fixed in "
    "scripts/fable_fix139e_tail.py)")
DEFAULT_CONFIG139E["mouth"]["stand_in"] = (
    "Loop139eMouth (Loop139cMouth unchanged)")
DEFAULT_CONFIG139E["daemon"]["module"] = "Loop139eDaemon (this file)"


def build_agent139e(cfg: dict | None = None) -> Loop139eAgentLoop:
    """Build the loop139c agent shape with the 139e gated clarify swapped in."""
    cfg = dict(DEFAULT_CONFIG139E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop139eMouth()
    reasoner = L148b.ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop139eAgentLoop(
        state_dir, ears=Loop139eEars(L96.Loop96Ears(chain)), mouth=mouth,
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
    loop.notes.append("sleep139e: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


class Loop139eDaemon(L139c.Loop139cDaemon):
    """Loop139cDaemon shape with the 139e agent inside (settle gate kept).

    process_file/settled_files/run are inherited unchanged from
    Loop139cDaemon (108 receipts + reconcile + 104-schema sleep logs, 141
    settle, tmp/dot skip). Name ends in Daemon / starts with Loop so the
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
        self.loop = build_agent139e(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def atomic_write_text(path: Path, text: str) -> None:
    return L138b.atomic_write_text(path, text)


def run_daemon139e(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop139eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 139e gated-clarify loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop139c)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG139E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG139E)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG139E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon139e(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent139e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
