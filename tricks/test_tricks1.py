import json, sys, time
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import tricks1 as t, summarize as sm

def test_tool_call_xml():
    txt = "Let me compute.\n\n<tool_call>\n<function=python>\n<parameter=code>\nprint(2+3)\nx=1\n</parameter>\n</function>\n</tool_call>"
    assert t.parse_tool_calls(txt) == [("python", {"code": "print(2+3)\nx=1"})]

def test_tool_call_json_and_multi():
    txt = '<tool_call>\n{"name": "python", "arguments": {"code": "print(1)"}}\n</tool_call>\n<tool_call>{"name":"search_wikipedia","arguments":"{\\"query\\": \\"x\\"}"}</tool_call>'
    assert t.parse_tool_calls(txt) == [("python", {"code": "print(1)"}), ("search_wikipedia", {"query": "x"})]
    assert t.parse_tool_calls("no calls here") == []

def test_tool_call_unterminated_and_bare():
    assert t.parse_tool_calls("<tool_call>\n<function=python>\n<parameter=code>\nprint(7)\n</parameter>")[0][1]["code"] == "print(7)"
    assert t.parse_tool_calls("<function=search_wikipedia><parameter=query>Paris</parameter></function>") == [("search_wikipedia", {"query": "Paris"})]

@pytest.mark.parametrize("s,v", [("12", 12), ("$1,234.50", 1234.5), ("-2.5", -2.5), ("\\frac{3}{4}", .75), ("-\\dfrac{1}{2}", -.5),
                                 ("3/4", .75), ("42 dollars", 42), ("50\\%", 50), ("abc", None), ("1/0", None)])
def test_parse_number(s, v):
    got = t.parse_number(s)
    assert (got is None) if v is None else abs(got - v) < 1e-9

def test_parse_answer():
    assert t.parse_answer("blah 5\nFinal answer: 1,200") == 1200
    assert t.parse_answer("Final answer: 3\nthen more\n**Final answer:** $\\frac{1}{4}$") == .25
    assert t.parse_answer("so \\boxed{\\frac{7}{2}} ok 99") == 3.5
    assert t.parse_answer("we get 4 then 17.") == 17
    assert t.parse_answer("Final answer: none\n\\boxed{8}") == 8
    assert t.parse_answer("no digits") is None

def test_boxed_nested():
    assert t.last_boxed("\\boxed{a} \\boxed{\\frac{1}{2}}") == "\\frac{1}{2}"

def test_strip_think():
    assert t.strip_think("<think>\nx 5\n</think>\n\nFinal answer: 3", True) == "Final answer: 3"
    assert t.strip_think("long reasoning 5", True) == ""
    assert t.strip_think("plain 5") == "plain 5"

def test_num_match():
    assert t.num_match(1e9 + 1e4, 1e9) and not t.num_match(1e9 + 1e6, 1e9)
    assert t.num_match(0.00005, 0) and not t.num_match(0.001, 0) and not t.num_match(None, 1)

def test_majority():
    assert t.majority([3, None, 5, 5, 3, 7]) == 3   # tie -> first
    assert t.majority([1, 2, 2, None]) == 2
    assert t.majority([None]) is None
    assert t.majority([1e9, 1e9 + 1, 5]) == 1e9     # tolerance clustering

def test_popqa_match():
    assert t.popqa_match("It is Paris, France", ["paris"]) and not t.popqa_match("Rome", ["Paris", "Lyon"])

def test_python_exec():
    assert t.run_python("print(2+3)") == "5"
    t0 = time.time(); out = t.run_python("while True: pass", timeout=1)
    assert "timed out" in out and time.time() - t0 < 5
    assert len(t.run_python("print('a'*5000)")) == 2000
    assert "ZeroDivisionError" in t.run_python("1/0")
    assert "Error" in t.exec_tool("nope", {}) and "missing" in t.exec_tool("python", {})

class FakeTok:
    def apply_chat_template(self, msgs, tools=None, add_generation_prompt=True, tokenize=False, enable_thinking=False):
        return json.dumps(msgs)

def test_tool_loop():
    def eng(prompts, **kw):
        outs = []
        for p in prompts:
            m = json.loads(p)
            outs.append([("<tool_call>\n<function=python>\n<parameter=code>\nprint(6*7)\n</parameter>\n</function>\n</tool_call>", 10)] if m[-1]["role"] == "user"
                        else [("Final answer: " + m[-1]["content"], 5)])
        return outs
    convs = [[{"role": "user", "content": "q"}] for _ in range(3)]
    r = t.run_tool_loop(eng, FakeTok(), convs, [t.PY_TOOL], 4, 100)
    assert all(x["calls"] == 1 and x["tokens"] == 15 and t.parse_answer(x["text"]) == 42 for x in r)

def test_tool_loop_round_cap():
    eng = lambda ps, **kw: [[("<tool_call>{\"name\":\"python\",\"arguments\":{\"code\":\"print(1)\"}}</tool_call>", 1)] for _ in ps]
    r = t.run_tool_loop(eng, FakeTok(), [[{"role": "user", "content": "q"}]], [t.PY_TOOL], 4, 10)
    assert r[0]["calls"] == 4

def test_run_arm_set_vote_and_stats():
    class E:
        def __call__(self, ps, **kw):
            assert kw["n"] == 8
            return [[("Final answer: 5", 3)] * 5 + [("Final answer: 9", 3)] * 3 for _ in ps]
    rows = [{"id": "a", "q": "x", "gold": 5.0}, {"id": "b", "q": "y", "gold": 9.0}]
    recs = t.run_arm_set("vote8", "gsmh", rows, E(), FakeTok())
    assert [r["correct"] for r in recs] == [True, False] and [r["pass8"] for r in recs] == [True, True] and recs[0]["tokens"] == 24
    s = t.stats(recs)
    assert s["accuracy"] == .5 and s["n"] == 2 and s["pass_at_8"] == 1 and len(s["ci95"]) == 2

def test_popqa_arm():
    eng = lambda ps, **kw: [[("The capital is Paris.", 4)] for _ in ps]
    rows = [{"id": "p", "q": "?", "gold": ["Paris"], "bucket": "rare"}]
    assert t.run_arm_set("plain", "popqa", rows, eng, FakeTok())[0]["correct"] is True

def test_limit_rows():
    rows = [{"bucket": "rare"}] * 5 + [{"bucket": "pop"}] * 5
    assert len(t.limit_rows("popqa", rows, 4)) == 4 and len(t.limit_rows("gsmh", rows, 3)) == 3

def _res(**arms):
    return {a: {s: {"accuracy": v, "ci95": [v, v], "n": 1, "mean_tokens": 1, "mean_tool_calls": 0} for s, v in d.items()} for a, d in arms.items()}

def test_verdicts():
    r = _res(s_plain={"gsmh": .5}, s_py={"gsmh": .7}, b_plain={"gsmh": .65, "math": .8, "popqa": .3, "popqa_rare": .15},
             s_wiki={"popqa": .45, "popqa_rare": .30}, s_think={"math": .78}, s_vote8={"math": .6})
    v = sm.verdicts(r)
    assert v["P1"][0] == "PASS" and v["P2"][0] == "PASS" and v["P3"][0] == "PASS"
    r["s_py"]["gsmh"]["accuracy"] = .51; r["s_wiki"]["popqa"]["accuracy"] = .3
    r["s_think"]["math"]["accuracy"] = .6; r["s_vote8"]["math"]["accuracy"] = .65
    v = sm.verdicts(r)
    assert v["P1"][0] == "WRONG" and v["P2"][0] == "WRONG" and v["P3"][0] == "WRONG"
    r["s_py"]["gsmh"]["accuracy"] = .6; r["s_think"]["math"]["accuracy"] = .72
    v = sm.verdicts(r)
    assert v["P1"][0] == "MIXED" and v["P3"][0] == "MIXED"
    assert sm.verdicts({})["P1"][0] == "n/a"

def test_report_files(tmp_path):
    (tmp_path / "small").mkdir()
    (tmp_path / "small" / "result_s_py.json").write_text(json.dumps(_res(x={"gsmh": .5})["x"]))
    assert "s_py" in sm.report(str(tmp_path))

def test_paired_ci():
    a = [{"id": i, "correct": True} for i in range(50)]; b = [{"id": i, "correct": False} for i in range(50)]
    lo, hi = sm.paired_diff_ci(a, b); assert lo == hi == 1.0

def test_build_sets_network():
    try:
        sets = t.build_sets()
    except Exception as e:
        pytest.skip(f"network/HF unavailable: {type(e).__name__}: {str(e)[:100]}")
    assert len(sets["gsmh"]) == 300 and 0 < len(sets["math"]) <= 300 and len(sets["popqa"]) == 400
    assert all(isinstance(r["gold"], list) for r in sets["popqa"]) and sets == t.build_sets()
    assert sum(r["bucket"] == "rare" for r in sets["popqa"]) == 200

def test_wikipedia_network():
    r = t.search_wikipedia("Eiffel Tower")
    if r.startswith("Error"):
        pytest.skip(r)
    assert "Eiffel" in r
