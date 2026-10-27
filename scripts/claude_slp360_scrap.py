#!/usr/bin/env python3
"""slp-360: the SCRAP LAYER (Fix-sleep thread, 2026-09-25; plan design/v3/30-modes/360-sleep-plan.md).

Ben's rule: the notebook saves taught facts only; anything derived lives in a separate, disposable layer.
Today the notebook contract lets sleep write `sleep-derived` rows and lets sleep/thinking write
`inferred` rows, and both are answering sources (fable_notebook_contract.py:51,59). In 0.1 the Sleep145
chain writes a "sleep" entity, a `sleep_report` relation and one sleep-derived report row per installed
word into the MAIN notebook (fable_sleep130_agent.py:738-766).

ONE CHANGE: every write sleep makes, and every `inferred` / `sleep-derived` row from any actor, goes to a
scrap layer (<state_dir>/scrap360/scrap.jsonl) instead of the main notebook. Scrap rows never answer:
nothing reads them to answer a question. Sleep still READS the main notebook (it needs taught rows).

  install_scrap360(loop)   wraps loop.sleeper.sleep (sleep gets a proxy notebook: reads from main,
                           writes to scrap) and loop.nb.assert_fact (derived sources go to scrap).
Nothing sealed is edited; this file only wraps a built loop.

Side effect, stated: the report row's id is no longer a main fact id, so the word-route answer trail no
longer starts with it (fable_sleep130_agent.py:187 prepends it only when it is set). Replies do not
change; `trail` drops one pointer that was never a world fact.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import fable_notebook_contract as C

SCRAP_DIR360 = "scrap360"
SCRAP_LOG360 = "scrap.jsonl"
DERIVED360 = ("sleep-derived", "inferred")


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


class ScrapLayer360:
    """Append-only JSONL of everything sleep (or a derivation) would have written. Never answers.

    Ids live in their own namespace (SE0001 entities, SF00001 rows), so they can never be
    mistaken for main-notebook ids. A torn final line is ignored on load, as in the contract.
    """

    def __init__(self, state_dir) -> None:
        self.root = Path(state_dir) / SCRAP_DIR360
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / SCRAP_LOG360
        self.rows: list[dict] = []
        self.event_ids: set[str] = set()
        self.entities: dict[str, str] = {}
        self.aliases: dict[str, str] = {}
        self.n_facts = 0
        self.torn_tail = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for i, line in enumerate(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:
                    self.torn_tail = True
                    break
                raise C.LogCorrupt(f"scrap360: bad line {i + 1}")
            self._index(row)

    def _index(self, row: dict) -> None:
        self.rows.append(row)
        self.event_ids.add(row.get("event_id", ""))
        if row["kind"] == "ENTITY":
            self.entities[row["entity_id"]] = row["name"]
            self.aliases.setdefault(_norm(row["name"]), row["entity_id"])
        elif row["kind"] == "FACT":
            self.n_facts += 1

    def _append(self, row: dict) -> None:
        row = dict(row, n=len(self.rows))
        line = json.dumps(row, ensure_ascii=False, sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._index(row)

    def digest(self) -> str:
        if not self.path.exists():
            return ""
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    # ------------------------------------------------------------ writes
    def new_entity(self, event_id: str, name: str) -> C.Result:
        if event_id in self.event_ids:
            eid = self.aliases.get(_norm(name))
            return C.Result(C.DUPLICATE_OK, {"entity_id": eid} if eid else {})
        eid = f"SE{len(self.entities) + 1:04d}"
        self._append({"kind": "ENTITY", "event_id": event_id, "entity_id": eid, "name": str(name).strip()})
        return C.Result(C.SAVED, {"text": f"{str(name).strip()} is {eid} (scrap)", "entity_id": eid})

    def record(self, kind: str, event_id: str, **fields) -> C.Result:
        if event_id in self.event_ids:
            return C.Result(C.DUPLICATE_OK)
        self._append(dict(fields, kind=kind, event_id=event_id))
        return C.Result(C.SAVED, {"text": f"{kind.lower()} kept in scrap"})

    def fact(self, event_id: str, actor: str, source: str, subject: str, relation: str,
             value: dict, subject_name: str, **extra) -> C.Result:
        if event_id in self.event_ids:
            return C.Result(C.DUPLICATE_OK)
        sid = f"SF{self.n_facts + 1:05d}"
        self._append({"kind": "FACT", "event_id": event_id, "scrap_id": sid, "actor": actor,
                      "source": source, "subject": subject, "relation": relation, "value": value,
                      **{k: v for k, v in extra.items() if v not in (None, (), [])}})
        shown = value.get("literal", value.get("entity", ""))
        # No "fact_id" key: callers that keep a main-notebook fact id get None, never a scrap id.
        return C.Result(C.SAVED, {"text": f"{subject_name}'s {relation} is {shown} (scrap)",
                                  "scrap_id": sid})


class ScrapProxy360:
    """What the sleeper sees as `notebook`: reads go to the main notebook, every write goes to scrap."""

    def __init__(self, main, scrap: ScrapLayer360) -> None:
        self._main = main
        self._scrap = scrap

    def __getattr__(self, name):
        return getattr(self._main, name)

    def resolve(self, name: str) -> C.Result:
        eid = self._scrap.aliases.get(_norm(name))
        if eid is not None:
            return C.Result(C.OK, {"entity_id": eid, "answer": self._scrap.entities[eid]})
        return self._main.resolve(name)

    def new_entity(self, event_id: str, name: str) -> C.Result:
        return self._scrap.new_entity(event_id, name)

    def declare_relation(self, event_id: str, relation: str, functional: bool) -> C.Result:
        return self._scrap.record("RELATION", event_id, relation=relation, functional=bool(functional))

    def add_alias(self, event_id: str, entity_id: str, alias: str) -> C.Result:
        return self._scrap.record("ALIAS", event_id, entity_id=entity_id, alias=alias)

    def assert_fact(self, event_id, actor, source, subject, relation, value, *, correction=False,
                    raw=None, rule_id=None, deps=(), provenance=None) -> C.Result:
        if source == "taught":
            return C.Result(C.NOT_ALLOWED, {"actor": f"{actor} during sleep"})
        name = self._scrap.entities.get(subject) or self._main.entities.get(subject, subject)
        return self._scrap.fact(event_id, actor, source, subject, relation, value, name,
                                raw=raw, rule_id=rule_id, deps=list(deps), provenance=provenance)

    def retract(self, event_id, actor, fact_id, reason) -> C.Result:
        if str(fact_id).startswith("SF"):
            return self._scrap.record("RETRACT", event_id, fact_id=fact_id, actor=actor, reason=reason)
        return C.Result(C.NOT_ALLOWED, {"actor": f"{actor} during sleep"})

    def promote(self, event_id, actor, fact_id) -> C.Result:
        return C.Result(C.NOT_ALLOWED, {"actor": f"{actor} during sleep"})

    def approve_rule(self, event_id, actor, rule_id, body) -> C.Result:
        return C.Result(C.NOT_ALLOWED, {"actor": f"{actor} during sleep"})

    def propose_merge(self, event_id, actor, keep, other) -> C.Result:
        return self._scrap.record("MERGE_PROPOSAL", event_id, actor=actor, keep=keep, other=other)


def main_derived_rows(nb) -> int:
    """Rows in the MAIN notebook whose source is derived (the rule says this must be 0)."""
    facts = getattr(nb, "facts", {}) or {}
    return sum(1 for f in facts.values() if f.get("source") in DERIVED360)


def install_scrap360(loop) -> ScrapLayer360:
    if getattr(loop, "scrap360", None) is not None:
        return loop.scrap360
    scrap = ScrapLayer360(loop.dir)
    loop.scrap360 = scrap
    loop.scrap360_stats = {"sleeps": 0, "scrap_rows_by_sleep": 0, "derived_redirected": 0}

    inner_sleep = loop.sleeper.sleep

    def sleep360(experience, notebook):
        before = len(scrap.rows)
        out = inner_sleep(experience, ScrapProxy360(notebook, scrap))
        loop.scrap360_stats["sleeps"] += 1
        loop.scrap360_stats["scrap_rows_by_sleep"] += len(scrap.rows) - before
        return out

    loop.sleeper.sleep = sleep360

    nb = loop.nb
    inner_assert = nb.assert_fact

    def assert_fact360(event_id, actor, source, subject, relation, value, **kw):
        if source in DERIVED360:
            loop.scrap360_stats["derived_redirected"] += 1
            name = nb.entities.get(subject, subject)
            return scrap.fact(event_id, actor, source, subject, relation, value, name,
                              raw=kw.get("raw"), rule_id=kw.get("rule_id"),
                              deps=list(kw.get("deps", ()) or ()), provenance=kw.get("provenance"))
        return inner_assert(event_id, actor, source, subject, relation, value, **kw)

    nb.assert_fact = assert_fact360
    loop.notes.append("slp-360: sleep writes and derived rows go to scrap360/, never the main notebook")
    return scrap
