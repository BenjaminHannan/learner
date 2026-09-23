#!/usr/bin/env python3
"""Experiment 160b -- THE ONE CHANGE vs exp 160: bare corrections target the
fact the agent's IMMEDIATELY previous reply stated.

Exp-160's sealed rule ("the most recent saved teach") makes WRONG writes on
the director's probes: after "Tom's city is Oslo." / "Ann's city is Rome." /
"What is Ann's city?" / "hi" / "What is Tom's city?" (-> "Tom's city is
Oslo.") / "I meant Paris", 160 rewrites ANN (most-recent saved teach) while
the user had just been talking about TOM; and "Tom's city is Oslo." /
"Who is Bob's boss?" (-> don't know) / "no wait, it's Denver" rewrites TOM
although the previous reply stated no fact.

THE RULE (sealed; relative to 160's ORIGINAL sealed rule the memory changes
from "previous user turn's teach" to "previous AGENT reply's stated fact"):
  A turn is a BARE CORRECTION iff it matches one of 160's five sealed shapes
  (reused by import: fable_fix160_barecorrect.parse_bare_correction -- same
  prefixes, same V validation, same pure function). Resolution targets the
  ONE fact the agent's IMMEDIATELY previous reply stated:
    - the triple it just saved (a single wrote-write teach/correct record),
      or
    - the final-hop fact of the answer it just gave (a single OK answer
      record whose trail covers every hop exactly once; the last trail fact
      is e.g. (Rao, city, seattle) for "Nadia's teacher's city is seattle.").
  If the previous reply stated no fact (refusal/clarify/small talk/
  MISSING_FACT/UNKNOWN_ENTITY/0 writes), or more than one fact (multi-row
  answer, several records), or there is no previous reply -> the sealed
  clarify with 0 writes (same exact text as 160, reused by import).
  Nothing older than the previous reply is ever targeted: every turn's
  records REPLACE the memory (None clears it); only the next turn's bare
  correction may use it.
  A bare correction goes through the loop's EXISTING correction machinery
  (super()._act with {"act":"correct",...}, same guards, same "Saved: ..."
  reply, same audit trail and supersede rules as "Actually, X's R is V.").

Cooperative MIXIN (LastStated160bMixin): hear() reuses 160's tag_actions
(base hear first, only a single clarify re-tagged, so non-matching turns are
byte-identical to loop150); _act() resolves bare_correct against
_last_stated160b; _listening_tick() recomputes _last_stated160b from the
turn's own records and persists it in state.json ("last_stated160b") across
resume. No existing file edited.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix160_barecorrect as B160  # noqa: E402 (sealed shapes+clarify, read-only)

# Reused sealed pieces (same shapes, same clarify, same teach-triple parse).
parse_bare_correction = B160.parse_bare_correction
tag_actions = B160.tag_actions
CLARIFY_MSG = B160.CLARIFY_MSG


def _display_value(nb, value: dict) -> str:
    """Notebook value -> display string (entity name or literal text)."""
    if isinstance(value, dict) and "entity" in value:
        try:
            return nb.entities.get(value["entity"], value["entity"])
        except Exception:
            return str(value["entity"])
    if isinstance(value, dict):
        return str(value.get("literal", ""))
    return str(value)


def final_hop_triple(record: dict, nb) -> dict | None:
    """A single OK answer record -> its final-hop (subject, relation, value).

    Requires the trail to cover every hop exactly once (len(trail) ==
    len(relations)); multi-row answers (several facts stated) and partial
    trails return None. Returns None for any non-OK status.
    """
    if not isinstance(record, dict) or record.get("kind") != "answer":
        return None
    if record.get("status") != "OK":
        return None
    relations = record.get("relations") or []
    fields = record.get("fields") or {}
    if fields.get("multi"):
        return None
    trail = fields.get("trail") or []
    if not relations or not trail or len(trail) != len(relations):
        return None
    try:
        facts = nb.facts
    except Exception:
        return None
    fact = facts.get(trail[-1])
    if not isinstance(fact, dict):
        return None
    subject, relation, value = (fact.get("subject"), fact.get("relation"),
                                fact.get("value"))
    if subject is None or not relation or value is None:
        return None
    try:
        name = nb.entities.get(subject)
    except Exception:
        name = None
    if not name:
        return None
    return {"name": name, "relation": relation,
            "value": _display_value(nb, value),
            "is_person": isinstance(value, dict) and "entity" in value}


def stated_from_records(records: list, nb) -> dict | None:
    """The ONE fact the previous reply stated, else None.

    Exactly one record stating exactly one fact: a single wrote-write
    teach/correct triple, or a single OK answer's final-hop fact. Zero,
    several, or fact-free records (clarify/refusal/small talk/MISSING/
    UNKNOWN/multi) -> None.
    """
    if not isinstance(records, list) or len(records) != 1:
        return None
    rec = records[0]
    if not isinstance(rec, dict):
        return None
    if rec.get("kind") == "write":
        return B160.triple_from_record(rec)
    return final_hop_triple(rec, nb)


class LastStated160bMixin:
    """Stackable mixin: bare corrections against the previous reply's fact."""

    _last_stated160b: dict | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return tag_actions(actions, turn)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "bare_correct":
            prev = getattr(self, "_last_stated160b", None)
            if (isinstance(prev, dict) and prev.get("name")
                    and prev.get("relation") is not None):
                built = {"act": "correct", "name": prev["name"],
                         "relation": prev["relation"],
                         "value": action["value"],
                         "is_person": bool(prev.get("is_person"))}
                return super()._act(built)  # type: ignore[misc]
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify", "text": CLARIFY_MSG}
        return super()._act(action)  # type: ignore[misc]

    def _listening_tick(self) -> dict:  # type: ignore[no-redef]
        event = super()._listening_tick()  # type: ignore[misc]
        recs = (event.get("detail") or {}).get("records") or []
        # Only the immediately previous reply counts: replace every turn
        # (a fact-free reply clears the memory; nothing older is targeted).
        self._last_stated160b = stated_from_records(recs, self.nb)  # type: ignore[attr-defined]
        return event

    def _save(self) -> None:  # type: ignore[no-redef]
        super()._save()  # type: ignore[misc]
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
            raw["last_stated160b"] = getattr(self, "_last_stated160b", None)
            tmp = self.state_path.with_name(  # type: ignore[attr-defined]
                f"{self.state_path.name}.tmp160b")  # type: ignore[attr-defined]
            import os as _os
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(raw, ensure_ascii=False,
                                        sort_keys=True))
                handle.flush()
                _os.fsync(handle.fileno())
            _os.replace(tmp, self.state_path)  # type: ignore[attr-defined]
        except OSError:
            pass

    def _load(self) -> None:  # type: ignore[no-redef]
        super()._load()  # type: ignore[misc]
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
            val = raw.get("last_stated160b")
            self._last_stated160b = val if isinstance(val, dict) else None
        except (OSError, ValueError):
            self._last_stated160b = None
