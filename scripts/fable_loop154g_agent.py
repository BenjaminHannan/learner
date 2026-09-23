#!/usr/bin/env python3
"""Experiment 154g -- "No," corrections REPLACE on multi-valued relations (Muse).

Base: loop154e (scripts/fable_loop154e_agent.py), subclassed read-only.
No loop154e / loop154c / loop154b / loop138b file is edited; everything
new lives here (+ scripts/fable_fix154g_nocorrect.py +
artifacts/fable-nocorrect154g-20260922/).

THE ONE CHANGE versus loop154e: a bare explicit correction
("<No,|Actually,|Correction:> X's R is Y." with R multi-valued per
is_multi154e) no longer ADDS a second value. Instead:
  * exactly ONE current value  -> replace it (single-valued correction
    mechanics: one taught FACT via Listening._teach(correction=True) plus
    a RETRACT of the replaced row; reply "Saved: X's R is Y.
    (It was Z.)" -- the base Saved correction style naming the old value).
  * TWO OR MORE current values -> 0 writes + the one fixed sealed
    question "Which one should Y replace: A or B?" (3+: "A, B or C").
    The next turn naming exactly one listed value replaces that value
    (same mechanics/reply); any other next turn cancels (0 writes) and
    is processed normally (it may itself open a new question).
  * NO current value            -> behave like a plain teach (the base
    path for "No,"/"Actually,"; an emulated plain teach for
    "Correction:", which the base stack misparses into a junk subject).
Plain teaches without a prefix keep the 154e add path byte-identical,
as do correct-not ("Y, not Z"), forget-one, repeats, asks, quotes and
every single-valued turn (they never enter the new path).

Director probe fixed: after "Rana's language is Hindi.", the turn "No,
Rana's language is Urdu." now replaces Hindi (ask shows only Urdu)
instead of replying "Saved: ... (I also have Hindi.)".
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
import fable_fix154b_multival as M154  # noqa: E402 (154b readers, read-only)
import fable_fix154e_allowlist as M154E  # noqa: E402 (allow-list, read-only)
import fable_fix154g_nocorrect as M154G  # noqa: E402 (this exp's helpers)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop154b_agent as L154b  # noqa: E402 (wrapped base, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (wrapped base, read-only)
import fable_loop154e_agent as L154e  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


class Loop154gEars(L154e.Loop154eEars):
    """Loop154eEars + the bare-correction divert (multi-valued only).

    hear(): (1) a pending replace-question is answered/cancelled here;
    (2) everything 154e owns (correct-not, forget-one, base) runs first
    via super().hear(); (3) a bare "<prefix> X's R is Y." turn the base
    mapped to teach/correct on a multi-valued key is diverted to the
    replace path (one value), the fixed question (2+ values), or left
    alone (0 values / repeat of the single value / unknown name /
    screened value/subject -- all byte-identical to loop154e).
    """

    name = "loop154g-ears"

    def hear(self, turn: str) -> list[dict]:
        pending = getattr(self, "pending_replace154g", None)
        if isinstance(pending, dict):
            hit = M154G.match_single_candidate154g(
                turn, list(pending.get("candidates", [])))
            if hit is not None:
                try:
                    self.last_stage, self.last_score = (
                        "loop154g-replace-answer", 1.0)
                except AttributeError:
                    pass
                self.pending_replace154g = None
                return [{"act": "replace_one154g",
                         "name": pending["name"],
                         "relation": pending["rel_surface"],
                         "rel_key": pending["key"],
                         "new": pending["new"], "old": hit,
                         "raw": turn}]
            # Any other next turn cancels (0 writes here) and is
            # processed normally below (it may open a fresh question).
            self.pending_replace154g = None
        actions = super().hear(turn)
        diverted = self._divert_bare_correction154g(turn, actions)
        return diverted if diverted is not None else actions

    def _divert_bare_correction154g(
            self, turn: str, actions: list[dict]) -> list[dict] | None:
        nb = getattr(self, "nb", None)
        if nb is None:
            return None
        if not (isinstance(actions, list) and len(actions) == 1
                and isinstance(actions[0], dict)
                and actions[0].get("act") in ("teach", "correct")):
            # "Correction:"-prefixed turns never parse as teach/correct
            # in the base stack (they grow a junk subject); still divert
            # them by parsing the raw turn directly.
            base_triple = None
        else:
            base_triple = actions[0]
        parsed = M154G.parse_bare_correction154g(turn)
        if parsed is None:
            return None
        is_correction_colon = parsed["prefix"].rstrip().endswith(":")
        if base_triple is not None and not is_correction_colon:
            # "No,"/"Actually," turns the base stack parses as the same
            # triple: only divert those (byte-safety). "Correction:"
            # turns are never parsed right by the base (junk subjects via
            # the 137 upgrade), so they divert on the raw parse alone.
            if str(base_triple.get("name", "")) != parsed["name"]:
                return None
            if M154G.relation_key154g(
                    str(base_triple.get("relation", ""))) != parsed["rel_key"]:
                return None
            if str(base_triple.get("value", "")) != parsed["value"]:
                return None
        if V139b.screen_value_139b(parsed["value"]) is not None:
            return None
        if S150.screen_subject_150(parsed["name"])[0] != "store":
            return None
        key = parsed["rel_key"]
        if nb.resolve(parsed["name"]).status != C.OK:
            # Unknown name: "No,"/"Actually," already behave like a plain
            # teach on the base path (person created, Saved). The base
            # stack misparses "Correction:" (junk subject), so emulate
            # the plain teach explicitly (spec: no current value acts
            # like a plain teach).
            if not is_correction_colon:
                return None
            return [{"act": "teach", "name": parsed["name"],
                     "relation": parsed["relation"],
                     "value": parsed["value"],
                     "is_person": key in A.PERSON_RELATIONS}]
        resolved = nb.resolve(parsed["name"])
        eid = resolved.detail["entity_id"]
        values = M154.current_values154b(nb, eid, key)
        if not values:
            # No current value: behave like a plain teach (base path for
            # "No,"/"Actually,"; emulated plain teach for "Correction:").
            if not is_correction_colon:
                return None
            return [{"act": "teach", "name": parsed["name"],
                     "relation": parsed["relation"],
                     "value": parsed["value"],
                     "is_person": key in A.PERSON_RELATIONS}]
        if len(values) == 1 and parsed["value"] == values[0]:
            # Prefix-repeat of the single value: "I already have that."
            # (base-identical for "No,"/"Actually,"; repaired for
            # "Correction:", which the base misparses).
            try:
                self.last_stage, self.last_score = (
                    "loop154g-repeat", 1.0)
            except AttributeError:
                pass
            return [{"act": "replace_one154g",
                     "name": parsed["name"],
                     "relation": parsed["relation"],
                     "rel_key": key,
                     "new": parsed["value"], "old": values[0],
                     "raw": turn}]
        if len(values) == 1:
            try:
                self.last_stage, self.last_score = (
                    "loop154g-correct-single", 1.0)
            except AttributeError:
                pass
            return [{"act": "correct_single154g",
                     "name": parsed["name"],
                     "relation": parsed["relation"],
                     "rel_key": key,
                     "new": parsed["value"], "old": values[0],
                     "raw": turn}]
        try:
            self.last_stage, self.last_score = (
                "loop154g-replace-ask", 1.0)
        except AttributeError:
            pass
        self.pending_replace154g = {
            "name": parsed["name"], "entity_id": eid, "key": key,
            "rel_surface": parsed["relation"], "new": parsed["value"],
            "candidates": list(values)}
        return [{"act": "ask_replace154g",
                 "name": parsed["name"],
                 "relation": parsed["relation"],
                 "rel_key": key,
                 "new": parsed["value"],
                 "candidates": list(values),
                 "raw": turn}]


class Loop154gAgentLoop(L154e.Loop154eAgentLoop):
    """Loop154eAgentLoop + the three replace actions.

    turn() inherited VERBATIM. Every other act falls through to the
    154e _act (multi add, correct-not, forget-one, single-valued
    change-prompt, asks) byte-identical.
    """

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") == "ask_replace154g":
            self.counters["clarifications"] += 1
            return {"kind": "clarify",
                    "text": M154G.replace_question154g(
                        str(action.get("new", "")),
                        [str(v) for v in action.get("candidates", [])])}
        if isinstance(action, dict) and action.get("act") in (
                "correct_single154g", "replace_one154g"):
            return self._act_replace154g(action)
        return super()._act(action)

    def _act_replace154g(self, action: dict) -> dict:
        """Replace one current multi value (one-value correction, or the
        pending answer naming one listed value).

        Mechanics mirror the base single-valued correction path: the new
        value is taught with correction=True (the exact
        Listening._teach call the base "correct" act makes), and the
        replaced row is retracted (the contract only sets `supersedes`
        on functional relations, so on a non-functional key the replace
        is one taught FACT plus one RETRACT -- the same two kinds the
        154b correct-not path writes; never a CONFLICT, never a pending
        confirm). Reply: the base Saved correction style naming the old
        value: "Saved: X's R is Y. (It was Z.)".
        """
        nb = self.nb
        name, key = action["name"], action["rel_key"]
        new, old = action["new"], action["old"]
        resolved = nb.resolve(name)
        if resolved.status != C.OK:
            self.counters["clarifications"] += 1
            return {"kind": "clarify", "text": resolved.say()}
        eid = resolved.detail["entity_id"]
        if new == old:
            return {"kind": "write", "line": action.get("raw", ""),
                    "text": "I already have that.", "wrote": False,
                    "pending": False}
        subject = nb.entities[eid]
        owner = f"{subject}'s {key}"
        arrow = "->" if key in A.PERSON_RELATIONS else "="
        before = len(nb.events)
        try:
            add_text = self.listening._teach(name, key, arrow, new, True)
        except C.LogCorrupt as exc:
            self.counters["clarifications"] += 1
            return {"kind": "clarify",
                    "text": ("I could NOT save that: the notebook reported "
                             f"a problem ({exc}).")}
        added = len(nb.events) > before
        if self.listening.pending is not None:
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
        reply = f"Saved: {owner} is {new}. (It was {old}.)"
        return {"kind": "write", "line": action.get("raw", ""), "text": reply,
                "wrote": wrote, "pending": False}


DEFAULT_CONFIG154G: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG154G["ears"]["stand_in"] = (
    "Loop154gEars (loop154e stack + bare-correction divert on multi-valued "
    "keys: 1 value replaces, 2+ ask one fixed question, 0 values fall "
    "through; every other turn falls through to the loop154e path "
    "byte-identical)")
DEFAULT_CONFIG154G["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (replace confirmations render through the "
    "base template)")
DEFAULT_CONFIG154G["daemon"]["module"] = "Loop154gDaemon (this file)"
DEFAULT_CONFIG154G["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent154g(cfg: dict | None = None) -> Loop154gAgentLoop:
    """Build the loop138b agent shape with the 154e allow-list + 154g
    bare-correction rules."""
    cfg = dict(DEFAULT_CONFIG154G, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop154gAgentLoop(
        state_dir, ears=Loop154gEars(Loop96Ears(chain)), mouth=mouth,
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
    loop.notes.append("sleep154g: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 138b)")
    loop.notes.append("multival154g: MULTI_VALUED_154C + language are "
                      "non-functional (add, never change-prompt)")
    loop.notes.append("nocorrect154g: bare No,/Actually,/Correction: "
                      "corrections on multi-valued keys REPLACE (1 value) "
                      "or ask one fixed question (2+ values)")
    return loop


class Loop154gDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 154g agent inside."""

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
        self.loop = build_agent154g(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon154g(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154gDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154g nocorrect loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154G to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154G)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154G)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154g(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154g(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
