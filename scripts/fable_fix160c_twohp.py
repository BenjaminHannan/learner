#!/usr/bin/env python3
"""Experiment 160c -- THE ONE CHANGE vs loop160b: after a multi-hop answer,
a bare correction asks which fact is meant instead of guessing the last hop.

Step 1 (where 160b picks the last-stated fact):
  scripts/fable_fix160b_laststated.py:141-151
  (LastStated160bMixin._act: on {"act":"bare_correct"} it reads
  self._last_stated160b -- the triple the previous reply saved, or the
  FINAL-hop fact of the answer it just gave (final_hop_triple, lines 73-110)
  -- and synthesizes {"act":"correct", same name/relation/is_person, V}
  through super()._act. That is the guess Ben's ruling (2026-09-22) removes
  for chains of >= 2 facts.)

THE RULE (sealed; relative to 160b, the memory widens from "one stated fact"
to "the full stated chain", and the resolve gains one branch):
  A turn is a BARE CORRECTION iff it matches one of 160's five sealed shapes
  with a valid V (reused by import: fable_fix160b_laststated
  .parse_bare_correction -- same prefixes, same V validation, same pure
  function). Resolution:
    - If the agent's IMMEDIATELY previous reply stated a chain of >= 2 facts
      (one OK answer record whose trail covers every hop exactly once and
      has >= 2 hops, e.g. trail [F00001, F00002] for "Kim's boss's city is
      Rome."), the bare turn writes NOTHING and replies with the chain's
      facts as options, e.g.:
        Which one is wrong: Kim's boss is Lee, or Lee's city is Rome?
        Say e.g. "Actually, Lee's city is Milan."
      (the example names the LAST chain fact with the bare value V, so the
      user can copy the pattern; the turn itself performs 0 FACT writes and
      counts one clarification, like 160's sealed clarify).
    - Otherwise (single-fact previous reply, no-fact previous reply, several
      records, or no previous reply) the turn is handled EXACTLY as loop160b
      handles it (delegated to super()._act: the final-hop write, or 160's
      sealed clarify with 0 writes). An explicit follow-up correction
      ("Actually, Lee's city is Milan.") then works as in loop160b through
      the loop's EXISTING correction machinery (same guards, same "Saved: ..."
      reply, same audit trail and supersede rules).
  Every turn's records REPLACE the chain memory (a non-chain reply clears it
  to None); nothing older than the previous reply is ever addressed.

Cooperative MIXIN (TwoHop160cMixin): stacked OUTSIDE LastStated160bMixin
(loop160c = 160c-mixin + loop160b); hear() untouched (160b's tag reused, so
non-matching turns are byte-identical to loop160b); _act() intercepts
bare_correct only when _chain160c holds >= 2 facts, else delegates;
_listening_tick() recomputes _chain160c from the turn's own records and
persists it in state.json ("chain160c") across resume. No existing file
edited; 160b's _last_stated160b bookkeeping runs unchanged via super().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix160b_laststated as B160b  # noqa: E402 (base rule, read-only)


def _display_value(nb, value) -> str:
    """Notebook value -> display string (entity name or literal text)."""
    if isinstance(value, dict) and "entity" in value:
        try:
            return nb.entities.get(value["entity"], value["entity"])
        except Exception:
            return str(value["entity"])
    if isinstance(value, dict):
        return str(value.get("literal", ""))
    return str(value)


def chain_triples(record: dict, nb) -> list[dict] | None:
    """A single OK multi-hop answer record -> its full chain of facts.

    Requires the trail to cover every hop exactly once (len(trail) ==
    len(relations)) with >= 2 hops; every trail fact id must resolve in the
    notebook to (subject, relation, value) with a named subject. Returns the
    ordered hop list, else None (single-hop, fact-free, multi-row, partial
    trails, and non-answer records all return None so the caller falls back
    to byte-identical loop160b behaviour).
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
    if len(trail) < 2:
        return None
    try:
        facts = nb.facts
    except Exception:
        return None
    chain: list[dict] = []
    for fid in trail:
        fact = facts.get(fid)
        if not isinstance(fact, dict):
            return None
        subject, relation, value = (fact.get("subject"),
                                    fact.get("relation"), fact.get("value"))
        if subject is None or not relation or value is None:
            return None
        try:
            name = nb.entities.get(subject)
        except Exception:
            name = None
        if not name:
            return None
        chain.append({"name": name, "relation": relation,
                      "value": _display_value(nb, value),
                      "is_person": isinstance(value, dict)
                      and "entity" in value})
    return chain


def chain_from_records(records: list, nb) -> list[dict] | None:
    """The previous reply's stated chain (>= 2 facts), else None."""
    if not isinstance(records, list) or len(records) != 1:
        return None
    return chain_triples(records[0], nb)


def _fact_phrase(triple: dict) -> str:
    return f"{triple['name']}'s {triple['relation']} is {triple['value']}"


def clarify_for_chain(chain: list[dict], value: str) -> str:
    """Which-one-is-wrong clarify listing every chain fact, with an example
    naming the last chain fact and the bare value V."""
    opts = [_fact_phrase(t) for t in chain]
    if len(opts) == 2:
        listed = f"{opts[0]}, or {opts[1]}"
    else:
        listed = ", ".join(opts[:-1]) + f", or {opts[-1]}"
    last = chain[-1]
    return (f"Which one is wrong: {listed}? Say e.g. "
            f'"Actually, {last["name"]}\'s {last["relation"]} is {value}."')


class TwoHop160cMixin:
    """Stackable mixin: bare corrections after a >= 2-fact chain clarify."""

    _chain160c: list[dict] | None = None

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "bare_correct":
            chain = getattr(self, "_chain160c", None)
            if isinstance(chain, list) and len(chain) >= 2:
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify",
                        "text": clarify_for_chain(chain, action["value"])}
        return super()._act(action)  # type: ignore[misc]

    def _listening_tick(self) -> dict:  # type: ignore[no-redef]
        event = super()._listening_tick()  # type: ignore[misc]
        recs = (event.get("detail") or {}).get("records") or []
        # Only the immediately previous reply counts: replace every turn
        # (a non-chain reply clears the memory; nothing older is addressed).
        try:
            self._chain160c = chain_from_records(recs, self.nb)  # type: ignore[attr-defined]
        except Exception:
            self._chain160c = None
        return event

    def _save(self) -> None:  # type: ignore[no-redef]
        super()._save()  # type: ignore[misc]
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
            raw["chain160c"] = getattr(self, "_chain160c", None)
            tmp = self.state_path.with_name(  # type: ignore[attr-defined]
                f"{self.state_path.name}.tmp160c")  # type: ignore[attr-defined]
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
            val = raw.get("chain160c")
            self._chain160c = val if isinstance(val, list) else None
        except (OSError, ValueError):
            self._chain160c = None
