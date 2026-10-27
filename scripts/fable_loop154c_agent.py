#!/usr/bin/env python3
"""Experiment 154c -- MULTI-VALUED relations as an ALLOW-LIST (Muse).

Base: loop154b (scripts/fable_loop154b_agent.py), subclassed read-only.
No loop154b / loop138b file is edited; everything new lives here (+
scripts/fable_fix154c_allowlist.py + artifacts/fable-multival154c-20260922/).

STEP 1 ANSWER: 154b's multi-valued test is
scripts/fable_fix154b_multival.py:39-41 (`is_single154b`: True iff the key
is in SINGLE_VALUED_154; the add-a-second-value path fires for every key
NOT in that table). 154c replaces that test with
scripts/fable_fix154c_allowlist.py `is_multi154c` (True iff the key is in
MULTI_VALUED_154C). The notebook contract already holds two current values
for non-functional relations (scripts/fable_notebook_contract.py:335,
:413-419, :678-682 -- see 154b's design doc, unchanged).

THE ONE CHANGE versus loop154b: the add-a-second-value path fires ONLY for
relations in MULTI_VALUED_154C (sister, brother, sibling, friend, child,
son, daughter, pet, dog, cat, cousin, grandchild + spacing variants, aunt,
uncle, colleague, coworker + spacing variants, notable_work). Every
relation NOT in the allow-list behaves byte-identically to loop138b
(change-prompt / replace); everything in it behaves byte-identically to
loop154b (sealed 154b reply forms: add parenthetical, oldest-first
and-join ask, mid-chain clarify, correct-not, forget-one-value).
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
import fable_fix154c_allowlist as M154C  # noqa: E402 (this exp's allow-list)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop154b_agent as L154b  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


def _wrap_relation154c(loop) -> None:
    """Instance-level Listening._relation: ONLY allow-listed relations are
    declared non-functional (contract accumulates values); every other
    relation -- single-valued AND deny-listed multi (citizenship, language,
    ...) -- is declared functional, exactly the base behaviour, so a
    re-teach replaces via the loop138b change-prompt.

    Additive: only the bound method on this loop's Listening instance is
    replaced; no other file is touched.
    """
    listening = loop.listening
    nb = loop.nb

    def _relation154c(relation: str) -> None:
        known = {e["relation"] for e in nb.events if e["kind"] == "RELATION"}
        if relation not in known:
            nb.declare_relation(listening._eid("rel"), relation,
                                not M154C.is_multi154c(relation))

    listening._relation = _relation154c  # type: ignore[method-assign]


class Loop154cEars(L154b.Loop154bEars):
    """Loop154bEars with the two pre-scans gated on the allow-list.

    Correct-not / forget-one-value shapes on allow-listed relations take
    the 154b path; every other turn -- including those shapes on
    deny-listed relations (citizenship, language, ...) -- falls through to
    Loop138bEars.hear byte-identical (never via Loop154bEars.hear, whose
    154b conditions would fire on deny-listed keys).
    """

    name = "loop154c-ears"

    def hear(self, turn: str) -> list[dict]:
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = M154.parse_correct_not154b(turn)
            if parsed is not None and M154C.is_multi154c(parsed["relation"]):
                if nb.resolve(parsed["name"]).status == C.OK:
                    if V139b.screen_value_139b(parsed["new"]) is None and \
                            S150.screen_subject_150(parsed["name"])[0] == "store":
                        try:
                            self.last_stage, self.last_score = (
                                "loop154c-correct-not", 1.0)
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
                    M154C.is_multi154c(forgotten["relation"]):
                try:
                    self.last_stage, self.last_score = (
                        "loop154c-forget-one", 1.0)
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


class Loop154cAgentLoop(L154b.Loop154bAgentLoop):
    """Loop154bAgentLoop with the multi path gated on MULTI_VALUED_154C.

    turn() is inherited VERBATIM (L2 router + Self99 live answers).
    _act_correct_multi154b / _act_forget_one154b / _act_multi_teach154b are
    inherited VERBATIM (they only ever run for allow-listed keys, because
    the ears only emit those actions for allow-listed keys)."""

    # -- main override --------------------------------------------------
    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "correct_multi154b":
            return self._act_correct_multi154b(action)
        if isinstance(action, dict) and action.get("act") == "forget_one154b":
            return self._act_forget_one154b(action)
        if isinstance(action, dict) and action.get("act") in ("teach", "correct"):
            key = M154.relation_key154b(str(action.get("relation", "")))
            if M154C.is_multi154c(key) and action.get("name") and \
                    action.get("value"):
                return self._act_multi_teach154b(action, key)
            return L138b.Loop138bAgentLoop._act(self, action)
        if isinstance(action, dict) and action.get("act") == "ask":
            record = L138b.Loop138bAgentLoop._act(self, action)
            if (isinstance(record, dict) and record.get("kind") == "answer"
                    and record.get("status") == C.OK):
                return self._post_ask154c(action, record)
            return record
        return L138b.Loop138bAgentLoop._act(self, action)

    def _post_ask154c(self, action: dict, record: dict) -> dict:
        """154b's _post_ask154b with the multi condition replaced: list /
        clarify ONLY through allow-listed hops. Deny-listed hops keep the
        base reply byte-identical."""
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
            if not M154C.is_multi154c(relations[0]):
                return record
            values = M154.current_values154b(nb, entity_id, relations[0])
            if len(values) >= 2:
                record = dict(record)
                fields = dict(fields, answer=M154.join_and154b(values))
                record["fields"] = fields
            return record
        # Multi-hop: walk the non-final hops; the first ALLOW-LISTED hop
        # with 2+ current values asks which one (never chains on).
        subject = entity_id
        for hop, rel in enumerate(relations[:-1]):
            values = M154.current_values154b(nb, subject, rel)
            if M154C.is_multi154c(rel) and len(values) >= 2:
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


DEFAULT_CONFIG154C: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG154C["ears"]["stand_in"] = (
    "Loop154cEars (loop154b stack + allow-list gate; deny-listed turns fall "
    "through to the loop138b path byte-identical)")
DEFAULT_CONFIG154C["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (multi lists render through the base template)")
DEFAULT_CONFIG154C["daemon"]["module"] = "Loop154cDaemon (this file)"
DEFAULT_CONFIG154C["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent154c(cfg: dict | None = None) -> Loop154cAgentLoop:
    """Build the loop138b agent shape with the 154c allow-list rules."""
    cfg = dict(DEFAULT_CONFIG154C, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop154cAgentLoop(
        state_dir, ears=Loop154cEars(Loop96Ears(chain)), mouth=mouth,
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
    _wrap_relation154c(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep154c: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 138b)")
    loop.notes.append("multival154c: ONLY MULTI_VALUED_154C relations are "
                      "non-functional (add, never change-prompt)")
    return loop


class Loop154cDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 154c agent inside (settle gate + atomic
    clients inherited unchanged). Name ends in Daemon / starts with Loop so
    the marks123 loader picks this class."""

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
        self.loop = build_agent154c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon154c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154c allow-list loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154C)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
