#!/usr/bin/env python3
"""Experiment 56 conformance: 24 hand-written reasoner cases + 6 miner cases.

Builds one small thought notebook (qualified + unqualified taught rows over
1-hop and 2/3-hop chains), asks each question through the qualifier-aware
wrapper AND through plain reasoner50 (naive control, identical questions).

A case passes when status, answer and reason all match expectation. The naive
control is expected to FAIL every case where a qualified row must be gated
(it answers through to_v1() projections). A 'wrong answer' is OK-with-wrong-
answer or OK-where-MISSING-was-expected; the wrapper must produce zero.

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_qual56_conformance.py --out artifacts/fable-qual56-20260921
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_reasoner50 as R50  # noqa: E402
from fable_qual56_miner_filter import (  # noqa: E402
    chain_passes_through_qualified,
    filter_qualified_turns,
)
from fable_qual56_reasoner import QualifierAwareReasoner  # noqa: E402
from fable_thought49_notebook import ThoughtNotebook  # noqa: E402
from fable_thought49_schema import (  # noqa: E402
    Provenance,
    Qualifier,
    ThoughtV2,
    Value,
)

Q19 = Qualifier("when", Value.of_text("2019"))
Q20 = Qualifier("when", Value.of_text("2020"))
QT300 = Qualifier("at_temp", Value.of_text("300 K"))
QPERM = Qualifier("contract", Value.of_text("perm"))

WHEN19 = {"when": "2019"}
WHEN20 = {"when": "2020"}
BOTH = {"when": "2019", "contract": "perm"}
T300 = {"at_temp": "300 K"}
T310 = {"at_temp": "310 K"}


def T(subj, rel, lit, quals=()) -> ThoughtV2:
    return ThoughtV2(
        subject=subj, relation=rel, value=Value.of_text(lit),
        provenance=Provenance(document="exp56",
                              sentence=f"{subj} {rel} {lit} taught.",
                              claimed_by="taught"),
        qualifiers=tuple(quals), source="taught")


def TE(subj, rel, target_eid, quals=()) -> ThoughtV2:
    return ThoughtV2(
        subject=subj, relation=rel, value=Value.of_entity(target_eid),
        provenance=Provenance(document="exp56",
                              sentence=f"{subj} {rel} {target_eid} taught.",
                              claimed_by="taught"),
        qualifiers=tuple(quals), source="taught")


def build_notebook(root: Path) -> ThoughtNotebook:
    tn = ThoughtNotebook(root)
    for rel in ("works_at", "lives_in", "boss"):
        tn.declare_relation(f"q56-{rel}", rel, True)
    tn.declare_relation("q56-skill", "skill", False)
    eid = {}
    for name in ("Ann", "Ben", "Cat", "Dan", "Eli", "Fay"):
        eid[name] = tn.ensure_entity(f"q56-e-{name}", name).detail["entity_id"]
    rows = [
        T(eid["Ann"], "works_at", "Acme", (Q19,)),
        T(eid["Ann"], "lives_in", "Paris"),
        # Non-functional 'skill' lets an unqualified and a qualified taught row
        # coexist active (functional relations refuse the second write). The
        # unqualified 'typing' row is OLDER so the naive newest-first view
        # prefers the qualified 'soldering' row (control must fail).
        T(eid["Ben"], "skill", "typing"),
        T(eid["Ben"], "skill", "soldering", (Q20,)),
        TE(eid["Cat"], "boss", eid["Dan"]),
        T(eid["Dan"], "works_at", "Umbrella", (Q19,)),
        TE(eid["Dan"], "boss", eid["Eli"]),
        T(eid["Eli"], "lives_in", "Rome", (Q19, QPERM)),
        T(eid["Fay"], "works_at", "Hooli", (Q19,)),
        T(eid["Fay"], "lives_in", "Oslo", (QT300,)),
    ]
    for i, thought in enumerate(rows):
        res = tn.add_thought(thought, event_id=f"q56-f{i}")
        assert res.status == C.SAVED, (i, res)
    return tn


def Q(name, relations, qualifiers=None):
    q = {"name": name, "relations": list(relations)}
    if qualifiers is not None:
        q["qualifiers"] = qualifiers
    return q


# (id, question, expected_status, expected_answer, expected_reason)
CASES = [
    ("C1", Q("Ann", ["works_at"]), C.MISSING_FACT, None, "qualified"),
    ("C2", Q("Ann", ["works_at"], WHEN19), C.OK, "Acme", None),
    ("C3", Q("Ann", ["works_at"], WHEN20), C.MISSING_FACT, None, "qualified"),
    ("C4", Q("Ann", ["lives_in"]), C.OK, "Paris", None),
    ("C5", Q("Ben", ["skill"]), C.OK, "typing", None),
    ("C6", Q("Ben", ["skill"], WHEN20), C.OK, "typing", None),
    ("C7", Q("Cat", ["boss"]), C.OK, "Dan", None),
    ("C8", Q("Eli", ["lives_in"]), C.MISSING_FACT, None, "qualified"),
    ("C9", Q("Eli", ["lives_in"], WHEN19), C.MISSING_FACT, None, "qualified"),
    ("C10", Q("Eli", ["lives_in"], BOTH), C.OK, "Rome", None),
    ("C11", Q("Fay", ["lives_in"]), C.MISSING_FACT, None, "qualified"),
    ("C12", Q("Fay", ["lives_in"], T300), C.OK, "Oslo", None),
    ("C13", Q("Fay", ["lives_in"], T310), C.MISSING_FACT, None, "qualified"),
    ("C14", Q("Cat", ["boss", "works_at"]), C.MISSING_FACT, None, "qualified"),
    ("C15", Q("Cat", ["boss", "works_at"], WHEN19), C.OK, "Umbrella", None),
    ("C16", Q("Cat", ["boss", "works_at"], WHEN20), C.MISSING_FACT, None, "qualified"),
    ("C17", Q("Ann", ["boss"]), C.MISSING_FACT, None, None),
    ("C18", Q("Dan", ["works_at"]), C.MISSING_FACT, None, "qualified"),
    ("C19", Q("Dan", ["works_at"], WHEN19), C.OK, "Umbrella", None),
    ("C20", Q("Cat", ["boss", "boss"]), C.OK, "Eli", None),
    ("C21", Q("Cat", ["boss", "boss", "lives_in"]), C.MISSING_FACT, None, "qualified"),
    ("C22", Q("Cat", ["boss", "boss", "lives_in"], BOTH), C.OK, "Rome", None),
    ("C23", Q("Ann", ["lives_in", "works_at"]), C.BROKEN_CHAIN, None, None),
    ("C24", Q("Fay", ["works_at"]), C.MISSING_FACT, None, "qualified"),
]


def check(got: dict, status: str, answer, reason) -> bool:
    if got["status"] != status:
        return False
    if status == C.OK:
        return got["fields"].get("answer") == answer
    if reason is None:
        return "reason" not in got["fields"]
    return got["fields"].get("reason") == reason


def is_wrong(got: dict, status: str, answer) -> bool:
    """A wrong answer: OK given where MISSING expected, or a wrong OK value."""
    if got["status"] != C.OK:
        return False
    if status != C.OK:
        return True
    return got["fields"].get("answer") != answer


def run_miner_checks(tn) -> list:
    """Six hand-written miner-filter checks on the same notebook."""
    out = []

    def turn(kind, **kw):
        t = {"kind": kind}
        t.update(kw)
        return t

    log = [
        turn("ask", pair_id="a1", start="Cat", chain=["boss", "works_at"],
             status=C.OK, answer="Umbrella"),
        turn("confirm", pair_id="a1", value="Umbrella"),
        turn("ask", pair_id="a2", start="Cat", chain=["boss"],
             status=C.OK, answer="Dan"),
        turn("confirm", pair_id="a2", value="Dan"),
        turn("correct", start="Ann", chain=["works_at"], value="Acme"),
        turn("smalltalk", text="hello there"),
    ]
    before = json.dumps(log, sort_keys=True)
    kept = filter_qualified_turns(log, tn)
    kinds = [(t.get("kind"), t.get("pair_id", t.get("text", t.get("value")))) for t in kept]
    out.append(("M1", ("ask", "a1") not in kinds, "qualified-chain ask dropped"))
    out.append(("M2", ("ask", "a2") in kinds and ("confirm", "a2") in kinds,
                "unqualified ask+confirm kept"))
    out.append(("M3", not any(t.get("kind") == "correct" for t in kept),
                "qualified-chain correction dropped"))
    out.append(("M4", ("smalltalk", "hello there") in kinds,
                "non-chain turns pass through"))
    out.append(("M5", json.dumps(log, sort_keys=True) == before and len(log) == 6,
                "input log untouched (pure)"))
    out.append(("M6", chain_passes_through_qualified("Cat", ["boss", "works_at"], tn)
                and not chain_passes_through_qualified("Cat", ["boss"], tn)
                and not chain_passes_through_qualified("Nobody", ["boss"], tn),
                "walk detector: qualified hop / clean hop / unknown start"))
    return [(i, bool(ok), note) for i, ok, note in out]


def main() -> int:
    ap = argparse.ArgumentParser(description="Experiment 56 conformance")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(dir=str(SCRIPTS)) as tmp:
        tn = build_notebook(Path(tmp) / "nb")
        nb = tn.nb  # the unmodified contract notebook underneath
        aware = QualifierAwareReasoner()
        naive = R50.FableReasoner50()

        rows = []
        for cid, question, status, answer, reason in CASES:
            got = aware.answer(question, nb)
            ctl = naive.answer(question, nb)
            ok = check(got, status, answer, reason)
            ctl_ok = check(ctl, status, answer, reason)
            rows.append({"id": cid, "pass": bool(ok), "naive_pass": bool(ctl_ok),
                         "wrong": bool(is_wrong(got, status, answer)),
                         "naive_wrong": bool(is_wrong(ctl, status, answer)),
                         "got": got, "naive": ctl,
                         "expect": {"status": status, "answer": answer,
                                    "reason": reason}})
            print(f"{cid} ours={'PASS' if ok else 'FAIL'} "
                  f"naive={'PASS' if ctl_ok else 'FAIL'} "
                  f"got={got['status']} {json.dumps(got['fields'], default=str)[:110]}",
                  flush=True)

        miner = run_miner_checks(tn)
        for mid, ok, note in miner:
            print(f"{mid} {'PASS' if ok else 'FAIL'}  {note}", flush=True)

    n = len(rows)
    ours = sum(r["pass"] for r in rows)
    naive_fail = sum(not r["naive_pass"] for r in rows)
    wrong = sum(r["wrong"] for r in rows)
    naive_wrong = sum(r["naive_wrong"] for r in rows)
    miner_ok = sum(ok for _, ok, _ in miner)
    summary = {"cases": n, "ours_pass": ours, "naive_fail": naive_fail,
               "ours_wrong": wrong, "naive_wrong": naive_wrong,
               "miner": f"{miner_ok}/{len(miner)}"}
    print(json.dumps(summary))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "conformance.json").write_text(
        json.dumps({"rows": rows,
                    "miner": [{"id": m, "pass": bool(ok), "note": note}
                              for m, ok, note in miner],
                    "summary": summary}, indent=1))
    ok_all = ours == n and miner_ok == len(miner)
    print("CONFORMANCE", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
