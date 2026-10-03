"""Thought notebook v2 -- a WRAPPER (never an edit) around fable_notebook_contract.

Storage
  Every v2 row is written through the unmodified Milestone-1 Notebook, with the full
  v2 record embedded under ``provenance["thought_v2"]``.  One events.jsonl, one hash
  chain, one set of guarantees (append-only, fsync + read-back, torn-tail survival,
  tamper detection, supersede-not-delete, source priority, AMBIGUOUS never guesses).
  The v2 index (fact_id -> ThoughtV2) is rebuilt from that log on every load.

Answering
  ``ask()`` is the contract's hop loop re-expressed in this wrapper (same statuses,
  details, MAX_HOPS; contract file untouched) over the to_v1() projections of stored
  rows, plus Ben's ruling 2026-09-21: a QUALIFIED row only answers when the question
  carries matching qualifiers -- otherwise the hop abstains with MISSING_FACT
  (reason=qualified).  Unqualified rows answer exactly as before.

Marks (Ben ruling 2026-09-21)
  Promoting one of two conflicting claims APPENDS a THOUGHT_MARK event
  (kind=unknown to the contract -- it passes through the chain untouched) recording
  "superseded-by-promotion" on each different-valued paper/web claim for the same
  subject+relation.  Never a delete: the marked row stays in the log, in thoughts_for,
  and retrievable by get_thought().

Relation ids (Ben ruling 2026-09-21)
  add_thought() suggests relation_id when the raw relation exactly matches one of
  WebRED's 521 names; the raw string is always kept and always what ask() uses.

Who may write what (unchanged contract rights, mapped from source):
  taught          -> actor "listening"
  proposed        -> actor "thinking"      (papers without a URL land here)
  web-quarantine  -> actor "thinking"      (needs a URL, as in the contract)
  inferred        -> actor "thinking"      (needs an approved rule + active deps)
  sleep-derived   -> actor "sleep"
  web-verified    -> actor "thinking"      (contract still demands 2-site evidence)

Papers never answer until Ben promotes them: a paper row is source web-quarantine or
proposed, both outside ANSWERING_SOURCES.  promote() is re-expressed here so the
promoted taught row keeps its typed value, qualifiers and provenance (the contract's
promote only carries subject/relation/value).
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_notebook_contract as C                      # noqa: E402
from fable_thought49_schema import (                      # noqa: E402
    CLAIM_TAUGHT, MARK_SUPERSEDED_BY_PROMOTION, SchemaError, ThoughtV2, Provenance,
    norm_relation, suggest_relation_id,
)

Result = C.Result

# source -> the only actor allowed to write it (mirrors WRITE_RIGHTS in the contract)
ACTOR_FOR_SOURCE = {
    "taught": "listening",
    "proposed": "thinking",
    "web-quarantine": "thinking",
    "inferred": "thinking",
    "sleep-derived": "sleep",
    "web-verified": "thinking",
}


class _BadQualifiers(Exception):
    pass


def _value_matches(value, provided) -> bool:
    """Question-side value == row-side qualifier value. Exact only; never coerced."""
    target = value.to_v1_value()
    if isinstance(provided, dict):
        return provided == target
    if value.kind == "entity":
        return str(provided) == target.get("entity")
    if value.kind == "boolean":
        if isinstance(provided, bool):
            return provided is value.boolean
        return str(provided).strip().lower() == target.get("literal")
    if value.kind == "number":
        if isinstance(provided, bool):
            return False
        try:
            return float(provided) == float(value.number)
        except (TypeError, ValueError):
            return str(provided) == target.get("literal")
    return str(provided) == target.get("literal")


def _qualifiers_match(qualifiers, required: dict) -> bool:
    """Every row qualifier must be present and equal in the question (Ben ruling:
    a bare question never satisfies a qualified row)."""
    if not required:
        return False
    need = {norm_relation(key): val for key, val in required.items()}
    for qual in qualifiers:
        key = norm_relation(qual.relation)
        if key not in need or not _value_matches(qual.value, need[key]):
            return False
    return True


class ThoughtNotebook:
    """Duck-types the Milestone-1 Notebook API (delegation, not inheritance edits),
    plus add_thought / get_thought / thoughts_for / ensure_entity."""

    FORMAT = 2

    def __init__(self, root) -> None:
        self.nb = C.Notebook(root)          # unmodified contract notebook
        self.root = Path(root)
        self.marks: dict = {}               # fact_id -> {mark, by} (from THOUGHT_MARK)
        self._rebuild_marks()
        self._rebuild_index()

    # ------------------------------------------------------------- delegation
    def __getattr__(self, name):
        """Everything not defined here is the contract notebook (facts, events,
        entities, aliases, assert_fact, declare_relation, retract, promote
        primitives, repair_torn_tail, torn_tail, active, resolve, ...)."""
        nb = self.__dict__.get("nb")
        if nb is None:
            raise AttributeError(name)
        return getattr(nb, name)

    # ------------------------------------------------------------------ index
    def _rebuild_marks(self) -> None:
        for event in self.nb.events:
            if event.get("kind") == "THOUGHT_MARK":
                self.marks[event["fact_id"]] = {"mark": event["mark"],
                                                "by": event.get("by")}

    def _rebuild_index(self) -> None:
        self.thoughts: dict = {}
        for fact_id in list(self.nb.facts):
            self._index_one(fact_id)

    def _index_one(self, fact_id: str) -> Optional[ThoughtV2]:
        """Lazily index a fact (covers writes that went through the contract API
        directly instead of add_thought)."""
        if fact_id in self.thoughts:
            return self.thoughts[fact_id]
        try:
            thought = ThoughtV2.from_v1(self.nb.facts[fact_id])
        except SchemaError:
            return None                 # foreign event: invisible to v2 reads
        mark = self.marks.get(fact_id)
        if mark:
            thought = replace(thought, mark=mark["mark"], marked_by=mark.get("by"))
        self.thoughts[fact_id] = thought
        return thought

    # ---------------------------------------------------------------- writes
    def ensure_entity(self, event_id: str, name: str) -> Result:
        """Resolve-or-create WITHOUT guessing: an ambiguous name returns AMBIGUOUS
        and creates nothing (two people may share a name; they are never merged)."""
        found = self.nb.resolve(name)
        if found.status == C.OK:
            return Result(C.OK, {"entity_id": found.detail["entity_id"],
                                 "answer": found.detail["answer"], "existing": True})
        if found.status == C.AMBIGUOUS:
            return found
        return self.nb.new_entity(event_id, name)

    def add_thought(self, thought: ThoughtV2, event_id: Optional[str] = None,
                    *, correction: bool = False, raw: Optional[str] = None,
                    strict: bool = True) -> Result:
        """Validate a v2 row and append it through the contract notebook.

        The same content written twice shares one deterministic event id -> the
        contract answers DUPLICATE_OK and the log does not grow.

        relation_id: suggested automatically when the raw relation exactly matches a
        WebRED relation name (Ben ruling); the raw relation string is never rewritten.
        """
        if thought.relation_id is None:
            suggestion = suggest_relation_id(thought.relation)
            if suggestion:
                thought = replace(thought, relation_id=suggestion)
        try:
            thought.validate(strict=strict)
        except SchemaError as exc:
            return Result(C.BAD_REQUEST, {"reason": str(exc)})
        if thought.subject not in self.nb.entities:
            return Result(C.BAD_REQUEST, {"reason": "unknown subject id"})
        actor = ACTOR_FOR_SOURCE.get(thought.source)
        if actor is None:
            return Result(C.BAD_REQUEST, {"reason": "unknown source"})
        try:
            payload = thought.to_v1()
        except SchemaError as exc:
            return Result(C.BAD_REQUEST, {"reason": str(exc)})
        source = payload.pop("source")
        if raw is not None:
            payload["raw"] = raw
        if event_id is None:
            event_id = thought.content_event_id()
        result = self.nb.assert_fact(event_id, actor, source, correction=correction,
                                     **payload)
        if result.status == C.SAVED:
            fact_id = result.detail["fact_id"]
            self.thoughts[fact_id] = replace(thought, thought_id=fact_id)
        return result

    def promote(self, event_id: str, actor: str, fact_id: str) -> Result:
        """Ben approves a proposed / quarantined row.

        Same rights and same refusal rules as the contract's promote (Ben only;
        only proposed/web-quarantine rows promote), but the promoted taught row
        keeps its typed value, qualifiers and provenance -- recorded as a new
        taught fact that supersedes any taught answer; the original row is kept.
        Conflicting different-valued paper/web claims for the same subject+relation
        are MARKED "superseded-by-promotion" (append-only THOUGHT_MARK event),
        never deleted (Ben ruling 2026-09-21).
        """
        if self.nb._dup(event_id):
            return Result(C.DUPLICATE_OK)
        if actor != "ben":
            return Result(C.NOT_ALLOWED, {"actor": actor})
        fact = self.nb.facts.get(fact_id)
        if fact is None or fact["source"] not in ("proposed", "web-quarantine"):
            return Result(C.BAD_REQUEST, {"reason": "only proposed or quarantined rows promote"})
        old = self.thoughts.get(fact_id)
        if old is None:
            old = ThoughtV2.from_v1(fact)
        taught = replace(
            old,
            source="taught",
            confidence=1.0,
            rule_id=None,
            deps=(),
            thought_id=None,
            mark=None,
            marked_by=None,
            provenance=replace(old.provenance,
                               claimed_by=CLAIM_TAUGHT,
                               promoted_from=fact_id),
        )
        result = self.add_thought(taught, event_id=event_id, correction=True,
                                  raw="promoted from %s" % fact_id, strict=False)
        if result.status != C.SAVED:
            return result
        self._mark_conflicting_loser(result.detail["fact_id"], taught)
        return result

    def _mark(self, fact_id: str, mark: str, by: str) -> Result:
        """Append a THOUGHT_MARK event (contract passes unknown kinds through the
        chain untouched) and attach the mark to the in-memory row."""
        event_id = "t49m-" + hashlib.sha256(
            ("%s|%s|%s" % (fact_id, mark, by)).encode("utf-8")).hexdigest()[:20]
        if self.nb._dup(event_id):
            return Result(C.DUPLICATE_OK)
        if fact_id not in self.nb.facts:
            return Result(C.BAD_REQUEST, {"reason": "unknown fact"})
        self.nb._append({"kind": "THOUGHT_MARK", "event_id": event_id,
                         "fact_id": fact_id, "mark": mark, "by": by, "actor": "ben"})
        self.marks[fact_id] = {"mark": mark, "by": by}
        thought = self.thoughts.get(fact_id)
        if thought is not None:
            self.thoughts[fact_id] = replace(thought, mark=mark, marked_by=by)
        return Result(C.SAVED, {"text": "%s marked %s" % (fact_id, mark)})

    def _mark_conflicting_loser(self, taught_fid: str, taught: ThoughtV2) -> None:
        for fid, thought in list(self.thoughts.items()):
            if (fid == taught_fid or thought.mark is not None
                    or thought.source not in ("proposed", "web-quarantine")
                    or thought.subject != taught.subject
                    or thought.relation != taught.relation
                    or not self.nb.active(fid)
                    or thought.value.to_v1_value() == taught.value.to_v1_value()):
                continue
            self._mark(fid, MARK_SUPERSEDED_BY_PROMOTION, taught_fid)

    # ------------------------------------------------------------------ reads
    def ask(self, name: str, relations: list, entity_id: Optional[str] = None,
            qualifiers=None) -> Result:
        """The contract hop loop (same statuses/details/hops), over to_v1()
        projections, with Ben's qualifier gate: a qualified row answers only when
        the question carries matching qualifiers; otherwise MISSING_FACT
        (reason=qualified) -- abstain rather than answer a bare conditioned claim.

        ``qualifiers``: None, a dict (applied at every hop), or a list parallel to
        ``relations`` (entries None|dict).  Keys are qualifier relations, values are
        the expected value (string, number, bool, or {"entity"/"literal": ...}).
        """
        if not relations or len(relations) > C.MAX_HOPS:
            return Result(C.BAD_REQUEST, {"reason": "need 1-%d hops" % C.MAX_HOPS})
        try:
            hop_req = self._hop_requirements(relations, qualifiers)
        except _BadQualifiers:
            return Result(C.BAD_REQUEST, {
                "reason": "qualifiers must be None, a dict, or a list parallel to relations"})
        if entity_id is None:
            found = self.nb.resolve(name)
            if found.status != C.OK:
                return found
            entity_id = found.detail["entity_id"]
        elif entity_id not in self.nb.entities:
            return Result(C.BAD_REQUEST, {"reason": "unknown entity id"})
        trail: list = []
        value: dict = {"entity": entity_id}
        for hop, relation in enumerate(relations):
            if "entity" not in value:
                return Result(C.BROKEN_CHAIN, {
                    "subject": self.nb.entities[entity_id],
                    "relation": relations[hop - 1],
                    "value": self.nb._show(value), "hop": hop, "trail": trail})
            entity_id = value["entity"]
            rows, qualified_miss = self._gate(self.nb.current(entity_id, relation),
                                              hop_req[hop])
            if not rows:
                detail = {"subject": self.nb.entities[entity_id], "relation": relation,
                          "hop": hop + 1, "trail": trail}
                if qualified_miss:
                    detail["reason"] = "qualified"
                return Result(C.MISSING_FACT, detail)
            if relation in self.nb.functional or len(rows) == 1:
                value = rows[0]["value"]
                trail.append(rows[0]["fact_id"])
            else:
                answer = ", ".join(self.nb._show(row["value"]) for row in rows)
                return Result(C.OK, {"answer": answer,
                                     "trail": trail + [r["fact_id"] for r in rows],
                                     "source": rows[0]["source"], "multi": True})
        return Result(C.OK, {"answer": self.nb._show(value), "trail": trail,
                             "source": self.nb.facts[trail[-1]]["source"]})

    @staticmethod
    def _hop_requirements(relations: list, qualifiers) -> list:
        if qualifiers is None:
            return [{} for _ in relations]
        if isinstance(qualifiers, dict):
            return [dict(qualifiers) for _ in relations]
        if isinstance(qualifiers, (list, tuple)) and len(qualifiers) == len(relations):
            return [{} if q is None else dict(q) for q in qualifiers]
        raise _BadQualifiers()

    def _gate(self, rows: list, required: dict):
        """Drop qualified rows whose conditions the question does not match."""
        kept, qualified_miss = [], False
        for row in rows:
            thought = self._index_one(row["fact_id"])
            if thought is None or not thought.qualifiers:
                kept.append(row)
            elif _qualifiers_match(thought.qualifiers, required):
                kept.append(row)
            else:
                qualified_miss = True
        return kept, qualified_miss

    def get_thought(self, fact_id: str) -> Optional[ThoughtV2]:
        if fact_id in self.nb.facts:
            return self._index_one(fact_id)
        return self.thoughts.get(fact_id)

    def thoughts_for(self, subject: str, relation: Optional[str] = None,
                     *, active_only: bool = True) -> list:
        """All v2 rows for a subject (optionally one relation).  With
        active_only=False this is history: superseded/retracted rows included."""
        for fact_id in list(self.nb.facts):
            self._index_one(fact_id)
        rows = []
        for fact_id, thought in self.thoughts.items():
            if thought.subject != subject:
                continue
            if relation is not None and thought.relation != relation:
                continue
            if active_only and not self.nb.active(fact_id):
                continue
            rows.append(thought)
        rows.sort(key=lambda t: self.nb.facts[t.thought_id]["n"])
        return rows


# ---------------------------------------------------------------- naive foil
class NaiveThoughtNotebook:
    """Last-write-wins dict keyed by (subject, relation).  Exists only to FAIL the
    v2 conformance suite: no chain, no source gating, no history, no qualifiers,
    restart loses everything."""

    FORMAT = 2

    def __init__(self, root) -> None:
        self.root = Path(root)
        self.rows: dict = {}
        self.thoughts: dict = {}
        self.facts: dict = {}
        self.events: list = []
        self.names: dict = {}
        self.entities: dict = {}
        self.torn_tail = False
        self._n = 0

    def ensure_entity(self, event_id, name):
        key = " ".join(str(name).strip().lower().split())
        entity_id = self.names.get(key)
        if entity_id is None:
            entity_id = "E%04d" % (len(self.names) + 1)
            self.names[key] = entity_id
            self.entities[entity_id] = name
        return Result(C.OK, {"entity_id": entity_id, "answer": name})

    def declare_relation(self, event_id, relation, functional):
        return Result(C.SAVED)

    def new_entity(self, event_id, name):
        return self.ensure_entity(event_id, name)

    def add_thought(self, thought, event_id=None, *, correction=False, raw=None,
                    strict=True):
        self._n += 1
        fact_id = "F%05d" % self._n
        self.rows[(thought.subject, thought.relation)] = thought
        self.thoughts[fact_id] = thought
        self.facts[fact_id] = {"fact_id": fact_id, "n": self._n, "source": thought.source}
        self.events.append({"fact_id": fact_id})
        return Result(C.SAVED, {"fact_id": fact_id})

    def assert_fact(self, event_id, actor, source, subject, relation, value, **kw):
        from fable_thought49_schema import Value
        val = Value.of_entity(value["entity"]) if "entity" in value \
            else Value.of_text(str(value.get("literal", "")))
        thought = ThoughtV2(
            subject=subject, relation=relation, value=val,
            provenance=Provenance(document="naive", sentence="", claimed_by="taught"),
            source=source, confidence=1.0,
        )
        return self.add_thought(thought, event_id)

    def promote(self, event_id, actor, fact_id):
        return Result(C.SAVED)           # promotion changes nothing that answers

    def resolve(self, name):
        key = " ".join(str(name).strip().lower().split())
        if key in self.names:
            return Result(C.OK, {"entity_id": self.names[key], "answer": name})
        return Result(C.UNKNOWN_ENTITY, {"name": name})

    def get_thought(self, fact_id):
        return self.thoughts.get(fact_id)

    def thoughts_for(self, subject, relation=None, *, active_only=True):
        out = [t for (s, r), t in self.rows.items()
               if s == subject and (relation is None or r == relation)]
        return out

    def ask(self, name, relations, entity_id=None, **kw):
        key = " ".join(str(name).strip().lower().split())
        current = self.names.get(key) if entity_id is None else entity_id
        if current is None:
            return Result(C.UNKNOWN_ENTITY, {"name": name})
        for relation in relations:
            thought = self.rows.get((current, relation))
            if thought is None:
                return Result(C.MISSING_FACT, {"subject": current, "relation": relation})
            if thought.qualifiers:
                return Result(C.MISSING_FACT, {"subject": current, "relation": relation,
                                               "reason": "qualified"})
            value = thought.value.to_v1_value()
            if "entity" in value:
                current = value["entity"]
            else:
                return Result(C.OK, {"answer": value["literal"], "source": thought.source})
        return Result(C.OK, {"answer": self.entities.get(current, current),
                             "source": "taught"})

    def __getattr__(self, name):
        raise AttributeError(name)
