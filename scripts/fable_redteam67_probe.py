#!/usr/bin/env python3
"""REDTEAM67 adversarial probe of the plain-software core (read-only use of the core).

Cases are ACTION SEQUENCES on the notebook / reasoner (not English: the ears are
not under test). Each case records expected (from the contract docstring +
design docs 36/50/49), observed, and verdict OK / BUG / UNCLEAR.

Under test: fable_notebook_contract, fable_listening_m1, fable_reasoner50,
fable_qual56_reasoner, fable_thought49_notebook (+schema), fable_agent_loop.
Finds bugs only; fixes nothing.

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
  --python 3.12 --with torch --with numpy python -B scripts/fable_redteam67_probe.py
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_listening_m1 as L  # noqa: E402
import fable_reasoner50 as R50  # noqa: E402
import fable_qual56_reasoner as Q56  # noqa: E402
from fable_thought49_notebook import ThoughtNotebook  # noqa: E402
from fable_thought49_schema import (  # noqa: E402
    Provenance, Qualifier, ThoughtV2, Value,
)
import fable_agent_loop as G  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "scratchpad" / "fable_redteam67"
E = lambda i: {"entity": i}  # noqa: E731
LI = lambda t: {"literal": t}  # noqa: E731

RESULTS: list[dict] = []


def fresh(name: str) -> C.Notebook:
    d = ROOT / name
    if d.exists():
        shutil.rmtree(d)
    return C.Notebook(d)


def mk(tag: str, nb: C.Notebook, name: str) -> str:
    r = nb.new_entity(f"{tag}-e-{name}", name)
    assert r.status == C.SAVED, r
    return r.detail["entity_id"]


def decl(nb: C.Notebook, tag: str, relation: str, functional: bool = True) -> None:
    nb.declare_relation(f"{tag}-rel-{relation}", relation, functional)


def case(cid: str, title: str, expected: str, fn) -> None:
    try:
        observed, verdict, note = fn()
    except Exception as exc:  # noqa: BLE001 -- a crash is itself a finding
        observed, verdict, note = f"CRASH {type(exc).__name__}: {exc}", "BUG", "crashed"
    RESULTS.append({"id": cid, "title": title, "expected": expected,
                    "observed": observed, "verdict": verdict, "note": note})
    print(f"{cid} [{verdict}] {title}\n    exp: {expected}\n    obs: {observed}")


def v_ok(obs: str) -> tuple[str, str, str]:
    return obs, "OK", ""


def v_bug(obs: str, note: str = "") -> tuple[str, str, str]:
    return obs, "BUG", note


# ------------------------------------------------------------- contract core
def t01():
    nb = fresh("rt01"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    r1 = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    r2 = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Lisbon"))
    ans = nb.ask("Mira", ["city"])
    obs = f"first={r1.status} second={r2.status} answer={ans.detail.get('answer')} events={len(nb.events)}"
    if r1.status == C.SAVED and r2.status == C.DUPLICATE_OK and ans.detail.get("answer") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t02():
    nb = fresh("rt02"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    f1 = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    f2 = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Paris"), correction=True)
    f3 = nb.assert_fact("e3", "listening", "taught", a, "city", LI("Rome"), correction=True)
    ans = nb.ask("Mira", ["city"])
    act = [f for f in (f1.detail["fact_id"], f2.detail["fact_id"], f3.detail["fact_id"]) if nb.active(f)]
    obs = f"answer={ans.detail.get('answer')} active={act} sup2={f2.detail.get('supersedes')} sup3={f3.detail.get('supersedes')}"
    if ans.detail.get("answer") == "Rome" and act == [f3.detail["fact_id"]]:
        return v_ok(obs)
    return v_bug(obs)


def t03():
    nb = fresh("rt03"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    r = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Paris"), correction=True)
    ans = nb.ask("Mira", ["city"])
    obs = f"status={r.status} supersedes={r.detail.get('supersedes')} answer={ans.detail.get('answer')}"
    if r.status == C.SAVED and r.detail.get("supersedes") is None and ans.detail.get("answer") == "Paris":
        return v_ok(obs)
    return v_bug(obs)


def t04():
    nb = fresh("rt04"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    r = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Paris"))
    ans = nb.ask("Mira", ["city"])
    obs = f"status={r.status} answer={ans.detail.get('answer')}"
    if r.status == C.CONFLICT and ans.detail.get("answer") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t05():
    nb = fresh("rt05"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    c = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Paris"))
    r = nb.assert_fact("e3", "listening", "taught", a, "city", LI("Paris"), correction=True)
    ans = nb.ask("Mira", ["city"])
    obs = f"conflict={c.status} corrected={r.status} answer={ans.detail.get('answer')}"
    if c.status == C.CONFLICT and r.status == C.SAVED and ans.detail.get("answer") == "Paris":
        return v_ok(obs)
    return v_bug(obs)


def t06():
    nb = fresh("rt06")
    s1 = mk("t", nb, "Sam")
    s2 = nb.new_entity("e-sam2", "Sam").detail["entity_id"]
    r = nb.resolve("Sam")
    nb.add_alias("e-al", s1, "Samuel")
    r2 = nb.resolve("Samuel")
    obs = f"resolve-Sam={r.status} ids={r.detail.get('ids')} alias={r2.status}"
    if r.status == C.AMBIGUOUS and r.detail.get("ids") == [s1, s2] and r2.status == C.OK:
        return v_ok(obs)
    return v_bug(obs)


def t07():
    nb = fresh("rt07"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira"); b = mk("t", nb, "Ana")
    nb.add_alias("e-al", b, "Annie")
    nb.assert_fact("e1", "listening", "taught", b, "city", LI("Porto"))
    ans = nb.ask("Annie", ["city"])
    obs = f"status={ans.status} answer={ans.detail.get('answer')}"
    if ans.status == C.OK and ans.detail.get("answer") == "Porto":
        return v_ok(obs)
    return v_bug(obs)


def t08():
    nb = fresh("rt08"); decl(nb, "t", "mother"); a = mk("t", nb, "Narcissus")
    r = nb.assert_fact("e1", "listening", "taught", a, "mother", E(a))
    ans = nb.ask("Narcissus", ["mother"])
    obs = f"write={r.status} answer={ans.detail.get('answer')}"
    if r.status == C.SAVED and ans.detail.get("answer") == "Narcissus":
        return v_ok(obs)
    return v_bug(obs)


def t09():
    nb = fresh("rt09"); decl(nb, "t", "mother")
    a = mk("t", nb, "A"); b = mk("t", nb, "B")
    t0 = time.time()
    nb.assert_fact("e1", "listening", "taught", a, "mother", E(b))
    nb.assert_fact("e2", "listening", "taught", b, "mother", E(a))
    ans = nb.ask("A", ["mother", "mother"])
    dt = time.time() - t0
    obs = f"answer={ans.detail.get('answer')} status={ans.status} dt={dt:.2f}s"
    if ans.detail.get("answer") == "A" and dt < 5:
        return v_ok(obs)
    return v_bug(obs)


def t10():
    nb = fresh("rt10"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    f1 = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    f2 = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Paris"), correction=True)
    obs = (f"sup={f2.detail.get('supersedes')}=={f1.detail.get('fact_id')} "
           f"old_active={nb.active(f1.detail['fact_id'])} answer={nb.ask('Mira', ['city']).detail.get('answer')}")
    if f2.detail.get("supersedes") == f1.detail["fact_id"] and not nb.active(f1.detail["fact_id"]):
        return v_ok(obs)
    return v_bug(obs)


def t11():
    nb = fresh("rt11"); decl(nb, "t", "friend", False)
    t = mk("t", nb, "Tom"); a = mk("t", nb, "Ana"); m = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", t, "friend", E(a))
    nb.assert_fact("e2", "listening", "taught", t, "friend", E(m))
    ans = nb.ask("Tom", ["friend"])
    obs = f"status={ans.status} multi={ans.detail.get('multi')} answer={ans.detail.get('answer')}"
    if ans.status == C.OK and ans.detail.get("multi") is True and set(ans.detail.get("answer").split(", ")) == {"Ana", "Mira"}:
        return v_ok(obs)
    return v_bug(obs)


def t12():
    nb = fresh("rt12"); decl(nb, "t", "city"); mk("t", nb, "Mira")
    r = nb.ask("Mira", ["city"])
    obs = f"status={r.status} say={r.say()!r}"
    if r.status == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def t13():
    nb = fresh("rt13"); decl(nb, "t", "city"); mk("t", nb, "Mira")
    r = nb.ask("Zed", ["city"])
    obs = f"status={r.status}"
    if r.status == C.UNKNOWN_ENTITY:
        return v_ok(obs)
    return v_bug(obs)


def t14():
    nb = fresh("rt14"); decl(nb, "t", "city"); a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    r = nb.ask("Mira", ["pet"])
    obs = f"status={r.status}"
    if r.status == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def chain_case(n: int):
    def fn():
        nb = fresh(f"rtchain{n}"); decl(nb, "t", "mother")
        ids = [mk("t", nb, f"P{i}") for i in range(n + 1)]
        for i in range(n):
            nb.assert_fact(f"e{i}", "listening", "taught", ids[i], "mother", E(ids[i + 1]))
        ans = nb.ask("P0", ["mother"] * n)
        return ans
    return fn


def t15():
    ans = chain_case(3)()
    obs = f"status={ans.status} answer={ans.detail.get('answer')}"
    if ans.status == C.OK and ans.detail.get("answer") == "P3":
        return v_ok(obs)
    return v_bug(obs)


def t16():
    ans = chain_case(5)()
    obs = f"status={ans.status} answer={ans.detail.get('answer')}"
    if ans.status == C.OK and ans.detail.get("answer") == "P5":
        return v_ok(obs)
    return v_bug(obs)


def t17():
    ans = chain_case(8)()
    obs = f"status={ans.status} answer={ans.detail.get('answer')}"
    if ans.status == C.OK and ans.detail.get("answer") == "P8":
        return v_ok(obs)
    return v_bug(obs)


def t18():
    nb = fresh("rt18"); decl(nb, "t", "mother"); mk("t", nb, "A")
    r = nb.ask("A", ["mother"] * 9)
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t19():
    nb = fresh("rt19")
    r = nb.ask("Nobody", [])
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t20():
    nb = fresh("rt20"); decl(nb, "t", "mother"); decl(nb, "t", "city")
    m = mk("t", nb, "Mira"); a = mk("t", nb, "Old"); n = mk("t", nb, "New")
    nb.assert_fact("e1", "listening", "taught", m, "mother", E(a))
    nb.assert_fact("e2", "listening", "taught", a, "city", LI("Oslo"))
    nb.assert_fact("e3", "listening", "taught", m, "mother", E(n), correction=True)
    nb.assert_fact("e4", "listening", "taught", n, "city", LI("Roma"))
    ans = nb.ask("Mira", ["mother", "city"])
    obs = f"answer={ans.detail.get('answer')} trail={ans.detail.get('trail')}"
    if ans.detail.get("answer") == "Roma":
        return v_ok(obs)
    return v_bug(obs)


def t21():
    nb = fresh("rt21"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "thinking", "web-quarantine", a, "city", LI("Madrid"),
                   provenance={"url": "https://x.org/p", "quoted_span": "Madrid"})
    r = nb.ask("Mira", ["city"])
    obs = f"status={r.status}"
    if r.status == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def t22():
    nb = fresh("rt22"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "creative", "proposed", a, "city", LI("Madrid"))
    r = nb.ask("Mira", ["city"])
    obs = f"status={r.status}"
    if r.status == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def t23():
    nb = fresh("rt23"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    q = nb.assert_fact("e1", "thinking", "web-quarantine", a, "city", LI("Madrid"),
                       provenance={"url": "https://x.org/p", "quoted_span": "Madrid"})
    # find the quarantined fact id
    fid = [fid for fid, f in nb.facts.items() if f["source"] == "web-quarantine"][0]
    r = nb.promote("e-prom", "ben", fid)
    ans = nb.ask("Mira", ["city"])
    obs = f"promote={r.status} answer={ans.detail.get('answer')} src={ans.detail.get('source')} q={q.status}"
    if r.status == C.SAVED and ans.detail.get("answer") == "Madrid" and ans.detail.get("source") == "taught":
        return v_ok(obs)
    return v_bug(obs)


def t24():
    nb = fresh("rt24"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "creative", "proposed", a, "city", LI("Madrid"))
    fid = [fid for fid, f in nb.facts.items()][0]
    r = nb.promote("e-prom", "thinking", fid)
    obs = f"status={r.status}"
    if r.status == C.NOT_ALLOWED:
        return v_ok(obs)
    return v_bug(obs)


def t25():
    nb = fresh("rt25"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    fid = [fid for fid, f in nb.facts.items()][0]
    r = nb.promote("e-prom", "ben", fid)
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t26():
    nb = fresh("rt26"); decl(nb, "t", "mother"); decl(nb, "t", "grandmother")
    m = mk("t", nb, "Mira"); a = mk("t", nb, "Ana"); g = mk("t", nb, "Gran")
    nb.assert_fact("e1", "listening", "taught", m, "mother", E(a))
    nb.assert_fact("e2", "listening", "taught", a, "mother", E(g))
    nb.approve_rule("e-r", "ben", "R1", "grandmother via mother")
    f1 = [fid for fid, f in nb.facts.items() if f["subject"] == m][0]
    f2 = [fid for fid, f in nb.facts.items() if f["subject"] == a][0]
    r = nb.assert_fact("e3", "thinking", "inferred", m, "grandmother", E(g),
                       rule_id="R1", deps=(f1, f2))
    ans = nb.ask("Mira", ["grandmother"])
    obs = f"write={r.status} answer={ans.detail.get('answer')} src={ans.detail.get('source')}"
    if r.status == C.SAVED and ans.detail.get("answer") == "Gran":
        return v_ok(obs)
    return v_bug(obs)


def t27():
    nb = fresh("rt27"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    r = nb.assert_fact("e1", "thinking", "inferred", a, "city", LI("X"),
                       rule_id="NORULE", deps=("F00001",))
    obs = f"status={r.status}"
    if r.status == C.NOT_ALLOWED:
        return v_ok(obs)
    return v_bug(obs)


def t28():
    nb = fresh("rt28"); decl(nb, "t", "city"); decl(nb, "t", "capital")
    a = mk("t", nb, "Mira")
    f = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    fid = f.detail["fact_id"]
    nb.approve_rule("e-r", "ben", "R1", "body")
    nb.assert_fact("e2", "thinking", "inferred", a, "capital", LI("Lisbon"),
                   rule_id="R1", deps=(fid,))
    nb.retract("e3", "listening", fid, "forget")
    r = nb.ask("Mira", ["capital"])
    obs = f"status={r.status}"
    if r.status == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def t29():
    nb = fresh("rt29"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    f = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    nb.approve_rule("e-r", "ben", "R1", "body")
    nb.assert_fact("e2", "thinking", "inferred", a, "city", LI("Paris"),
                   rule_id="R1", deps=(f.detail["fact_id"],))
    ans = nb.ask("Mira", ["city"])
    obs = f"answer={ans.detail.get('answer')} src={ans.detail.get('source')}"
    if ans.detail.get("answer") == "Lisbon" and ans.detail.get("source") == "taught":
        return v_ok(obs)
    return v_bug(obs)


def t30():
    nb = fresh("rt30"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "sleep", "sleep-derived", a, "city", LI("Oslo"))
    nb.assert_fact("e2", "listening", "taught", a, "city", LI("Lisbon"))
    ans = nb.ask("Mira", ["city"])
    obs = f"answer={ans.detail.get('answer')} src={ans.detail.get('source')}"
    if ans.detail.get("answer") == "Lisbon" and ans.detail.get("source") == "taught":
        return v_ok(obs)
    return v_bug(obs)


def t31():
    nb = fresh("rt31"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "sleep", "sleep-derived", a, "city", LI("Oslo"))
    ans = nb.ask("Mira", ["city"])
    obs = f"answer={ans.detail.get('answer')} src={ans.detail.get('source')}"
    if ans.detail.get("answer") == "Oslo" and ans.detail.get("source") == "sleep-derived":
        return v_ok(obs)
    return v_bug(obs)


def t32():
    nb = fresh("rt32"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    one = {"evidence": [{"url": "https://a.org/p", "quoted_span": "Lisbon"}]}
    r1 = nb.assert_fact("e1", "thinking", "web-verified", a, "city", LI("Lisbon"), provenance=one)
    two = {"evidence": [{"url": "https://a.org/p", "quoted_span": "Lisbon"},
                        {"url": "https://b.org/q", "quoted_span": "Lisbon"}]}
    r2 = nb.assert_fact("e2", "thinking", "web-verified", a, "city", LI("Lisbon"), provenance=two)
    ans = nb.ask("Mira", ["city"])
    say = ans.say()
    obs = f"one={r1.status} two={r2.status} ans={ans.status} say={say!r}"
    if r1.status == C.BAD_REQUEST and r2.status == C.SAVED and ans.status == C.OK and "didn't tell me" in say:
        return v_ok(obs)
    return v_bug(obs)


def t33():
    nb = fresh("rt33"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    f = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    nb.retract("e2", "listening", f.detail["fact_id"], "forget")
    mid = nb.ask("Mira", ["city"])
    r = nb.assert_fact("e3", "listening", "taught", a, "city", LI("Lisbon"))
    ans = nb.ask("Mira", ["city"])
    obs = f"after_retract={mid.status} reteach={r.status} answer={ans.detail.get('answer')}"
    if mid.status == C.MISSING_FACT and r.status == C.SAVED and ans.detail.get("answer") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t34():
    nb = fresh("rt34")
    r = nb.retract("e1", "listening", "F99999", "x")
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t35():
    nb = fresh("rt35"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    f = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    r = nb.retract("e2", "thinking", f.detail["fact_id"], "x")
    obs = f"status={r.status}"
    if r.status == C.NOT_ALLOWED:
        return v_ok(obs)
    return v_bug(obs)


def t36():
    nb = fresh("rt36")
    names = ["Mira", "M\u012bra", "Mira\U0001f600"]
    ids = [mk(f"t{i}", nb, n) for i, n in enumerate(names)]
    rs = [nb.resolve(n) for n in names]
    obs = f"entities={len(set(ids))} resolves={[r.status for r in rs]}"
    if len(set(ids)) == 3 and all(r.status == C.OK for r in rs):
        return v_ok(obs)
    return v_bug(obs)


def t37():
    nb = fresh("rt37")
    a = mk("t", nb, "Mira")
    rs = [nb.resolve(v) for v in ["  MIRA ", "mira", "MiRa", " mira"]]
    obs = f"statuses={[r.status for r in rs]} eids={[r.detail.get('entity_id') for r in rs]}"
    if all(r.status == C.OK and r.detail.get("entity_id") == a for r in rs):
        return v_ok(obs)
    return v_bug(obs)


def t38():
    nb = fresh("rt38")
    r = nb.new_entity("e1", "   ")
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t39():
    nb = fresh("rt39")
    a = mk("t", nb, "Mira")
    r = nb.add_alias("e1", a, "  ")
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t40():
    nb = fresh("rt40"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    r = nb.assert_fact("e1", "listening", "taught", a, "city", LI(""))
    ans = nb.ask("Mira", ["city"])
    obs = f"write={r.status} ask={ans.status} answer={ans.detail.get('answer')!r}"
    # contract has no empty-value validation; record behaviour (no crash expected)
    if r.status == C.SAVED and ans.status == C.OK:
        return obs, "UNCLEAR", "empty literal stored+answered; contract silent on emptiness"
    return v_bug(obs)


def t41():
    nb = fresh("rt41")
    long = "Ab" * 250
    r = nb.new_entity("e1", long)
    q = nb.resolve("ab" * 250)
    obs = f"write={r.status} resolve={q.status} match={q.detail.get('entity_id') == r.detail.get('entity_id')}"
    if r.status == C.SAVED and q.status == C.OK and q.detail.get("entity_id") == r.detail.get("entity_id"):
        return v_ok(obs)
    return v_bug(obs)


def t42():
    nb = fresh("rt42"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    n0 = len(nb.events)
    r1 = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    n1 = len(nb.events)
    r2 = nb.assert_fact("e1", "listening", "taught", a, "city", LI("Paris"), correction=True)
    n2 = len(nb.events)
    obs = f"first={r1.status} replay={r2.status} grew={n2 - n1} base={n1 - n0}"
    if r1.status == C.SAVED and r2.status == C.DUPLICATE_OK and n2 == n1 and n1 == n0 + 1:
        return v_ok(obs)
    return v_bug(obs)


def t43():
    nb = fresh("rt43"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    r1 = nb.assert_fact("e1", "intruder", "taught", a, "city", LI("X"))
    r2 = nb.assert_fact("e2", "thinking", "taught", a, "city", LI("X"))
    obs = f"unknown_actor={r1.status} wrong_rights={r2.status}"
    if r1.status == C.BAD_REQUEST and r2.status == C.NOT_ALLOWED:
        return v_ok(obs)
    return v_bug(obs)


def t44():
    nb = fresh("rt44"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira"); b = mk("t", nb, "Ana")
    r1 = nb.assert_fact("e1", "listening", "taught", a, "city", {"entity": b, "literal": "X"})
    r2 = nb.assert_fact("e2", "listening", "taught", a, "city", {})
    obs = f"both={r1.status} neither={r2.status}"
    if r1.status == C.BAD_REQUEST and r2.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t45():
    nb = fresh("rt45"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    r1 = nb.assert_fact("e1", "listening", "taught", "E9999", "city", LI("X"))
    r2 = nb.assert_fact("e2", "listening", "taught", a, "city", E("E9999"))
    obs = f"bad_subject={r1.status} bad_object={r2.status}"
    if r1.status == C.BAD_REQUEST and r2.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t46():
    nb = fresh("rt46"); decl(nb, "t", "city"); decl(nb, "t", "mother")
    m = mk("t", nb, "Mira"); a = mk("t", nb, "Ana")
    nb.assert_fact("e1", "listening", "taught", m, "city", LI("Lisbon"))
    nb.assert_fact("e2", "listening", "taught", m, "mother", E(a))
    r = nb.ask("Mira", ["city", "mother"])
    obs = f"status={r.status} hop={r.detail.get('hop')} value={r.detail.get('value')!r}"
    if r.status == C.BROKEN_CHAIN and r.detail.get("hop") == 1 and r.detail.get("value") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t47():
    nb = fresh("rt47"); decl(nb, "t", "city")
    m1 = mk("t", nb, "Mira")
    m2 = nb.new_entity("e-m2", "Mira").detail["entity_id"]
    nb.assert_fact("e1", "listening", "taught", m1, "city", LI("Rome"))
    nb.assert_fact("e2", "listening", "taught", m2, "city", LI("Oslo"))
    r = nb.ask("Mira", ["city"], entity_id=m2)
    obs = f"status={r.status} answer={r.detail.get('answer')}"
    if r.status == C.OK and r.detail.get("answer") == "Oslo":
        return v_ok(obs)
    return v_bug(obs)


def t48():
    nb = fresh("rt48"); decl(nb, "t", "city"); mk("t", nb, "Mira")
    r = nb.ask("Mira", ["city"], entity_id="E9999")
    obs = f"status={r.status}"
    if r.status == C.BAD_REQUEST:
        return v_ok(obs)
    return v_bug(obs)


def t49a():
    # tamper a TRUE middle line (several lines follow it): must raise LogCorrupt
    d = ROOT / "rt49a"
    if d.exists():
        shutil.rmtree(d)
    nb = fresh("rt49a"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira"); b = mk("t", nb, "Ana")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    nb.assert_fact("e2", "listening", "taught", b, "city", LI("Porto"))
    nb.assert_fact("e3", "listening", "taught", a, "mother", E(b)) if False else None
    raw = (d / "events.jsonl").read_text(encoding="utf-8").split("\n")
    lines = [ln for ln in raw if ln.strip()]
    idx = next(i for i, ln in enumerate(lines) if '"event_id": "e1"' in ln)
    assert idx < len(lines) - 1, "need a line after the tampered one"
    mid = json.loads(lines[idx])
    mid["value"] = {"literal": "HACKED"}
    lines[idx] = json.dumps(mid, sort_keys=True, ensure_ascii=False)
    (d / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        C.Notebook(d)
        return v_bug("tampered MIDDLE line loaded without error")
    except C.LogCorrupt as exc:
        return v_ok(f"LogCorrupt: {exc}")


def t49b():
    # edit ONLY the last line's value: no later line checks its hash. Record behaviour.
    d = ROOT / "rt49b"
    if d.exists():
        shutil.rmtree(d)
    nb = fresh("rt49b"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    raw = (d / "events.jsonl").read_text(encoding="utf-8").split("\n")
    lines = [ln for ln in raw if ln.strip()]
    mid = json.loads(lines[-1])
    mid["value"] = {"literal": "HACKED"}
    lines[-1] = json.dumps(mid, sort_keys=True, ensure_ascii=False)
    (d / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        nb2 = C.Notebook(d)
        ans = nb2.ask("Mira", ["city"]).detail.get("answer")
        obs = f"loaded silently, answers {ans!r}"
    except C.LogCorrupt as exc:
        return v_ok(f"detected: {exc}")
    if ans == "HACKED":
        return obs, "BUG", "last-line value edit is silent; needs file access"
    return v_bug(obs)


def t50():
    d = ROOT / "rt50"
    if d.exists():
        shutil.rmtree(d)
    nb = fresh("rt50"); decl(nb, "t", "city")
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    with open(d / "events.jsonl", "a", encoding="utf-8") as h:
        h.write('{"kind": "FACT", "half": "written"\n')
    nb2 = C.Notebook(d)
    flag = nb2.torn_tail
    before = nb2.ask("Mira", ["city"]).detail.get("answer") if not flag else None
    nb2.repair_torn_tail()
    after = nb2.ask("Mira", ["city"])
    obs = f"torn={flag} pre_repair_answer={before} post={after.status}/{after.detail.get('answer')}"
    if flag is True and after.detail.get("answer") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t51():
    d = ROOT / "rt51"
    if d.exists():
        shutil.rmtree(d)
    nb = C.Notebook(d)
    nb.declare_relation("rel", "city", True)
    t0 = time.time()
    for i in range(10000):
        r = nb.new_entity(f"ent-{i}", f"Citizen{i:05d}")
        eid = r.detail["entity_id"]
        nb.assert_fact(f"fact-{i}", "listening", "taught", eid, "city", LI(f"Town{i}"))
    write_s = time.time() - t0
    t0 = time.time()
    nb2 = C.Notebook(d)
    load_s = time.time() - t0
    ok_chain = len(nb2.events) == len(nb.events) and nb2.last_sha == nb.last_sha
    t0 = time.time()
    ans = nb2.ask("Citizen05000", ["city"])
    q_ms = (time.time() - t0) * 1000
    obs = (f"facts={len(nb2.facts)} chain_intact={ok_chain} write_s={write_s:.1f} "
           f"load_s={load_s:.1f} query_ms={q_ms:.1f} answer={ans.detail.get('answer')}")
    if ok_chain and ans.detail.get("answer") == "Town5000" and q_ms < 5000 and write_s + load_s < 1500:
        return v_ok(obs)
    if not ok_chain or ans.detail.get("answer") != "Town5000":
        return v_bug(obs)
    return obs, "UNCLEAR", "correct but slower than the 5s/25min budget"


def t52():
    nb = fresh("rt52"); decl(nb, "t", "city")
    m = mk("t", nb, "Mira"); o = mk("t", nb, "Other")
    nb.assert_fact("e1", "listening", "taught", m, "city", LI("Lisbon"))
    before = nb.ask("Mira", ["city"]).detail.get("answer")
    nb.propose_merge("e-m", "listening", m, o)
    after = nb.ask("Mira", ["city"]).detail.get("answer")
    amb = nb.resolve("Mira").status
    obs = f"before={before} after={after} resolve={amb}"
    if before == after == "Lisbon" and amb == C.OK:
        return v_ok(obs)
    return v_bug(obs)


def t53():
    nb = fresh("rt53")
    r = nb.approve_rule("e-r", "thinking", "R1", "body")
    obs = f"status={r.status}"
    if r.status == C.NOT_ALLOWED:
        return v_ok(obs)
    return v_bug(obs)


def t54():
    nb = fresh("rt54"); decl(nb, "t", "city", True)
    nb.declare_relation("rel2", "city", False)  # widen after functional: additive log
    a = mk("t", nb, "Mira")
    nb.assert_fact("e1", "listening", "taught", a, "city", LI("Lisbon"))
    r = nb.assert_fact("e2", "listening", "taught", a, "city", LI("Paris"))
    obs = f"second_write={r.status} functional_still={('city' in nb.functional)}"
    # RELATION events only ever add: city stays functional -> CONFLICT expected
    if r.status == C.CONFLICT and "city" in nb.functional:
        return v_ok(obs)
    return v_bug(obs)


# ------------------------------------------------------- reasoner50 parity
def parity_nb(tag: str) -> C.Notebook:
    nb = fresh(tag)
    decl(nb, tag, "mother"); decl(nb, tag, "city"); decl(nb, tag, "friend", False)
    ids = {n: mk(tag, nb, n) for n in ("Mira", "Tom", "Ana")}
    m2 = nb.new_entity(f"{tag}-e-mira2", "Mira").detail["entity_id"]
    ids["Mira2"] = m2
    nb.add_alias(f"{tag}-al", ids["Tom"], "Tommy")
    nb.assert_fact(f"{tag}-f1", "listening", "taught", ids["Mira"], "mother", E(ids["Ana"]))
    nb.assert_fact(f"{tag}-f2", "listening", "taught", ids["Ana"], "city", LI("Porto"))
    nb.assert_fact(f"{tag}-f3", "listening", "taught", ids["Mira"], "city", LI("Lisbon"))
    nb.assert_fact(f"{tag}-f4", "listening", "taught", ids["Tom"], "friend", E(ids["Ana"]))
    nb.assert_fact(f"{tag}-f5", "listening", "taught", ids["Tom"], "friend", E(ids["Mira"]))
    nb.assert_fact(f"{tag}-f6", "creative", "proposed", ids["Ana"], "mother", E(ids["Tom"]))
    nb.assert_fact(f"{tag}-f7", "thinking", "web-quarantine", ids["Ana"], "city", LI("Madrid"),
                   provenance={"url": "https://x.org", "quoted_span": "s"})
    nb.assert_fact(f"{tag}-f9", "listening", "taught", m2, "city", LI("Oslo"))
    return nb, ids


def cmp_frame(reasoner, nb, frame):
    mine = reasoner.answer(frame, nb)
    r = nb.ask(frame.get("name", ""), list(frame.get("relations") or []),
               entity_id=frame.get("entity_id"))
    theirs = {"kind": "answer", "status": r.status, "name": frame.get("name", ""),
              "relations": list(frame.get("relations") or []), "fields": dict(r.detail)}
    return mine, theirs


def t55():
    nb, ids = parity_nb("rt55")
    r50 = R50.FableReasoner50()
    frames = [{"name": "Tommy", "relations": ["friend"]},
              {"name": "Tom", "relations": ["friend"], "entity_id": ids["Tom"]}]
    bad = [(f, *cmp_frame(r50, nb, f)) for f in frames
           if cmp_frame(r50, nb, f)[0] != cmp_frame(r50, nb, f)[1]]
    obs = f"compared={len(frames)} disagreements={len(bad)}"
    if not bad:
        return v_ok(obs)
    return v_bug(obs + f" ex={str(bad[0])[:300]}")


def t56():
    nb, ids = parity_nb("rt56")
    r50 = R50.FableReasoner50()
    frames = [{"name": "Ana", "relations": ["mother"]},
              {"name": "Ana", "relations": ["city"]}]
    disagree = [f for f in frames if cmp_frame(r50, nb, f)[0] != cmp_frame(r50, nb, f)[1]]
    obs = f"source-filter frames={len(frames)} disagreements={len(disagree)}"
    if not disagree:
        return v_ok(obs)
    return v_bug(obs)


def t57():
    nb, ids = parity_nb("rt57")
    r50 = R50.FableReasoner50()
    frames = [{"name": "Mira", "relations": ["city", "mother"], "entity_id": ids["Mira"]},
              {"name": "Ana", "relations": ["city", "mother", "city"], "entity_id": ids["Ana"]}]
    disagree = [f for f in frames if cmp_frame(r50, nb, f)[0] != cmp_frame(r50, nb, f)[1]]
    obs = f"broken-chain frames={len(frames)} disagreements={len(disagree)}"
    if not disagree:
        return v_ok(obs)
    return v_bug(obs + f" ex={str([cmp_frame(r50, nb, f) for f in disagree])[:400]}")


def t58():
    nb, ids = parity_nb("rt58")
    r50 = R50.FableReasoner50()
    frames = [{"name": "Mira", "relations": ["city"]},
              {"name": "Ghost", "relations": ["mother"]},
              {"name": "x", "relations": ["mother"], "entity_id": "E9999"},
              {"name": "Mira", "relations": []},
              {"name": "Mira", "relations": ["mother"] * 9}]
    disagree = [f for f in frames if cmp_frame(r50, nb, f)[0] != cmp_frame(r50, nb, f)[1]]
    obs = f"status frames={len(frames)} disagreements={len(disagree)}"
    if not disagree:
        return v_ok(obs)
    return v_bug(obs)


def t59():
    nb, ids = parity_nb("rt59")
    r50 = R50.FableReasoner50()
    frames = [{"name": "Tom", "relations": ["never_taught_rel"], "entity_id": ids["Tom"]},
              {"name": "Mira", "relations": ["mother", "never_taught_rel"], "entity_id": ids["Mira"]}]
    rows = [(f, *cmp_frame(r50, nb, f)) for f in frames]
    bad = [f for f, m, t in rows if m != t or m["status"] != C.MISSING_FACT or "answer" in m["fields"]]
    obs = f"unknown-relation frames={len(frames)} bad={len(bad)}"
    if not bad:
        return v_ok(obs)
    return v_bug(obs)


def t60():
    nb, ids = parity_nb("rt60")
    r50 = R50.FableReasoner50()
    frame = {"name": "Ana", "relations": ["friend"], "entity_id": ids["Ana"]}
    before = cmp_frame(r50, nb, frame)
    nb.assert_fact("rt60-f10", "listening", "taught", ids["Ana"], "friend", E(ids["Tom"]), correction=True)
    mine, theirs = cmp_frame(r50, nb, frame)
    obs = f"parity_before={before[0] == before[1]} after_equal={mine == theirs} answer={mine['fields'].get('answer')}"
    if before[0] == before[1] and mine == theirs and mine["fields"].get("answer") == "Tom":
        return v_ok(obs)
    return v_bug(obs)


# ------------------------------------------------------- qualifier wrappers
def qual_nb(tag: str, rel: str = "city", qual_rel: str = "when", qual_val=None):
    tnb = ThoughtNotebook(fresh(tag).root)
    nb = tnb.nb
    a = mk(tag, nb, "Mira")
    qual_val = qual_val if qual_val is not None else Value.of_date("2019")
    th = ThoughtV2(subject=a, relation=rel, value=Value.of_text("Lisbon"),
                   provenance=Provenance(document="d1", sentence="Mira lived in Lisbon in 2019.",
                                         claimed_by="taught"),
                   qualifiers=(Qualifier(qual_rel, qual_val),), source="taught", confidence=1.0)
    r = tnb.add_thought(th, event_id=f"{tag}-q1")
    return tnb, nb, a, r


def t61():
    tnb, nb, a, r = qual_nb("rt61")
    assert r.status == C.SAVED, r
    bare_t = tnb.ask("Mira", ["city"])
    bare_q = Q56.QualifierAwareReasoner().answer({"name": "Mira", "relations": ["city"]}, nb)
    obs = (f"tbook={bare_t.status}/{bare_t.detail.get('reason')} "
           f"q56={bare_q['status']}/{bare_q['fields'].get('reason')}")
    if (bare_t.status == C.MISSING_FACT and bare_t.detail.get("reason") == "qualified"
            and bare_q["status"] == C.MISSING_FACT and bare_q["fields"].get("reason") == "qualified"):
        return v_ok(obs)
    return v_bug(obs)


def t62():
    tnb, nb, a, r = qual_nb("rt62")
    assert r.status == C.SAVED, r
    q = {"when": "2019"}
    got_t = tnb.ask("Mira", ["city"], qualifiers=q)
    got_q = Q56.QualifierAwareReasoner().answer(
        {"name": "Mira", "relations": ["city"], "qualifiers": q}, nb)
    obs = f"tbook={got_t.status}/{got_t.detail.get('answer')} q56={got_q['status']}/{got_q['fields'].get('answer')}"
    if got_t.status == C.OK and got_t.detail.get("answer") == "Lisbon" and got_q == {
            "kind": "answer", "status": C.OK, "name": "Mira", "relations": ["city"],
            "fields": got_q["fields"]} and got_q["fields"].get("answer") == "Lisbon":
        return v_ok(obs)
    return v_bug(obs)


def t63():
    tnb, nb, a, r = qual_nb("rt63")
    assert r.status == C.SAVED, r
    q = {"when": "2020"}
    got_t = tnb.ask("Mira", ["city"], qualifiers=q)
    got_q = Q56.QualifierAwareReasoner().answer(
        {"name": "Mira", "relations": ["city"], "qualifiers": q}, nb)
    obs = f"tbook={got_t.status} q56={got_q['status']}"
    if got_t.status == C.MISSING_FACT and got_q["status"] == C.MISSING_FACT:
        return v_ok(obs)
    return v_bug(obs)


def t64():
    tnb = ThoughtNotebook(fresh("rt64").root)
    nb = tnb.nb
    decl(nb, "t", "mother")
    m = mk("t", nb, "Mira"); a = mk("t", nb, "Ana")
    nb.assert_fact("t-e1", "listening", "taught", m, "mother", E(a))
    th = ThoughtV2(subject=a, relation="city", value=Value.of_text("Porto"),
                   provenance=Provenance(document="d1", sentence="Ana in Porto in 2019.",
                                         claimed_by="taught"),
                   qualifiers=(Qualifier("when", Value.of_date("2019")),),
                   source="taught", confidence=1.0)
    r = tnb.add_thought(th, event_id="t-q1")
    assert r.status == C.SAVED, r
    bare = tnb.ask("Mira", ["mother", "city"])
    withq = tnb.ask("Mira", ["mother", "city"], qualifiers={"when": "2019"})
    obs = f"bare={bare.status}/{bare.detail.get('reason')} qualified={withq.status}/{withq.detail.get('answer')}"
    if bare.status == C.MISSING_FACT and withq.status == C.OK and withq.detail.get("answer") == "Porto":
        return v_ok(obs)
    return v_bug(obs)


def t65():
    # boolean qualifier, question passes a real bool: wrappers must agree
    tnb, nb, a, _ = qual_nb("rt65", rel="city", qual_rel="open",
                            qual_val=Value.of_boolean(True))
    # add_thought result checked inside qual_nb path; rebuild explicitly:
    assert _.status == C.SAVED, _
    q = {"open": True}
    got_t = tnb.ask("Mira", ["city"], qualifiers=q)
    got_q = Q56.QualifierAwareReasoner().answer(
        {"name": "Mira", "relations": ["city"], "qualifiers": q}, nb)
    obs = f"tbook={got_t.status}/{got_t.detail.get('answer', got_t.detail.get('reason'))} q56={got_q['status']}"
    if got_t.status == got_q["status"] and got_t.status == C.OK:
        return v_ok(obs)
    if got_t.status != got_q["status"]:
        return v_bug(obs, "wrappers disagree on bool qualifier: one answers, one abstains")
    return obs, "UNCLEAR", "both agree on non-OK"


def t66():
    # non-functional relation, unqualified taught + qualified taught both active
    tnb = ThoughtNotebook(fresh("rt66").root)
    nb = tnb.nb
    decl(nb, "t", "friend", False)
    t = mk("t", nb, "Tom"); a = mk("t", nb, "Ana"); m = mk("t", nb, "Mira")
    th1 = ThoughtV2(subject=t, relation="friend", value=Value.of_entity(a),
                    provenance=Provenance(document="d", sentence="Tom friend Ana.", claimed_by="taught"),
                    source="taught", confidence=1.0)
    r1 = tnb.add_thought(th1, event_id="t-u1")
    th2 = ThoughtV2(subject=t, relation="friend", value=Value.of_entity(m),
                    provenance=Provenance(document="d", sentence="Tom friend Mira in 2019.",
                                          claimed_by="taught"),
                    qualifiers=(Qualifier("when", Value.of_date("2019")),),
                    source="taught", confidence=1.0)
    r2 = tnb.add_thought(th2, event_id="t-q1")
    assert r1.status == C.SAVED and r2.status == C.SAVED, (r1, r2)
    q = {"when": "2019"}
    got_t = tnb.ask("Tom", ["friend"], qualifiers=q)
    got_q = Q56.QualifierAwareReasoner().answer(
        {"name": "Tom", "relations": ["friend"], "qualifiers": q}, nb)
    obs = (f"tbook={got_t.status}/{got_t.detail.get('answer')} "
           f"q56={got_q['status']}/{got_q['fields'].get('answer')}")
    if got_t.detail.get("answer") == got_q["fields"].get("answer"):
        return v_ok(obs)
    return v_bug(obs, "wrappers disagree: unqualified-vs-qualified priority differs")


# ------------------------------------------------------- listening + loop
def t67():
    nb = fresh("rt67")
    ear = L.Listening(nb)
    taught0 = sum(1 for e in nb.events if e["kind"] == "FACT" and e["source"] == "taught")
    q = ear.hear("quote Tom said Mira lives in Oslo")
    t1 = ear.hear("teach Mira city = Lisbon")
    t2 = ear.hear("teach Mira city = Paris")
    taught = sum(1 for e in nb.events if e["kind"] == "FACT" and e["source"] == "taught")
    f = ear.hear("forget Mira city")
    miss = ear.hear("ask Mira city")
    obs = (f"quote={q!r} t1={t1!r} t2={t2!r} taught_rows={taught} "
           f"forget={f!r} after={miss!r}")
    if ("didn't save" in q and taught == taught0 + 1 and "change it" in t2
            and "Forgotten" in f and "don't know" in miss):
        return v_ok(obs)
    return v_bug(obs)


def t68():
    import tempfile
    d = str(ROOT / "rt68")
    if Path(d).exists():
        shutil.rmtree(d)
    loop = G.AgentLoop(d)
    said1 = loop.turn("Mira's city is Lisbon.")
    said2 = loop.turn("What is Mira's city?")
    loop4 = G.AgentLoop(str(ROOT / "rt68b"))
    said4 = loop4.turn("Who is P0's mother's mother's mother's city?")
    obs = f"teach={said1} ask={said2} fourhop={said4}"
    if any("Lisbon" in s for s in said1) and any("Lisbon" in s for s in said2):
        if any("1 to 3" in s or "only follow" in s for s in said4):
            return obs, "UNCLEAR", "loop roundtrip fine; 4-hop refused by FakeEars 3-hop stub limit (scaffolding, not the core)"
        return v_ok(obs)
    return v_bug(obs)


CASES = [
    ("RT01", "duplicate teach same value", "second write DUPLICATE_OK, answer kept", t01),
    ("RT02", "teach then correct then re-correct", "latest wins, older two inactive", t02),
    ("RT03", "correction of never-taught fact", "SAVED with supersedes None, answers", t03),
    ("RT04", "second value without correct flag", "CONFLICT, old value kept", t04),
    ("RT05", "conflict then correction", "corrected value wins", t05),
    ("RT06", "alias collision: two people Sam", "AMBIGUOUS with both ids", t06),
    ("RT07", "unique alias resolves", "OK via alias", t07),
    ("RT08", "self-reference X mother of X", "SAVED, ask returns X", t08),
    ("RT09", "cycle A mother of B, B mother of A", "2-hop returns A, terminates", t09),
    ("RT10", "functional relation correction supersedes", "old inactive, new answers", t10),
    ("RT11", "non-functional two values", "OK multi with both names", t11),
    ("RT12", "ask before teaching", "MISSING_FACT", t12),
    ("RT13", "ask unknown entity", "UNKNOWN_ENTITY", t13),
    ("RT14", "ask unknown relation", "MISSING_FACT", t14),
    ("RT15", "3-hop chain", "OK P3", t15),
    ("RT16", "5-hop chain", "OK P5", t16),
    ("RT17", "8-hop chain (max)", "OK P8", t17),
    ("RT18", "9-hop chain", "BAD_REQUEST", t18),
    ("RT19", "0-hop ask", "BAD_REQUEST", t19),
    ("RT20", "chain through superseded fact", "new value used", t20),
    ("RT21", "web-quarantine asked as taught", "MISSING_FACT", t21),
    ("RT22", "proposed asked as taught", "MISSING_FACT", t22),
    ("RT23", "ben promotes proposed row", "SAVED, answers as taught", t23),
    ("RT24", "promote by non-ben", "NOT_ALLOWED", t24),
    ("RT25", "promote a taught row", "BAD_REQUEST", t25),
    ("RT26", "inferred with approved rule+deps", "SAVED and answers", t26),
    ("RT27", "inferred with unapproved rule", "NOT_ALLOWED", t27),
    ("RT28", "inferred dep retracted", "MISSING_FACT", t28),
    ("RT29", "inferred vs taught conflict", "taught wins", t29),
    ("RT30", "sleep-derived vs taught", "taught wins", t30),
    ("RT31", "sleep-derived alone", "OK source sleep-derived", t31),
    ("RT32", "web-verified 1 vs 2 domains", "BAD_REQUEST then SAVED+OK with suffix", t32),
    ("RT33", "retract then re-teach", "SAVED, answers again", t33),
    ("RT34", "retract unknown fact", "BAD_REQUEST", t34),
    ("RT35", "retract taught by non-listening", "NOT_ALLOWED", t35),
    ("RT36", "unicode names distinct", "3 entities, each resolves", t36),
    ("RT37", "case/whitespace name variants", "all resolve to same entity", t37),
    ("RT38", "empty name", "BAD_REQUEST", t38),
    ("RT39", "empty alias", "BAD_REQUEST", t39),
    ("RT40", "empty literal value", "contract silent; record behaviour", t40),
    ("RT41", "500-char name", "SAVED and resolves", t41),
    ("RT42", "duplicate event_id replay", "DUPLICATE_OK, log unchanged", t42),
    ("RT43", "unknown actor / wrong rights", "BAD_REQUEST / NOT_ALLOWED", t43),
    ("RT44", "value with both/neither keys", "BAD_REQUEST both", t44),
    ("RT45", "unknown subject/object ids", "BAD_REQUEST both", t45),
    ("RT46", "broken chain at literal", "BROKEN_CHAIN hop 1 value Lisbon", t46),
    ("RT47", "entity_id bypasses ambiguity", "OK Oslo", t47),
    ("RT48", "bad entity_id", "BAD_REQUEST", t48),
    ("RT49a", "tampered true-middle line", "LogCorrupt on load", t49a),
    ("RT49b", "edited last-line value", "record whether silent", t49b),
    ("RT50", "torn tail then repair", "flag set, repair recovers answer", t50),
    ("RT51", "10000 facts verify+query", "chain intact, fast query", t51),
    ("RT52", "merge proposal changes nothing", "answer and resolve unchanged", t52),
    ("RT53", "approve rule by non-ben", "NOT_ALLOWED", t53),
    ("RT54", "redeclare functional as non-functional", "stays functional (additive), CONFLICT", t54),
    ("RT55", "r50 parity: multi-value", "100% agreement", t55),
    ("RT56", "r50 parity: source filter", "100% agreement", t56),
    ("RT57", "r50 parity: broken-chain fields", "100% agreement", t57),
    ("RT58", "r50 parity: statuses/edges", "100% agreement", t58),
    ("RT59", "r50 parity: unknown relation", "MISSING_FACT, no answer field", t59),
    ("RT60", "r50 cache invalidation", "new write visible, still parity", t60),
    ("RT61", "qualified row, bare question", "MISSING reason qualified, both wrappers", t61),
    ("RT62", "qualified row, matching qualifier", "OK Lisbon, both wrappers", t62),
    ("RT63", "qualified row, wrong qualifier", "MISSING_FACT both wrappers", t63),
    ("RT64", "chain through qualified hop", "bare MISSING, qualified OK Porto", t64),
    ("RT65", "bool qualifier passed as bool", "wrappers agree", t65),
    ("RT66", "unqualified+qualified same S+R", "wrappers agree", t66),
    ("RT67", "listening quote/conflict/forget", "no write on quote, clarify, forgotten", t67),
    ("RT68", "agent-loop roundtrip + 4-hop", "teach/ask fine; stub hop limit noted", t68),
]


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for cid, title, expected, fn in CASES:
        case(cid, title, expected, fn)
    dt = time.time() - t0
    n_ok = sum(1 for r in RESULTS if r["verdict"] == "OK")
    n_bug = sum(1 for r in RESULTS if r["verdict"] == "BUG")
    n_unc = sum(1 for r in RESULTS if r["verdict"] == "UNCLEAR")
    out = Path(__file__).resolve().parent.parent / "artifacts" / "fable-redteam67-20260921"
    out.mkdir(parents=True, exist_ok=True)
    (out / "probe-results.json").write_text(json.dumps(
        {"cases": RESULTS, "summary": {"total": len(RESULTS), "OK": n_ok, "BUG": n_bug,
                                       "UNCLEAR": n_unc, "seconds": round(dt, 1)}}, indent=1))
    print(f"\nTOTAL={len(RESULTS)} OK={n_ok} BUG={n_bug} UNCLEAR={n_unc} seconds={dt:.1f}")
    print(f"wrote {out / 'probe-results.json'}")
    return 0 if n_bug == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
