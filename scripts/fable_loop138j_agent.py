#!/usr/bin/env python3
"""Experiment 138j -- MERGE LAYER C onto loop138i (Muse).

loop138j = loop138i + TEN director-verified pieces ported read-only as
mixins. New files only; no existing file edited. Loop155 stays OUT (no
155 class in the MRO, no fable_loop155* module imported -- verified by
the M1 driver check).

PORTED (each verified by the director; rule bodies imported read-only;
port plan: design/v3/30-modes/138j-merge-layer-c-muse.md):

(1) 180b silent case-insensitive known-name match (built on 138h):
    L180B.Case180bMixin (scripts/fable_loop180b_agent.py:223) stacked
    OUTERMOST ears + the 180b display pass
    (Loop180bAgentLoop._listening_tick, :253) as Disp180bTickMixin in
    THIS file (outermost tick; calls L180B helpers read-only).
(2) 193 missing-apostrophe possessives (built on 138h):
    F193.Apos193Mixin (scripts/fable_fix193_apos.py:210), ears #2.
(3) 164b "Tell me about Kim." (built on 138h): L164B.About164bMixin
    (scripts/fable_loop164b_agent.py:154) ears #3 + the 164b USER safety
    net (Loop164bAgentLoop._listening_tick, :221) as About164bTickMixin
    in THIS file (calls L164B helpers read-only).
(4) 189 + 189b repeat requests (built on 138g / 189): turn-level. ONE
    check with L189B.is_repeat189b (scripts/fable_loop189b_agent.py:137,
    a strict superset of the 189 closed list) outermost in turn();
    echo/no-prev bookkeeping mirrors Loop189bAgentLoop.turn (:184).
(5) 190 + 190b reverse questions (built on 138g / 190):
    L190B.Reverse190bMixin (scripts/fable_loop190b_agent.py:61) outside
    R190.Reverse190Mixin (scripts/fable_fix190_reverse.py:207), ears
    #4/#5 (both super-first; fire only on all-clarify).
(6) 187b self questions (built on 138g via the 187 agent): turn-level
    gate. turn() is the 138g body verbatim (L134 path + logging +
    route127/decline) with the single inserted classify_self187 step
    (scripts/fable_loop187_agent.py:135) on the notebook-missed path,
    answers via L187.self187_answer (:165); plus 138h's raw-USER
    backstop. No new ears/_act.
(7) 192 corrections say what they replaced (built on 167e):
    F192.CorrectReply192Mixin
    (scripts/fable_fix192_correctreply.py:176) on the loop tick (inside
    the 164b tick, outside the 138i chain). Reply-only.
(8) 154f plain negation (built on 154e): Negate154fEarsMixin.hear in
    THIS file = Loop154fEars.hear
    (scripts/fable_loop154f_agent.py:62) + Negate154fActMixin._act in
    THIS file = Loop154fAgentLoop._act/_act_negate_one154f (:89, :120).
    Ears #6; _act outside the 138i multi.
(9) 154g No/Actually/Correction on multi-valued relations (built on
    154e): Replace154gEarsMixin in THIS file = Loop154gEars.hear +
    _divert_bare_correction154g (scripts/fable_loop154g_agent.py:74,
    :99) + Replace154gActMixin._act in THIS file = Loop154gAgentLoop
    ._act (:211) with ONE directed change: _act_replace154g emits 192's
    Updated template (director decision) instead of 154g-own Saved
    ("Updated: {S}'s {R} is {N} (it was {O})."); mechanics
    (teach+retract, ask flow, stored facts) are 154g-own identical.
    Ears #7; _act outside the 138i multi.
(10) 188 statement-shaped fallback (built on 138g): turn-level swap
    applied LAST to the final reply (byte-equality gate:
    reply == QUESTION_FALLBACK188 and is_statement_shaped188, exactly
    scripts/fable_loop188_agent.py:137-147). Fires only when nothing
    else parses. 0 writes by construction.

Ears order (outermost first):
  Case180b > Apos193 > About164b > Reverse190b > Reverse190 >
  Negate154f > Replace154g > Loop138iEars.
Preserves every sealed relative order (190b>190; 189b>189 by grammar
superset; 154f/154g prescans outside the 154e-owned chain).
Loop _act: Replace154g + Negate154f > 138i chain (154e-multi > 171b >
171 > 173-namecheck > 138g tail chain). _listening_tick (outside-in):
180b display > 164b safety > CorrectReply192 > 154d yes/no peek (138i)
> 138h 173/166/166c rendering. turn(): 189b repeat check > 138g body +
187 gate + 138h scrub > 188 swap.
Reasoner/notebook/sleep/daemon: 138i unchanged (Reasoner138d,
IndexedLoopNotebook, sleep145 retrofit, settle + exactly-once daemon
with idle_seconds). 170 index installed once at import unless
FABLE138J_INDEX=off (the G4 off-arm).

KNOWN OVERLAP (predicted before running; M1 lists case by case):
  154g one-value replaces + post-answer confirmations move reply-only
  Saved->Updated (director wording; stored facts 154g-own identical).
  192's own tick never fires on 154g replaces (multi keys set no
  `supersedes`; the Updated line matches no Saved guard).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138j_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138j-20260922/loop138j-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_fix139b_valueguard as V139B  # noqa: E402 (154g value screen)
import fable_fix150_subjectguard as S150  # noqa: E402 (154g subject screen)
import fable_fix154b_multival as M154  # noqa: E402 (154b forms, read-only)
import fable_fix154e_allowlist as M154E  # noqa: E402 (154e gate, read-only)
import fable_fix154f_negate as N154F  # noqa: E402 (154f parser, read-only)
import fable_fix154g_nocorrect as M154G  # noqa: E402 (154g helpers, read-only)
import fable_fix166_me as M166  # noqa: E402 (USER_KEY + scrub, read-only)
import fable_fix168_ground as G168  # noqa: E402 (187 cando, read-only)
import fable_fix190_reverse as R190  # noqa: E402 (190 mixin, read-only)
import fable_fix192_correctreply as F192  # noqa: E402 (192 mixin, read-only)
import fable_fix193_apos as F193  # noqa: E402 (193 mixin, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (wrapped stack, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped stack, read-only)
import fable_loop164b_agent as L164B  # noqa: E402 (164b mixin, read-only)
import fable_loop180b_agent as L180B  # noqa: E402 (180b mixin, read-only)
import fable_loop187_agent as L187  # noqa: E402 (187 gate, read-only)
import fable_loop188_agent as L188  # noqa: E402 (188 swap, read-only)
import fable_loop189_agent as L189  # noqa: E402 (189 prev key, read-only)
import fable_loop189b_agent as L189B  # noqa: E402 (189b grammar, read-only)
import fable_loop190_agent as L190  # noqa: E402 (190 stack, read-only)
import fable_loop190b_agent as L190B  # noqa: E402 (190b mixin, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop96_agent as L96  # noqa: E402 (inner chain ears, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_self105 as S105  # noqa: E402 (decline text, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_fix170_compose import install_index170  # noqa: E402 (170, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b/loop138d use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b/loop138d set; no file edited).
A._APOS = L134._APOS_SHOUTED_134

# 170 speed index: installed once at import (same pattern as
# scripts/fable_loop170_agent.py:38-40). FABLE138J_INDEX=off skips it
# (the G4 off-arm runs in a separate process with this set).
if os.environ.get("FABLE138J_INDEX", "on") != "off":
    install_index170()


def _norm(text: object) -> str:
    return " ".join(str(text).split())


# ------------------------- the 154f port (ears prescan, this file)
class Negate154fEarsMixin:
    """154f plain-negation pre-scan (this file) =
    Loop154fEars.hear (scripts/fable_loop154f_agent.py:62): known-name
    "X's R is not Y." claims act negate_one154f; everything else falls
    through to super().hear() untouched.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            parsed = N154F.parse_negate154f(turn)
            if parsed is not None:
                if nb.resolve(parsed["name"]).status == C.OK:
                    try:
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop138j-negate-one", 1.0)
                    except AttributeError:
                        pass
                    return [{"act": "negate_one154f",
                             "name": parsed["name"],
                             "relation": parsed["relation"],
                             "rel_key": parsed["relation"],
                             "value": parsed["value"],
                             "raw": turn}]
        return super().hear(turn)  # type: ignore[misc]


# ------------------------- the 154g port (ears divert, this file)
class Replace154gEarsMixin:
    """154g bare-correction divert (this file) = Loop154gEars.hear +
    _divert_bare_correction154g
    (scripts/fable_loop154g_agent.py:74, :99): a pending replace-question
    is answered/cancelled here; everything 138i owns runs first via
    super().hear(); a bare "<prefix> X's R is Y." turn the base mapped
    to teach/correct on a multi-valued key is diverted to the replace
    path (one value), the fixed question (2+ values), or left alone.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        pending = getattr(self, "pending_replace154g", None)
        if isinstance(pending, dict):
            if turn == pending.get("ask_turn"):
                # Re-hear of the very turn that issued the question: the
                # 154d yes/no peek (inside the 138i tick) re-runs
                # ears.hear() on the same text after the real hear. A
                # naive cancel here would destroy the just-issued
                # question, so replay the ask idempotently instead. A
                # real next turn always differs in text and takes the
                # match/cancel path below; retyping the ask verbatim
                # re-asks with pending kept, exactly like loop154g-own
                # (whose divert re-fires on the same text).
                return [{"act": "ask_replace154g",
                         "name": pending["name"],
                         "relation": pending["rel_surface"],
                         "rel_key": pending["key"],
                         "new": pending["new"],
                         "candidates": list(pending.get("candidates", [])),
                         "raw": turn}]
            hit = M154G.match_single_candidate154g(
                turn, list(pending.get("candidates", [])))
            if hit is not None:
                try:
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop138j-replace-answer", 1.0)
                except AttributeError:
                    pass
                # NOTE: the pending answer is NOT consumed here. The
                # 154d yes/no peek (inside the 138i tick) re-runs
                # ears.hear() on the same text BEFORE the real hear,
                # and consuming here would let the peek steal the
                # answer (its action is discarded). The consume happens
                # in _act_replace138j, which runs exactly once per real
                # turn. A re-heard answer replays the same replace_one
                # action idempotently.
                return [{"act": "replace_one154g",
                         "name": pending["name"],
                         "relation": pending["rel_surface"],
                         "rel_key": pending["key"],
                         "new": pending["new"], "old": hit,
                         "raw": turn}]
            # Any other next turn cancels (0 writes here) and is
            # processed normally below (it may open a fresh question).
            self.pending_replace154g = None
        actions = super().hear(turn)  # type: ignore[misc]
        diverted = self._divert_bare_correction138j(turn, actions)  # type: ignore[attr-defined]
        return diverted if diverted is not None else actions

    def _divert_bare_correction138j(  # type: ignore[no-redef]
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
            if str(base_triple.get("name", "")) != parsed["name"]:
                return None
            if M154G.relation_key154g(
                    str(base_triple.get("relation", ""))) != parsed["rel_key"]:
                return None
            if str(base_triple.get("value", "")) != parsed["value"]:
                return None
        if V139B.screen_value_139b(parsed["value"]) is not None:
            return None
        if S150.screen_subject_150(parsed["name"])[0] != "store":
            return None
        key = parsed["rel_key"]
        if nb.resolve(parsed["name"]).status != C.OK:
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
            if not is_correction_colon:
                return None
            return [{"act": "teach", "name": parsed["name"],
                     "relation": parsed["relation"],
                     "value": parsed["value"],
                     "is_person": key in A.PERSON_RELATIONS}]
        if len(values) == 1 and parsed["value"] == values[0]:
            try:
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop138j-repeat", 1.0)
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
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop138j-correct-single", 1.0)
            except AttributeError:
                pass
            return [{"act": "correct_single154g",
                     "name": parsed["name"],
                     "relation": parsed["relation"],
                     "rel_key": key,
                     "new": parsed["value"], "old": values[0],
                     "raw": turn}]
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                "loop138j-replace-ask", 1.0)
        except AttributeError:
            pass
        self.pending_replace154g = {
            "name": parsed["name"], "entity_id": eid, "key": key,
            "rel_surface": parsed["relation"], "new": parsed["value"],
            "candidates": list(values), "ask_turn": turn}
        return [{"act": "ask_replace154g",
                 "name": parsed["name"],
                 "relation": parsed["relation"],
                 "rel_key": key,
                 "new": parsed["value"],
                 "candidates": list(values),
                 "raw": turn}]


# ------------------------------------------------- ears: merge layer C
class Loop138jEars(L180B.Case180bMixin, F193.Apos193Mixin,
                   L164B.About164bMixin, L190B.Reverse190bMixin,
                   R190.Reverse190Mixin, Negate154fEarsMixin,
                   Replace154gEarsMixin, L138I.Loop138iEars):
    """Loop138iEars + layer-C stages, each cooperative: unclaimed turns
    fall through to super().hear() untouched. Sealed relative orders
    kept (180b > 193 normalise first; about before reverse; 190b > 190;
    154f/154g prescans outside the 154e-owned chain).
    """

    name = "loop138j-layer-c"


# ----------------- loop _act: 154f negate-one + 154g replace (this file)
class Negate154fActMixin:
    """154f _act (this file) = Loop154fAgentLoop._act/_act_negate_one154f
    (scripts/fable_loop154f_agent.py:120, :89): negate_one154f retracts
    exactly the named taught value; every other action falls through.
    """

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "negate_one154f":
            return self._act_negate_one138j(action)  # type: ignore[attr-defined]
        return super()._act(action)  # type: ignore[misc]

    def _act_negate_one138j(self, action: dict) -> dict:  # type: ignore[no-redef]
        nb = self.nb  # type: ignore[attr-defined]
        name, key, value = (action["name"], action["rel_key"],
                            action["value"])
        resolved = nb.resolve(name)
        if resolved.status != C.OK:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify", "text": resolved.say()}
        eid = resolved.detail["entity_id"]
        subject = nb.entities[eid]
        owner = f"{subject}'s {key}"
        matches = [row for row in M154.taught_current154b(nb, eid, key)
                   if M154.display154b(nb, row["value"]) == value]
        if not matches:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify",
                    "text": f"I don't have {value} as {owner}."}
        for row in matches:
            nb.retract(self.listening._eid("forget"), "listening",  # type: ignore[attr-defined]
                       row["fact_id"], "Ben retracted")
        self.counters["writes"] += 1  # type: ignore[attr-defined]
        remainers = M154.current_values154b(nb, eid, key)
        if remainers:
            reply = (f"OK, {owner} is not {value}. "
                     f"I still have {M154.join_and154b(remainers)}.")
        else:
            reply = (f"OK, {owner} is not {value}. "
                     f"I don't have another {key} for {subject}.")
        return {"kind": "write", "line": action.get("raw", ""),
                "text": reply, "wrote": True, "pending": False}


class Replace154gActMixin:
    """154g _act (this file) = Loop154gAgentLoop._act
    (scripts/fable_loop154g_agent.py:211) with ONE directed change:
    _act_replace154g emits 192's Updated template (director decision)
    instead of 154g-own Saved. Mechanics (teach + retract, ask flow,
    stored facts) are 154g-own identical.
    """

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "ask_replace154g":
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify",
                    "text": M154G.replace_question154g(
                        str(action.get("new", "")),
                        [str(v) for v in action.get("candidates", [])])}
        if isinstance(action, dict) and action.get("act") in (
                "correct_single154g", "replace_one154g"):
            return self._act_replace138j(action)  # type: ignore[attr-defined]
        return super()._act(action)  # type: ignore[misc]

    def _act_replace138j(self, action: dict) -> dict:  # type: ignore[no-redef]
        # Consume the pending answer HERE (not in hear): hear runs twice
        # per turn (154d peek first, then the real hear) and the peek's
        # action is discarded, so consuming in hear would let the peek
        # steal the answer.
        try:
            inner = getattr(self, "_inner138j_ears", None)
            if inner is not None:
                inner.pending_replace154g = None
        except Exception:  # noqa: BLE001
            pass
        nb = self.nb  # type: ignore[attr-defined]
        name, key = action["name"], action["rel_key"]
        new, old = action["new"], action["old"]
        resolved = nb.resolve(name)
        if resolved.status != C.OK:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify", "text": resolved.say()}
        eid = resolved.detail["entity_id"]
        if new == old:
            return {"kind": "write", "line": action.get("raw", ""),
                    "text": "I already have that.", "wrote": False,
                    "pending": False}
        subject = nb.entities[eid]
        arrow = "->" if key in A.PERSON_RELATIONS else "="
        before = len(nb.events)
        try:
            add_text = self.listening._teach(name, key, arrow, new, True)  # type: ignore[attr-defined]
        except C.LogCorrupt as exc:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify",
                    "text": ("I could NOT save that: the notebook reported "
                             f"a problem ({exc}).")}
        added = len(nb.events) > before
        if self.listening.pending is not None:  # type: ignore[attr-defined]
            self.counters["writes"] += int(added)  # type: ignore[attr-defined]
            return {"kind": "write", "line": action.get("raw", ""),
                    "text": add_text, "wrote": added,
                    "pending": True}
        retracted = 0
        for row in M154.taught_current154b(nb, eid, key):
            if M154.display154b(nb, row["value"]) == old:
                nb.retract(self.listening._eid("forget"), "listening",  # type: ignore[attr-defined]
                           row["fact_id"], "Ben corrected")
                retracted += 1
        wrote = bool(added or retracted)
        self.counters["writes"] += int(wrote)  # type: ignore[attr-defined]
        if not added and not retracted:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify", "text": "I already have that."}
        # DIRECTOR DECISION: 192's Updated template for every replacement
        # (relation in the answer path's spaced surface, 192's own rule).
        reply = (f"Updated: {subject}'s {str(key).replace('_', ' ')} "
                 f"is {new} (it was {old}).")
        return {"kind": "write", "line": action.get("raw", ""), "text": reply,
                "wrote": wrote, "pending": False}


# ------------- loop ticks: 180b display + 164b safety net (this file)
class Disp180bTickMixin:
    """180b display pass (this file) =
    Loop180bAgentLoop._listening_tick
    (scripts/fable_loop180b_agent.py:253): after the loop's own tick,
    resolve said lines to stored name casing (166c overrides honoured);
    pretend say-echo turns pass through byte-identical.
    """

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        try:
            pre_turn = self.inbox[0] if self.inbox else ""  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pre_turn = ""
        event = super()._listening_tick()  # type: ignore[misc]
        try:
            if L180B.is_say180b(pre_turn):
                return event  # pretend echo: bytes untouched
            try:
                ov = getattr(self, "_dc166c", None)
            except Exception:  # noqa: BLE001
                ov = None
            names = L180B.notebook_names180b(self.nb, ov)  # type: ignore[attr-defined]
            if not names:
                return event
            said = event.get("said", [])
            event["said"] = [L180B.resolve180b(line, names)
                             for line in said]
        except Exception:  # noqa: BLE001
            pass
        return event


class About164bTickMixin:
    """164b USER safety net (this file) =
    Loop164bAgentLoop._listening_tick
    (scripts/fable_loop164b_agent.py:221): the 138i tick runs verbatim
    (154d/173/166 rendering + 166c display pass); then the 138h USER
    template applies idempotently to about-claimed turns only.
    """

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        event = super()._listening_tick()  # type: ignore[misc]
        try:
            turn = event.get("detail", {}).get("turn", "")
        except Exception:  # noqa: BLE001
            return event
        try:
            if (L164B._match164b(turn or "") is not None
                    and any(M166.USER_KEY in str(line)
                            for line in event.get("said", []))):
                event["said"] = [L164B._render_user164b(str(line))
                                 for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


# ------------------------------------------- loop: 138i + layer C
class Loop138jAgentLoop(Disp180bTickMixin, About164bTickMixin,
                        F192.CorrectReply192Mixin, Negate154fActMixin,
                        Replace154gActMixin, L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + layer C.

    turn() = the 138g body verbatim (L134 notebook path + live-state
    logging + route127/decline) with three inserted stages: the 189b
    repeat check FIRST (before everything, incl. the Say-pretend rule
    inside the base path); the 187 self-paraphrase gate on the
    notebook-missed path (exactly where loop187 puts it); the 188
    statement-fallback swap applied LAST to the final reply
    (byte-equality gate: fires only when nothing else parsed).
    """

    def turn(self, text: str) -> list[str]:
        # [189b] THE ONE CHECK: outermost repeat-request stage (the 189
        # closed list is a strict subset of the 189b grammar, so one
        # check covers both pieces). Repeats echo _prev189 verbatim (or
        # the fixed line), write nothing, re-run nothing, never
        # overwrite _prev189.
        prev = getattr(self, "_prev189", None)
        if L189B.is_repeat189b(text):
            echo = prev if prev is not None else L189B.NO_PREV189B
            try:
                n = len(self.self_turn_log) + 1
                self.self_turn_log.append({
                    "n": n, "ben": text, "reply": echo, "records": [],
                    "statuses": [],
                    "stage": getattr(
                        getattr(self, "ears", None),
                        "last_stage", ""),
                    "score": getattr(
                        getattr(self, "ears", None), "last_score", 0.0),
                    "wrote": False, "via": "repeat189b",
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", ""),
                })
                self.self_mode_log.append({
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", "")})
            except Exception:
                pass
            return [echo]
        # [138g body verbatim] the L134 notebook path + live-state
        # logging (scripts/fable_loop138g_agent.py:304-322).
        before = set(self.nb.facts)
        said = L134.Loop134AgentLoop.turn(self, text)
        reply = " ".join(said) if said else "(nothing to say)"
        records = list(getattr(self, "last_records", []))
        n = len(self.self_turn_log) + 1
        after = set(self.nb.facts)
        for fid in after - before:
            self.self_origin[fid] = {"by": "Ben", "turn": n}
        self.self_turn_log.append({
            "n": n, "ben": text, "reply": reply, "records": records,
            "statuses": [r.get("status", r.get("kind")) for r in records],
            "stage": getattr(self.ears, "last_stage", ""),
            "score": getattr(self.ears, "last_score", 0.0),
            "wrote": len(after - before) > 0 or str(text).startswith("forget"),
            "via": "loop", "tick": self.tick, "mode": self.mode,
        })
        self.self_mode_log.append({"tick": self.tick, "mode": self.mode})
        self.last_routed = None
        if L138.notebook_missed(records):
            # [187] THE ONE CHANGE: self-paraphrase routing first
            # (scripts/fable_loop187_agent.py:205-216).
            kind187 = L187.classify_self187(text)
            if kind187 is not None:
                tag, ans = L187.self187_answer(self, kind187, text)
                entry = {"n": n, "text": text, "intent": tag,
                         "info": {"self187": kind187}, "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = tag
                self.self_turn_log[-1]["reply"] = ans
                self._prev189 = ans
                return [ans]
            intent, info = L138._route127(text)
            if intent != "DECLINE":
                # [168] grounded self answer (138g verbatim).
                ans = G168.grounded_self_answer(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                self._prev189 = ans
                return [ans]
            ans = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
            entry = {"n": n, "text": text, "intent": "DECLINE",
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans}
            self.self_routed.append(entry)
            self.last_routed = entry
            self.self_turn_log[-1]["routed"] = "DECLINE"
            self.self_turn_log[-1]["reply"] = ans
            # [188] statement-fallback swap (byte-equality gate: only
            # when the base served the generic question fallback on a
            # statement-shaped turn -- i.e. nothing else parsed).
            if (ans == L188.QUESTION_FALLBACK188
                    and L188.is_statement_shaped188(text)):
                self.self_turn_log[-1]["reply"] = \
                    L188.STATEMENT_FALLBACK188
                ans = L188.STATEMENT_FALLBACK188
                entry["answer"] = ans
            self._prev189 = ans
            return [ans]
        # Hit path: [138h] raw-USER backstop (verbatim).
        if (M166.USER_KEY not in str(text)
                and any(M166.USER_KEY in line for line in said)):
            said = [self._scrub_user_key(line) for line in said]
        # [188] swap on the hit path (no-op unless the base served the
        # generic question fallback on a statement-shaped turn).
        joined = " ".join(said).strip() if said else ""
        if (joined == L188.QUESTION_FALLBACK188
                and L188.is_statement_shaped188(text)):
            self.self_turn_log[-1]["reply"] = L188.STATEMENT_FALLBACK188
            said = [L188.STATEMENT_FALLBACK188]
        self._prev189 = " ".join(said) if said else "(nothing to say)"
        return said


DEFAULT_CONFIG138J: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG138J["ears"]["stand_in"] = (
    "Loop138jEars (loop138i stack + layer C outside-in: 180b silent "
    "known-name case match, 193 missing-apostrophe possessives, 164b "
    "read-only about-stage, 190b+190 reverse lookup, 154f plain "
    "negation, 154g bare-correction replace; 189b repeat + 187 self "
    "gate + 188 statement fallback at turn level; 192 Updated replies; "
    "167e label mouth; 154d yes/no tick; 170 index)")
DEFAULT_CONFIG138J["daemon"]["module"] = "Loop138jDaemon (this file)"
DEFAULT_CONFIG138J["self"] = dict(L138I.DEFAULT_CONFIG138I.get("self", {}))
DEFAULT_CONFIG138J["self"]["router"] = (
    "route127 (frozen novelty-guard router, scripts/fable_self127.py) "
    "+ classify_self187 paraphrase gate "
    "(scripts/fable_loop187_agent.py) on the notebook-missed path")


def build_agent138j(cfg: dict | None = None) -> Loop138jAgentLoop:
    """Build the loop138i agent shape with merge layer C stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG138J, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop138jEars(L96.Loop96Ears(chain))
    loop = Loop138jAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    # 142 teach/chain index patches on the INNER ears (before the sleep
    # wrap replaces loop.ears with its Sleep130Ears delegate).
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
    # L2 live-self state (Self99-shaped logs; the 168-style turn above
    # maintains them -- same shape loop138/loop138b keep).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # 189b previous-reply echo state (in-memory only, never persisted).
    loop._prev189 = None
    # 146d doubt store (notebook-side doubts146.json contract, shared by
    # the loop and the inner ears; attached BEFORE the sleep wrap).
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    # 166c display-case overrides (agent-layer only; notebook append-only).
    loop._dc166c = {}
    # Inner ears handle: _act_replace138j consumes the 154g pending
    # answer here (hear runs twice per turn: 154d peek, then real).
    loop._inner138j_ears = inner_ears
    # 154e relation functionality (instance-level Listening._relation
    # patch: allow-listed keys incl. language are non-functional).
    L138I._wrap_relation154e(loop)
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138j: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop138j: loop138i + merge layer C (180b case + "
                      "193 apos + 164b about + 189b repeat + 190b/190 "
                      "reverse + 187 self gate + 192 Updated + 154f "
                      "negate + 154g replace + 188 statefall; 155 stays "
                      "OUT)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138jDaemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 138j agent inside."""

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
        self.loop = build_agent138j(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138j(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138jDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138j merge layer C")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138J to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--mro", action="store_true",
                        help="print ears MRO + 155 module scan and exit")
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138J)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    if args.mro:
        names = [c.__name__ for c in Loop138jEars.__mro__]
        mods = sorted(m for m in sys.modules if "fable_loop155" in m)
        print(json.dumps({"ears_mro": names,
                          "has155class": any("155" in n for n in names),
                          "fable_loop155_modules": mods}, indent=1))
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138J)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138j(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138j(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
