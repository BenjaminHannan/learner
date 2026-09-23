#!/usr/bin/env python3
"""Experiment 163 -- THE ONE CHANGE: case-insensitive name matching at the
entity layer (lowercase names).

Director probes: after "Omar's sister is Priya.", "Is Priya Omar's sister?"
answers Yes but the lowercase "is priya omar's sister?" falls back to
"I only know that omar's sister is Priya." (lowercase echo, missed Yes);
"who is tom's boss?" after "Tom's boss is Ann." answers with a lowercase
echo ("tom's boss is Ann."); a first-mention lowercase teach ("tom's boss
is ann.") stores the lowercase display forms verbatim. Phone users type
lowercase constantly.

Step 1 file:line map (loop150 stack; all read-only, never edited):
- names MATCHED on lookup: scripts/fable_notebook_contract.py:116-117
  (_norm: alias keys are case-folded, so Notebook.resolve at :235-242 is
  already case-insensitive) and the hop loop Notebook.ask at :390-421;
  reasoner entry scripts/fable_fix77_core.py:208-228
  (QualifierAwareReasoner77.answer resolves the ask name via nb.resolve);
  ears question parses scripts/fable_agent_loop.py:122-129 (FakeEars ask),
  scripts/fable_bench73_english_arm.py:215-237 (_entity_mentions, lowercased)
  and :246-314 (compose_question), scripts/fable_bench92_english_arm.py:145
  (_entity_mentions92) and :198-243 (compose_n_hop).
- names WRITTEN: scripts/fable_listening_m1.py:46-58 (_person:
  resolve-or-create) and :106-127 (_teach), entity rows
  scripts/fable_notebook_contract.py:268-277 (new_entity stores the typed
  display verbatim); loop write paths scripts/fable_agent_loop.py:344-350
  (_act teach/correct line) and scripts/fable_loop90_agent.py:353-373
  (structured teach straight to the doorway); teach/correct detect
  scripts/fable_loop90_agent.py:153-170 (Bench73Stage._teach_action);
  replies echo the typed ask name scripts/fable_agent_loop.py:155-172
  (FakeMouth builds the owner from record["name"], not the display form).

THE ONE CHANGE (this file; loop150 imported read-only, nothing edited):
every teach/correct action under one of the loop's person relations, and
every ask action's NAME span, is canonicalised through the notebook's own
case-insensitive resolve, at ears hear() and again at loop _act() just
before the write (same two levels as the 139b/150 guards):

  (a) question side: an all-lowercase owner span that resolves to exactly
      one known entity is replaced by that entity's stored display form,
      so replies always print the display form. Spans that do not resolve
      (UNKNOWN) or resolve ambiguously are left byte-identical, so the base
      abstain/clarify paths own those turns unchanged.
  (b) teach side (person relations only): an all-lowercase name/value span
      that resolves to exactly one known entity is written as that entity
      (display form); an all-lowercase NEW span is stored with its first
      letter capitalised per token ("tom" -> "Tom"), and a later
      capitalised mention resolves to it case-insensitively.
  (c) teaches under any other relation (cities, sports, positions, office
      phrases -- including the exp-102 legal all-lowercase common-noun
      entities "wide receiver", "association football", "baseball") are
      byte-identical: lookup already merges them case-insensitively via
      the notebook's own _norm, and their typed display is preserved.
  (d) spans with deliberate inner capitals or mixed case (McDonald,
      DeShawn, iPhone, TOM, eBay) are never all-lowercase, so they keep
      their typed form byte-identical. Two stored entities that differ
      only by case (both typed capitalised and differently, e.g. "Tom"
      vs "TOM" via person lines) still resolve AMBIGUOUS: the span is left
      untouched and the base "which one?" clarify owns the turn (0 writes,
      0 wrong answers; the probe reports the collision).

Additive only: every other module is imported read-only, never edited.
Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)

# Relation keys whose values are entity-valued person names (the loop's own
# person table; FakeEars marks exactly these is_person=True).
PERSON_KEYS: frozenset = frozenset(A.PERSON_RELATIONS)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def is_all_lowercase_name(span: str) -> bool:
    """True when the span is a name typed fully in lowercase.

    Requires at least one cased character and every cased character
    lowercase (str.islower): "tom" True; "McDonald"/"DeShawn"/"iPhone"/
    "TOM"/"eBay" False; "123"/"..." False (no cased characters, not names).
    """
    text = _norm(span)
    if not text:
        return False
    return text.islower()


def capitalise_display(span: str) -> str:
    """Display form for a new all-lowercase name: first letter per token.

    Only the first cased character of each whitespace-separated token is
    upper-cased; every other character is untouched ("tom" -> "Tom",
    "mary jane" -> "Mary Jane"). Callers guarantee all-lowercase input.
    """
    out = []
    for tok in _norm(span).split(" "):
        done = False
        chars = []
        for ch in tok:
            if not done and ch.isalpha():
                chars.append(ch.upper())
                done = True
            else:
                chars.append(ch)
        out.append("".join(chars))
    return " ".join(out)


def canonicalise_name(span: str, nb, *, for_store: bool) -> str:
    """All-lowercase span -> stored display form; anything else unchanged.

    - not all-lowercase (McDonald, DeShawn, iPhone, TOM, mixed, numbers)
      -> typed form, byte-identical.
    - all-lowercase + resolves to exactly one entity -> its display form.
    - all-lowercase + AMBIGUOUS (case-only collision) -> typed form, so the
      base clarify owns the turn (never merge, never guess).
    - all-lowercase + UNKNOWN (or no notebook bound) -> capitalised display
      when for_store (teach side: the new entity), else typed form (ask
      side: the base UNKNOWN path owns it).
    """
    text = _norm(span)
    if not is_all_lowercase_name(text):
        return span
    if nb is None:
        return capitalise_display(text) if for_store else span
    try:
        found = nb.resolve(text)
    except Exception:
        return span
    if found.status == "OK" and found.detail.get("entity_id"):
        try:
            return nb.entities.get(found.detail["entity_id"], span)
        except Exception:
            return span
    if for_store and found.status == "UNKNOWN_ENTITY":
        return capitalise_display(text)
    return span


def canonicalise_action(action: dict, nb) -> dict:
    """Teach/correct (person relations) / ask action with display forms.

    Teach/correct under a person relation key: name and value spans
    canonicalised for store. Teach/correct under any other relation:
    untouched (common-noun entities and literals keep typed form; lookup
    already merges case-insensitively). Ask: name span canonicalised for
    lookup (unknown stays, so base UNKNOWN owns it). Any other act, or no
    change, returns the action untouched.
    """
    if not isinstance(action, dict):
        return action
    act = action.get("act")
    if act in ("teach", "correct"):
        if str(action.get("relation", "")) not in PERSON_KEYS:
            return action
        out = action
        new_name = canonicalise_name(action.get("name", ""), nb,
                                     for_store=True)
        if new_name != action.get("name", ""):
            out = copy.copy(action)
            out["name"] = new_name
        new_value = canonicalise_name(out.get("value", ""), nb,
                                      for_store=True)
        if new_value != out.get("value", ""):
            if out is action:
                out = copy.copy(action)
            out["value"] = new_value
        return out
    if act == "ask":
        name = action.get("name", "")
        new_name = canonicalise_name(name, nb, for_store=False)
        if new_name != name:
            out = copy.copy(action)
            out["name"] = new_name
            return out
        return action
    return action


def canonicalise_actions(actions: list[dict], nb) -> list[dict]:
    return [canonicalise_action(a, nb) for a in list(actions)]


class Lowercase163Mixin:
    """Stackable mixin: case-insensitive names at the entity layer.

    Cooperative (super() first): on ears it runs after the base hear (so
    the 129 strip + 139b/150 screens inside loop150 have already run); on
    the loop it re-checks strip-then-canonicalise just before the write
    (covers the inner-chain delegate path). Same shape as
    SubjectGuard150Mixin; only the transform (display-form names) differs.
    Relation keys, forget/alias/person/quote/answer/clarify paths untouched.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return canonicalise_actions(
            actions, getattr(self, "nb", None))

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct", "ask"):
            checked = copy.copy(action)
            if checked.get("act") in ("teach", "correct"):
                cleaned = P129.strip_sentence_punct(checked.get("name", ""))
                if cleaned:
                    checked["name"] = cleaned
            fixed = canonicalise_action(
                checked, getattr(self, "nb", None))
            if fixed is not checked or fixed != action:
                return super()._act(fixed)  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]
