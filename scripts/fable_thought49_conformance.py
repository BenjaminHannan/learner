#!/usr/bin/env python3
"""Conformance suite for the v2 thought format (design doc 49).  Plain software.

``--selftest`` runs five marks:

  A  the contract's lifecycle suite through ThoughtNotebook   -- must be ALL pass
  B  the contract's lifecycle suite through Notebook (control)-- must be ALL pass
  C  the contract's lifecycle suite through NaiveNotebook     -- must FAIL >= 15
  D  33 new v2 sequences through ThoughtNotebook             -- must be ALL pass
  E  the 33 v2 sequences through NaiveThoughtNotebook        -- must FAIL >= 15

The naive foils are last-write-wins dictionaries.  A suite that a naive version
passes is not testing anything, so both naive foils are required to fail.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_notebook_contract as C                     # noqa: E402
from fable_thought49_schema import (                    # noqa: E402
    Qualifier, Provenance, SchemaError, ThoughtV2, Value,
)
from fable_thought49_notebook import (                  # noqa: E402
    NaiveThoughtNotebook, ThoughtNotebook,
)

SAVED, DUPLICATE_OK, CONFLICT, AMBIGUOUS = C.SAVED, C.DUPLICATE_OK, C.CONFLICT, C.AMBIGUOUS
OK, MISSING_FACT, BAD_REQUEST, NOT_ALLOWED = C.OK, C.MISSING_FACT, C.BAD_REQUEST, C.NOT_ALLOWED
LogCorrupt = C.LogCorrupt
LOG_NAME = C.LOG_NAME

# real provenance used in tests (sentences/urls from the doc-49 hand-map fixtures)
ARXIV_RESA = "https://arxiv.org/abs/2506.04108"
ARXIV_ACC = "https://arxiv.org/abs/2605.24518"
SENT_RESA = ("Notably, ReSA delivers up to 2.42x end-to-end speedup under decoding "
             "at 256K sequence length, making it a practical solution.")
SENT_ACC = ("Preliminary results show accuracy values of 0.8200 for hard masking "
            "and 0.8165 for soft masking, closely matching the 0.8200 of full attention.")


# ------------------------------------------------------------------- helpers
def _setup2(nb):
    for relation in ("mother", "city", "pet"):
        nb.declare_relation("rel-" + relation, relation, True)
    nb.declare_relation("rel-friend", "friend", False)
    nb.declare_relation("rel-accuracy", "accuracy", True)
    ids = {}
    for name in ("Mira", "Tom", "Ana"):
        ids[name] = nb.ensure_entity("ent-" + name, name).detail["entity_id"]
    return ids


def _taught(subject, relation, value, sentence="Ben said so.", **kw):
    return ThoughtV2(
        subject=subject, relation=relation, value=value,
        provenance=Provenance(document="spoken:listening", sentence=sentence,
                              claimed_by="taught"),
        source="taught", confidence=1.0, **kw)


def _paper(pid, subject, relation, value, sentence, url, confidence=0.7, source="web-quarantine",
           document=None, **kw):
    return ThoughtV2(
        subject=subject, relation=relation, value=value,
        provenance=Provenance(document=document or url, sentence=sentence,
                              claimed_by="paper:" + pid, url=url),
        source=source, confidence=confidence, **kw)


# ------------------------------------------------- new v2 lifecycle sequences
def v2_cases():
    """33 sequences over the widened format.  Each takes (factory, tmp dir)."""
    cases = []

    def case(fn):
        cases.append(fn)
        return fn

    @case
    def n01_number_value_roundtrip(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_taught(i["Mira"], "accuracy improvement",
                                   Value.of_number(12, "%"),
                                   sentence="Method M improves accuracy by 12%."))
        if r.status != SAVED:
            return False
        t = nb.get_thought(r.detail["fact_id"])
        said = nb.ask("Mira", ["accuracy improvement"])
        return (t is not None and t.value.kind == "number" and t.value.number == 12.0
                and t.value.unit == "%" and said.status == OK
                and said.detail["answer"] == "12%")

    @case
    def n02_unit_rendering_variants(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.add_thought(_taught(i["Mira"], "speed", Value.of_number(3.5, "m/s")))
        nb.add_thought(_taught(i["Mira"], "fraction", Value.of_number(0.82)))
        nb.add_thought(_taught(i["Tom"], "speed", Value.of_number(2.42, "x")))
        return (nb.ask("Mira", ["speed"]).detail.get("answer") == "3.5 m/s"
                and nb.ask("Mira", ["fraction"]).detail.get("answer") == "0.82"
                and nb.ask("Tom", ["speed"]).detail.get("answer") == "2.42 x")

    @case
    def n03_date_value_and_format_gate(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_taught(i["Mira"], "date of birth",
                                   Value.of_date("1959-06-06")))
        try:
            Value.of_date("June 6, 1959").validate()
            unformatted = False
        except SchemaError:
            unformatted = True
        return (r.status == SAVED and unformatted
                and nb.ask("Mira", ["date of birth"]).detail.get("answer") == "1959-06-06")

    @case
    def n04_boolean_value(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_taught(i["Mira"], "obstructs gradients",
                                   Value.of_boolean(False),
                                   sentence="The mask does not obstruct gradients."))
        t = nb.get_thought(r.detail["fact_id"])
        said = nb.ask("Mira", ["obstructs gradients"])
        return (r.status == SAVED and t.value.kind == "boolean" and t.value.boolean is False
                and said.detail.get("answer") == "false")

    @case
    def n05_text_span_value(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.add_thought(_taught(i["Mira"], "headline result",
                               Value.of_text("state-of-the-art under both inference modes")))
        said = nb.ask("Mira", ["headline result"])
        return said.detail.get("answer") == "state-of-the-art under both inference modes"

    @case
    def n06_entity_value_two_hop(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.add_thought(_taught(i["Mira"], "mother", Value.of_entity(i["Ana"])))
        nb.add_thought(_taught(i["Ana"], "city", Value.of_text("Porto")))
        said = nb.ask("Mira", ["mother", "city"])
        return said.status == OK and said.detail.get("answer") == "Porto"

    @case
    def n07_open_relation_stores_and_answers(mk, d):
        nb = mk(d); i = _setup2(nb)
        relation = "improves accuracy on ImageNet"
        r = nb.add_thought(_taught(i["Mira"], relation, Value.of_number(12, "%"),
                                   relation_id=None))
        said = nb.ask("Mira", [relation])
        return (r.status == SAVED and said.status == OK
                and nb.get_thought(r.detail["fact_id"]).relation == relation)

    @case
    def n08_qualifiers_preserved_on_write(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper(
            "arXiv:2506.04108", i["Mira"], "delivers speedup",
            Value.of_number(2.42, "x"), SENT_RESA, ARXIV_RESA,
            qualifiers=(Qualifier("when", Value.of_text("decoding at 256K")),
                        Qualifier("compared to", Value.of_text("sparse baseline")))))
        t = nb.get_thought(r.detail["fact_id"])
        return (r.status == SAVED and len(t.qualifiers) == 2
                and t.qualifiers[0].relation == "when"
                and t.qualifiers[0].value.text == "decoding at 256K"
                and t.qualifiers[1].relation == "compared to")

    @case
    def n09_qualifiers_survive_restart(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper(
            "arXiv:2605.24518", i["Mira"], "accuracy on SST-2",
            Value.of_number(0.82), SENT_ACC, ARXIV_ACC,
            qualifiers=(Qualifier("on dataset", Value.of_text("SST-2")),
                        Qualifier("mask", Value.of_text("hard")))))
        again = mk(d)
        t = again.get_thought(r.detail["fact_id"])
        return (t is not None and len(t.qualifiers) == 2
                and t.qualifiers[1].value.text == "hard"
                and t.value.number == 0.82)

    @case
    def n10_v1_projection_drops_qualifiers(mk, d):
        # pure adapter check (no notebook needed)
        row = ThoughtV2(
            subject="E0001", relation="improves accuracy",
            value=Value.of_number(12, "%"),
            provenance=Provenance(document="https://example.org/p", 
                                  sentence="Method X improves accuracy by 12% when Z.",
                                  claimed_by="paper:P1", url="https://example.org/p"),
            qualifiers=(Qualifier("when", Value.of_text("Z is on")),),
            source="web-quarantine")
        v1 = row.to_v1()
        provenance = dict(v1["provenance"])
        embedded = provenance.pop("thought_v2")
        bare = {k: v1[k] for k in ("subject", "relation", "value", "source")}
        import json as _json
        return (_json.dumps(bare) + _json.dumps(provenance, sort_keys=True)
                ).find("Z is on") == -1 and v1["value"] == {"literal": "12%"} and \
            embedded["qualifiers"][0]["value"]["text"] == "Z is on"

    @case
    def n11_paper_claim_never_answers(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper("arXiv:2506.04108", i["Mira"], "delivers speedup",
                                  Value.of_number(2.42, "x"), SENT_RESA, ARXIV_RESA))
        said = nb.ask("Mira", ["delivers speedup"])
        return r.status == SAVED and said.status == MISSING_FACT

    @case
    def n12_promote_makes_it_answer_and_keeps_row(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper(
            "arXiv:2605.24518", i["Mira"], "accuracy on SST-2",
            Value.of_number(0.82), SENT_ACC, ARXIV_ACC,
            qualifiers=(Qualifier("mask", Value.of_text("hard")),)))
        fid = r.detail["fact_id"]
        bad = nb.promote("p1", "thinking", fid)
        before = nb.ask("Mira", ["accuracy on SST-2"])
        good = nb.promote("p2", "ben", fid)
        bare = nb.ask("Mira", ["accuracy on SST-2"])
        matched = nb.ask("Mira", ["accuracy on SST-2"], qualifiers={"mask": "hard"})
        wrong = nb.ask("Mira", ["accuracy on SST-2"], qualifiers={"mask": "soft"})
        if bad.status != NOT_ALLOWED or before.status != MISSING_FACT or good.status != SAVED:
            return False
        # Ben ruling 1: promoted QUALIFIED row abstains on the bare question...
        if bare.status != MISSING_FACT or bare.detail.get("reason") != "qualified":
            return False
        # ...and answers only when the question matches the qualifier.
        if matched.status != OK or matched.detail.get("answer") != "0.82" \
                or matched.detail.get("source") != "taught":
            return False
        if wrong.status != MISSING_FACT:
            return False
        taught_row = nb.get_thought(matched.detail["trail"][-1])
        original = nb.get_thought(fid)
        return (taught_row.value.kind == "number" and taught_row.value.number == 0.82
                and taught_row.provenance.claimed_by == "taught"
                and taught_row.provenance.promoted_from == fid
                and len(taught_row.qualifiers) == 1
                and original is not None and original.provenance.claimed_by == "paper:arXiv:2605.24518")

    @case
    def n13_promote_refuses_non_promotable(mk, d):
        nb = mk(d); i = _setup2(nb)
        taught = nb.add_thought(_taught(i["Mira"], "city", Value.of_text("Lisbon")))
        return (nb.promote("p1", "ben", "F99999").status == BAD_REQUEST
                and nb.promote("p2", "ben", taught.detail["fact_id"]).status == BAD_REQUEST
                and nb.promote("p3", "sleep", taught.detail["fact_id"]).status == NOT_ALLOWED)

    @case
    def n14_two_papers_conflict_both_kept_neither_answers(mk, d):
        nb = mk(d); i = _setup2(nb)
        a = _paper("fixture-A", i["Mira"], "improves accuracy", Value.of_number(12, "%"),
                   "Fixture A: Method X improves accuracy by 12%.",
                   "https://example.org/paper-a")
        b = _paper("fixture-B", i["Mira"], "improves accuracy", Value.of_number(15, "%"),
                   "Fixture B: Method X improves accuracy by 15%.",
                   "https://example.org/paper-b")
        r1 = nb.add_thought(a)
        r2 = nb.add_thought(b)
        rows = nb.thoughts_for(i["Mira"], "improves accuracy", active_only=False)
        said = nb.ask("Mira", ["improves accuracy"])
        return (r1.status == SAVED and r2.status == SAVED and len(rows) == 2
                and {t.provenance.claimed_by for t in rows} == {"paper:fixture-A",
                                                               "paper:fixture-B"}
                and said.status == MISSING_FACT)

    @case
    def n15_promoting_one_keeps_the_other(mk, d):
        nb = mk(d); i = _setup2(nb)
        a = nb.add_thought(_paper(
            "fixture-A", i["Mira"], "improves accuracy", Value.of_number(12, "%"),
            "Fixture A: Method X improves accuracy by 12%.",
            "https://example.org/paper-a"))
        nb.add_thought(_paper(
            "fixture-B", i["Mira"], "improves accuracy", Value.of_number(15, "%"),
            "Fixture B: Method X improves accuracy by 15%.",
            "https://example.org/paper-b"))
        nb.promote("p1", "ben", a.detail["fact_id"])
        said = nb.ask("Mira", ["improves accuracy"])
        rows = nb.thoughts_for(i["Mira"], "improves accuracy", active_only=False)
        return (said.status == OK and said.detail.get("answer") == "12%"
                and said.detail.get("source") == "taught" and len(rows) == 3
                and any(t.provenance.claimed_by == "paper:fixture-B" for t in rows))

    @case
    def n16_taught_beats_later_paper_claim(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(80, "%")))
        nb.add_thought(_paper("fixture-B", i["Mira"], "accuracy",
                              Value.of_number(79, "%"),
                              "Fixture B: accuracy is 79%.",
                              "https://example.org/paper-b"))
        said = nb.ask("Mira", ["accuracy"])
        return said.status == OK and said.detail.get("answer") == "80%" \
            and said.detail.get("source") == "taught"

    @case
    def n17_taught_conflict_without_correction(mk, d):
        nb = mk(d); i = _setup2(nb)
        first = nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(80, "%")))
        second = nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(81, "%")))
        said = nb.ask("Mira", ["accuracy"])
        return (first.status == SAVED and second.status == CONFLICT
                and said.detail.get("answer") == "80%")

    @case
    def n18_correction_supersedes_keeps_old_row(mk, d):
        nb = mk(d); i = _setup2(nb)
        first = nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(80, "%")))
        second = nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(81, "%")),
                                correction=True)
        active = nb.thoughts_for(i["Mira"], "accuracy", active_only=True)
        old = nb.get_thought(first.detail["fact_id"])
        said = nb.ask("Mira", ["accuracy"])
        return (second.detail.get("supersedes") == first.detail["fact_id"]
                and len(active) == 1 and active[0].value.number == 81.0
                and old is not None and not nb.active(first.detail["fact_id"])
                and said.detail.get("answer") == "81%")

    @case
    def n19_confidence_recorded(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper("fixture-A", i["Mira"], "improves accuracy",
                                  Value.of_number(12, "%"),
                                  "Fixture A: improves accuracy by 12%.",
                                  "https://example.org/paper-a", confidence=0.6))
        t = nb.get_thought(r.detail["fact_id"])
        v1 = t.to_v1()
        no_conf = ThoughtV2(
            subject=i["Mira"], relation="city", value=Value.of_text("Lisbon"),
            provenance=Provenance(document="spoken:listening", sentence="Mira lives in Lisbon.",
                                  claimed_by="taught"),
            source="taught", confidence=None)
        return (t.confidence == 0.6 and v1["provenance"]["confidence"] == 0.6
                and no_conf.confidence is None)

    @case
    def n20_claimed_by_paper_recorded(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper("arXiv:2506.04108", i["Mira"], "delivers speedup",
                                  Value.of_number(2.42, "x"), SENT_RESA, ARXIV_RESA))
        t = nb.get_thought(r.detail["fact_id"])
        return (t.provenance.claimed_by == "paper:arXiv:2506.04108"
                and t.provenance.sentence == SENT_RESA
                and t.to_v1()["provenance"]["claimed_by"] == "paper:arXiv:2506.04108"
                and t.source == "web-quarantine")

    @case
    def n21_adapter_roundtrip_exact_and_degraded(mk, d):
        row = _taught("E0001", "improves accuracy", Value.of_number(12, "%"),
                      sentence="Method X improves accuracy by 12% when Z.",
                      relation_id="open:improves-accuracy",
                      qualifiers=(Qualifier("when", Value.of_text("Z")),))
        v1 = row.to_v1()
        fact = dict(v1, fact_id="F00042")
        back = ThoughtV2.from_v1(fact)
        exact = back.to_dict() == replace(row, thought_id="F00042").to_dict()
        legacy = ThoughtV2.from_v1({
            "fact_id": "F00007", "subject": "E0001", "relation": "city",
            "value": {"literal": "Lisbon"}, "source": "taught"})
        degraded = (legacy.value.kind == "text" and legacy.value.text == "Lisbon"
                    and legacy.confidence is None and legacy.qualifiers == ()
                    and legacy.provenance.claimed_by == "taught")
        return exact and degraded

    @case
    def n22_native_v1_write_degrades_never_guesses(mk, d):
        nb = mk(d); i = _setup2(nb)
        res = nb.assert_fact("a", "listening", "taught", i["Mira"], "city",
                             {"literal": "Lisbon"})
        t = nb.get_thought(res.detail["fact_id"])
        return (t is not None and t.value.kind == "text" and t.value.text == "Lisbon"
                and t.confidence is None
                and t.provenance.document == "v1-legacy"
                and t.provenance.claimed_by == "taught")

    @case
    def n23_tampering_detected(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.add_thought(_taught(i["Mira"], "city", Value.of_text("Lisbon")))
        nb.add_thought(_taught(i["Tom"], "pet", Value.of_text("dog")))
        path = Path(d) / LOG_NAME
        path.write_text(path.read_text(encoding="utf-8").replace("Lisbon", "Madrid"),
                        encoding="utf-8")
        try:
            mk(d)
        except LogCorrupt:
            return True
        return False

    @case
    def n24_ambiguous_entity_never_guesses(mk, d):
        nb = mk(d)
        nb.ensure_entity("e1", "Mira")
        nb.new_entity("e2", "Mira")
        r = nb.ensure_entity("e3", "Mira")
        return r.status == AMBIGUOUS and len(r.detail.get("ids", [])) == 2 \
            and len(nb.entities) == 2

    @case
    def n25_quarantine_needs_sentence_and_url(mk, d):
        nb = mk(d); i = _setup2(nb)
        no_sentence = _paper("fixture-A", i["Mira"], "city", Value.of_text("Rome"),
                             "", "https://example.org/p")
        no_url = ThoughtV2(
            subject=i["Mira"], relation="city", value=Value.of_text("Rome"),
            provenance=Provenance(document="doc:7", sentence="Mira lives in Rome.",
                                  claimed_by="paper:fixture-A"),
            source="web-quarantine")
        ok = _paper("fixture-A", i["Mira"], "city", Value.of_text("Rome"),
                    "Mira lives in Rome.", "https://example.org/p")
        return (nb.add_thought(no_sentence).status == BAD_REQUEST
                and nb.add_thought(no_url).status == BAD_REQUEST
                and nb.add_thought(ok).status == SAVED)

    @case
    def n26_same_content_is_idempotent(mk, d):
        nb = mk(d); i = _setup2(nb)
        row = _taught(i["Mira"], "city", Value.of_text("Lisbon"))
        first = nb.add_thought(row)
        before = len(nb.events)
        second = nb.add_thought(row)
        return (first.status == SAVED and second.status == DUPLICATE_OK
                and len(nb.events) == before)

    @case
    def n27_inferred_never_overwrites_taught(mk, d):
        nb = mk(d); i = _setup2(nb)
        nb.approve_rule("r49", "ben", "R49", "accuracy falls back to a taught value")
        dep = nb.add_thought(_taught(i["Mira"], "accuracy", Value.of_number(80, "%")))
        inferred = ThoughtV2(
            subject=i["Mira"], relation="accuracy", value=Value.of_number(79, "%"),
            provenance=Provenance(document="rule:R49",
                                  sentence="Inferred from dependency facts.",
                                  claimed_by="system:inferred"),
            source="inferred", confidence=0.5, rule_id="R49",
            deps=(dep.detail["fact_id"],))
        r = nb.add_thought(inferred)
        said = nb.ask("Mira", ["accuracy"])
        return (r.status == SAVED and said.status == OK
                and said.detail.get("answer") == "80%"
                and said.detail.get("source") == "taught")

    @case
    def n28_chain_and_index_survive_restart(mk, d):
        nb = mk(d); i = _setup2(nb)
        r1 = nb.add_thought(_taught(i["Mira"], "city", Value.of_text("Lisbon")))
        nb.add_thought(_paper("fixture-A", i["Tom"], "pet", Value.of_text("dog"),
                              "Fixture: Tom's pet is a dog.",
                              "https://example.org/paper-a"))
        again = mk(d)
        t = again.get_thought(r1.detail["fact_id"])
        return (not again.torn_tail and len(again.events) == len(nb.events)
                and t is not None and t.value.text == "Lisbon"
                and t.to_dict() == nb.get_thought(r1.detail["fact_id"]).to_dict())

    @case
    def n29_mixed_qualifiers_order_and_types(mk, d):
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_paper(
            "fixture-A", i["Mira"], "delivers speedup", Value.of_number(2.42, "x"),
            "Fixture: 2.42x speedup at 256K decoding.",
            "https://example.org/paper-a",
            qualifiers=(Qualifier("on dataset", Value.of_text("SST-2")),
                        Qualifier("by", Value.of_number(2.42, "x")),
                        Qualifier("under", Value.of_boolean(True)))))
        t = nb.get_thought(r.detail["fact_id"])
        kinds = [q.value.kind for q in t.qualifiers]
        return ([q.relation for q in t.qualifiers]
                == ["on dataset", "by", "under"] and kinds == ["text", "number", "boolean"])

    @case
    def n30_paper_without_url_is_proposed_and_still_never_answers(mk, d):
        nb = mk(d); i = _setup2(nb)
        row = _paper("fixture-C", i["Mira"], "city", Value.of_text("Rome"),
                     "Fixture C: Method X was evaluated in Rome.",
                     url=None, source="proposed",
                     document="webred:dev:999")
        r = nb.add_thought(row)
        before = nb.ask("Mira", ["city"])
        promoted = nb.promote("p1", "ben", r.detail["fact_id"])
        after = nb.ask("Mira", ["city"])
        return (r.status == SAVED and before.status == MISSING_FACT
                and promoted.status == SAVED and after.status == OK
                and after.detail.get("answer") == "Rome"
                and after.detail.get("source") == "taught")

    @case
    def n31_qualified_rows_answer_only_matching_questions(mk, d):
        """Ben ruling 1: bare question + qualified fact -> MISSING_FACT (abstain)."""
        nb = mk(d); i = _setup2(nb)
        r = nb.add_thought(_taught(
            i["Mira"], "accuracy", Value.of_number(82, "%"),
            qualifiers=(Qualifier("on dataset", Value.of_text("SST-2")),)))
        bare = nb.ask("Mira", ["accuracy"])
        match = nb.ask("Mira", ["accuracy"], qualifiers={"on dataset": "SST-2"})
        wrong_value = nb.ask("Mira", ["accuracy"], qualifiers={"on dataset": "ImageNet"})
        missing_key = nb.ask("Mira", ["accuracy"], qualifiers={"when": "SST-2"})
        nb.add_thought(_taught(i["Mira"], "city", Value.of_text("Lisbon")))
        unqualified = nb.ask("Mira", ["city"])
        return (r.status == SAVED
                and bare.status == MISSING_FACT
                and bare.detail.get("reason") == "qualified"
                and match.status == OK and match.detail.get("answer") == "82%"
                and wrong_value.status == MISSING_FACT
                and missing_key.status == MISSING_FACT
                and unqualified.status == OK
                and unqualified.detail.get("answer") == "Lisbon")

    @case
    def n32_promotion_marks_loser_never_deletes(mk, d):
        """Ben ruling 2: mark the conflicting loser 'superseded-by-promotion'."""
        nb = mk(d); i = _setup2(nb)
        a = nb.add_thought(_paper(
            "fixture-A", i["Mira"], "improves accuracy", Value.of_number(12, "%"),
            "Fixture A: Method X improves accuracy by 12%.",
            "https://example.org/paper-a"))
        b = nb.add_thought(_paper(
            "fixture-B", i["Mira"], "improves accuracy", Value.of_number(15, "%"),
            "Fixture B: Method X improves accuracy by 15%.",
            "https://example.org/paper-b"))
        c = nb.add_thought(_paper(
            "fixture-C", i["Mira"], "improves accuracy", Value.of_number(12, "%"),
            "Fixture C: Method X improves accuracy by 12%.",
            "https://example.org/paper-c"))
        good = nb.promote("p1", "ben", a.detail["fact_id"])
        taught_fid = good.detail["fact_id"]
        loser = nb.get_thought(b.detail["fact_id"])
        same_value = nb.get_thought(c.detail["fact_id"])
        rows = nb.thoughts_for(i["Mira"], "improves accuracy", active_only=False)
        # no-conflict promote marks nothing
        lone = nb.add_thought(_paper(
            "fixture-D", i["Mira"], "city", Value.of_text("Rome"),
            "Fixture D: evaluated in Rome.", "https://example.org/paper-d"))
        nb.promote("p2", "ben", lone.detail["fact_id"])
        again = mk(d)
        loser_reloaded = again.get_thought(b.detail["fact_id"])
        return (good.status == SAVED
                and loser is not None
                and loser.mark == "superseded-by-promotion"
                and loser.marked_by == taught_fid
                and same_value is not None and same_value.mark is None
                and len(rows) == 4
                and again.get_thought(lone.detail["fact_id"]) is not None
                and again.get_thought(b.detail["fact_id"]) is not None
                and loser_reloaded is not None
                and loser_reloaded.mark == "superseded-by-promotion")

    @case
    def n33_relation_id_suggested_raw_kept(mk, d):
        """Ben ruling 3: suggest a WebRED id on exact match; raw string always kept."""
        nb = mk(d); i = _setup2(nb)
        hit = nb.add_thought(_taught(i["Mira"], "place of birth",
                                     Value.of_text("Louisville")))
        miss = nb.add_thought(_taught(i["Mira"], "improves accuracy on Y 12%",
                                      Value.of_number(12, "%")))
        explicit = nb.add_thought(_taught(i["Ana"], "mother",
                                          Value.of_entity(i["Tom"]),
                                          relation_id="custom:mother"))
        t_hit = nb.get_thought(hit.detail["fact_id"])
        t_miss = nb.get_thought(miss.detail["fact_id"])
        t_explicit = nb.get_thought(explicit.detail["fact_id"])
        said = nb.ask("Mira", ["place of birth"])
        return (t_hit.relation_id == "place of birth"
                and t_hit.relation == "place of birth"
                and t_hit.to_v1()["relation"] == "place of birth"
                and t_miss.relation_id is None
                and t_explicit.relation_id == "custom:mother"
                and said.status == OK and said.detail.get("answer") == "Louisville")

    return cases


def run_v2_suite(factory) -> list:
    rows = []
    for fn in v2_cases():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                passed, note = bool(fn(factory, tmp)), ""
            except Exception as exc:
                passed, note = False, "%s: %s" % (type(exc).__name__, exc)
        rows.append((fn.__name__, passed, note))
    return rows


NAIVE_MUST_FAIL_AT_LEAST = 15


def main() -> int:
    parser = argparse.ArgumentParser(description="thought format v2 conformance")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not args.selftest:
        parser.print_help()
        return 0

    print("== A: contract lifecycle suite through ThoughtNotebook ==")
    a = C.run_suite(ThoughtNotebook)
    for name, ok, note in a:
        print("%s  %s %s" % ("PASS" if ok else "FAIL", name, note))
    a_pass = sum(ok for _, ok, _ in a)

    print("== B: contract lifecycle suite through Notebook (control) ==")
    b = C.run_suite(C.Notebook)
    b_pass = sum(ok for _, ok, _ in b)
    for (name, ok, note), (name2, ok2, _) in zip(a, b):
        if not (ok and ok2):
            print("mismatch/fail:", name, "wrapper:", ok, "control:", ok2, note)

    print("== C: contract lifecycle suite through NaiveNotebook (must fail) ==")
    c = C.run_suite(C.NaiveNotebook)
    c_fail = sum(not ok for _, ok, _ in c)

    print("== D: v2 sequences through ThoughtNotebook ==")
    d = run_v2_suite(ThoughtNotebook)
    for name, ok, note in d:
        print("%s  %s %s" % ("PASS" if ok else "FAIL", name, note))
    d_pass = sum(ok for _, ok, _ in d)

    print("== E: v2 sequences through NaiveThoughtNotebook (must fail) ==")
    e = run_v2_suite(NaiveThoughtNotebook)
    for name, ok, note in e:
        if ok:
            print("naive unexpectedly passed:", name)
    e_fail = sum(not ok for _, ok, _ in e)

    print("---- counts ----")
    print("A wrapper x contract: %d/%d" % (a_pass, len(a)))
    print("B control  x contract: %d/%d" % (b_pass, len(b)))
    print("C naive    x contract: fails %d/%d (need >= %d)" % (c_fail, len(c), NAIVE_MUST_FAIL_AT_LEAST))
    print("D wrapper  x v2:       %d/%d" % (d_pass, len(d)))
    print("E naive    x v2:       fails %d/%d (need >= %d)" % (e_fail, len(e), NAIVE_MUST_FAIL_AT_LEAST))
    good = (a_pass == len(a) == b_pass == len(b) and d_pass == len(d)
            and c_fail >= NAIVE_MUST_FAIL_AT_LEAST and e_fail >= NAIVE_MUST_FAIL_AT_LEAST)
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
