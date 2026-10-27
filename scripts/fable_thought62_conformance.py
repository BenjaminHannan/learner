#!/usr/bin/env python3
"""Conformance for thought v3 (doc 67): groups + no-value rows. Plain software.

Marks (see artifacts/fable-thought62-20260921/PASSMARKS.md, sealed first):
  T1  32/32 contract lifecycle cases through the wrapper (old behaviour kept)
  T2  >= 20/20 new wrapper cases (g01..g22)
  T3  rescued >= 15/17 formerly-unrepresentable sentences (gold17 table)
  T4  0 answers from empty/link rows
  T5  to_v1() byte-identical to v2 on ungrouped rows
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_notebook_contract as C                     # noqa: E402
import fable_thought49_schema as V2                     # noqa: E402
from fable_thought49_notebook import (                  # noqa: E402
    ThoughtNotebook as V2Notebook,
)
from fable_thought62_schema import (                    # noqa: E402
    EMPTY_REASONS, NO_VALUE_KINDS, SchemaError, ThoughtNotebook3,
    ThoughtV3, Value3, project_to_v1,
)

SAVED, DUPLICATE_OK = C.SAVED, C.DUPLICATE_OK
OK, MISSING_FACT, BAD_REQUEST, NOT_ALLOWED = C.OK, C.MISSING_FACT, C.BAD_REQUEST, C.NOT_ALLOWED
LogCorrupt = C.LogCorrupt
LOG_NAME = C.LOG_NAME


# ------------------------------------------------------------------ helpers
def _setup3(nb):
    for relation in ("mother", "city", "pet", "accuracy"):
        nb.declare_relation("rel-" + relation, relation, True)
    nb.declare_relation("rel-friend", "friend", False)
    ids = {}
    for name in ("Mira", "Tom", "Ana"):
        ids[name] = nb.ensure_entity("ent-" + name, name).detail["entity_id"]
    return ids


def _v2prov(document, sentence, claimed_by, url=None):
    return V2.Provenance(document=document, sentence=sentence,
                         claimed_by=claimed_by, url=url)


def _ordinary(subject, relation, value, sentence="Ben said so.", **kw):
    return ThoughtV3(
        subject=subject, relation=relation, value=value,
        provenance=_v2prov("spoken:listening", sentence, "taught"),
        source="taught", confidence=1.0, **kw)


def _paper(subject, relation, value, pid, sentence, url, confidence=0.6,
           source="web-quarantine", document=None, **kw):
    return ThoughtV3(
        subject=subject, relation=relation, value=value,
        provenance=_v2prov(document or url, sentence, "paper:" + pid, url=url),
        source=source, confidence=confidence, **kw)


def _empty(subject, relation, reason, sentence, document):
    return ThoughtV3(
        subject=subject, relation=relation, value=Value3.of_empty(reason),
        provenance=_v2prov(document, sentence, "web-quarantine"),
        source="proposed", confidence=None)


def _link(subject, relation, url, reason, sentence, document):
    return ThoughtV3(
        subject=subject, relation=relation,
        value=Value3.of_link(url, reason),
        provenance=_v2prov(document, sentence, "paper:code-note", url=url),
        source="proposed", confidence=None)


def _V3(subject, relation, v2value, sentence="Ben said so.", **kw):
    v = v2value
    value = Value3(kind=v.kind, entity=v.entity, number=v.number, unit=v.unit,
                   date=v.date, text=v.text, boolean=v.boolean)
    return _ordinary(subject, relation, value, sentence, **kw)


# ------------------------------------------- gold rows for the 17 sentences
def gold17(nb):
    """Hand-written v3 rows for doc-49 sections 5-6's 17 failures.

    Returns [(label, extension, [ThoughtV3, ...])] with extension in
    {"empty", "link", "group"}.  Entities are created on nb.
    """
    ent = {}

    def E(name):
        if name not in ent:
            ent[name] = nb.ensure_entity("ent62-" + str(len(ent)),
                                         name).detail["entity_id"]
        return ent[name]

    gold = []

    def add(label, extension, rows):
        gold.append((label, extension, rows))
        return rows

    # --- WebRED dev fragments / absent relations -> empty rows (ext 1)
    add("W13", "empty", [_empty(
        E("CRC Handbook of Chemistry and Physics"), "maintained by",
        "fragment", "CRC. (1996) Handbook of Chemistry and Physics, 76th edn.",
        "webred:dev:2887")])
    add("W19", "empty", [_empty(
        E("Thomas Frank"), "country of citizenship", "absent",
        "Patrick da Silva got his first call-up for the Danish national U19 "
        "team on 19 March 2013 by national U19-coach Thomas Frank.",
        "webred:dev:2136")])
    add("W20", "empty", [_empty(
        E("United States of America"), "contains administrative territorial entity",
        "absent",
        "Saraju Mohanty is an American professor ... at the University of "
        "North Texas in Denton, Texas.", "webred:dev:1989")])
    add("W21", "empty", [_empty(
        E("College of Engineering and Technology, Bhubaneswar"),
        "headquarters location", "fragment",
        "College of Engineering and Technology, Bhubaneswar alumni",
        "webred:dev:1155")])
    add("W22", "empty", [_empty(
        E("DeKalb County"), "shares border with", "absent",
        "In early 2007 MARTA made a request to the City of Atlanta, DeKalb "
        "County, and Fulton County to seek a 15-year extension of the 1% "
        "sales tax from 2032 to 2047.", "webred:dev:592")])
    add("W23", "empty", [_empty(
        E("New York City"), "capital of", "absent",
        "They had been commissioned by the U.S. Army based on a proposal by "
        "the Salmagundi Club of New York.", "webred:dev:1027")])
    add("W24", "empty", [_empty(
        E("Poland"), "country", "absent",
        "``It gives you a very religious feeling, especially because it's "
        "Christmastime,'' said Waldemar Kierzkowski.", "webred:dev:851")])
    add("W25", "empty", [_empty(
        E("Cambridge University Press"), "headquarters location", "fragment",
        "Cambridge: Cambridge University Press.", "webred:dev:1107")])
    add("W27", "empty", [_empty(
        E("Kahlur State"), "capital", "absent",
        "Kahlur Fort is situated in erstwhile princely state of Kahlur (also "
        "known as Bilaspur) in Himachal Pradesh.", "webred:dev:3573")])
    add("W30", "empty", [_empty(
        E("United States of America"), "diplomatic relation", "fragment",
        "Leaves on the tree are coloured by source country, the UK (green "
        "circles), Canada (red) and the United States (blue).",
        "webred:dev:2510")])

    # --- WebRED tables / surveys / geology -> groups of cell rows (ext 2).
    # Each group hangs off one document entity (the paragraph/table is the
    # subject; each member is one cell), so the group answers as one claim.
    add("W26", "group", [
        _paper(E("domestic tables paragraph"), "lists country table",
               Value3(kind="text", text="Belgium"), "webred:tables",
               "In addition, further upstream deviations in domestic tables of "
               "several other countries also play a role, including the tables "
               "of Belgium, Germany, the United States, India, Russia, and the "
               "RoW region.", None, source="proposed",
               document="webred:dev:1470", group_id="w26-tables"),
        _paper(E("domestic tables paragraph"), "lists country table",
               Value3(kind="text", text="Germany"), "webred:tables",
               "In addition, further upstream deviations in domestic tables of "
               "several other countries also play a role, including the tables "
               "of Belgium, Germany, the United States, India, Russia, and the "
               "RoW region.", None, source="proposed",
               document="webred:dev:1470", group_id="w26-tables")])
    surv_q = (V2.Qualifier("across models", V2.Value.of_text("three models")),)
    add("W28", "group", [
        _paper(E("survey paragraph"), "maximum change for Netherlands",
               Value3(kind="number", number=66.0, unit="%"), "webred:survey",
               "Representatives of this group of countries are the United States "
               "(a maximum change of 20% across the three models), Russia (34%), "
               "the Netherlands (66%), and Belgium (71%).", None,
               source="proposed", document="webred:dev:439",
               qualifiers=surv_q, group_id="w28-survey"),
        _paper(E("survey paragraph"), "maximum change for Belgium",
               Value3(kind="number", number=71.0, unit="%"), "webred:survey",
               "Representatives of this group of countries are the United States "
               "(a maximum change of 20% across the three models), Russia (34%), "
               "the Netherlands (66%), and Belgium (71%).", None,
               source="proposed", document="webred:dev:439",
               qualifiers=surv_q, group_id="w28-survey")])
    add("W29", "group", [
        _paper(E("basin sequence"), "formation present in Venezuela",
               Value3(kind="text", text="La Quinta Formation"), "webred:geology",
               "The sedimentary sequence drilled in the basin starts with the La "
               "Quinta Formation, that is found in a widespread area across "
               "northern Colombia and Venezuela.", None, source="proposed",
               document="webred:dev:3382", group_id="w29-geology"),
        _paper(E("basin sequence"), "formation present in Colombia",
               Value3(kind="text", text="La Quinta Formation"), "webred:geology",
               "The sedimentary sequence drilled in the basin starts with the La "
               "Quinta Formation, that is found in a widespread area across "
               "northern Colombia and Venezuela.", None, source="proposed",
               document="webred:dev:3382", group_id="w29-geology")])

    # --- arXiv multi-claim / list -> groups (ext 2)
    SSA = "https://arxiv.org/abs/2511.20102"
    add("A17", "group", [
        _paper(E("SSA"), "headline result",
               Value3(kind="text", text="state-of-the-art under sparse and full "
                                       "attention"), "2511.20102",
               "SSA achieves state-of-the-art under both sparse and full "
               "attention inference modes.", SSA, group_id="a17-ssa"),
        _paper(E("SSA"), "adapts to inference constraints",
               Value3(kind="boolean", boolean=True), "2511.20102",
               "SSA adapts to inference constraints.",
               SSA, qualifiers=(V2.Qualifier(
                   "when", V2.Value.of_text("sparse or full attention")),),
               group_id="a17-ssa"),
        _paper(E("SSA"), "compared to dense attention",
               Value3(kind="text", text="superior efficiency with matching quality"),
               "2511.20102", "SSA is superior to dense attention in efficiency "
               "with matching quality.", SSA,
               qualifiers=(V2.Qualifier(
                   "compared to", V2.Value.of_text("dense attention")),),
               group_id="a17-ssa")])
    DMA = "https://arxiv.org/abs/2508.02124"
    add("A18", "group", [
        _paper(E("DMA"), "key innovation",
               Value3(kind="text", text="trainable dynamic mask"), "2508.02124",
               "We introduce three key innovations.", DMA,
               qualifiers=(V2.Qualifier(
                   "list index", V2.Value.of_number(1)),), group_id="a18-dma"),
        _paper(E("DMA"), "key innovation",
               Value3(kind="text", text="gradient-safe sparse weights"), "2508.02124",
               "We introduce three key innovations.", DMA,
               qualifiers=(V2.Qualifier(
                   "list index", V2.Value.of_number(2)),), group_id="a18-dma"),
        _paper(E("DMA"), "key innovation",
               Value3(kind="text", text="open kernel implementation"), "2508.02124",
               "We introduce three key innovations.", DMA,
               qualifiers=(V2.Qualifier(
                   "list index", V2.Value.of_number(3)),), group_id="a18-dma")])

    # --- arXiv code URLs -> link rows (ext 1). Exact code URLs were not
    # fetched (offline run), so the link points at the paper page and the
    # sentence quote records that the sentence is URL-only metadata.
    add("A19", "link", [_link(
        E("ReSA"), "code available at", "https://arxiv.org/abs/2506.04108",
        "metadata", "Code is available at https://... (URL-only metadata "
        "sentence; exact target not fetched offline).", "arxiv:2506.04108")])
    add("A20", "link", [_link(
        E("DMA"), "kernel open-source at", "https://arxiv.org/abs/2508.02124",
        "metadata", "Kernel open-source at https://... (URL-only metadata "
        "sentence; exact target not fetched offline).", "arxiv:2508.02124")])
    return gold


# ------------------------------------------------------- new wrapper cases
def new_cases():
    cases = []

    def case(fn):
        cases.append(fn)
        return fn

    @case
    def g01_empty_fragment_never_answers(mk, d):
        nb = mk(d); i = _setup3(nb)
        r = nb.add_thought3(_empty(i["Mira"], "city", "fragment",
                                   "Mira lives in ... (truncated citation).",
                                   "webred:dev:1"))
        asked = nb.ask("Mira", ["city"])
        grouped = nb.ask_group("Mira", "no-such-group")
        return (r.status == SAVED and asked.status == MISSING_FACT
                and grouped.status == MISSING_FACT
                and grouped.detail.get("reason") == "partial_group")

    @case
    def g02_empty_absent_never_answers(mk, d):
        nb = mk(d); i = _setup3(nb)
        nb.add_thought3(_empty(i["Mira"], "country of citizenship", "absent",
                               "Thomas Frank coaches the team.", "webred:dev:2"))
        return nb.ask("Mira", ["country of citizenship"]).status == MISSING_FACT

    @case
    def g03_empty_metadata_never_answers(mk, d):
        nb = mk(d); i = _setup3(nb)
        nb.add_thought3(_empty(i["Mira"], "caption", "metadata",
                               "Figure 1. Overview diagram.", "paper:caps"))
        return nb.ask("Mira", ["caption"]).status == MISSING_FACT

    @case
    def g04_link_never_answers(mk, d):
        nb = mk(d); i = _setup3(nb)
        r = nb.add_thought3(_link(i["Mira"], "code available at",
                                  "https://example.org/code", "metadata",
                                  "Code is available at https://example.org/code.",
                                  "arxiv:x"))
        return (r.status == SAVED
                and nb.ask("Mira", ["code available at"]).status == MISSING_FACT
                and nb.ask_group("Mira", "zz").detail.get("reason") == "partial_group")

    @case
    def g05_no_value_must_be_proposed(mk, d):
        try:
            ThoughtV3(subject="E0001", relation="city",
                      value=Value3.of_empty("absent"),
                      provenance=_v2prov("d", "s", "taught"),
                      source="taught", confidence=1.0)
            return False
        except SchemaError:
            pass
        try:
            ThoughtV3(subject="E0001", relation="city",
                      value=Value3.of_link("https://example.org", "metadata"),
                      provenance=_v2prov("d", "s", "taught"),
                      source="taught", confidence=1.0)
            return False
        except SchemaError:
            return True

    @case
    def g06_reason_vocab_gate(mk, d):
        for bad in ("unknown", "", None, "Fragment"):
            try:
                Value3.of_empty(bad).validate()
                return False
            except SchemaError:
                pass
        return all(Value3.of_empty(r).validate() is None for r in EMPTY_REASONS)

    @case
    def g07_link_url_gate(mk, d):
        try:
            Value3.of_link("not-a-url", "metadata").validate()
            return False
        except SchemaError:
            return True

    @case
    def g08_promote_refuses_no_value(mk, d):
        nb = mk(d); i = _setup3(nb)
        e = nb.add_thought3(_empty(i["Mira"], "city", "fragment", "frag.", "d:1"))
        li = nb.add_thought3(_link(i["Mira"], "code available at",
                                   "https://example.org/c", "metadata",
                                   "Code at https://example.org/c.", "d:2"))
        refused = (nb.promote("p1", "ben", e.detail["fact_id"]).status == BAD_REQUEST
                   and nb.promote("p2", "ben", li.detail["fact_id"]).status == BAD_REQUEST)
        still = (nb.ask("Mira", ["city"]).status == MISSING_FACT
                 and nb.ask("Mira", ["code available at"]).status == MISSING_FACT)
        return refused and still

    @case
    def g09_partial_group_one_promoted(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["A17"]:
            nb.add_thought3(row)
        nb.promote("p1", "ben", nb.group_members("a17-ssa")[0].thought_id)
        said = nb.ask_group("SSA", "a17-ssa")
        return said.status == MISSING_FACT and said.detail.get("reason") == "partial_group"

    @case
    def g10_full_group_answers(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for n, row in enumerate(gold["A17"]):
            nb.add_thought3(row)
        for n, mem in enumerate(nb.group_members("a17-ssa")):
            nb.promote("p%d" % (n + 1), "ben", mem.thought_id)
        said = nb.ask_group("SSA", "a17-ssa",
                            qualifiers={"when": "sparse or full attention",
                                        "compared to": "dense attention"})
        return (said.status == OK and said.detail.get("members") == 3
                and said.detail.get("group_id") == "a17-ssa"
                and "headline result" in said.detail.get("answer", "")
                and len(said.detail.get("trail", [])) == 3)

    @case
    def g11_plain_ask_abstains_on_member(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["W28"]:
            nb.add_thought3(row)
        before = nb.ask("survey paragraph", ["maximum change for Netherlands"])
        for n, mem in enumerate(nb.group_members("w28-survey")):
            nb.promote("q%d" % (n + 1), "ben", mem.thought_id)
        after = nb.ask("survey paragraph", ["maximum change for Netherlands"])
        full = nb.ask_group("survey paragraph", "w28-survey",
                            qualifiers={"across models": "three models"})
        return (before.status == MISSING_FACT
                and after.detail.get("reason") == "partial_group"
                and full.status == OK and "66%" in full.detail.get("answer", ""))

    @case
    def g12_group_qualifier_mismatch_abstains(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["W28"]:
            nb.add_thought3(row)
        for n, mem in enumerate(nb.group_members("w28-survey")):
            nb.promote("q%d" % (n + 10), "ben", mem.thought_id)
        wrong = nb.ask_group("survey paragraph", "w28-survey",
                             qualifiers={"across models": "five models"})
        missing = nb.ask_group("survey paragraph", "w28-survey")
        return (wrong.status == MISSING_FACT
                and wrong.detail.get("reason") == "partial_group"
                and missing.status == MISSING_FACT)

    @case
    def g13_to_v1_drops_no_value(mk, d):
        nb = mk(d); i = _setup3(nb)
        e = _empty(i["Mira"], "city", "fragment", "frag.", "d:1")
        li = _link(i["Mira"], "code available at", "https://example.org/c",
                   "metadata", "Code.", "d:2")
        ok_row = _V3(i["Mira"], "city", V2.Value.of_text("Lisbon"))
        try:
            e.to_v1()
            return False
        except SchemaError:
            pass
        try:
            li.to_v1()
            return False
        except SchemaError:
            pass
        projected = project_to_v1([e, ok_row, li])
        return len(projected) == 1 and projected[0]["relation"] == "city"

    @case
    def g14_to_v1_group_tag(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        row = gold["W29"][0]
        nb.add_thought3(row)
        stored = nb.group_members("w29-geology")[0]
        payload = stored.to_v1()
        return (payload["value"] == {"literal": "La Quinta Formation"}
                and "[group w29-geology]" in payload["raw"]
                and payload["provenance"]["group_id"] == "w29-geology"
                and payload["provenance"]["quoted_span"].find("[group") == -1)

    @case
    def g15_ungrouped_byte_identical(mk, d):
        nb = mk(d); i = _setup3(nb)
        battery = [
            _V3(i["Mira"], "accuracy improvement", V2.Value.of_number(12, "%"),
                sentence="Improves by 12%."),
            _V3(i["Mira"], "date of birth", V2.Value.of_date("1959-06-06")),
            _V3(i["Mira"], "obstructs gradients", V2.Value.of_boolean(False)),
            _V3(i["Mira"], "headline result",
                V2.Value.of_text("state-of-the-art under both modes")),
            _V3(i["Mira"], "mother", V2.Value.of_entity(i["Ana"])),
            ThoughtV3(subject=i["Mira"], relation="delivers speedup",
                      value=Value3(kind="number", number=2.42, unit="x"),
                      provenance=_v2prov("https://example.org/p",
                                         "Delivers 2.42x when Z.", "paper:P1",
                                         url="https://example.org/p"),
                      qualifiers=(V2.Qualifier(
                          "when", V2.Value.of_text("Z is on")),),
                      source="web-quarantine", confidence=0.7),
        ]
        for row in battery:
            v2row = row._to_v2()
            left = json.dumps(row.to_v1(), sort_keys=True, ensure_ascii=False)
            right = json.dumps(v2row.to_v1(), sort_keys=True, ensure_ascii=False)
            if left != right:
                return False
        return True

    @case
    def g16_group_roundtrip_restart(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["W29"]:
            nb.add_thought3(row)
        again = mk(d)
        members = again.group_members("w29-geology")
        said = again.ask_group("basin sequence", "w29-geology")
        return (len(members) == 2
                and {t.value.text for t in members} == {"La Quinta Formation"}
                and said.status == MISSING_FACT)

    @case
    def g17_empty_roundtrip_restart(mk, d):
        nb = mk(d); i = _setup3(nb)
        nb.add_thought3(_empty(i["Mira"], "maintained by", "fragment",
                               "CRC. (1996) Handbook, 76th edn.", "webred:dev:9"))
        again = mk(d)
        rows = again.thoughts_for3(i["Mira"], "maintained by")
        return (len(rows) == 1 and rows[0].value.kind == "empty"
                and rows[0].value.reason == "fragment"
                and again.ask("Mira", ["maintained by"]).status == MISSING_FACT)

    @case
    def g18_hash_chain_intact(mk, d):
        nb = mk(d); i = _setup3(nb)
        nb.add_thought3(_V3(i["Mira"], "city", V2.Value.of_text("Lisbon")))
        nb.add_thought3(_empty(i["Tom"], "capital", "absent",
                               "The club met in the capital.", "webred:dev:8"))
        path = Path(d) / LOG_NAME
        path.write_text(path.read_text(encoding="utf-8").replace("Lisbon", "Madrid"),
                        encoding="utf-8")
        try:
            mk(d)
        except LogCorrupt:
            return True
        return False

    @case
    def g19_v2_readers_unaffected(mk, d):
        nb = mk(d); i = _setup3(nb)
        plain = _V3(i["Mira"], "city", V2.Value.of_text("Lisbon"))
        r1 = nb.add_thought3(plain)
        nb.add_thought3(_empty(i["Tom"], "capital", "absent",
                               "The club met.", "webred:dev:8"))
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["W29"]:
            nb.add_thought3(row)
        old = V2Notebook(d)
        t_plain = old.get_thought(r1.detail["fact_id"])
        n_empty_visible = 0
        for fid in old.nb.facts:
            t = old.get_thought(fid)
            if t is not None and t.value.kind in NO_VALUE_KINDS:
                n_empty_visible += 1
        n_grouped_visible = 0
        for fid in old.nb.facts:
            t = old.get_thought(fid)
            if t is not None and t.value.kind == "text" \
                    and t.value.text == "La Quinta Formation":
                n_grouped_visible += 1
        return (t_plain is not None and t_plain.value.text == "Lisbon"
                and n_empty_visible == 0 and n_grouped_visible == 2)

    @case
    def g20_gold17_all_rescued(mk, d):
        nb = mk(d)
        gold = gold17(nb)
        if len(gold) != 17:
            return False
        exts = {}
        for label, extension, rows in gold:
            if len(rows) < 1:
                return False
            if extension == "group" and (len(rows) < 2
                                         or len({r.group_id for r in rows}) != 1):
                return False
            for row in rows:
                if nb.add_thought3(row).status != SAVED:
                    return False
            exts[extension] = exts.get(extension, 0) + 1
        return exts.get("empty", 0) == 10 and exts.get("link", 0) == 2 \
            and exts.get("group", 0) == 5

    @case
    def g21_singleton_group_abstains(mk, d):
        nb = mk(d); i = _setup3(nb)
        nb.add_thought3(_ordinary(
            i["Mira"], "city", Value3(kind="text", text="Lisbon"),
            group_id="lonely"))
        said = nb.ask_group("Mira", "lonely")
        return said.status == MISSING_FACT \
            and said.detail.get("reason") == "partial_group"

    @case
    def g22_ask_group_unknown_subject(mk, d):
        nb = mk(d)
        gold = dict((label, rows) for label, _, rows in gold17(nb))
        for row in gold["W29"]:
            nb.add_thought3(row)
        return nb.ask_group("Zed", "w29-geology").status != OK
    return cases


def run_new_suite(factory) -> list:
    rows = []
    for fn in new_cases():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                passed, note = bool(fn(factory, tmp)), ""
            except Exception as exc:
                passed, note = False, "%s: %s" % (type(exc).__name__, exc)
        rows.append((fn.__name__, passed, note))
    return rows


def count_no_value_answers(factory) -> tuple:
    """T4: every ask/ask_group over empty/link rows; count OK answers (bar 0)."""
    asked, answered = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        nb = factory(tmp)
        i = _setup3(nb)
        nb.add_thought3(_empty(i["Mira"], "city", "fragment", "frag.", "d:1"))
        nb.add_thought3(_empty(i["Mira"], "country", "absent", "nope.", "d:2"))
        nb.add_thought3(_empty(i["Mira"], "caption", "metadata", "Fig.", "d:3"))
        nb.add_thought3(_link(i["Mira"], "code available at",
                              "https://example.org/c", "metadata",
                              "Code at https://example.org/c.", "d:4"))
        for rel in ("city", "country", "caption", "code available at"):
            asked += 1
            if nb.ask("Mira", [rel]).status == OK:
                answered += 1
        asked += 1
        if nb.ask("Mira", ["city", "country"]).status == OK:
            answered += 1
        for gid in ("g", "nope"):
            asked += 1
            if nb.ask_group("Mira", gid).status == OK:
                answered += 1
    return asked, answered


def count_byte_identical(factory) -> tuple:
    """T5: ungrouped wrapper to_v1() vs v2 to_v1() over a value-kind battery."""
    with tempfile.TemporaryDirectory() as tmp:
        nb = factory(tmp)
        i = _setup3(nb)
        battery = [
            _V3(i["Mira"], "accuracy improvement", V2.Value.of_number(12, "%"),
                sentence="Improves by 12%."),
            _V3(i["Mira"], "fraction", V2.Value.of_number(0.82)),
            _V3(i["Mira"], "speed", V2.Value.of_number(3.5, "m/s")),
            _V3(i["Mira"], "date of birth", V2.Value.of_date("1959-06-06")),
            _V3(i["Mira"], "obstructs gradients", V2.Value.of_boolean(False)),
            _V3(i["Mira"], "headline result",
                V2.Value.of_text("state-of-the-art")),
            _V3(i["Mira"], "mother", V2.Value.of_entity(i["Ana"])),
            _V3(i["Tom"], "city", V2.Value.of_text("Lisbon")),
        ]
        total, same = 0, 0
        for row in battery:
            total += 1
            left = json.dumps(row.to_v1(), sort_keys=True, ensure_ascii=False)
            right = json.dumps(row._to_v2().to_v1(), sort_keys=True,
                               ensure_ascii=False)
            if left == right:
                same += 1
    return total, same


def main() -> int:
    parser = argparse.ArgumentParser(description="thought v3 conformance")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not args.selftest:
        parser.print_help()
        return 0

    print("== T1: contract lifecycle suite through ThoughtNotebook3 ==")
    a = C.run_suite(ThoughtNotebook3)
    for name, ok, note in a:
        print("%s  %s %s" % ("PASS" if ok else "FAIL", name, note))
    t1_pass = sum(ok for _, ok, _ in a)

    print("== T2: new v3 cases ==")
    b = run_new_suite(ThoughtNotebook3)
    for name, ok, note in b:
        print("%s  %s %s" % ("PASS" if ok else "FAIL", name, note))
    t2_pass = sum(ok for _, ok, _ in b)

    print("== T3: gold17 rescue ==")
    with tempfile.TemporaryDirectory() as tmp:
        nb = ThoughtNotebook3(tmp)
        gold = gold17(nb)
        rescued, per_ext = 0, {}
        for label, extension, rows in gold:
            ok = all(nb.add_thought3(row).status == SAVED for row in rows)
            if extension == "group":
                ok = ok and len(rows) >= 2
            rescued += 1 if ok else 0
            per_ext[extension] = per_ext.get(extension, 0) + (1 if ok else 0)
            print("%s  %s [%s] %d row(s)" % ("RESCUED" if ok else "NOT",
                                             label, extension, len(rows)))
    print("rescued %d/17 %s" % (rescued, per_ext))

    print("== T4: no-value answers ==")
    asked, answered = count_no_value_answers(ThoughtNotebook3)
    print("OK answers from empty/link rows: %d/%d asked" % (answered, asked))

    print("== T5: byte-identical adapter ==")
    total, same = count_byte_identical(ThoughtNotebook3)
    print("identical %d/%d" % (same, total))

    print("---- marks ----")
    t1 = (t1_pass == 32 == len(a))
    t2 = (t2_pass == len(b) >= 20)
    t3 = (rescued >= 15)
    t4 = (answered == 0)
    t5 = (same == total)
    print("T1 old 32/32: %d/%d %s" % (t1_pass, len(a), "PASS" if t1 else "FAIL"))
    print("T2 new >=20/20: %d/%d %s" % (t2_pass, len(b), "PASS" if t2 else "FAIL"))
    print("T3 rescued >=15/17: %d/17 %s %s" % (rescued, per_ext, "PASS" if t3 else "FAIL"))
    print("T4 0 answers: %d %s" % (answered, "PASS" if t4 else "FAIL"))
    print("T5 byte-identical: %d/%d %s" % (same, total, "PASS" if t5 else "FAIL"))
    good = t1 and t2 and t3 and t4 and t5
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
