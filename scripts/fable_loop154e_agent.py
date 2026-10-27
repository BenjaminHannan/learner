#!/usr/bin/env python3
"""Experiment 154e -- language joins the multi-valued allow-list (Muse).

Base: loop154c (scripts/fable_loop154c_agent.py), subclassed read-only.
No loop154c / loop154b / loop138b file is edited; everything new lives
here (+ scripts/fable_fix154e_allowlist.py +
artifacts/fable-lang154e-20260922/).

THE ONE CHANGE versus loop154c: the add-a-second-value path fires for
"language" as well as MULTI_VALUED_154C. Every other relation behaves
byte-identically to loop154c: allow-listed keys take the sealed 154b
forms (add parenthetical, oldest-first and-join ask, mid-chain clarify,
correct-not, forget-one-value); deny-listed keys (citizenship, city,
boss, ...) take the loop138b change-prompt path.
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
import fable_fix154e_allowlist as M154E  # noqa: E402 (this exp's allow-list)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop154b_agent as L154b  # noqa: E402 (wrapped base, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


def _wrap_relation154e(loop) -> None:
    """Instance-level Listening._relation: allow-listed keys (154c set +
    language) are non-functional; everything else functional (base)."""
    listening = loop.listening
    nb = loop.nb

    def _relation154e(relation: str) -> None:
        known = {e["relation"] for e in nb.events if e["kind"] == "RELATION"}
        if relation not in known:
            nb.declare_relation(listening._eid("rel"), relation,
                                not M154E.is_multi154e(relation))

    listening._relation = _relation154e  # type: ignore[method-assign]


class Loop154eEars(L154c.Loop154cEars):
    """Loop154cEars with the gate widened to is_multi154e (language added).

    Correct-not / forget-one-value shapes on language take the 154b path;
    every other turn -- including those shapes on citizenship/city/boss --
    falls through to Loop138bEars.hear byte-identical (never via
    Loop154bEars.hear).
    """

    name = "loop154e-ears"

    def hear(self, turn: str) -> list[dict]:
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = M154.parse_correct_not154b(turn)
            if parsed is not None and M154E.is_multi154e(parsed["relation"]):
                if nb.resolve(parsed["name"]).status == C.OK:
                    if V139b.screen_value_139b(parsed["new"]) is None and \
                            S150.screen_subject_150(parsed["name"])[0] == "store":
                        try:
                            self.last_stage, self.last_score = (
                                "loop154e-correct-not", 1.0)
                        except AttributeError:
                            pass
                        return [{"act": "correct_multi154b",
                                  "name": parsed["name"],
                                  "relation": parsed["relation"],
                                  "rel_key": parsed["relation"],
                                  "new": parsed["new"], "old": parsed["old"],
                                  "raw": turn}]
            forgotten = M154.parse_forget_one154b(turn, nb)
            if forgotten is not None and \
                    M154E.is_multi154e(forgotten["relation"]):
                try:
                    self.last_stage, self.last_score = (
                        "loop154e-forget-one", 1.0)
                except AttributeError:
                    pass
                return [{"act": "forget_one154b",
                          "name": forgotten["name"],
                          "relation": forgotten["relation"],
                          "rel_key": forgotten["relation"],
                          "value": forgotten["value"],
                          "entity_id": forgotten["entity_id"],
                          "raw": turn}]
        return L138b.Loop138bEars.hear(self, turn)


class Loop154eAgentLoop(L154c.Loop154cAgentLoop):
    """Loop154cAgentLoop with the multi gate widened to is_multi154e.

    turn() inherited VERBATIM. _act_correct_multi154b /
    _act_forget_one154b / _act_multi_teach154b inherited VERBATIM from
    154b (they only run for allow-listed keys, which the ears gate).
    """

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "correct_multi154b":
            return self._act_correct_multi154b(action)
        if isinstance(action, dict) and action.get("act") == "forget_one154b":
            return self._act_forget_one154b(action)
        if isinstance(action, dict) and action.get("act") in ("teach", "correct"):
            key = M154.relation_key154b(str(action.get("relation", "")))
            if M154E.is_multi154e(key) and action.get("name") and \
                    action.get("value"):
                return self._act_multi_teach154b(action, key)
            return L138b.Loop138bAgentLoop._act(self, action)
        if isinstance(action, dict) and action.get("act") == "ask":
            record = L138b.Loop138bAgentLoop._act(self, action)
            if (isinstance(record, dict) and record.get("kind") == "answer"
                    and record.get("status") == C.OK):
                return self._post_ask154e(action, record)
            return record
        return L138b.Loop138bAgentLoop._act(self, action)

    def _post_ask154e(self, action: dict, record: dict) -> dict:
        """154c's _post_ask154c with the gate widened to is_multi154e."""
        nb = self.nb
        relations = [M154.relation_key154b(str(r))
                     for r in (action.get("relations") or [])]
        fields = dict(record.get("fields") or {})
        if not fields.get("multi"):
            return record
        name = str(action.get("name", ""))
        entity_id = action.get("entity_id")
        if entity_id is None and name:
            resolved = nb.resolve(name)
            if resolved.status != C.OK:
                return record
            entity_id = resolved.detail["entity_id"]
        if entity_id is None or entity_id not in nb.entities:
            return record
        if len(relations) == 1:
            if not M154E.is_multi154e(relations[0]):
                return record
            values = M154.current_values154b(nb, entity_id, relations[0])
            if len(values) >= 2:
                record = dict(record)
                fields = dict(fields, answer=M154.join_and154b(values))
                record["fields"] = fields
            return record
        subject = entity_id
        for hop, rel in enumerate(relations[:-1]):
            values = M154.current_values154b(nb, subject, rel)
            if M154E.is_multi154e(rel) and len(values) >= 2:
                owner_bits = [nb.entities[entity_id]] + [
                    r.replace("_", " ") for r in
                    (action.get("relations") or [])[:hop + 1]]
                owner = "'s ".join(owner_bits)
                self.counters["answers"] -= 1
                self.counters["clarifications"] += 1
                return {"kind": "clarify",
                        "text": (f"{owner} is {M154.join_and154b(values)}. "
                                  "Which one do you mean?")}
            rows = M154.taught_current154b(nb, subject, rel)
            if len(rows) == 1 and "entity" in rows[0]["value"]:
                subject = rows[0]["value"]["entity"]
            else:
                break
        return record


DEFAULT_CONFIG154E: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG154E["ears"]["stand_in"] = (
    "Loop154eEars (loop154c stack + language on the allow-list; "
    "deny-listed turns fall through to the loop138b path byte-identical)")
DEFAULT_CONFIG154E["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (multi lists render through the base template)")
DEFAULT_CONFIG154E["daemon"]["module"] = "Loop154eDaemon (this file)"
DEFAULT_CONFIG154E["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent154e(cfg: dict | None = None) -> Loop154eAgentLoop:
    """Build the loop138b agent shape with the 154e allow-list rules."""
    cfg = dict(DEFAULT_CONFIG154E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop154eAgentLoop(
        state_dir, ears=Loop154eEars(Loop96Ears(chain)), mouth=mouth,
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
    _wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep154e: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 138b)")
    loop.notes.append("multival154e: MULTI_VALUED_154C + language are "
                      "non-functional (add, never change-prompt)")
    return loop


class Loop154eDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 154e agent inside."""

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
        self.loop = build_agent154e(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon154e(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154e language-multi loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154E)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154e(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
