#!/usr/bin/env python3
"""Experiment 154b -- SECOND VALUES for multi-valued relations (Muse).

Base: loop138b (scripts/fable_loop138b_agent.py), subclassed read-only.
No loop138b file is edited; everything new lives here (+
scripts/fable_fix154b_multival.py + artifacts/fable-multival154b-20260922/).

STEP 1 ANSWER (contract check): the notebook CONTRACT already holds two
current values for one (subject, relation) with NO storage-rule change:
  * scripts/fable_notebook_contract.py:329-342 -- assert_fact refuses a
    second different taught value with CONFLICT ONLY when
    ``relation in self.functional``; otherwise it appends a new FACT and
    both rows stay active (current(), :244-255).
  * scripts/fable_notebook_contract.py:403-419 -- ask() on a
    non-functional relation with 2+ rows returns OK multi=True joined.
  * scripts/fable_notebook_contract.py:678-682 (c27) -- the lifecycle
    suite proves it (friend accumulates Tom + Ana).
What blocks second values on loop138b is NOT the contract but two upper
layers: scripts/fable_listening_m1.py:33 (FUNCTIONAL_BY_DEFAULT=True) with
_relation (:60-63) declaring EVERY unseen relation functional, and
scripts/fable_loop90_agent.py:153-170 (Bench73Stage._teach_action mapping
any second different value to act="correct", i.e. supersede). This file
overrides exactly those two behaviours for relations NOT in
SINGLE_VALUED_154 (scripts/fable_fix154_yesno.py:64-76, read-only);
single-valued relations keep today's change-prompt byte-identical.

THE ONE CHANGE (sealed forms):
  * multi-valued teach of a new different value ADDS:
    "Saved: Omar's sister is Lena. (I also have Priya.)"
  * single-hop multi ask lists oldest-first:
    "Omar's sister is Priya and Lena." (3+: "A, B and C")
  * 2-hop through a non-final multi hop with 2+ values clarifies:
    "Omar's sister is Priya and Lena. Which one do you mean?"
  * "No, Omar's sister is Lena, not Priya." retracts Priya only, adds
    Lena: "Saved: Omar's sister is Lena." (+ remainers parenthetical).
  * "Forget Omar's sister Priya." retracts that value only:
    "Forgotten: Omar's sister Priya."
  * whole-slot forget, yes/no confirm, and every single-valued turn are
    the untouched base path.
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
import fable_fix154b_multival as M154  # noqa: E402 (this exp's helpers)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


def _wrap_relation154b(loop) -> None:
    """Instance-level Listening._relation: single-valued relations stay
    functional (base behaviour); every other relation is declared
    non-functional so the contract accumulates values (contract :329-342).

    Additive: only the bound method on this loop's Listening instance is
    replaced; scripts/fable_listening_m1.py is untouched. On notebooks
    where a relation was already declared functional (append-only RELATION
    events), the earlier declaration sticks -- a documented limit.
    """
    listening = loop.listening
    nb = loop.nb

    def _relation154b(relation: str) -> None:
        known = {e["relation"] for e in nb.events if e["kind"] == "RELATION"}
        if relation not in known:
            nb.declare_relation(listening._eid("rel"), relation,
                                M154.is_single154b(relation))

    listening._relation = _relation154b  # type: ignore[method-assign]


class Loop154bEars(L138b.Loop138bEars):
    """Loop138bEars + two multi-only pre-scans (single-valued turns fall
    through to super().hear byte-identical)."""

    name = "loop154b-ears"

    def hear(self, turn: str) -> list[dict]:
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = M154.parse_correct_not154b(turn)
            if parsed is not None and not M154.is_single154b(parsed["relation"]):
                if nb.resolve(parsed["name"]).status == C.OK:
                    if V139b.screen_value_139b(parsed["new"]) is None and \
                            S150.screen_subject_150(parsed["name"])[0] == "store":
                        try:
                            self.last_stage, self.last_score = (
                                "loop154b-correct-not", 1.0)
                        except AttributeError:
                            pass
                        return [{"act": "correct_multi154b",
                                 "name": parsed["name"],
                                 "relation": parsed["relation"],
                                 "rel_key": parsed["relation"],
                                 "new": parsed["new"], "old": parsed["old"],
                                 "raw": turn}]
            forgotten = M154.parse_forget_one154b(turn, nb)
            if forgotten is not None:
                try:
                    self.last_stage, self.last_score = (
                        "loop154b-forget-one", 1.0)
                except AttributeError:
                    pass
                return [{"act": "forget_one154b",
                         "name": forgotten["name"],
                         "relation": forgotten["relation"],
                         "rel_key": forgotten["relation"],
                         "value": forgotten["value"],
                         "entity_id": forgotten["entity_id"],
                         "raw": turn}]
        return super().hear(turn)


class Loop154bAgentLoop(L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop with the 154b multi-valued teach/ask rules.

    turn() is inherited VERBATIM (L2 router + Self99 live answers)."""

    # -- custom actions -------------------------------------------------
    def _act_correct_multi154b(self, action: dict) -> dict:
        nb = self.nb
        name, key = action["name"], action["rel_key"]
        new, old = action["new"], action["old"]
        resolved = nb.resolve(name)
        if resolved.status != C.OK:
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": resolved.say()}
        eid = resolved.detail["entity_id"]
        subject = nb.entities[eid]
        owner = f"{subject}'s {key}"
        arrow = "->" if key in A.PERSON_RELATIONS else "="
        before = len(nb.events)
        try:
            add_text = self.listening._teach(name, key, arrow, new, False)
        except C.LogCorrupt as exc:
            self.counters["clarifications"] += 1
            return {"kind": "clarify",
                    "text": ("I could NOT save that: the notebook reported "
                             f"a problem ({exc}).")}
        added = len(nb.events) > before
        if self.listening.pending is not None:
            # The add did not land cleanly (e.g. ambiguous value name):
            # report the doorway text, retract nothing.
            self.counters["writes"] += int(added)
            return {"kind": "write", "line": action.get("raw", ""),
                    "text": add_text, "wrote": added,
                    "pending": True}
        retracted = 0
        for row in M154.taught_current154b(nb, eid, key):
            if M154.display154b(nb, row["value"]) == old:
                nb.retract(self.listening._eid("forget"), "listening",
                           row["fact_id"], "Ben corrected")
                retracted += 1
        wrote = bool(added or retracted)
        self.counters["writes"] += int(wrote)
        if not added and not retracted:
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": "I already have that."}
        remainers = [v for v in M154.current_values154b(nb, eid, key)
                     if v != new]
        reply = f"Saved: {owner} is {new}."
        if remainers:
            reply += f" (I also have {M154.join_and154b(remainers)}.)"
        if not retracted:
            reply += f" (I didn't have {old}.)"
        return {"kind": "write", "line": action.get("raw", ""), "text": reply,
                "wrote": wrote, "pending": False}

    def _act_forget_one154b(self, action: dict) -> dict:
        nb = self.nb
        eid, key, value = (action["entity_id"], action["rel_key"],
                           action["value"])
        owner = f"{nb.entities[eid]}'s {key}"
        matches = [row for row in M154.taught_current154b(nb, eid, key)
                   if M154.display154b(nb, row["value"]) == value]
        if not matches:
            self.counters["clarifications"] += 1
            return {"kind": "clarify",
                    "text": f"I don't have {owner} {value}."}
        for row in matches:
            nb.retract(self.listening._eid("forget"), "listening",
                       row["fact_id"], "Ben asked")
        self.counters["writes"] += 1
        return {"kind": "write", "line": action.get("raw", ""),
                "text": f"Forgotten: {owner} {value}.", "wrote": True,
                "pending": False}

    # -- main override --------------------------------------------------
    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "correct_multi154b":
            return self._act_correct_multi154b(action)
        if isinstance(action, dict) and action.get("act") == "forget_one154b":
            return self._act_forget_one154b(action)
        if isinstance(action, dict) and action.get("act") in ("teach", "correct"):
            key = M154.relation_key154b(str(action.get("relation", "")))
            if not M154.is_single154b(key) and action.get("name") and action.get("value"):
                return self._act_multi_teach154b(action, key)
        record = super()._act(action)
        if (isinstance(action, dict) and action.get("act") == "ask"
                and isinstance(record, dict) and record.get("kind") == "answer"
                and record.get("status") == C.OK):
            return self._post_ask154b(action, record)
        return record

    def _act_multi_teach154b(self, action: dict, key: str) -> dict:
        """A new different value on a multi-valued relation ADDS (never a
        change-prompt); the reply names the values it now sits beside."""
        nb = self.nb
        incoming = str(action.get("value", ""))
        others: list[str] = []
        resolved = nb.resolve(str(action.get("name", "")))
        if resolved.status == C.OK:
            others = [v for v in M154.current_values154b(
                nb, resolved.detail["entity_id"], key) if v != incoming]
        action = dict(action, act="teach")
        record = super()._act(action)
        if (isinstance(record, dict) and bool(record.get("wrote"))
                and others and isinstance(record.get("text"), str)):
            record = dict(record)
            record["text"] = (record["text"]
                              + f" (I also have {M154.join_and154b(others)}.)")
        return record

    def _post_ask154b(self, action: dict, record: dict) -> dict:
        """Single-hop multi asks list oldest-first with 'and'; a non-final
        multi hop with 2+ values clarifies instead of chaining on."""
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
            values = M154.current_values154b(nb, entity_id, relations[0])
            if len(values) >= 2:
                record = dict(record)
                fields = dict(fields, answer=M154.join_and154b(values))
                record["fields"] = fields
            return record
        # Multi-hop: walk the non-final hops; the first multi-valued hop
        # with 2+ current values asks which one (never chains on).
        subject = entity_id
        for hop, rel in enumerate(relations[:-1]):
            values = M154.current_values154b(nb, subject, rel)
            if not M154.is_single154b(rel) and len(values) >= 2:
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


DEFAULT_CONFIG154B: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG154B["ears"]["stand_in"] = (
    "Loop154bEars (loop138b stack + multi-only correct-not/forget-one "
    "pre-scans; single-valued turns fall through byte-identical)")
DEFAULT_CONFIG154B["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (multi lists render through the base template)")
DEFAULT_CONFIG154B["daemon"]["module"] = "Loop154bDaemon (this file)"
DEFAULT_CONFIG154B["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent154b(cfg: dict | None = None) -> Loop154bAgentLoop:
    """Build the loop138b agent shape with the 154b multi-value rules."""
    cfg = dict(DEFAULT_CONFIG154B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop154bAgentLoop(
        state_dir, ears=Loop154bEars(Loop96Ears(chain)), mouth=mouth,
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
    _wrap_relation154b(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep154b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 138b)")
    loop.notes.append("multival154b: non-SINGLE_VALUED_154 relations are "
                      "non-functional (add, never change-prompt)")
    return loop


class Loop154bDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 154b agent inside (settle gate + atomic
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
        self.loop = build_agent154b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon154b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154b multi-value loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154B)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
