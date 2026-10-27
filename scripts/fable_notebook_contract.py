"""Milestone 1 -- the NOTEBOOK CONTRACT as plain software (no model anywhere in this file).

Design sources: design/v3/28-outside-review-adjudication-fable.md (#13, #17, #18, M16-M21),
design/v3/30-modes/decided-inputs-fable.md, 32-ben-simplification-ruling.md.

THE CONTRACT
  * One append-only event log (``events.jsonl``).  Nothing is ever rewritten.  Every event
    carries the sha256 of the previous line, so reordering or editing is detected on load.
  * Entities have stable IDs (``E0001``); names are ALIASES that point at IDs.  Two people
    may share a name: resolving that name returns AMBIGUOUS, never a guess, never a merge.
  * Facts are ``(subject entity, relation, object)`` with a SOURCE tag:
        taught          only the LISTENING actor may write it
        proposed        a guess; never answers a question
        inferred        derived by a Ben-approved rule from listed dependency facts
        web-quarantine  text from the web; never answers a question until Ben promotes it
        sleep-derived   written by sleep; ranks below taught and inferred
  * Corrections SUPERSEDE, they do not delete.  A second different taught value without an
    explicit correction is refused with CONFLICT (LISTENING then asks Ben).
  * Inferred facts are invalidated automatically when any dependency stops being active.
    Inferences never overwrite taught facts.
  * Events are idempotent: replaying an event_id writes nothing and returns DUPLICATE_OK.
  * "saved" is only said after flush + fsync + read-back of the line (ack != success).
  * Questions run a HARD-CODED hop loop and return a discrete status, rendered through
    deterministic templates: OK, MISSING_FACT, BROKEN_CHAIN, AMBIGUOUS, UNKNOWN_ENTITY.
  * A torn final line (crash mid-write) is ignored on load and reported; a bad line in the
    middle is an error.

``--selftest`` runs the 30-sequence lifecycle suite against this notebook AND against a
naive last-write-wins dictionary; the naive one must fail (conformance: a test that a
naive version passes is not testing anything).
"""

from __future__ import annotations

from urllib.parse import urlparse

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_VERSION = 1
LOG_NAME = "events.jsonl"
GENESIS = "0" * 64

SOURCES = ("taught", "proposed", "inferred", "web-quarantine", "sleep-derived", "web-verified")
ANSWERING_SOURCES = ("taught", "inferred", "sleep-derived", "web-verified")  # priority order
MIN_WEB_DOMAINS = 2   # a web-verified row needs quotes from this many different websites
ACTORS = ("listening", "working", "creative", "thinking", "sleep", "ben")
WRITE_RIGHTS = {
    "listening": {"taught"},
    "working": {"proposed"},
    "creative": {"proposed"},
    "thinking": {"proposed", "web-quarantine", "inferred", "web-verified"},
    "sleep": {"sleep-derived", "inferred", "proposed"},
    "ben": set(),  # Ben speaks through LISTENING; 'ben' only approves, promotes, merges
}
MAX_HOPS = 8

# statuses
OK = "OK"
SAVED = "SAVED"
DUPLICATE_OK = "DUPLICATE_OK"
CONFLICT = "CONFLICT"
AMBIGUOUS = "AMBIGUOUS"
UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
MISSING_FACT = "MISSING_FACT"
BROKEN_CHAIN = "BROKEN_CHAIN"
NOT_ALLOWED = "NOT_ALLOWED"
BAD_REQUEST = "BAD_REQUEST"

TEMPLATES = {
    SAVED: "Saved: {text}.",
    DUPLICATE_OK: "I already have that.",
    CONFLICT: "I have {subject}'s {relation} as {old}. Do you want me to change it to {new}?",
    AMBIGUOUS: "I know more than one {name}: {choices}. Which one do you mean?",
    UNKNOWN_ENTITY: "I don't know anyone called {name}.",
    MISSING_FACT: "I don't know {subject}'s {relation}.",
    BROKEN_CHAIN: "{subject}'s {relation} is {value}, which is not someone I can look up.",
    OK: "{answer}.",
    NOT_ALLOWED: "That write is not allowed from {actor}.",
    BAD_REQUEST: "I could not use that: {reason}.",
}


class LogCorrupt(RuntimeError):
    pass


@dataclass
class Result:
    status: str
    detail: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (OK, SAVED, DUPLICATE_OK)

    def say(self) -> str:
        try:
            if self.status == OK and self.detail.get("source") == "web-verified":
                return TEMPLATES[OK].format(**self.detail) + " (I read that online; you didn't tell me.)"
            return TEMPLATES[self.status].format(**self.detail)
        except KeyError:
            return self.status


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


class Notebook:
    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / LOG_NAME
        self.torn_tail = False
        self._reset()
        self._load()

    # ------------------------------------------------------------------ state
    def _reset(self) -> None:
        self.events: list[dict] = []
        self.event_ids: set[str] = set()
        self.last_sha = GENESIS
        self.entities: dict[str, str] = {}          # entity_id -> display name
        self.aliases: dict[str, list[str]] = {}     # normalised alias -> [entity_id]
        self.facts: dict[str, dict] = {}            # fact_id -> fact event
        self.superseded: dict[str, str] = {}        # fact_id -> superseding fact_id
        self.retracted: set[str] = set()
        self.rules: dict[str, str] = {}             # approved rule_id -> body
        self.functional: set[str] = set()           # relations with one value
        self.merge_proposals: dict[str, dict] = {}

    def _load(self) -> None:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for number, line in enumerate(lines):
            last = number == len(lines) - 1
            try:
                event = json.loads(line)
                if event["prev"] != self.last_sha:
                    raise LogCorrupt(f"line {number + 1}: hash chain broken")
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                if last:
                    self.torn_tail = True  # crash mid-write: ignore, report
                    return
                raise LogCorrupt(f"line {number + 1}: {exc}") from exc
            self._apply(event)
            self.last_sha = _sha(line)

    # ------------------------------------------------------------ durable log
    def _append(self, event: dict) -> None:
        if self.torn_tail:
            raise LogCorrupt("torn final line present; run repair_torn_tail() first")
        event = dict(event, n=len(self.events) + 1, prev=self.last_sha, v=FORMAT_VERSION)
        line = json.dumps(event, sort_keys=True, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        with open(self.path, "rb") as handle:  # read-back before anyone says "saved"
            handle.seek(-(len(line.encode("utf-8")) + 1), os.SEEK_END)
            if handle.read().decode("utf-8") != line + "\n":
                raise LogCorrupt("read-back mismatch")
        self._apply(event)
        self.last_sha = _sha(line)

    def repair_torn_tail(self) -> None:
        """Copy the good prefix to a new file and swap it in (the torn bytes are kept)."""
        if not self.torn_tail:
            return
        raw = self.path.read_text(encoding="utf-8")
        good, _, torn = raw.rpartition("\n")
        (self.root / "torn-tail.txt").write_text(torn, encoding="utf-8")
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(good + "\n" if good else "", encoding="utf-8")
        os.replace(tmp, self.path)
        self.torn_tail = False
        self._reset()
        self._load()

    def _apply(self, event: dict) -> None:
        kind = event["kind"]
        if kind == "ENTITY":
            self.entities[event["entity_id"]] = event["name"]
            self.aliases.setdefault(_norm(event["name"]), []).append(event["entity_id"])
        elif kind == "ALIAS":
            ids = self.aliases.setdefault(_norm(event["alias"]), [])
            if event["entity_id"] not in ids:
                ids.append(event["entity_id"])
        elif kind == "FACT":
            self.facts[event["fact_id"]] = event
            if event.get("supersedes"):
                self.superseded[event["supersedes"]] = event["fact_id"]
        elif kind == "RETRACT":
            self.retracted.add(event["fact_id"])
        elif kind == "RULE":
            self.rules[event["rule_id"]] = event["body"]
        elif kind == "RELATION":
            if event["functional"]:
                self.functional.add(event["relation"])
        elif kind == "MERGE_PROPOSAL":
            self.merge_proposals[event["proposal_id"]] = event
        elif kind == "PROMOTE":
            pass  # promotion is recorded as a new taught FACT that supersedes; see promote()
        self.events.append(event)
        self.event_ids.add(event["event_id"])

    # ---------------------------------------------------------------- helpers
    def _dup(self, event_id: str) -> bool:
        return event_id in self.event_ids

    def active(self, fact_id: str) -> bool:
        fact = self.facts.get(fact_id)
        if fact is None or fact_id in self.retracted or fact_id in self.superseded:
            return False
        if fact["source"] == "inferred":
            if fact["rule_id"] not in self.rules:
                return False
            return all(self.active(dep) for dep in fact["deps"])
        return True

    def resolve(self, name: str) -> Result:
        ids = self.aliases.get(_norm(name), [])
        if not ids:
            return Result(UNKNOWN_ENTITY, {"name": name})
        if len(ids) > 1:
            choices = ", ".join(f"{self.entities[i]} ({i})" for i in ids)
            return Result(AMBIGUOUS, {"name": name, "choices": choices, "ids": list(ids)})
        return Result(OK, {"entity_id": ids[0], "answer": self.entities[ids[0]]})

    def current(self, entity_id: str, relation: str) -> list[dict]:
        """Active answering facts for (entity, relation), best source first."""
        rows = [
            fact for fact_id, fact in self.facts.items()
            if fact["subject"] == entity_id and fact["relation"] == relation
            and fact["source"] in ANSWERING_SOURCES and self.active(fact_id)
        ]
        rows.sort(key=lambda f: (ANSWERING_SOURCES.index(f["source"]), -f["n"]))
        if rows:  # inferences and sleep rows never stand beside a taught row
            best = rows[0]["source"]
            rows = [row for row in rows if row["source"] == best]
        return rows

    def _show(self, value: dict) -> str:
        return self.entities[value["entity"]] if "entity" in value else str(value["literal"])

    # ----------------------------------------------------------------- writes
    def declare_relation(self, event_id: str, relation: str, functional: bool) -> Result:
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        self._append({"kind": "RELATION", "event_id": event_id, "relation": relation,
                      "functional": bool(functional)})
        return Result(SAVED, {"text": f"relation {relation}"})

    def new_entity(self, event_id: str, name: str) -> Result:
        """Always creates a NEW person, even if the name is already known (two Miras)."""
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if not _norm(name):
            return Result(BAD_REQUEST, {"reason": "empty name"})
        entity_id = f"E{len(self.entities) + 1:04d}"
        self._append({"kind": "ENTITY", "event_id": event_id, "entity_id": entity_id,
                      "name": name.strip()})
        return Result(SAVED, {"text": f"{name.strip()} is {entity_id}", "entity_id": entity_id})

    def add_alias(self, event_id: str, entity_id: str, alias: str) -> Result:
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if entity_id not in self.entities or not _norm(alias):
            return Result(BAD_REQUEST, {"reason": "unknown entity or empty alias"})
        self._append({"kind": "ALIAS", "event_id": event_id, "entity_id": entity_id,
                      "alias": alias.strip()})
        return Result(SAVED, {"text": f"{alias.strip()} is another name for {self.entities[entity_id]}"})

    def approve_rule(self, event_id: str, actor: str, rule_id: str, body: str) -> Result:
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if actor != "ben":
            return Result(NOT_ALLOWED, {"actor": actor})
        self._append({"kind": "RULE", "event_id": event_id, "rule_id": rule_id, "body": body})
        return Result(SAVED, {"text": f"rule {rule_id}"})

    def assert_fact(self, event_id: str, actor: str, source: str, subject: str,
                    relation: str, value: dict, *, correction: bool = False,
                    raw: str | None = None, rule_id: str | None = None,
                    deps: tuple[str, ...] = (), provenance: dict | None = None) -> Result:
        """``subject`` is an entity_id; ``value`` is {"entity": id} or {"literal": text}."""
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if actor not in ACTORS or source not in SOURCES:
            return Result(BAD_REQUEST, {"reason": "unknown actor or source"})
        if source not in WRITE_RIGHTS[actor]:
            return Result(NOT_ALLOWED, {"actor": actor})
        if subject not in self.entities:
            return Result(BAD_REQUEST, {"reason": "unknown subject id"})
        if ("entity" in value) == ("literal" in value):
            return Result(BAD_REQUEST, {"reason": "value needs exactly one of entity/literal"})
        if "entity" in value and value["entity"] not in self.entities:
            return Result(BAD_REQUEST, {"reason": "unknown object id"})
        if source == "inferred":
            if rule_id not in self.rules:
                return Result(NOT_ALLOWED, {"actor": f"{actor} (rule not approved by Ben)"})
            if not deps or not all(self.active(dep) for dep in deps):
                return Result(BAD_REQUEST, {"reason": "inferred needs active dependency facts"})
        if source == "web-quarantine" and not (provenance and provenance.get("url")
                                               and provenance.get("quoted_span")):
            return Result(BAD_REQUEST, {"reason": "web rows need url and quoted_span"})
        if source == "web-verified":
            evidence = (provenance or {}).get("evidence") or []
            domains = {urlparse(e.get("url", "")).netloc.lower().removeprefix("www.")
                       for e in evidence if e.get("url") and e.get("quoted_span")} - {""}
            if len(domains) < MIN_WEB_DOMAINS:
                return Result(BAD_REQUEST, {
                    "reason": f"web-verified needs quotes from {MIN_WEB_DOMAINS} different websites"})

        supersedes = None
        if source in ANSWERING_SOURCES:
            same_source = [f for f in self.current(subject, relation) if f["source"] == source]
            for old in same_source:
                if old["value"] == value:
                    return Result(DUPLICATE_OK)
            if same_source and relation in self.functional:
                old = same_source[0]
                if source == "taught" and not correction:
                    return Result(CONFLICT, {
                        "subject": self.entities[subject], "relation": relation,
                        "old": self._show(old["value"]), "new": self._show(value),
                        "old_fact_id": old["fact_id"]})
                supersedes = old["fact_id"]

        fact_id = f"F{len(self.facts) + 1:05d}"
        self._append({"kind": "FACT", "event_id": event_id, "fact_id": fact_id, "actor": actor,
                      "source": source, "subject": subject, "relation": relation,
                      "value": value, "supersedes": supersedes, "raw": raw,
                      "rule_id": rule_id, "deps": list(deps), "provenance": provenance})
        text = f"{self.entities[subject]}'s {relation} is {self._show(value)}"
        return Result(SAVED, {"text": text, "fact_id": fact_id, "supersedes": supersedes})

    def retract(self, event_id: str, actor: str, fact_id: str, reason: str) -> Result:
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        fact = self.facts.get(fact_id)
        if fact is None:
            return Result(BAD_REQUEST, {"reason": "unknown fact"})
        if fact["source"] == "taught" and actor != "listening":
            return Result(NOT_ALLOWED, {"actor": actor})
        self._append({"kind": "RETRACT", "event_id": event_id, "fact_id": fact_id,
                      "actor": actor, "reason": reason})
        return Result(SAVED, {"text": f"forgot {fact_id}"})

    def promote(self, event_id: str, actor: str, fact_id: str) -> Result:
        """Ben approves a proposed / quarantined row; it becomes a taught row via LISTENING."""
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if actor != "ben":
            return Result(NOT_ALLOWED, {"actor": actor})
        fact = self.facts.get(fact_id)
        if fact is None or fact["source"] not in ("proposed", "web-quarantine"):
            return Result(BAD_REQUEST, {"reason": "only proposed or quarantined rows promote"})
        result = self.assert_fact(event_id, "listening", "taught", fact["subject"],
                                  fact["relation"], fact["value"], correction=True,
                                  raw=f"promoted from {fact_id}",
                                  provenance={"promoted_from": fact_id})
        return result

    def propose_merge(self, event_id: str, actor: str, keep: str, other: str) -> Result:
        """Identity merges are only ever PROPOSALS; nothing in the view changes."""
        if self._dup(event_id):
            return Result(DUPLICATE_OK)
        if keep not in self.entities or other not in self.entities or keep == other:
            return Result(BAD_REQUEST, {"reason": "bad entity ids"})
        self._append({"kind": "MERGE_PROPOSAL", "event_id": event_id, "proposal_id": event_id,
                      "actor": actor, "keep": keep, "other": other})
        return Result(SAVED, {"text": f"merge proposal {keep} <- {other} (waiting for Ben)"})

    # ------------------------------------------------------------------ reads
    def ask(self, name: str, relations: list[str], entity_id: str | None = None) -> Result:
        """``entity_id`` skips name lookup (used after Ben answered "which Mira?")."""
        if not relations or len(relations) > MAX_HOPS:
            return Result(BAD_REQUEST, {"reason": f"need 1-{MAX_HOPS} hops"})
        if entity_id is None:
            found = self.resolve(name)
            if found.status != OK:
                return found
            entity_id = found.detail["entity_id"]
        elif entity_id not in self.entities:
            return Result(BAD_REQUEST, {"reason": "unknown entity id"})
        trail: list[str] = []
        value: dict = {"entity": entity_id}
        for hop, relation in enumerate(relations):
            if "entity" not in value:
                return Result(BROKEN_CHAIN, {
                    "subject": self.entities[entity_id], "relation": relations[hop - 1],
                    "value": self._show(value), "hop": hop, "trail": trail})
            entity_id = value["entity"]
            rows = self.current(entity_id, relation)
            if not rows:
                return Result(MISSING_FACT, {"subject": self.entities[entity_id],
                                             "relation": relation, "hop": hop + 1, "trail": trail})
            if relation in self.functional or len(rows) == 1:
                value = rows[0]["value"]
                trail.append(rows[0]["fact_id"])
            else:
                answer = ", ".join(self._show(row["value"]) for row in rows)
                return Result(OK, {"answer": answer, "trail": trail + [r["fact_id"] for r in rows],
                                   "source": rows[0]["source"], "multi": True})
        return Result(OK, {"answer": self._show(value), "trail": trail,
                           "source": self.facts[trail[-1]]["source"]})


# ------------------------------------------------------------------ naive foil
class NaiveNotebook:
    """Last-write-wins dictionary keyed by NAME. Exists only to fail the suite."""

    def __init__(self, root) -> None:
        self.rows: dict[tuple[str, str], str] = {}
        self.functional: set[str] = set()
        self.names: dict[str, str] = {}
        self.entities = self.names

    def declare_relation(self, event_id, relation, functional):
        return Result(SAVED)

    def new_entity(self, event_id, name):
        self.names[_norm(name)] = name
        return Result(SAVED, {"entity_id": _norm(name)})

    def add_alias(self, event_id, entity_id, alias):
        self.names[_norm(alias)] = entity_id
        return Result(SAVED)

    def approve_rule(self, event_id, actor, rule_id, body):
        return Result(SAVED)

    def assert_fact(self, event_id, actor, source, subject, relation, value, **kw):
        self.rows[(subject, relation)] = value.get("entity") or value.get("literal")
        return Result(SAVED, {"fact_id": f"{subject}/{relation}"})

    def retract(self, event_id, actor, fact_id, reason):
        subject, relation = fact_id.split("/")
        self.rows.pop((subject, relation), None)
        return Result(SAVED)

    def promote(self, event_id, actor, fact_id):
        return Result(SAVED)

    def propose_merge(self, event_id, actor, keep, other):
        return Result(SAVED)

    def resolve(self, name):
        key = _norm(name)
        return Result(OK, {"entity_id": key}) if key in self.names else Result(UNKNOWN_ENTITY)

    def ask(self, name, relations):
        key = _norm(name)
        if key not in self.names:
            return Result(UNKNOWN_ENTITY)
        for relation in relations:
            if (key, relation) not in self.rows:
                return Result(MISSING_FACT)
            key = self.rows[(key, relation)]
        return Result(OK, {"answer": self.names.get(key, key)})


# ------------------------------------------------------------ lifecycle suite
def _setup(nb):
    for relation in ("mother", "city", "pet"):
        nb.declare_relation(f"rel-{relation}", relation, True)
    nb.declare_relation("rel-friend", "friend", False)
    ids = {}
    for name in ("Mira", "Tom", "Ana"):
        ids[name] = nb.new_entity(f"ent-{name}", name).detail["entity_id"]
    return ids


def _teach(nb, eid, subject, relation, value, **kw):
    return nb.assert_fact(eid, "listening", "taught", subject, relation, value, **kw)


def lifecycle_cases():
    """30 sequences. Each takes (notebook factory, tmp dir) and returns True on pass."""
    E, L = (lambda i: {"entity": i}), (lambda t: {"literal": t})
    cases = []

    def case(fn):
        cases.append(fn)
        return fn

    @case
    def c01_teach_then_ask(mk, d):
        nb = mk(d); i = _setup(nb)
        return _teach(nb, "a", i["Mira"], "city", L("Lisbon")).status == SAVED and \
            nb.ask("Mira", ["city"]).detail.get("answer") == "Lisbon"

    @case
    def c02_two_hop(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "mother", E(i["Ana"])); _teach(nb, "b", i["Ana"], "city", L("Porto"))
        return nb.ask("Mira", ["mother", "city"]).detail.get("answer") == "Porto"

    @case
    def c03_missing_fact_status(mk, d):
        nb = mk(d); _setup(nb)
        r = nb.ask("Mira", ["city"])
        return r.status == MISSING_FACT and "don't know" in r.say()

    @case
    def c04_missing_at_second_hop(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "mother", E(i["Ana"]))
        r = nb.ask("Mira", ["mother", "city"])
        return r.status == MISSING_FACT and r.detail.get("hop") == 2 and r.detail.get("subject") == "Ana"

    @case
    def c05_broken_chain(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon"))
        return nb.ask("Mira", ["city", "mother"]).status == BROKEN_CHAIN

    @case
    def c06_unknown_entity(mk, d):
        nb = mk(d); _setup(nb)
        return nb.ask("Zed", ["city"]).status == UNKNOWN_ENTITY

    @case
    def c07_conflict_without_correction(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon"))
        r = _teach(nb, "b", i["Mira"], "city", L("Paris"))
        return r.status == CONFLICT and nb.ask("Mira", ["city"]).detail.get("answer") == "Lisbon"

    @case
    def c08_correction_supersedes(mk, d):
        nb = mk(d); i = _setup(nb)
        first = _teach(nb, "a", i["Mira"], "city", L("Lisbon"))
        r = _teach(nb, "b", i["Mira"], "city", L("Paris"), correction=True)
        return r.detail.get("supersedes") == first.detail["fact_id"] and \
            nb.ask("Mira", ["city"]).detail.get("answer") == "Paris"

    @case
    def c09_old_value_still_in_log(mk, d):
        nb = mk(d); i = _setup(nb)
        first = _teach(nb, "a", i["Mira"], "city", L("Lisbon"))
        _teach(nb, "b", i["Mira"], "city", L("Paris"), correction=True)
        return nb.facts[first.detail["fact_id"]]["value"] == L("Lisbon") and not nb.active(first.detail["fact_id"])

    @case
    def c10_idempotent_event(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon")); before = len(nb.events)
        return _teach(nb, "a", i["Mira"], "city", L("Lisbon")).status == DUPLICATE_OK and len(nb.events) == before

    @case
    def c11_same_fact_new_event_no_dup_row(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon")); before = len(nb.events)
        return _teach(nb, "b", i["Mira"], "city", L("Lisbon")).status == DUPLICATE_OK and len(nb.events) == before

    @case
    def c12_two_miras_ambiguous(mk, d):
        nb = mk(d); _setup(nb); nb.new_entity("ent-Mira2", "Mira")
        r = nb.ask("Mira", ["city"])
        return r.status == AMBIGUOUS and len(r.detail.get("ids", [])) == 2

    @case
    def c13_two_miras_facts_stay_separate(mk, d):
        nb = mk(d); i = _setup(nb); m2 = nb.new_entity("ent-Mira2", "Mira").detail["entity_id"]
        _teach(nb, "a", i["Mira"], "city", L("Lisbon")); _teach(nb, "b", m2, "city", L("Oslo"))
        nb.add_alias("al", m2, "Mira K")
        return nb.ask("Mira K", ["city"]).detail.get("answer") == "Oslo" and nb.ask("Mira", ["city"]).status == AMBIGUOUS

    @case
    def c14_alias_resolves(mk, d):
        nb = mk(d); i = _setup(nb); nb.add_alias("al", i["Tom"], "Tommy")
        _teach(nb, "a", i["Tom"], "pet", L("cat"))
        return nb.ask("tommy", ["pet"]).detail.get("answer") == "cat"

    @case
    def c15_only_listening_writes_taught(mk, d):
        nb = mk(d); i = _setup(nb)
        r = nb.assert_fact("a", "thinking", "taught", i["Mira"], "city", L("Rome"))
        return r.status == NOT_ALLOWED and nb.ask("Mira", ["city"]).status == MISSING_FACT

    @case
    def c16_proposed_never_answers(mk, d):
        nb = mk(d); i = _setup(nb)
        nb.assert_fact("a", "creative", "proposed", i["Mira"], "city", L("Rome"))
        return nb.ask("Mira", ["city"]).status == MISSING_FACT

    @case
    def c17_web_quarantine_never_answers(mk, d):
        nb = mk(d); i = _setup(nb)
        r = nb.assert_fact("a", "thinking", "web-quarantine", i["Mira"], "city", L("Rome"),
                           provenance={"url": "https://example.org", "quoted_span": "Mira lives in Rome"})
        return r.status == SAVED and nb.ask("Mira", ["city"]).status == MISSING_FACT

    @case
    def c18_web_needs_provenance(mk, d):
        nb = mk(d); i = _setup(nb)
        return nb.assert_fact("a", "thinking", "web-quarantine", i["Mira"], "city", L("Rome")).status == BAD_REQUEST

    @case
    def c19_promotion_by_ben_only(mk, d):
        nb = mk(d); i = _setup(nb)
        f = nb.assert_fact("a", "creative", "proposed", i["Mira"], "city", L("Rome")).detail["fact_id"]
        bad = nb.promote("p1", "thinking", f)
        good = nb.promote("p2", "ben", f)
        return bad.status == NOT_ALLOWED and good.status == SAVED and nb.ask("Mira", ["city"]).detail.get("source") == "taught"

    @case
    def c20_inferred_needs_approved_rule(mk, d):
        nb = mk(d); i = _setup(nb)
        dep = _teach(nb, "a", i["Mira"], "mother", E(i["Ana"])).detail["fact_id"]
        r = nb.assert_fact("b", "thinking", "inferred", i["Ana"], "friend", E(i["Mira"]), rule_id="R1", deps=(dep,))
        return r.status == NOT_ALLOWED

    @case
    def c21_inferred_answers_after_rule(mk, d):
        nb = mk(d); i = _setup(nb); nb.approve_rule("r", "ben", "R1", "city(x)=city(mother(x)) if unknown")
        d1 = _teach(nb, "a", i["Mira"], "mother", E(i["Ana"])).detail["fact_id"]
        d2 = _teach(nb, "b", i["Ana"], "city", L("Porto")).detail["fact_id"]
        nb.assert_fact("c", "thinking", "inferred", i["Mira"], "city", L("Porto"), rule_id="R1", deps=(d1, d2))
        r = nb.ask("Mira", ["city"])
        return r.detail.get("answer") == "Porto" and r.detail.get("source") == "inferred"

    @case
    def c22_inferred_invalidated_by_correction(mk, d):
        nb = mk(d); i = _setup(nb); nb.approve_rule("r", "ben", "R1", "x")
        d1 = _teach(nb, "a", i["Mira"], "mother", E(i["Ana"])).detail["fact_id"]
        d2 = _teach(nb, "b", i["Ana"], "city", L("Porto")).detail["fact_id"]
        nb.assert_fact("c", "thinking", "inferred", i["Mira"], "city", L("Porto"), rule_id="R1", deps=(d1, d2))
        _teach(nb, "e", i["Ana"], "city", L("Faro"), correction=True)
        return nb.ask("Mira", ["city"]).status == MISSING_FACT

    @case
    def c23_inferred_never_beats_taught(mk, d):
        nb = mk(d); i = _setup(nb); nb.approve_rule("r", "ben", "R1", "x")
        d1 = _teach(nb, "a", i["Ana"], "city", L("Porto")).detail["fact_id"]
        _teach(nb, "b", i["Mira"], "city", L("Lisbon"))
        nb.assert_fact("c", "thinking", "inferred", i["Mira"], "city", L("Porto"), rule_id="R1", deps=(d1,))
        return nb.ask("Mira", ["city"]).detail.get("answer") == "Lisbon"

    @case
    def c24_sleep_cannot_touch_taught(mk, d):
        nb = mk(d); i = _setup(nb)
        f = _teach(nb, "a", i["Mira"], "city", L("Lisbon")).detail["fact_id"]
        r1 = nb.retract("x", "sleep", f, "tidy")
        nb.assert_fact("y", "sleep", "sleep-derived", i["Mira"], "city", L("Rome"))
        return r1.status == NOT_ALLOWED and nb.ask("Mira", ["city"]).detail.get("answer") == "Lisbon"

    @case
    def c25_merge_is_only_a_proposal(mk, d):
        nb = mk(d); i = _setup(nb); m2 = nb.new_entity("ent-Mira2", "Mira").detail["entity_id"]
        nb.propose_merge("m", "sleep", i["Mira"], m2)
        return nb.ask("Mira", ["city"]).status == AMBIGUOUS and len(nb.entities) == 4

    @case
    def c26_retract_then_missing(mk, d):
        nb = mk(d); i = _setup(nb)
        f = _teach(nb, "a", i["Mira"], "city", L("Lisbon")).detail["fact_id"]
        nb.retract("x", "listening", f, "Ben said forget it")
        return nb.ask("Mira", ["city"]).status == MISSING_FACT and f in nb.facts

    @case
    def c27_multi_valued_relation(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "friend", E(i["Tom"])); r = _teach(nb, "b", i["Mira"], "friend", E(i["Ana"]))
        ans = nb.ask("Mira", ["friend"]).detail.get("answer", "")
        return r.status == SAVED and "Tom" in ans and "Ana" in ans

    @case
    def c28_survives_restart(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon")); _teach(nb, "b", i["Mira"], "city", L("Paris"), correction=True)
        again = mk(d)
        return again.ask("Mira", ["city"]).detail.get("answer") == "Paris" and len(again.events) == len(nb.events)

    @case
    def c29_torn_tail_is_survived(mk, d):
        nb = mk(d); i = _setup(nb); _teach(nb, "a", i["Mira"], "city", L("Lisbon"))
        with open(Path(d) / LOG_NAME, "a", encoding="utf-8") as handle:
            handle.write('{"kind": "FACT", "event_id": "torn", "fact_')
        again = mk(d)
        ok = again.torn_tail and again.ask("Mira", ["city"]).detail.get("answer") == "Lisbon"
        again.repair_torn_tail()
        return ok and _teach(again, "b", i["Tom"], "pet", L("dog")).status == SAVED and not mk(d).torn_tail

    @case
    def c30_tampering_detected(mk, d):
        nb = mk(d); i = _setup(nb)
        _teach(nb, "a", i["Mira"], "city", L("Lisbon")); _teach(nb, "b", i["Tom"], "pet", L("dog"))
        path = Path(d) / LOG_NAME
        path.write_text(path.read_text(encoding="utf-8").replace("Lisbon", "Madrid"), encoding="utf-8")
        try:
            mk(d)
        except LogCorrupt:
            return True
        return False

    @case
    def c31_web_verified_needs_two_websites(mk, d):
        nb = mk(d); i = _setup(nb)
        one = {"evidence": [{"url": "https://a.org/x", "quoted_span": "q"},
                            {"url": "https://www.a.org/y", "quoted_span": "q"}]}
        two = {"evidence": [{"url": "https://a.org/x", "quoted_span": "q"},
                            {"url": "https://b.org/y", "quoted_span": "q"}]}
        r1 = nb.assert_fact("a", "thinking", "web-verified", i["Tom"], "city", L("Rome"), provenance=one)
        r2 = nb.assert_fact("b", "thinking", "web-verified", i["Tom"], "city", L("Rome"), provenance=two)
        said = nb.ask("Tom", ["city"])
        return (r1.status == BAD_REQUEST and r2.status == SAVED and said.status == OK
                and said.detail["source"] == "web-verified" and "online" in said.say())

    @case
    def c32_taught_beats_web_verified(mk, d):
        nb = mk(d); i = _setup(nb)
        two = {"evidence": [{"url": "https://a.org/x", "quoted_span": "q"},
                            {"url": "https://b.org/y", "quoted_span": "q"}]}
        nb.assert_fact("a", "thinking", "web-verified", i["Mira"], "city", L("Rome"), provenance=two)
        _teach(nb, "b", i["Mira"], "city", L("Lisbon"))
        said = nb.ask("Mira", ["city"])
        return said.detail.get("answer") == "Lisbon" and "online" not in said.say()

    return cases


def run_suite(factory) -> list[tuple[str, bool, str]]:
    rows = []
    for fn in lifecycle_cases():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                passed, note = bool(fn(factory, tmp)), ""
            except Exception as exc:  # a crash is a failed case, not a crashed suite
                passed, note = False, f"{type(exc).__name__}: {exc}"
        rows.append((fn.__name__, passed, note))
    return rows


NAIVE_MUST_FAIL_AT_LEAST = 15


def main() -> int:
    parser = argparse.ArgumentParser(description="Notebook contract (milestone 1)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not args.selftest:
        parser.print_help()
        return 0
    real, naive = run_suite(Notebook), run_suite(NaiveNotebook)
    for (name, ok, note), (_, naive_ok, _) in zip(real, naive):
        print(f"{'PASS' if ok else 'FAIL'}  naive:{'pass' if naive_ok else 'fail'}  {name} {note}")
    real_pass, naive_fail = sum(ok for _, ok, _ in real), sum(not ok for _, ok, _ in naive)
    print(f"contract notebook: {real_pass}/{len(real)}   naive notebook fails: {naive_fail}/{len(naive)}")
    good = real_pass == len(real) and naive_fail >= NAIVE_MUST_FAIL_AT_LEAST
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
