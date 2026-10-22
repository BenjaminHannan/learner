"""Tests (pytest-style, also runnable with `python tests/run_all.py`)."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from logicgen import templates as T  # noqa: E402
from logicgen.checker import run_program, solve, parse_program  # noqa: E402
from logicgen.generate import make_rows, SPLITS  # noqa: E402

_cache = {}


def rows(kind, split, n=2000, seed=7, mc=208):
    k = (kind, split, n, seed, mc)
    if k not in _cache:
        _cache[k] = make_rows(kind, split, n, seed, mc)
    return _cache[k]


def test_rule_kinds():
    assert run_program("F a(max); R a(x)>b(x); Q b(max)") == "true"                    # R1
    assert run_program("F a(max); R a(x)>~b(x); Q b(max)") == "false"                  # R2
    assert run_program("F a(max); F b(max); R a(x)&b(x)>c(x); Q c(max)") == "true"     # R3
    assert run_program("F a(max); R a(x)&b(x)>c(x); Q c(max)") == "unknown"           # conj missing
    assert run_program("F ~a(max); R ~a(x)>b(x); Q b(max)") == "true"                  # R4
    assert run_program("R ~a(x)>b(x); Q b(max)") == "unknown"                          # no closed world
    assert run_program("F a(max); R max: a>~b; Q b(max)") == "false"                   # R5
    assert run_program("F a(sam); R max: a>b; Q b(max)") == "unknown"                  # R5 wrong entity
    assert run_program("F a(max); R a(x)>b(x); Q b(sam)") == "unknown"
    assert run_program("F ~b(max); R a(x)>b(x); Q ~a(max)") == "unknown"              # no contrapositive
    assert run_program("F a(max); R a(x)>b(x); Q ~b(max)") == "false"


def test_depth_and_proof():
    f, r, q = parse_program("F a(m); R a(x)>b(x); R b(x)>~c(x); R a(x)>~c(x); Q c(m)")
    res = solve(f, r, q)
    assert res.label == "false" and res.depth == 1          # shortest proof uses the direct rule
    f, r, q = parse_program("F a(m); R a(x)>b(x); R b(x)>c(x); R c(x)>d(x); Q d(m)")
    res = solve(f, r, q)
    assert res.depth == 3 and [l[1] for l in res.proof] == ["b", "c", "d"]
    f, r, q = parse_program("F a(m); Q a(m)")
    assert solve(f, r, q).depth == 0


def test_contradiction_and_errors():
    assert run_program("F a(m); F ~a(m); Q a(m)") == "error"
    assert run_program("F a(m); R a(x)>b(x); F ~b(m); Q a(m)") == "error"
    assert run_program("F a(m)") == "error"
    assert run_program("garbage") == "error"
    assert run_program("F a(m); Q a(m); Q a(m)") == "error"


def test_template_counts_and_split():
    for k, v in T.TEMPLATES.items():
        need = {"FP": 8, "FN": 8, "Q": 8}.get(k, 12)
        assert len(v) >= need, k
        assert len(set(v)) == len(v)
        assert set(T.heldout_ids(k)).isdisjoint(T.train_ids(k))
        assert abs(len(T.heldout_ids(k)) - len(v) / 3) <= 1


def test_roundtrip_all_splits():
    for split in SPLITS:
        for kind in ("logic", "placebo"):
            rs = rows(kind, split)
            assert len(rs) == 2000
            for r in rs:
                assert run_program(r["program"]) == r["label"] == r["answer"], r["id"]
                assert r["answer"] in ("true", "false", "unknown")


def test_heldout_templates_never_in_train():
    for split, cfg in SPLITS.items():
        for kind in ("logic", "placebo"):
            for r in rows(kind, split, 600):
                assert r["template_set"] == cfg["tset"]
                for tid in r["template_ids"]:
                    k, i = tid.split(":")
                    held = int(i) in T.heldout_ids(k)
                    assert held == (cfg["tset"] == "heldout"), (split, tid)


def test_determinism():
    a = make_rows("logic", "train", 200, 3)
    assert a == make_rows("logic", "train", 200, 3)
    assert a != make_rows("logic", "train", 200, 4)
    assert make_rows("logic", "train", 60, 3) != make_rows("logic", "dev", 60, 3)


def test_label_balance_per_depth():
    for split in ("train", "test_wording", "test_deeper"):
        rs = rows("logic", split, 1200)
        c = Counter((r["depth"], r["label"]) for r in rs)
        for d in {r["depth"] for r in rs}:
            assert len({c[(d, l)] for l in ("true", "false", "unknown")}) == 1, (split, d)
    d0 = sum(r["depth"] == 0 for r in rows("logic", "train", 1200)) / 1200
    assert abs(d0 - .1) < .01


def test_max_chars_ascii_answers():
    for split in SPLITS:
        for kind in ("logic", "placebo"):
            for r in rows(kind, split, 600):
                assert r["chars"] == len(r["question"]) <= 208
                assert r["question"].isascii() and r["question"].isprintable()
                assert len(r["answer"]) <= 8
    for r in make_rows("logic", "train", 150, 1, 300):
        assert r["chars"] <= 300


def test_placebo():
    from logicgen.checker import parse_lit, neg_lit
    rs = rows("placebo", "train", 804)
    assert Counter(r["answer"] for r in rs) == {"true": 268, "false": 268, "unknown": 268}
    for r in rs:
        facts, rules, _ = parse_program(r["ctx"], need_query=False)
        lit = parse_lit(r["query"])
        closure = solve(facts, rules).closure
        assert r["depth"] == 0 and r["kind"] == "placebo"
        if r["answer"] == "true":
            assert lit in facts and r["steps"] == [T.atom_sentence(lit)]
        elif r["answer"] == "false":
            assert neg_lit(lit) in facts and lit not in closure
        else:   # never a derivable atom
            assert lit not in closure and neg_lit(lit) not in closure
            assert r["steps"] == ["Not enough information."]
    assert sum(bool(parse_program(r["ctx"], need_query=False)[1]) for r in rs) > 0.9 * len(rs)  # rules present
    # same context generator: placebo context equals the logic row's context
    lg = rows("logic", "train", 804)
    assert sum(a["ctx"] == b["ctx"] for a, b in zip(lg, rs)) > 0.25 * len(rs)


def test_gate_and_depths_override():
    rs = make_rows("logic", "gate", 1608, 5)
    c = Counter((r["depth"], r["label"]) for r in rs)
    assert set(r["depth"] for r in rs) == {0, 1, 2, 3}
    assert set(c.values()) == {134}, c        # 402 per depth, 134 per label within depth
    assert all(r["template_set"] == "heldout" for r in rs)
    for r in rs[:300]:
        assert run_program(r["program"]) == r["label"]
    rs = make_rows("logic", "train", 120, 5, depths=[2, 4])
    assert Counter(r["depth"] for r in rs) == {2: 60, 4: 60}


def test_steps():
    for r in rows("logic", "train", 300):
        if r["label"] == "unknown":
            assert r["steps"] == ["Not enough information."]
        else:
            assert len(r["steps"]) == max(1, r["depth"])


if __name__ == "__main__":
    pass
