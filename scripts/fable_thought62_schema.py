"""Thought format v3 (doc 67) -- a WRAPPER around v2 (never an edit).

Doc 56's extensions 1 and 2, nothing else:

  (a) no-value rows: value kinds ``link`` (a URL-only sentence) and ``empty``
      (the sentence states no usable value) with a ``reason`` in
      {fragment, absent, metadata}.  They are STORED as source ``proposed``
      and NEVER answer through ask()/ask_group() -- not even after a promote
      attempt (promote of a no-value row is refused).
  (b) ``group_id``: an optional string shared by 2+ ordinary rows that form
      one claim (multi-claim split, list, table).  The group gate answers a
      group only when EVERY member matches the question's constraints, else
      MISSING_FACT with reason ``partial_group``.

Storage: one events.jsonl, one hash chain -- every v3 row is written through
the unmodified v2 ThoughtNotebook (which itself wraps the unmodified M1
contract notebook), with the full v3 record embedded under
``provenance["thought_v2"]``:

  ungrouped ordinary row -> embedded record is EXACTLY the v2 dict, so
      ThoughtV2.to_v1() and ThoughtV3.to_v1() are byte-identical (mark T5);
      v2-only readers see the row natively;
  grouped ordinary row   -> embedded record is the v2 dict plus ``group_id``;
      v2-only readers see an ordinary row (group_id ignored), v3 readers see
      the group;
  link/empty row         -> embedded record is the v3 dict (schema
      fable_thought62); v2-only readers fail to parse it and ignore the row
      (it could never answer anyway: source is proposed).

to_v1(): link/empty rows have NO v1 projection (SchemaError -- they are
dropped by project_to_v1); grouped members project as ordinary rows tagged
with the group id in the raw source string and in provenance["group_id"];
ungrouped rows project byte-identically to v2.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional, Tuple

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_notebook_contract as C                      # noqa: E402
import fable_thought49_schema as V2                      # noqa: E402
from fable_thought49_notebook import (                   # noqa: E402
    ThoughtNotebook as V2Notebook,
    _qualifiers_match as _v2_qualifiers_match,
    _BadQualifiers,
    ACTOR_FOR_SOURCE,
)

Result = C.Result

SCHEMA = "fable_thought62"
FORMAT_VERSION = 3

VALUE_KINDS_V3 = V2.VALUE_KINDS + ("link", "empty")
EMPTY_REASONS = ("fragment", "absent", "metadata")
NO_VALUE_KINDS = ("link", "empty")


class SchemaError(V2.SchemaError):
    """Structural v3 violation (subclasses the v2 error, so v2 code paths agree)."""


def _nonempty_str(name: str, val) -> None:
    if not isinstance(val, str) or not val.strip() or val != val.strip():
        raise SchemaError("%s must be a non-empty string without surrounding "
                          "whitespace" % name)


# ------------------------------------------------------------------- Value3
@dataclass(frozen=True)
class Value3:
    """v2 typed value plus link (url + reason) and empty (reason only)."""

    kind: str
    entity: Optional[str] = None
    number: Optional[float] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    text: Optional[str] = None
    boolean: Optional[bool] = None
    link: Optional[str] = None
    reason: Optional[str] = None

    @classmethod
    def of_link(cls, url: str, reason: str = "metadata") -> "Value3":
        return cls("link", link=url, reason=reason)

    @classmethod
    def of_empty(cls, reason: str) -> "Value3":
        return cls("empty", reason=reason)

    def validate(self) -> None:
        if self.kind not in VALUE_KINDS_V3:
            raise SchemaError("unknown value kind %r" % (self.kind,))
        if self.kind in NO_VALUE_KINDS:
            if self.reason not in EMPTY_REASONS:
                raise SchemaError("link/empty need reason in %r, got %r"
                                  % (list(EMPTY_REASONS), self.reason))
            if self.kind == "link":
                if (not isinstance(self.link, str)
                        or not V2._URL_RE.match(self.link)):
                    raise SchemaError("link value needs an http(s) url")
            elif self.link is not None:
                raise SchemaError("empty value carries a link")
            extra = (self.entity, self.number, self.date, self.text,
                     self.boolean, self.unit)
            if any(part is not None for part in extra):
                raise SchemaError("%s value carries ordinary fields" % self.kind)
            return
        if self.link is not None or self.reason is not None:
            raise SchemaError("ordinary value carries link/empty fields")
        self.to_v2_value().validate()

    def to_v2_value(self) -> V2.Value:
        if self.kind in NO_VALUE_KINDS:
            raise SchemaError("%s values have no v2 projection" % self.kind)
        return V2.Value(kind=self.kind, entity=self.entity, number=self.number,
                        unit=self.unit, date=self.date, text=self.text,
                        boolean=self.boolean)

    def to_v1_value(self) -> dict:
        return self.to_v2_value().to_v1_value()

    def to_dict(self) -> dict:
        self.validate()
        if self.kind in NO_VALUE_KINDS:
            out = {"kind": self.kind, "reason": self.reason}
            if self.kind == "link":
                out["link"] = self.link
            return out
        return self.to_v2_value().to_dict()

    @classmethod
    def from_dict(cls, data: dict) -> "Value3":
        kind = data.get("kind")
        if kind in NO_VALUE_KINDS:
            val = cls(kind=kind, link=data.get("link"),
                      reason=data.get("reason"))
        else:
            val = cls(kind=kind, entity=data.get("entity"),
                      number=data.get("number"), unit=data.get("unit"),
                      date=data.get("date"), text=data.get("text"),
                      boolean=data.get("boolean"))
        val.validate()
        return val


# --------------------------------------------------------------- ThoughtV3
@dataclass(frozen=True)
class ThoughtV3:
    """One v3 thought: a v2 row plus optional group_id; value may be link/empty."""

    subject: str
    relation: str
    value: Value3
    provenance: V2.Provenance
    relation_id: Optional[str] = None
    qualifiers: Tuple[V2.Qualifier, ...] = field(default_factory=tuple)
    confidence: Optional[float] = 1.0
    source: str = V2.CLAIM_WEB
    rule_id: Optional[str] = None
    deps: Tuple[str, ...] = field(default_factory=tuple)
    group_id: Optional[str] = None
    thought_id: Optional[str] = None
    mark: Optional[str] = None
    marked_by: Optional[str] = None

    def __post_init__(self) -> None:
        self.validate(strict=False)

    @property
    def is_no_value(self) -> bool:
        return self.value.kind in NO_VALUE_KINDS

    def validate(self, strict: bool = False) -> None:
        if self.group_id is not None:
            _nonempty_str("group_id", self.group_id)
        if self.is_no_value:
            if self.source != "proposed":
                raise SchemaError("link/empty rows must be stored as "
                                  "source='proposed', got %r" % (self.source,))
            if self.group_id is not None:
                raise SchemaError("link/empty rows cannot join a group")
            self._validate_common()
            self.value.validate()
            self.provenance.validate(strict=False)
            if strict and not self.provenance.sentence.strip():
                raise SchemaError("no-value row needs the sentence it "
                                  "was converted from")
            return
        inner = self._to_v2(validated=False)
        try:
            inner.validate(strict=False)
        except V2.SchemaError as exc:
            raise SchemaError(str(exc))
        self.value.validate()
        if strict:
            inner.validate(strict=True)

    def _validate_common(self) -> None:
        if not isinstance(self.subject, str) or not V2._ENTITY_RE.match(self.subject):
            raise SchemaError("subject must be an entity id E####")
        if (not isinstance(self.relation, str) or not self.relation.strip()
                or self.relation != self.relation.strip()):
            raise SchemaError("relation must be a non-empty string without "
                              "surrounding whitespace")
        if self.relation_id is not None and not str(self.relation_id).strip():
            raise SchemaError("relation_id must be a non-empty string or None")
        if self.source not in V2.V1_SOURCES:
            raise SchemaError("unknown source %r" % (self.source,))
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(
                    self.confidence, (int, float)):
                raise SchemaError("confidence must be a number or None")
            if not (0.0 <= float(self.confidence) <= 1.0):
                raise SchemaError("confidence must lie in [0, 1]")
        for qual in self.qualifiers:
            qual.validate()

    def _to_v2(self, validated: bool = True) -> V2.ThoughtV2:
        """The inner v2 row (raises SchemaError for link/empty)."""
        row = V2.ThoughtV2(
            subject=self.subject, relation=self.relation,
            value=self.value.to_v2_value(), provenance=self.provenance,
            relation_id=self.relation_id, qualifiers=self.qualifiers,
            confidence=self.confidence, source=self.source,
            rule_id=self.rule_id, deps=self.deps, thought_id=self.thought_id,
            mark=self.mark, marked_by=self.marked_by)
        if validated:
            row.validate(strict=False)
        return row

    # ------------------------------------------------------------- adapters
    def to_v1(self) -> dict:
        """A legal assert_fact() payload.

        Link/empty rows have no projection (SchemaError -- dropped).  Grouped
        members project as ordinary rows tagged with the group id in the raw
        source string and provenance["group_id"].  Ungrouped rows project
        byte-identically to v2.
        """
        if self.is_no_value:
            raise SchemaError("%s rows have no v1 projection (dropped)"
                              % self.value.kind)
        self.validate(strict=True)
        payload = self._to_v2().to_v1()
        if self.group_id is not None:
            payload["raw"] = "%s [group %s]" % (payload["raw"], self.group_id)
            payload["provenance"]["group_id"] = self.group_id
            embedded = payload["provenance"]["thought_v2"]
            embedded["group_id"] = self.group_id
        return payload

    def to_dict(self) -> dict:
        self.validate(strict=False)
        out = {
            "schema": SCHEMA,
            "v": FORMAT_VERSION,
            "subject": self.subject,
            "relation": self.relation,
            "value": self.value.to_dict(),
            "provenance": self.provenance.to_dict(),
            "qualifiers": [q.to_dict() for q in self.qualifiers],
            "confidence": self.confidence,
            "source": self.source,
            "deps": list(self.deps),
        }
        if self.relation_id is not None:
            out["relation_id"] = self.relation_id
        if self.mark is not None:
            out["mark"] = self.mark
        if self.marked_by is not None:
            out["marked_by"] = self.marked_by
        if self.rule_id is not None:
            out["rule_id"] = self.rule_id
        if self.thought_id is not None:
            out["thought_id"] = self.thought_id
        if self.group_id is not None:
            out["group_id"] = self.group_id
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "ThoughtV3":
        return cls(
            subject=data.get("subject", ""),
            relation=data.get("relation", ""),
            value=Value3.from_dict(data.get("value") or {}),
            provenance=V2.Provenance.from_dict(data.get("provenance") or {}),
            relation_id=data.get("relation_id"),
            qualifiers=tuple(V2.Qualifier.from_dict(q)
                             for q in (data.get("qualifiers") or [])),
            confidence=data.get("confidence"),
            source=data.get("source", V2.CLAIM_WEB),
            rule_id=data.get("rule_id"),
            deps=tuple(data.get("deps") or ()),
            group_id=data.get("group_id"),
            thought_id=data.get("thought_id"),
            mark=data.get("mark"),
            marked_by=data.get("marked_by"),
        )

    @classmethod
    def from_v2(cls, row: V2.ThoughtV2,
                group_id: Optional[str] = None) -> "ThoughtV3":
        val = row.value
        value = Value3(kind=val.kind, entity=val.entity, number=val.number,
                       unit=val.unit, date=val.date, text=val.text,
                       boolean=val.boolean)
        return cls(subject=row.subject, relation=row.relation, value=value,
                   provenance=row.provenance, relation_id=row.relation_id,
                   qualifiers=row.qualifiers, confidence=row.confidence,
                   source=row.source, rule_id=row.rule_id, deps=row.deps,
                   group_id=group_id, thought_id=row.thought_id, mark=row.mark,
                   marked_by=row.marked_by)

    def content_event_id(self) -> str:
        payload = self.to_dict()
        payload.pop("thought_id", None)
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "t62-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def project_to_v1(rows: list) -> list:
    """Project v3 rows to v1 payloads; link/empty rows are dropped."""
    out = []
    for row in rows:
        try:
            out.append(row.to_v1())
        except SchemaError:
            continue
    return out


# ------------------------------------------------------- notebook wrapper
class ThoughtNotebook3:
    """Duck-types the v2 ThoughtNotebook API (composition, no edits), plus
    group/no-value behaviour.  Everything not defined here is the v2 wrapper
    (and through it, the contract notebook)."""

    FORMAT = 3

    def __init__(self, root) -> None:
        self.v2 = V2Notebook(root)
        self.root = Path(root)
        self.thoughts3: dict = {}
        self._rebuild_index()

    def __getattr__(self, name):
        v2 = self.__dict__.get("v2")
        if v2 is None:
            raise AttributeError(name)
        return getattr(v2, name)

    # ---------------------------------------------------------------- index
    def _rebuild_index(self) -> None:
        self.thoughts3 = {}
        for fact_id in list(self.v2.nb.facts):
            self._index_one(fact_id)

    def _raw_embedded(self, fact_id: str):
        fact = self.v2.nb.facts.get(fact_id) or {}
        return (fact.get("provenance") or {}).get("thought_v2")

    def _index_one(self, fact_id: str) -> Optional[ThoughtV3]:
        if fact_id in self.thoughts3:
            return self.thoughts3[fact_id]
        embedded = self._raw_embedded(fact_id)
        thought: Optional[ThoughtV3] = None
        try:
            if isinstance(embedded, dict) and embedded.get("schema") == SCHEMA:
                thought = ThoughtV3.from_dict(embedded)
            elif isinstance(embedded, dict) and embedded.get("group_id"):
                thought = ThoughtV3.from_v2(V2.ThoughtV2.from_dict(embedded),
                                            group_id=embedded.get("group_id"))
            else:
                v2row = self.v2._index_one(fact_id)
                if v2row is not None:
                    thought = ThoughtV3.from_v2(v2row)
        except (SchemaError, V2.SchemaError):
            return None
        if thought is not None:
            thought = replace(thought, thought_id=fact_id)
            mark = self.v2.marks.get(fact_id)
            if mark:
                thought = replace(thought, mark=mark["mark"],
                                  marked_by=mark.get("by"))
            self.thoughts3[fact_id] = thought
        return thought

    # --------------------------------------------------------------- writes
    def add_thought3(self, thought: ThoughtV3,
                     event_id: Optional[str] = None, *,
                     correction: bool = False, raw: Optional[str] = None,
                     strict: bool = True) -> Result:
        if thought.relation_id is None and not thought.is_no_value:
            suggestion = V2.suggest_relation_id(thought.relation)
            if suggestion:
                thought = replace(thought, relation_id=suggestion)
        try:
            thought.validate(strict=strict)
        except (SchemaError, V2.SchemaError) as exc:
            return Result(C.BAD_REQUEST, {"reason": str(exc)})
        if thought.subject not in self.v2.nb.entities:
            return Result(C.BAD_REQUEST, {"reason": "unknown subject id"})
        if thought.is_no_value:
            payload = self._no_value_payload(thought, raw=raw)
            source = payload.pop("source")
            actor = ACTOR_FOR_SOURCE.get(source, "thinking")
        else:
            try:
                payload = thought.to_v1()
            except (SchemaError, V2.SchemaError) as exc:
                return Result(C.BAD_REQUEST, {"reason": str(exc)})
            source = payload.pop("source")
            actor = ACTOR_FOR_SOURCE.get(source)
            if actor is None:
                return Result(C.BAD_REQUEST, {"reason": "unknown source"})
            if raw is not None:
                payload["raw"] = raw
                if thought.group_id is not None:
                    payload["raw"] = "%s [group %s]" % (raw, thought.group_id)
        if event_id is None:
            event_id = thought.content_event_id()
        result = self.v2.nb.assert_fact(event_id, actor, source,
                                        correction=correction, **payload)
        if result.status == C.SAVED:
            fact_id = result.detail["fact_id"]
            self.thoughts3[fact_id] = replace(thought, thought_id=fact_id)
        return result

    def _no_value_payload(self, thought: ThoughtV3,
                          raw: Optional[str] = None) -> dict:
        """A legal assert_fact() payload whose v1 value is a dummy literal.

        The row can never answer: source is proposed (outside
        ANSWERING_SOURCES), and the wrapper ask gate skips no-value rows
        explicitly as defence in depth.
        """
        if thought.value.kind == "link":
            dummy = "(link: %s)" % thought.value.link
        else:
            dummy = "(empty: %s)" % thought.value.reason
        embedded = thought.to_dict()
        embedded.pop("thought_id", None)
        provenance = {
            "url": thought.provenance.url,
            "quoted_span": thought.provenance.sentence,
            "document": thought.provenance.document,
            "claimed_by": thought.provenance.claimed_by,
            "confidence": thought.confidence,
            "thought_v2": embedded,
        }
        return {
            "subject": thought.subject,
            "relation": thought.relation,
            "value": {"literal": dummy},
            "source": "proposed",
            "raw": raw if raw is not None else thought.provenance.sentence,
            "rule_id": None,
            "deps": [],
            "provenance": provenance,
        }

    # v2-compatible alias: plain ThoughtV2 rows go through unchanged
    def add_thought(self, thought, event_id=None, *, correction=False,
                    raw=None, strict=True) -> Result:
        if isinstance(thought, ThoughtV3):
            return self.add_thought3(thought, event_id, correction=correction,
                                     raw=raw, strict=strict)
        result = self.v2.add_thought(thought, event_id, correction=correction,
                                     raw=raw, strict=strict)
        if result.status == C.SAVED:
            self._index_one(result.detail["fact_id"])
        return result

    def promote(self, event_id: str, actor: str, fact_id: str) -> Result:
        """Ben approves a proposed / quarantined row.  No-value rows are
        REFUSED (they never answer, so there is nothing to promote into an
        answer).  Group membership survives promotion."""
        if self.v2.nb._dup(event_id):
            return Result(C.DUPLICATE_OK)
        if actor != "ben":
            return Result(C.NOT_ALLOWED, {"actor": actor})
        fact = self.v2.nb.facts.get(fact_id)
        if fact is None or fact["source"] not in ("proposed", "web-quarantine"):
            return Result(C.BAD_REQUEST,
                           {"reason": "only proposed or quarantined rows promote"})
        old = self._index_one(fact_id)
        if old is None:
            return Result(C.BAD_REQUEST, {"reason": "unknown row"})
        if old.is_no_value:
            return Result(C.BAD_REQUEST,
                           {"reason": "link/empty rows never promote and never answer"})
        taught = replace(
            old, source="taught", confidence=1.0, rule_id=None, deps=(),
            thought_id=None, mark=None, marked_by=None,
            provenance=replace(old.provenance, claimed_by=V2.CLAIM_TAUGHT,
                               promoted_from=fact_id))
        result = self.add_thought3(taught, event_id=event_id, correction=True,
                                   raw="promoted from %s" % fact_id,
                                   strict=False)
        if result.status != C.SAVED:
            return result
        self._mark_conflicting_loser(result.detail["fact_id"], taught)
        return result

    def _mark_conflicting_loser(self, taught_fid: str,
                                taught: ThoughtV3) -> None:
        for fid, thought in list(self.thoughts3.items()):
            if (fid == taught_fid or thought.mark is not None
                    or thought.is_no_value
                    or thought.source not in ("proposed", "web-quarantine")
                    or thought.subject != taught.subject
                    or thought.relation != taught.relation
                    or not self.v2.nb.active(fid)
                    or thought.value.to_dict() == taught.value.to_dict()):
                continue
            self.v2._mark(fid, V2.MARK_SUPERSEDED_BY_PROMOTION, taught_fid)

    # ---------------------------------------------------------------- reads
    def get_thought3(self, fact_id: str) -> Optional[ThoughtV3]:
        if fact_id in self.v2.nb.facts:
            return self._index_one(fact_id)
        return self.thoughts3.get(fact_id)

    def get_thought(self, fact_id: str):
        return self.get_thought3(fact_id)

    def thoughts_for3(self, subject: str, relation: Optional[str] = None,
                      *, active_only: bool = True,
                      group_id: Optional[str] = None) -> list:
        for fact_id in list(self.v2.nb.facts):
            self._index_one(fact_id)
        rows = []
        for fact_id, thought in self.thoughts3.items():
            if thought.subject != subject:
                continue
            if relation is not None and thought.relation != relation:
                continue
            if group_id is not None and thought.group_id != group_id:
                continue
            if active_only and not self.v2.nb.active(fact_id):
                continue
            rows.append(thought)
        rows.sort(key=lambda t: self.v2.nb.facts[t.thought_id]["n"])
        return rows

    def thoughts_for(self, subject, relation=None, *, active_only=True):
        return self.thoughts_for3(subject, relation, active_only=active_only)

    def group_members(self, group_id: str, *,
                      active_only: bool = True) -> list:
        _nonempty_str("group_id", group_id)
        for fact_id in list(self.v2.nb.facts):
            self._index_one(fact_id)
        rows = [t for t in self.thoughts3.values()
                if t.group_id == group_id
                and (not active_only or self.v2.nb.active(t.thought_id))]
        rows.sort(key=lambda t: self.v2.nb.facts[t.thought_id]["n"])
        return rows

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
        """v2 qualifier gate plus v3 rules: no-value rows never pass; grouped
        rows never answer single-row questions (ask_group answers groups)."""
        kept, qualified_miss, group_hit = [], False, False
        for row in rows:
            thought = self._index_one(row["fact_id"])
            if thought is None or thought.is_no_value:
                continue
            if thought.group_id is not None:
                group_hit = True
                continue
            if not thought.qualifiers:
                kept.append(row)
            elif _v2_qualifiers_match(thought.qualifiers, required):
                kept.append(row)
            else:
                qualified_miss = True
        return kept, qualified_miss, group_hit

    def ask(self, name: str, relations: list, entity_id: Optional[str] = None,
            qualifiers=None) -> Result:
        """The v2 hop loop over ungrouped ordinary rows.  No-value rows never
        answer; grouped members abstain here with reason=partial_group (use
        ask_group for the whole group)."""
        if not relations or len(relations) > C.MAX_HOPS:
            return Result(C.BAD_REQUEST, {"reason": "need 1-%d hops" % C.MAX_HOPS})
        try:
            hop_req = self._hop_requirements(relations, qualifiers)
        except _BadQualifiers:
            return Result(C.BAD_REQUEST, {
                "reason": "qualifiers must be None, a dict, or a list parallel to relations"})
        if entity_id is None:
            found = self.v2.nb.resolve(name)
            if found.status != C.OK:
                return found
            entity_id = found.detail["entity_id"]
        elif entity_id not in self.v2.nb.entities:
            return Result(C.BAD_REQUEST, {"reason": "unknown entity id"})
        trail: list = []
        value: dict = {"entity": entity_id}
        for hop, relation in enumerate(relations):
            if "entity" not in value:
                return Result(C.BROKEN_CHAIN, {
                    "subject": self.v2.nb.entities[entity_id],
                    "relation": relations[hop - 1],
                    "value": self.v2.nb._show(value), "hop": hop, "trail": trail})
            entity_id = value["entity"]
            rows, qualified_miss, group_hit = self._gate(
                self.v2.nb.current(entity_id, relation), hop_req[hop])
            if not rows:
                detail = {"subject": self.v2.nb.entities[entity_id],
                          "relation": relation, "hop": hop + 1, "trail": trail}
                if group_hit:
                    detail["reason"] = "partial_group"
                elif qualified_miss:
                    detail["reason"] = "qualified"
                return Result(C.MISSING_FACT, detail)
            if relation in self.v2.nb.functional or len(rows) == 1:
                value = rows[0]["value"]
                trail.append(rows[0]["fact_id"])
            else:
                answer = ", ".join(self.v2.nb._show(row["value"]) for row in rows)
                return Result(C.OK, {"answer": answer,
                                     "trail": trail + [r["fact_id"] for r in rows],
                                     "source": rows[0]["source"], "multi": True})
        return Result(C.OK, {"answer": self.v2.nb._show(value), "trail": trail,
                             "source": self.v2.nb.facts[trail[-1]]["source"]})

    def ask_group(self, name: str, group_id: str,
                  qualifiers: Optional[dict] = None,
                  entity_id: Optional[str] = None) -> Result:
        """Answer a whole group: OK only when EVERY member matches the
        question's constraints (active, answering source, qualifier match);
        else MISSING_FACT with reason=partial_group.  No-value rows can never
        be members, so a group answer is always a real claim."""
        _nonempty_str("group_id", group_id)
        required = dict(qualifiers or {})
        if entity_id is None:
            found = self.v2.nb.resolve(name)
            if found.status != C.OK:
                return found
            entity_id = found.detail["entity_id"]
        elif entity_id not in self.v2.nb.entities:
            return Result(C.BAD_REQUEST, {"reason": "unknown entity id"})
        members = [t for t in self.group_members(group_id, active_only=False)
                   if t.subject == entity_id]
        live = [t for t in members if self.v2.nb.active(t.thought_id)]
        if len(members) < 2 or len(live) < 2:
            return Result(C.MISSING_FACT, {"subject": self.v2.nb.entities[entity_id],
                                           "reason": "partial_group",
                                           "group_id": group_id})
        # Only answering-source rows can carry the answer; a proposed original
        # whose identical taught promotion exists counts as covered by it.
        taught = [t for t in live
                  if t.source in V2.ANSWERING_SOURCES and not t.is_no_value
                  and (not t.qualifiers
                       or _v2_qualifiers_match(t.qualifiers, required))]
        if len(taught) < 2:
            return Result(C.MISSING_FACT, {
                "subject": self.v2.nb.entities[entity_id],
                "reason": "partial_group", "group_id": group_id})
        covered = []
        for thought in live:
            if thought in taught:
                covered.append(thought)
                continue
            if any(t.subject == thought.subject and t.relation == thought.relation
                   and t.value.to_dict() == thought.value.to_dict()
                   for t in taught):
                continue
            return Result(C.MISSING_FACT, {
                "subject": self.v2.nb.entities[entity_id],
                "reason": "partial_group", "group_id": group_id})
        parts, trail, sources = [], [], set()
        for thought in taught:
            parts.append("%s: %s" % (
                thought.relation,
                self.v2.nb._show(thought.value.to_v1_value())))
            trail.append(thought.thought_id)
            sources.add(thought.source)
        source = "taught" if sources == {"taught"} else sorted(sources)[0]
        return Result(C.OK, {"answer": "; ".join(parts), "trail": trail,
                             "source": source, "group_id": group_id,
                             "members": len(taught)})
