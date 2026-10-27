"""Thought format v2 (design doc 49) -- schema + v1 adapters. Plain software, no model.

WHY THIS EXISTS
  The Milestone-1 notebook fact is ``(subject, relation, object) + source tag`` over a
  closed relation list.  A paper sentence like "Method X improves accuracy on Y by 12%
  when Z" has nowhere to go: open relation, a NUMBER with a unit, two conditions, and a
  claim that is not yet believed.  The v2 row widens the format WITHOUT touching the v1
  contract guarantees:

    append-only hash chain        -- v2 rows live inside the v1 events.jsonl (embedded
                                     under provenance.thought_v2), so the chain, fsync
                                     read-back, torn-tail handling and tamper detection
                                     are inherited unchanged
    stable entity IDs + aliases    -- subject is still an E#### id; names are still
                                     aliases; AMBIGUOUS still never guesses
    source tags                    -- the v1 ``source`` field is kept as the
                                     ANSWERABILITY class; a new provenance record says
                                     WHO claimed the sentence (taught | paper:P |
                                     web-quarantine | system:<source>)
    supersede-not-delete           -- unchanged; corrections still supersede
    inferences never overwrite     -- unchanged; source priority lives in the contract
    taught
    AMBIGUOUS never guesses        -- unchanged; schema never parses a literal back into
                                      a number/entity on load (degrade to text instead)

ADAPTERS
  to_v1()    -> a legal fable_notebook_contract.assert_fact() payload.  Lossy by
                design: qualifiers are not projected into relation/value (they survive
                only inside the embedded v2 record), so the old hop loop answers the
                bare claim.
  from_v1()  -> ThoughtV2 from any v1 FACT event.  Exact when the event carries the
                embedded v2 record; otherwise DEGRADED (qualifiers=(), confidence=None,
                literal -> text value) -- degraded fields are blank, never guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Optional, Tuple

FORMAT_VERSION = 2
SCHEMA = "fable_thought49"

VALUE_KINDS = ("entity", "number", "date", "text", "boolean")

# v1 source tags (answerability classes) -- mirrored from fable_notebook_contract
V1_SOURCES = ("taught", "proposed", "inferred", "web-quarantine", "sleep-derived",
              "web-verified")
ANSWERING_SOURCES = ("taught", "inferred", "sleep-derived", "web-verified")

# claimed_by vocabulary
CLAIM_TAUGHT = "taught"
CLAIM_WEB = "web-quarantine"
CLAIM_PAPER_PREFIX = "paper:"
CLAIM_SYSTEM_PREFIX = "system:"

LEGACY_DOCUMENT = "v1-legacy"          # only document allowed an empty sentence quote
_ENTITY_RE = re.compile(r"^E\d+$")
_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")   # YYYY / YYYY-MM / YYYY-MM-DD
_URL_RE = re.compile(r"^https?://")


class SchemaError(ValueError):
    """Raised on construction of a structurally invalid v2 row."""


def number_literal(number: float, unit: Optional[str]) -> str:
    """Deterministic v1 rendering of a number+unit (the quote keeps the original text)."""
    text = "{:g}".format(float(number))
    if not unit:
        return text
    if unit == "%":
        return text + "%"
    return text + " " + unit


# --------------------------------------------------------------------- values
@dataclass(frozen=True)
class Value:
    """Typed object: entity id | number+unit | ISO date | text span | boolean."""

    kind: str
    entity: Optional[str] = None
    number: Optional[float] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    text: Optional[str] = None
    boolean: Optional[bool] = None

    # ---------------------------------------------------------- constructors
    @classmethod
    def of_entity(cls, entity_id: str) -> "Value":
        return cls("entity", entity=entity_id)

    @classmethod
    def of_number(cls, number: float, unit: Optional[str] = None) -> "Value":
        return cls("number", number=float(number), unit=unit)

    @classmethod
    def of_date(cls, date: str) -> "Value":
        return cls("date", date=date)

    @classmethod
    def of_text(cls, text: str) -> "Value":
        return cls("text", text=text)

    @classmethod
    def of_boolean(cls, boolean: bool) -> "Value":
        return cls("boolean", boolean=boolean)

    # ------------------------------------------------------------ validation
    def validate(self) -> None:
        if self.kind not in VALUE_KINDS:
            raise SchemaError("unknown value kind %r" % (self.kind,))
        if self.kind == "entity":
            if not self.entity or not _ENTITY_RE.match(self.entity):
                raise SchemaError("entity value needs an E#### id")
            extra = (self.number, self.date, self.text, self.boolean, self.unit)
            if any(part is not None for part in extra):
                raise SchemaError("entity value carries extra fields")
        elif self.kind == "number":
            if self.number is None or isinstance(self.number, bool):
                raise SchemaError("number value needs a number")
            if self.unit is not None and not isinstance(self.unit, str):
                raise SchemaError("unit must be a string or None")
            if any(part is not None for part in (self.entity, self.date, self.text,
                                                 self.boolean)):
                raise SchemaError("number value carries extra fields")
        elif self.kind == "date":
            if not self.date or not _DATE_RE.match(self.date):
                raise SchemaError("date must be YYYY, YYYY-MM or YYYY-MM-DD")
            if any(part is not None for part in (self.entity, self.number, self.text,
                                                 self.boolean, self.unit)):
                raise SchemaError("date value carries extra fields")
        elif self.kind == "text":
            if self.text is None or not isinstance(self.text, str) or self.text == "":
                raise SchemaError("text value needs a non-empty string")
            if any(part is not None for part in (self.entity, self.number, self.date,
                                                 self.boolean, self.unit)):
                raise SchemaError("text value carries extra fields")
        else:  # boolean
            if not isinstance(self.boolean, bool):
                raise SchemaError("boolean value needs true/false")
            if any(part is not None for part in (self.entity, self.number, self.date,
                                                 self.text, self.unit)):
                raise SchemaError("boolean value carries extra fields")

    # ------------------------------------------------------------ projection
    def to_v1_value(self) -> dict:
        """The v1 ``value`` argument: {"entity": id} or {"literal": text}."""
        self.validate()
        if self.kind == "entity":
            return {"entity": self.entity}
        if self.kind == "number":
            return {"literal": number_literal(self.number, self.unit)}
        if self.kind == "date":
            return {"literal": self.date}
        if self.kind == "boolean":
            return {"literal": "true" if self.boolean else "false"}
        return {"literal": self.text}

    # ------------------------------------------------------------- serialize
    def to_dict(self) -> dict:
        self.validate()
        out = {"kind": self.kind}
        if self.kind == "entity":
            out["entity"] = self.entity
        elif self.kind == "number":
            out["number"] = self.number
            if self.unit is not None:
                out["unit"] = self.unit
        elif self.kind == "date":
            out["date"] = self.date
        elif self.kind == "text":
            out["text"] = self.text
        else:
            out["boolean"] = self.boolean
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Value":
        val = cls(
            kind=data.get("kind"),
            entity=data.get("entity"),
            number=data.get("number"),
            unit=data.get("unit"),
            date=data.get("date"),
            text=data.get("text"),
            boolean=data.get("boolean"),
        )
        val.validate()
        return val


# ---------------------------------------------------------------- qualifiers
@dataclass(frozen=True)
class Qualifier:
    """A condition attached to a claim: relation is an open string ("when",
    "on dataset", "compared to", ...); value is a typed Value."""

    relation: str
    value: Value

    def validate(self) -> None:
        if not isinstance(self.relation, str) or not self.relation.strip():
            raise SchemaError("qualifier needs a non-empty relation")
        self.value.validate()

    def to_dict(self) -> dict:
        self.validate()
        return {"relation": self.relation, "value": self.value.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "Qualifier":
        q = cls(relation=data.get("relation"), value=Value.from_dict(data.get("value") or {}))
        q.validate()
        return q


# --------------------------------------------------------------- provenance
@dataclass(frozen=True)
class Provenance:
    """Who claimed the sentence, and where the sentence can be read back."""

    document: str                     # doc id or URL (e.g. "webred:dev:12", arXiv URL)
    sentence: str                     # exact quote the row was converted from
    claimed_by: str                   # taught | paper:<id> | web-quarantine | system:<src>
    url: Optional[str] = None
    promoted_from: Optional[str] = None

    def validate(self, strict: bool = False) -> None:
        if not isinstance(self.document, str) or not self.document.strip():
            raise SchemaError("provenance needs a document")
        if not isinstance(self.sentence, str):
            raise SchemaError("provenance sentence must be a string")
        if self.url is not None and not _URL_RE.match(self.url):
            raise SchemaError("url must be http(s)")
        claimed = self.claimed_by
        ok = claimed in (CLAIM_TAUGHT, CLAIM_WEB)
        if claimed.startswith(CLAIM_PAPER_PREFIX) or claimed.startswith(CLAIM_SYSTEM_PREFIX):
            ok = len(claimed) > len(CLAIM_PAPER_PREFIX if claimed.startswith(CLAIM_PAPER_PREFIX)
                                    else CLAIM_SYSTEM_PREFIX)
        if not ok:
            raise SchemaError("claimed_by must be taught, web-quarantine, paper:<id>, "
                              "system:<source> -- got %r" % (claimed,))
        if strict and not self.sentence.strip() and self.document != LEGACY_DOCUMENT:
            raise SchemaError("claim needs the sentence it was converted from")
        if strict and self.promoted_from and not str(self.promoted_from).startswith("F"):
            raise SchemaError("promoted_from must be a fact id")

    def effective_url(self) -> Optional[str]:
        if self.url:
            return self.url
        if _URL_RE.match(self.document or ""):
            return self.document
        return None

    def to_dict(self) -> dict:
        out = {"document": self.document, "sentence": self.sentence,
               "claimed_by": self.claimed_by}
        if self.url is not None:
            out["url"] = self.url
        if self.promoted_from is not None:
            out["promoted_from"] = self.promoted_from
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Provenance":
        return cls(document=data.get("document", ""), sentence=data.get("sentence", ""),
                   claimed_by=data.get("claimed_by", CLAIM_SYSTEM_PREFIX + "unknown"),
                   url=data.get("url"), promoted_from=data.get("promoted_from"))


# ------------------------------------------------------------- the v2 thought
@dataclass(frozen=True)
class ThoughtV2:
    """One widened thought.  ``source`` is the v1 answerability class (unchanged
    contract semantics); ``provenance.claimed_by`` says WHO is speaking."""

    subject: str                                   # entity id E####
    relation: str                                  # OPEN relation string
    value: Value
    provenance: Provenance
    relation_id: Optional[str] = None              # optional canonical id ("mother", "P19")
    qualifiers: Tuple[Qualifier, ...] = field(default_factory=tuple)
    confidence: Optional[float] = 1.0              # None = not recorded (legacy v1 rows)
    source: str = CLAIM_WEB                        # v1 source tag
    rule_id: Optional[str] = None                  # for source == inferred
    deps: Tuple[str, ...] = field(default_factory=tuple)
    thought_id: Optional[str] = None               # assigned by the notebook (fact id)

    def __post_init__(self) -> None:
        self.validate(strict=False)

    # ------------------------------------------------------------ validation
    def validate(self, strict: bool = False) -> None:
        if not isinstance(self.subject, str) or not _ENTITY_RE.match(self.subject):
            raise SchemaError("subject must be an entity id E####")
        if not isinstance(self.relation, str) or not self.relation.strip():
            raise SchemaError("relation must be a non-empty string")
        if self.relation != self.relation.strip():
            raise SchemaError("relation must not have surrounding whitespace")
        if self.relation_id is not None and not str(self.relation_id).strip():
            raise SchemaError("relation_id must be a non-empty string or None")
        if self.source not in V1_SOURCES:
            raise SchemaError("unknown source %r" % (self.source,))
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
                raise SchemaError("confidence must be a number or None")
            if not (0.0 <= float(self.confidence) <= 1.0):
                raise SchemaError("confidence must lie in [0, 1]")
        self.value.validate()
        self.provenance.validate(strict=strict)
        for qual in self.qualifiers:
            qual.validate()
        if strict:
            if self.source == "taught" and self.provenance.claimed_by != CLAIM_TAUGHT:
                raise SchemaError("taught rows must be claimed by taught")
            if self.source == "web-quarantine" and not self.provenance.effective_url():
                raise SchemaError("web-quarantine needs a url (use source='proposed' "
                                  "for documents without one)")
            if self.source == "inferred" and (not self.rule_id or not self.deps):
                raise SchemaError("inferred needs rule_id and deps")
            if self.source != "inferred" and self.rule_id:
                raise SchemaError("rule_id is only for inferred rows")

    # ------------------------------------------------------------- adapters
    def v1_url(self) -> Optional[str]:
        return self.provenance.effective_url()

    def to_v1(self) -> dict:
        """A legal fable_notebook_contract.assert_fact() payload.

        Lossy: qualifiers/relation_id are not projected into the v1 fact fields --
        they survive only inside provenance["thought_v2"], which from_v1() reads back
        exactly.  The old hop loop therefore answers the BARE claim.
        """
        self.validate(strict=True)
        embedded = self.to_dict()
        embedded.pop("thought_id", None)
        provenance = {
            "url": self.v1_url(),
            "quoted_span": self.provenance.sentence,
            "document": self.provenance.document,
            "claimed_by": self.provenance.claimed_by,
            "confidence": self.confidence,
            "thought_v2": embedded,
        }
        if self.provenance.promoted_from is not None:
            provenance["promoted_from"] = self.provenance.promoted_from
        return {
            "subject": self.subject,
            "relation": self.relation,
            "value": self.value.to_v1_value(),
            "source": self.source,
            "raw": self.provenance.sentence,
            "rule_id": self.rule_id,
            "deps": list(self.deps),
            "provenance": provenance,
        }

    @classmethod
    def from_v1(cls, fact: dict) -> "ThoughtV2":
        """Rebuild a thought from a v1 FACT event (exact if embedded, else degraded)."""
        provenance = fact.get("provenance") or {}
        embedded = provenance.get("thought_v2")
        thought_id = fact.get("fact_id")
        if isinstance(embedded, dict):
            row = cls.from_dict(embedded)
            return replace(row, thought_id=thought_id)
        # Degraded path: blank fields, never guessed (no literal -> number parsing).
        raw_value = fact.get("value") or {}
        if "entity" in raw_value:
            value = Value.of_entity(raw_value["entity"])
        else:
            value = Value.of_text(str(raw_value.get("literal", ""))) \
                if str(raw_value.get("literal", "")) else Value.of_text("(empty)")
        source = fact.get("source", "proposed")
        if source == CLAIM_TAUGHT:
            claimed = CLAIM_TAUGHT
        elif source == CLAIM_WEB:
            claimed = CLAIM_WEB
        else:
            claimed = CLAIM_SYSTEM_PREFIX + source
        doc = provenance.get("document") or provenance.get("url") or LEGACY_DOCUMENT
        return cls(
            subject=fact.get("subject", ""),
            relation=fact.get("relation", ""),
            value=value,
            provenance=Provenance(
                document=doc,
                sentence=fact.get("raw") or provenance.get("quoted_span") or "",
                claimed_by=claimed,
                url=provenance.get("url"),
                promoted_from=provenance.get("promoted_from"),
            ),
            confidence=provenance.get("confidence"),
            source=source,
            rule_id=fact.get("rule_id"),
            deps=tuple(fact.get("deps") or ()),
            thought_id=thought_id,
        )

    # ------------------------------------------------------------- serialize
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
        if self.rule_id is not None:
            out["rule_id"] = self.rule_id
        if self.thought_id is not None:
            out["thought_id"] = self.thought_id
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "ThoughtV2":
        return cls(
            subject=data.get("subject", ""),
            relation=data.get("relation", ""),
            value=Value.from_dict(data.get("value") or {}),
            provenance=Provenance.from_dict(data.get("provenance") or {}),
            relation_id=data.get("relation_id"),
            qualifiers=tuple(Qualifier.from_dict(q) for q in (data.get("qualifiers") or [])),
            confidence=data.get("confidence"),
            source=data.get("source", CLAIM_WEB),
            rule_id=data.get("rule_id"),
            deps=tuple(data.get("deps") or ()),
            thought_id=data.get("thought_id"),
        )

    def content_event_id(self) -> str:
        """Deterministic event id: writing the same content twice is DUPLICATE_OK."""
        payload = self.to_dict()
        payload.pop("thought_id", None)
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "t49-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]
