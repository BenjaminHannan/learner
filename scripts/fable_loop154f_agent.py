#!/usr/bin/env python3
"""Experiment 154f -- plain negation removes a taught value (Muse).

Base: loop154e (scripts/fable_loop154e_agent.py), subclassed read-only.
No loop154e / loop154c / loop154b / loop138b file is edited; everything
new lives here (+ scripts/fable_fix154f_negate.py +
artifacts/fable-negate154f-20260922/).

THE ONE CHANGE versus loop154e: a plain single-hop negation
"X's R is not Y." / "X's R isn't Y." where Y IS a current taught value
of (X, R) retracts exactly that value (notebook RETRACT event -- the
same event kind 154c's correct-not path uses via nb.retract()) and
replies one fixed sealed sentence:
  * remainers left:  "OK, Rana's language is not Hindi. I still have Urdu."
  * none left:       "OK, Kim's boss is not Lee. I don't have another
                      boss for Kim."
(single-valued relations included: taught facts only ever change by the
user's hand.) Where Y is NOT a current value: 0 writes and one fixed
reply "I don't have Hindi as Rana's language.". Unknown X falls
through to the base (the base's unknown-name reply). Questions,
multi-hop negations, correct-not / forget shapes and pretend/directive
prefixes never match the parser, so the base reply stays byte-identical.
Never an inference: asks still write nothing.
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

import fable_agent_loop as A  # noqa: E402 (Protocols + person set, read-only)
import fable_fix154b_multival as M154  # noqa: E402 (154b forms, read-only)
import fable_fix154e_allowlist as M154E  # noqa: E402 (allow-list, read-only)
import fable_fix154f_negate as N154F  # noqa: E402 (this exp's parser)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop154b_agent as L154b  # noqa: E402 (wrapped base, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (wrapped base, read-only)
import fable_loop154e_agent as L154e  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


class Loop154fEars(L154e.Loop154eEars):
    """Loop154eEars plus the plain-negation pre-scan.

    The negate shape ("X's R is not Y." / "X's R isn't Y.") never
    overlaps the 154e correct-not / forget-one shapes (different
    anchors), so scanning it first cannot divert any sealed 154e turn.
    Unknown names fall through to the base reply.
    """

    name = "loop154f-ears"

    def hear(self, turn: str) -> list[dict]:
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = N154F.parse_negate154f(turn)
            if parsed is not None:
                if nb.resolve(parsed["name"]).status == C.OK:
                    try:
                        self.last_stage, self.last_score = (
                            "loop154f-negate-one", 1.0)
                    except AttributeError:
                        pass
                    return [{"act": "negate_one154f",
                               "name": parsed["name"],
                               "relation": parsed["relation"],
                               "rel_key": parsed["relation"],
                               "value": parsed["value"],
                               "raw": turn}]
        return super().hear(turn)


class Loop154fAgentLoop(L154e.Loop154eAgentLoop):
    """Loop154eAgentLoop with the negate-one action added.

    turn() inherited VERBATIM. Every other action falls through to the
    154e stack byte-identical.
    """

    def _act_negate_one154f(self, action: dict) -> dict:
        nb = self.nb
        name, key, value = (action["name"], action["rel_key"],
                            action["value"])
        resolved = nb.resolve(name)
        if resolved.status != C.OK:
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": resolved.say()}
        eid = resolved.detail["entity_id"]
        subject = nb.entities[eid]
        owner = f"{subject}'s {key}"
        matches = [row for row in M154.taught_current154b(nb, eid, key)
                   if M154.display154b(nb, row["value"]) == value]
        if not matches:
            self.counters["clarifications"] += 1
            return {"kind": "clarify",
                    "text": f"I don't have {value} as {owner}."}
        for row in matches:
            nb.retract(self.listening._eid("forget"), "listening",
                       row["fact_id"], "Ben retracted")
        self.counters["writes"] += 1
        remainers = M154.current_values154b(nb, eid, key)
        if remainers:
            reply = (f"OK, {owner} is not {value}. "
                     f"I still have {M154.join_and154b(remainers)}.")
        else:
            reply = (f"OK, {owner} is not {value}. "
                     f"I don't have another {key} for {subject}.")
        return {"kind": "write", "line": action.get("raw", ""),
                "text": reply, "wrote": True, "pending": False}

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "negate_one154f":
            return self._act_negate_one154f(action)
        return super()._act(action)


DEFAULT_CONFIG154F: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG154F["ears"]["stand_in"] = (
    "Loop154fEars (loop154e stack + plain-negation removal; "
    "miss/unknown/question/multi-hop turns fall through byte-identical)")
DEFAULT_CONFIG154F["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (negation replies render as fixed text)")
DEFAULT_CONFIG154F["daemon"]["module"] = "Loop154fDaemon (this file)"
DEFAULT_CONFIG154F["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent154f(cfg: dict | None = None) -> Loop154fAgentLoop:
    """Build the loop138b agent shape with the 154f negate rules."""
    cfg = dict(DEFAULT_CONFIG154F, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop154fAgentLoop(
        state_dir, ears=Loop154fEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L138b.L90.build_thinker(loop.nb)
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
    L154e._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep154f: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 138b)")
    loop.notes.append("negate154f: plain single-hop negation retracts "
                      "exactly the named taught value (RETRACT event)")
    return loop


class Loop154fDaemon(L154e.Loop154eDaemon):
    """Loop154eDaemon shape with the 154f agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138b.D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent154f(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon154f(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154fDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154f negate loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154F to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154F)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154F)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154f(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154f(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
