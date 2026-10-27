#!/usr/bin/env python3
"""Experiment 168 -- SELF-GROUNDED canned replies (one change on loop138b).

Wraps the loop138 self path (route127 + Self99Agent.answer_self over live
loop state, inherited verbatim by loop138b) with a grounding gate. THE ONE
CHANGE (rule: a canned self reply may only state facts that exist in live
state right now):

  (a) any reply that names an entity or value is emitted ONLY if the
      notebook currently holds exactly the fact(s) it states -- otherwise
      the reply is replaced by the same sentence with the fact clause
      removed ("I do not have favourites." / "I have no opinions." /
      "I cannot predict." / "You never taught me their age, ...");
  (b) replies that depend on a web filing, sleep fact, proposal, taught
      rows, or a known entity check that it exists and otherwise say so
      plainly ("I haven't filed anything from the web.") instead of
      indexing an empty list / missing key.

Replies that name no fixed entity/value are returned byte-identical: the
wrapper calls the untouched base answerer and only rewrites the exact
guarded strings below. No existing file is edited; everything new lives
in this file (+ scripts/fable_loop168_agent.py).

Canned-reply census (scripts/fable_self99.py answer_self):
  names-fixed-fact: D1 favourite (Mira/colour/green), D7 opinion
      (Oslo/Paris), D4 prediction (Mira), D6 did-Tom-tell (Tom),
      D9 age (Mira), C5 who-taught (Oslo->Paris correction),
      C15 are-you-sure (Mira/Paris).
  depends-on-state: C1/C2 counts, C3/C4 first/last (crash when empty),
      C6/C7 web counts, C8/C9/C10 sleep, C11 forgotten (crash when empty),
      C12/C13/C14 corrections, C16 mode, C17 last turn, C18/C19/C20
      counters, C21 refusals, C22 unsure, C23 MISSING example, C26
      besides-me, C27 web row (CRASH when empty), C28 proposals,
      C29 rules, C30 mother-trail, D3 yesterday (turn count),
      D10 dreams (sleep counters).
  plain (byte-identical always): C7 rule text, C24/C25 capability sheet,
      D2 feelings, D5 why, D8 my-name, fallback decline.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_self99 as S99  # noqa: E402 (answer bodies, read-only)
import fable_self105 as S105  # noqa: E402 (canonical map, read-only)

# ------------------------------------------------------- exact base strings
FAVOURITE_BASE = ("I do not have favourites. I can only tell you Mira's "
                  "colour is green, because you taught me that.")
FAVOURITE_STRIPPED = "I do not have favourites."
OPINION_BASE = ("I have no opinions. Oslo and Paris are only values "
                "you taught me.")
OPINION_STRIPPED = "I have no opinions."
PREDICT_BASE = ("I cannot predict. Nothing you taught me says where "
                "Mira will live.")
PREDICT_STRIPPED = "I cannot predict."
TOM_PREFIX = "Tom has never spoken to me. All "
TOM_SUFFIX = " turns are yours."
AGE_BASE = "You never taught me Mira's age, so I do not know it."
AGE_STRIPPED = "You never taught me their age, so I do not know it."
C5_PREFIX = "You did, in turn "
WEB_EMPTY = "I haven't filed anything from the web."
FORGET_EMPTY = "I haven't forgotten anything you taught me."
TEACH_EMPTY = "You haven't taught me anything yet."
NO_RECORD = "I have no record of that, so I do not know it."
NO_RECORD_CITY = "I have no record of that city, so I cannot be sure."


# ------------------------------------------------------------- state checks
def _resolve_ok(nb, name: str):
    try:
        res = nb.resolve(name)
    except Exception:
        return None
    if getattr(res, "status", None) is not C.OK:
        return None
    try:
        return res.detail["entity_id"]
    except (KeyError, TypeError):
        return None


def _current_taught(nb, entity_id: str, relation: str):
    try:
        rows = nb.current(entity_id, relation)
    except Exception:
        return []
    return [f for f in rows
            if f.get("source") == "taught" and nb.active(f["fact_id"])]


def _show(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], "")
    return str(value.get("literal", ""))


def has_taught_value(nb, subject: str, relation: str, value: str) -> bool:
    """True iff the notebook currently holds subject/relation == value."""
    eid = _resolve_ok(nb, subject)
    if eid is None:
        return False
    for f in _current_taught(nb, eid, relation):
        if _show(nb, f["value"]).lower() == value.lower():
            return True
    return False


def taught_values(nb) -> set[str]:
    """Shown values of all active taught facts."""
    out = set()
    for fid, f in nb.facts.items():
        if f.get("source") == "taught" and nb.active(fid):
            out.add(_show(nb, f["value"]))
    return out


def entity_known(nb, name: str) -> bool:
    return _resolve_ok(nb, name) is not None


# ------------------------------------------------------- the grounding gate
def ground_reply(helper, intent: str, base: str) -> str:
    """Rewrite *only* the guarded exact strings; everything else identical."""
    nb = helper.nb
    snap_turns = None

    def turns() -> int:
        nonlocal snap_turns
        if snap_turns is None:
            try:
                snap_turns = int(helper.snapshot()["turns"])
            except Exception:
                snap_turns = len(helper.turn_log)
        return snap_turns

    # -- D1 favourite: keep only if Mira's colour is green right now --
    if intent == "D1" and base == FAVOURITE_BASE:
        if has_taught_value(nb, "Mira", "colour", "green"):
            return base
        return FAVOURITE_STRIPPED
    # -- D7 opinion: keep only if Oslo and Paris are both taught values --
    if intent == "D7" and base == OPINION_BASE:
        vals = taught_values(nb)
        if "Oslo" in vals and "Paris" in vals:
            return base
        return OPINION_STRIPPED
    # -- D4 prediction: keep only if Mira is known at all --
    if intent == "D4" and base == PREDICT_BASE:
        if entity_known(nb, "Mira"):
            return base
        return PREDICT_STRIPPED
    # -- D6 did-Tom-tell: keep only if Tom is known --
    if intent == "D6" and base.startswith(TOM_PREFIX) \
            and base.endswith(TOM_SUFFIX):
        if entity_known(nb, "Tom"):
            return base
        return (f"Nobody besides you has spoken to me. "
                f"All {turns()} turns are yours.")
    # -- D9 age --
    if intent == "D9" and base == AGE_BASE:
        if not entity_known(nb, "Mira"):
            return AGE_STRIPPED
        eid = _resolve_ok(nb, "Mira")
        ages = _current_taught(nb, eid, "age") if eid else []
        if ages:
            return f"Mira's age is {_show(nb, ages[0]['value'])}."
        return base
    # -- C5 who-taught-Mira-Paris: verify correction claim --
    if intent == "C5" and base.startswith(C5_PREFIX):
        eid = _resolve_ok(nb, "Mira")
        cur = _current_taught(nb, eid, "city") if eid else []
        cur_val = _show(nb, cur[0]["value"]) if cur else None
        if cur_val is None:
            return NO_RECORD
        if cur_val != "Paris":
            return f"You taught me Mira's city is {cur_val}, not Paris."
        olds = set()
        try:
            for o, n in nb.superseded.items():
                if cur and n == cur[0]["fact_id"]:
                    olds.add(_show(nb, nb.facts[o]["value"]))
        except Exception:
            pass
        if "Oslo" in olds:
            return base
        try:
            t = helper.origin.get(cur[0]["fact_id"], {}).get("turn", "?")
        except Exception:
            t = "?"
        return f"You did, in turn {t}."
    # -- C15 are-you-sure: verify Mira's city is known --
    if intent == "C15" and base.startswith(
            "Yes. You taught me Mira's city is "):
        eid = _resolve_ok(nb, "Mira")
        cur = _current_taught(nb, eid, "city") if eid else []
        if not cur:
            return NO_RECORD_CITY
        return base
    # -- C27 web row: plain when nothing filed --
    if intent == "C27":
        try:
            filings = helper.web_filings
        except AttributeError:
            filings = []
        if not filings:
            return WEB_EMPTY
        return base
    # -- C11 forgotten: plain when nothing forgotten --
    if intent == "C11" and base.startswith("I forgot: "):
        return base  # non-empty by construction; empty crashes below
    return base


def grounded_self_answer(loop, text: str, intent: str) -> str:
    """loop138's self_answer_from_live_state + grounding gate.

    Same Self99Agent facade over the loop's live state, same canonical
    question, then ground_reply. Crash net: any IndexError/KeyError/
    AttributeError inside the base answerer becomes a plain honest
    no-record reply (never an invented fact, never a crash).
    """
    helper = S99.Self99Agent.__new__(S99.Self99Agent)
    helper.loop = loop
    helper.nb = loop.nb
    helper.turn_log = loop.self_turn_log
    helper.mode_log = loop.self_mode_log
    helper.origin = loop.self_origin
    helper.web_filings = loop.self_web_filings
    helper.sleep_history = loop.self_sleep_history
    helper.forget_log = loop.self_forget_log
    helper.tau_hat = float(loop.parts90.get("tau_hat_used", 0.0))
    canonical = S105.CANONICAL[intent]
    try:
        base = helper.answer_self(canonical)
    except (IndexError, KeyError, AttributeError, AssertionError, TypeError):
        low = canonical.lower()
        if "web row come from" in low:
            return WEB_EMPTY
        if "forgotten" in low:
            return FORGET_EMPTY
        if ("last" in low and "teach" in low) or "first thing" in low:
            return TEACH_EMPTY
        if "are you sure" in low:
            return NO_RECORD_CITY
        return NO_RECORD
    # Empty-state crashes are caught above; replies that name no fixed
    # entity/value stay byte-identical (no other rewrite exists here).
    return ground_reply(helper, intent, base)
