import json, os, random, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
from build_corpus import assign_splits
from gen_templates import parse_array

GOOD = {"text": "Mira had {a} marbles and found {b} more, then gave {c} to Tobin. How many marbles does Mira have now?",
        "slots": {"a": [20, 90], "b": [5, 30], "c": [2, 15]}, "answer": "(a + b) - c",
        "steps": ["a + b", "s1 - c"], "n_steps": 2, "topic": "Marbles", "unit": "marbles"}


def good(**kw):
    t = json.loads(json.dumps(GOOD)); t.update(kw); return t


def test_valid_template_and_scratchpad():
    t, ps, at = core.check_schema(good())
    v = {"a": 37, "b": 46, "c": 9}
    inst = core.instance(t, ps, at, v)
    assert inst["scratchpad"] == "37 + 46 = 83. 83 - 9 = 74. Answer: 74"
    assert inst["answer"] == 74


def test_scratchpad_matches_answer_on_many_draws():
    t, ps, at = core.check_schema(good())
    for inst in core.make_instances(t, 100):
        assert inst["scratchpad"].endswith("Answer: %d" % inst["answer"])
        last = inst["scratchpad"].split(". ")[-2]
        assert last.endswith("= %d" % inst["answer"])
        for s in inst["steps"]:
            l, r = s.split(" = ")
            x, op, y = l.split()
            x, y = int(x), int(y)
            assert {"+": x + y, "-": x - y, "*": x * y, "/": x // y}[op] == int(r)


@pytest.mark.parametrize("expr", ["a.real", "__import__('os')", "abs(a)", "a ** 2", "a / b", "a if b else c",
                                  "[a]", "a % b", "-a", "a + 1.5", "'x'", "(lambda: 1)()", "a < b", "d + a"])
def test_ast_whitelist_rejects(expr):
    with pytest.raises(core.Bad):
        core.parse_expr(expr, {"a", "b", "c"})


def test_ast_whitelist_accepts_and_exact_div():
    tr = core.parse_expr("(a + b) * 2 // c - 1", {"a", "b", "c"})
    assert core.evaluate(tr, {"a": 4, "b": 2, "c": 3}) == 3
    with pytest.raises(core.Bad):
        core.evaluate(core.parse_expr("a // b", {"a", "b"}), {"a": 7, "b": 2})


@pytest.mark.parametrize("mut", [
    dict(steps=["a + b", "s1.real - c"]),
    dict(answer="a.real"),
    dict(text="Mira had {a} marbles and found {b} more, then gave 4 away. How many marbles are left now?"),
    dict(steps=["a + b"], n_steps=1),                      # c unused
    dict(slots={"a": [20, 90], "b": [5, 30], "c": [2, 15], "d": [2, 5]}),  # d not in text
    dict(steps=["a + b", "s1 - c", "s2 + 1", "s3 + 1", "s4 + 1"], n_steps=5),
    dict(steps=["a + b + c", "s1 - c"]),                   # not single op
])
def test_schema_rejections(mut):
    with pytest.raises(core.Bad):
        core.check_schema(good(**mut))


def test_noncomposing_template_rejected():
    acc = core.Acceptor([])
    assert acc.add(good(answer="(a + b) + c")) == "steps_do_not_compose"
    assert acc.add(good()) is None


def test_low_valid_rate_rejected():
    acc = core.Acceptor([])
    assert acc.add(good(slots={"a": [2, 10], "b": [2, 5], "c": [50, 90]})) == "low_valid_rate"


def test_leak_and_near_duplicate():
    old = ["Mira had 5 marbles and found 4 more, then gave 2 to Tobin. How many marbles does Mira have now?"]
    assert core.Acceptor(old).add(good()) == "leak_8gram"
    acc = core.Acceptor([])
    assert acc.add(good()) is None
    t2 = good(text=good()["text"].replace("Mira", "Lena"))
    assert acc.add(t2) == "near_duplicate"


def test_divisible_sampling_exact():
    t = {"text": "Rosa packs {a} cups equally into {b} boxes, then adds {c} cups. How many cups are in all?",
         "slots": {"a": [20, 400], "b": [3, 9], "c": [2, 30]}, "divisible": [["a", "b"]],
         "answer": "a // b + c", "steps": ["a // b", "s1 + c"], "n_steps": 2, "topic": "t"}
    acc = core.Acceptor([])
    assert acc.add(t) is None
    tt, ps, at = core.check_schema(t)
    for i in core.make_instances(tt, 50):
        assert i["answer"] > 0


def test_split_disjoint_and_structural():
    ts = []
    for i in range(400):
        ts.append({"id": "t_%04d" % i, "topic": "topic%d" % (i % 5), "n_steps": 1 + i % 4})
    sp, struct = assign_splits(ts)
    assert len(struct) == 2
    for t in ts:
        if t["n_steps"] == 4 and t["topic"] in struct:
            assert sp[t["id"]] == "heldout_structure"
        else:
            assert sp[t["id"]] in ("train", "dev", "heldout_template")
    # a template maps to exactly one split, deterministic
    assert assign_splits(ts)[0] == sp
    frac = sum(v == "train" for v in sp.values()) / len(sp)
    assert 0.7 < frac < 0.9


def test_parse_array_salvages_truncation():
    s = '[{"a":1},{"b":2},{"c":'
    assert parse_array(s) == [{"a": 1}, {"b": 2}]
