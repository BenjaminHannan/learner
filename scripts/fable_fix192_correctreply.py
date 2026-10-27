#!/usr/bin/env python3
"""Experiment 192 -- THE ONE CHANGE vs loop167e: corrections say what they replaced.

Director probe 09:49 on loop167e: after "Kim's boss is Sam.", both
"No, Kim's boss is Lee." and "Actually, Kim's boss is Lee." reply
"Saved: Kim's boss is Lee." -- the user is never told Sam was replaced;
the plain re-teach "Kim's boss is Lee." asks "I have Kim's boss as Sam.
Do you want me to change it to Lee?" (that question is kept).

THE ONE CHANGE (this file only; no 167e/167c/loop/agent-loop/contract/
listening file edited): reply text only, outermost. Whenever a turn
the USER marked as a correction -- an explicit correction form (No, /
Actually, / Correction: / Sorry-I-meant, verb twins included) or a yes
to the change question -- REPLACES an existing current value of a
single-valued relation (the turn's notebook write appended a FACT event
with `supersedes` set; both paths store with correction=True and
supersede only when the relation is functional / single-valued,
contract scripts/fable_notebook_contract.py:335-342), the Saved
confirmation is replaced by one fixed template naming both values:

    Updated: {Subject}'s {relation} is {New} (it was {Old}).

with the 167e relation surface (underscores spaced, the answer path's
own rule). Deliberately OUT of scope: silent bench73-stage
auto-corrects (a plain re-teach the template ears upgrade to
act=correct without any user correction marking) keep loop167e's
"Saved:" -- sealed harnesses judge those teach replies literally
(redteam143's teach_accepted takes only "Saved:"/"I already have
that."). Everything else is byte-identical to loop167e:
first-time teaches keep "Saved: ...", repeats keep "I already have
that.", a declined change keeps "Okay, I left it as it was.", the
change question itself is untouched, multi-valued additions never set
`supersedes` (the contract accumulates them) so they keep loop167e's
reply, and all non-write replies (answers, clarifies, MISSING_FACT,
Forgotten, hearsay refusals) never see a superseding FACT on their
turn, so they pass through untouched. Notebook events, stored facts,
keys, matching, and which reply is chosen are untouched: the rewrite
happens after the loop's own write, in _listening_tick post-processing,
and only touches the outgoing English strings.

Sealed template (exact): "Updated: Kim's boss is Lee (it was Sam)."
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop102_agent as L102  # noqa: E402 (F3 prefix rule, read-only)

# Listening may prefix any reply with its dropped-question note
# (scripts/fable_listening_m1.py:78).
_DROPPED = "(I dropped my earlier question.) "

# A 167e Saved confirmation (post-mouth: the relation slot is already
# spaced by the 167e label render, so it may contain spaces).
_SAVED_RE = re.compile(r"^Saved: (.+?)'s (.+) is (.+)\.$", re.DOTALL)

# An Updated confirmation produced by this experiment.
_UPDATED_RE = re.compile(
    r"^Updated: (.+?)'s (.+) is (.+) \(it was (.+)\)\.$", re.DOTALL)


def _is_explicit_correction_or_yes(rec: dict, turn: str) -> bool:
    """True for user-marked corrections and yes-to-change answers only.

    - Structured corrects come from the bench73 template stage (tagged
      loop121, or loop102 on the inner F3 path): the SAME action shape
      covers both explicit prefix corrections ("Correction:", "Sorry,
      I meant", ...) and silent auto-corrects (a plain re-teach the
      stage upgrades to correct). The discriminator is the turn text
      itself: explicit ⟺ it carries the sealed F3 correction prefix
      (fable_loop102_agent.strip_correction_prefix). Silent
      auto-corrects keep loop167e's "Saved:" -- sealed harnesses judge
      those teach replies literally (redteam143's teach_accepted takes
      only "Saved:"/"I already have that.").
    - Non-structured "correct ..." lines are the FakeEars No,/Actually,
      forms (verb twins included: the verb stage rewrites to the
      possessive twin and the base path tags it correct) -- explicit
      by construction.
    - A "yes" line that wrote a superseding FACT is a yes to the
      change question (any other "yes" writes nothing and is excluded
      by the caller).
    """
    if not isinstance(rec, dict) or rec.get("kind") != "write":
        return False
    struct = rec.get("structured")
    if isinstance(struct, dict):
        if struct.get("act") != "correct":
            return False
        try:
            return (L102.strip_correction_prefix(
                " ".join(str(turn).split())) is not None)
        except Exception:
            return False
    line = " ".join(str(rec.get("line", "")).split())
    if line.startswith("correct "):
        return True
    return line in ("yes", "yes.")


def _show(nb, value: dict) -> str:
    """Notebook value -> display string (entity name or literal text)."""
    if isinstance(value, dict) and "entity" in value:
        try:
            return nb.entities.get(value["entity"], value["entity"])
        except Exception:
            return str(value["entity"])
    if isinstance(value, dict):
        return str(value.get("literal", ""))
    return str(value)


def _spaced(relation: str) -> str:
    """The answer path's own surface rule (agent_loop.py:166-167)."""
    return relation.replace("_", " ")


def updated_text(nb, fact: dict) -> str | None:
    """The sealed Updated template for a superseding FACT, or None."""
    supersedes = fact.get("supersedes")
    if not supersedes:
        return None
    try:
        old = nb.facts.get(supersedes)
        subject = nb.entities.get(fact.get("subject"), "")
        new_disp = _show(nb, fact.get("value"))
        old_disp = _show(nb, old.get("value")) if old else ""
    except Exception:
        return None
    if not subject or not new_disp or not old_disp:
        return None
    return (f"Updated: {subject}'s {_spaced(fact.get('relation', ''))} "
            f"is {new_disp} (it was {old_disp}).")


def expected_saved_text(nb, fact: dict) -> str | None:
    """The base Saved record text this FACT must have confirmed."""
    try:
        subject = nb.entities.get(fact.get("subject"), "")
        new_disp = _show(nb, fact.get("value"))
    except Exception:
        return None
    if not subject or not new_disp:
        return None
    return f"Saved: {subject}'s {fact.get('relation', '')} is {new_disp}."


def correctreply_move(old: str, new: str) -> bool:
    """True when new == old (byte-identical) or new is old's Saved
    confirmation moved to the sealed Updated template with the same
    subject, relation surface, and new value plus a named old value.
    Shared by the 192 diff drivers so every suite judges reply moves
    by one rule."""
    if old == new:
        return True
    for prefix in (_DROPPED, ""):
        if old.startswith(prefix) and new.startswith(prefix):
            o, n = old[len(prefix):], new[len(prefix):]
            ms = _SAVED_RE.fullmatch(o)
            mu = _UPDATED_RE.fullmatch(n)
            if ms is not None and mu is not None:
                if (ms.group(1) == mu.group(1)
                        and _spaced(ms.group(2)) == mu.group(2)
                        and ms.group(3) == mu.group(3)
                        and mu.group(4)):
                    return True
    return False


class CorrectReply192Mixin:
    """Stackable outermost mixin: name both values on replacement turns.

    Cooperative: _listening_tick runs the loop's own tick first (writes,
    records, said, experience, counters byte-identical to loop167e by
    construction), then rewrites the outgoing English strings of exactly
    those write records whose turn appended a superseding FACT -- and
    only when the record's Saved text is exactly the confirmation that
    FACT would have produced (fail-safe: any mismatch keeps the base
    reply). `said` is rebuilt through the loop's own mouth so the 167e
    label render still applies downstream.
    """

    def _listening_tick(self):  # type: ignore[no-redef]
        before = len(self.nb.events)  # type: ignore[attr-defined]
        event = super()._listening_tick()  # type: ignore[misc]
        try:
            self._apply_correctreply192(event, before)  # type: ignore[attr-defined]
        except Exception:
            pass  # fail-safe: never break the loop; keep the base reply
        return event

    def _apply_correctreply192(self, event: dict, before: int) -> None:
        nb = self.nb  # type: ignore[attr-defined]
        fresh = [e for e in nb.events[before:]
                 if e.get("kind") == "FACT" and e.get("supersedes")]
        if not fresh:
            return
        records = (event.get("detail") or {}).get("records") or []
        if len(fresh) != 1 or len(records) != 1:
            # One English turn writes at most one triple; anything else
            # keeps the base reply (multi-record turns untouched).
            return
        fact = fresh[0]
        rec = records[0]
        if not isinstance(rec, dict) or rec.get("kind") != "write":
            return
        if not _is_explicit_correction_or_yes(
                rec, (event.get("detail") or {}).get("turn", "")):
            # Silent bench73-stage auto-correct re-teaches keep "Saved:".
            return
        text = rec.get("text", "")
        prefix = ""
        if text.startswith(_DROPPED):
            prefix, text = _DROPPED, text[len(_DROPPED):]
        if _SAVED_RE.fullmatch(text) is None:
            return
        if text != expected_saved_text(nb, fact):
            return  # not this FACT's confirmation; keep base reply
        new_text = updated_text(nb, fact)
        if new_text is None:
            return
        rec["text"] = prefix + new_text
        mouth = self.mouth  # type: ignore[attr-defined]
        event["said"] = [line for line in
                         (mouth.say(r) for r in records) if line]
