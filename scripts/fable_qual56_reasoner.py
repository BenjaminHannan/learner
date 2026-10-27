#!/usr/bin/env python3
"""Experiment 56: qualifier-aware reasoner -- a WRAPPER around fable_reasoner50.

Problem (doc 49): thought rows v2 carry qualifiers (e.g. time 'in 2019',
condition 'at 300 K'), but reasoner50 and livesleep52 see qualified rows only
through to_v1(), which drops the qualifiers. So a fact true only 'in 2019' can
answer a question with no year, and sleep can mine chains through qualified rows.

This module IMPORTS fable_reasoner50 read-only (never edits it) and re-runs the
same hard-coded hop loop over qualifier-filtered lookup views:

  (1) a row with qualifiers is used only when the question's qualifiers match
      (exact match on qualifier type+value, plain software); otherwise the hop
      abstains with MISSING_FACT and reason 'qualified';
  (2) an unqualified taught row always beats a qualified one when both exist
      for the same (subject, relation) -- even when the question is qualified;
  (3) hops never pass through qualified rows unless the question is qualified
      (per-hop requirements; a dict applies at every hop, a list runs parallel
      to the relations).

Question format: reasoner50's {name, relations, entity_id?} plus an optional
'qualifiers' key: None, a dict, or a list parallel to 'relations' (entries
None|dict). Keys are qualifier relations; values are the expected value as a
plain string/number/bool or a {"entity"/"literal": ...} dict.

Plain software, offline, CPU. No model, no training, no guessing.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_reasoner50 as R50  # noqa: E402  (read-only; never edited)
from fable_thought49_schema import (  # noqa: E402
    SchemaError,
    ThoughtV2,
    norm_relation,
)

ANS = R50.ANS
ANS_IDX = R50.ANS_IDX
ANSWER_THRESHOLD = R50.ANSWER_THRESHOLD
MAX_HOPS = R50.MAX_HOPS


class BadQualifiers(Exception):
    pass


def hop_requirements(relations: list, qualifiers) -> list:
    """Per-hop qualifier dicts. Mirrors ThoughtNotebook._hop_requirements."""
    if qualifiers is None:
        return [{} for _ in relations]
    if isinstance(qualifiers, dict):
        return [dict(qualifiers) for _ in relations]
    if isinstance(qualifiers, (list, tuple)) and len(qualifiers) == len(relations):
        return [{} if q is None else dict(q) for q in qualifiers]
    raise BadQualifiers(
        "qualifiers must be None, a dict, or a list parallel to relations")


def value_equals(row_value, provided) -> bool:
    """Exact match of a row qualifier value against the question's value."""
    target = row_value.to_v1_value()
    if isinstance(provided, dict):
        return provided == target
    if "entity" in target:
        return str(provided) == target["entity"]
    return str(provided) == target["literal"]


def qualifiers_match(qualifiers, required: dict) -> bool:
    """Every row qualifier must be present and exactly equal in the question.

    A bare question (no qualifiers) never satisfies a qualified row.
    """
    if not required:
        return False
    need = {norm_relation(k): v for k, v in required.items()}
    for qual in qualifiers:
        key = norm_relation(qual.relation)
        if key not in need or not value_equals(qual.value, need[key]):
            return False
    return True


def thought_of(fact: dict):
    """The v2 row behind a v1 fact, or None for foreign events.

    Facts without an embedded v2 record degrade to qualifier-free rows
    (blank fields, never guessed) -- they answer exactly as before.
    """
    try:
        return ThoughtV2.from_v1(fact)
    except SchemaError:
        return None


def fid_num(fid: str) -> int:
    return int(fid[1:])


def filtered_view(nb, rel: str, required: dict):
    """Qualifier-filtered lookup for one relation at one hop.

    Returns (out, qualified_dropped_any) where out maps subject_eid to the same
    ("E"/"L"/"M") entries RelationView builds. Selection order:

      active + answering source only  ->  qualifier gate  ->
      unqualified-taught priority (rule 2)  ->  best source first,
      newest within a source (contract order).
    """
    functional = rel in nb.functional
    kept_by_subj: dict[str, list[dict]] = {}
    dropped = False
    for fid, fact in nb.facts.items():
        if fact["relation"] != rel:
            continue
        if fact["source"] not in ANS or not nb.active(fid):
            continue
        thought = thought_of(fact)
        quals = thought.qualifiers if thought is not None else ()
        if quals and not qualifiers_match(quals, required):
            dropped = True
            continue
        kept_by_subj.setdefault(fact["subject"], []).append((fact, bool(quals)))
    out: dict[str, tuple] = {}
    for subj, rows in kept_by_subj.items():
        # Rule 2: an unqualified taught row beats every qualified row here.
        if any(f["source"] == "taught" and not q for f, q in rows):
            rows = [(f, q) for f, q in rows if not q]
            if not rows:
                dropped = True
                continue
        facts = [f for f, _ in rows]
        facts.sort(key=lambda f: (ANS_IDX[f["source"]], -f["n"]))
        best = facts[0]["source"]
        facts = [f for f in facts if f["source"] == best]
        src = ANS_IDX[best]
        if functional or len(facts) == 1:
            row = facts[0]
            val = row["value"]
            num = fid_num(row["fact_id"])
            if "entity" in val:
                out[subj] = ("E", val["entity"], num, src)
            else:
                out[subj] = ("L", str(val["literal"]), num, src)
        else:
            shows = []
            for row in facts:
                val = row["value"]
                if "entity" in val:
                    shows.append((nb.entities[val["entity"]], fid_num(row["fact_id"])))
                else:
                    shows.append((str(val["literal"]), fid_num(row["fact_id"])))
            out[subj] = ("M", shows, src)
    return out, dropped


def fid_str(num: int) -> str:
    return f"F{num:05d}"


class QualifierAwareReasoner(R50.FableReasoner50):
    """A reasoner50 that gates qualified rows per hop. Subclass-and-filter:
    the parent module is imported, never edited; learned-word stage expansion
    reuses the parent's hardened-logit tables verbatim."""

    def answer(self, question: dict, notebook) -> dict:
        nb = notebook
        self._sync(nb)
        name = question.get("name", "")
        relations = list(question.get("relations") or [])
        eid = question.get("entity_id")

        def rec(status: str, fields: dict) -> dict:
            return {"kind": "answer", "status": status, "name": name,
                    "relations": relations, "fields": fields}

        if not relations or len(relations) > MAX_HOPS:
            return rec(C.BAD_REQUEST, {"reason": f"need 1-{MAX_HOPS} hops"})
        try:
            hop_req = hop_requirements(relations, question.get("qualifiers"))
        except BadQualifiers:
            return rec(C.BAD_REQUEST, {
                "reason": "qualifiers must be None, a dict, or a list parallel to relations"})

        if eid is None:
            found = nb.resolve(name)
            if found.status != C.OK:
                return rec(found.status, dict(found.detail))
            eid = found.detail["entity_id"]
        elif eid not in nb.entities:
            return rec(C.BAD_REQUEST, {"reason": "unknown entity id"})

        # Per-(hop, relation) filtered views (a relation reused across hops with
        # different requirements gets one view per hop).
        views: dict[tuple, tuple] = {}

        def view_at(hop: int, rel: str):
            key = (hop, rel)
            if key not in views:
                views[key] = filtered_view(nb, rel, hop_req[hop])
            return views[key]

        def known(rel: str) -> bool:
            for fid, fact in nb.facts.items():
                if fact["relation"] == rel:
                    return True
            return rel in nb.functional

        def stages(tok: str, hop: int):
            if tok in self.words:
                return self.stage_options(self.words[tok])
            if known(tok):
                return [("skill", tok, 1.0)]
            return None

        trail: list[int] = []
        trail_src: list[int] = []
        subject = eid
        kind = "entity"
        lit_text = lit_producer = None
        conf = 1.0

        def fields_missing(hop: int, rel: str, qualified: bool) -> dict:
            detail = {"subject": nb.entities[subject], "relation": rel,
                      "hop": hop, "trail": [fid_str(n) for n in trail]}
            if qualified:
                detail["reason"] = "qualified"
            return detail

        def fields_broken(hop: int) -> dict:
            return {"subject": nb.entities[subject], "relation": lit_producer,
                    "value": lit_text, "hop": hop, "trail": [fid_str(n) for n in trail]}

        for hop, tok in enumerate(relations):
            if kind != "entity":
                return rec(C.BROKEN_CHAIN, fields_broken(hop))
            stage_list = stages(tok, hop)
            if stage_list is None:
                return rec(C.MISSING_FACT, fields_missing(hop + 1, tok, False))
            for opt, arg, weight in stage_list:
                if kind != "entity":
                    return rec(C.BROKEN_CHAIN, fields_broken(hop))
                if opt == "keep":
                    continue
                conf *= weight
                out, dropped = view_at(hop, arg)
                entry = out.get(subject)
                if entry is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg, dropped))
                tag = entry[0]
                if tag == "M":
                    shows, src = entry[1], entry[2]
                    return rec(C.OK, {"answer": ", ".join(s for s, _ in shows),
                                      "trail": [fid_str(n) for n in trail] + [fid_str(n) for _, n in shows],
                                      "source": ANS[src], "multi": True})
                trail.append(entry[2])
                trail_src.append(entry[3])
                if tag == "L":
                    kind, lit_text, lit_producer = "literal", entry[1], arg
                else:
                    subject = entry[1]

        if kind != "entity":
            return rec(C.OK, {"answer": lit_text, "trail": [fid_str(n) for n in trail],
                              "source": ANS[trail_src[-1]]})
        if conf < ANSWER_THRESHOLD:
            return rec(C.MISSING_FACT,
                       fields_missing(len(relations), relations[-1], False))
        return rec(C.OK, {"answer": nb.entities[subject], "trail": [fid_str(n) for n in trail],
                          "source": ANS[trail_src[-1]]})
