"""CPU tests for the pure parts of gate0.py (no vLLM, no model)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate0 as G  # noqa: E402

ROW = dict(id="train-1:q0", context="[world] In the mill, Saku is present.", question="[question] Where is Saku?", answer="the mill")


def test_prompt():
    m = G.build_user_message(ROW)
    assert m.startswith(ROW["context"] + "\n" + ROW["question"])
    assert m.endswith(G.INSTRUCTION)
    assert G.build_user_message(dict(ROW, context="")).startswith(ROW["question"])


def test_extract_off():
    assert G.extract_off("the mill<|ifm|im_end|>") == "the mill"
    assert G.extract_off("  \nthe mill.\nextra") == "the mill."
    assert G.extract_off("") == ""


def test_extract_on():
    t, a, tr = G.extract_on("Saku is in the mill.\n</ifm|think_faster>\nthe mill<|ifm|im_end|>")
    assert (t, a, tr) == ("Saku is in the mill.", "the mill", False)
    t, a, tr = G.extract_on("hmm the answer is the mill. wait")  # cut off while thinking
    assert a == "" and tr is True and t.startswith("hmm")
    # the answer is only what follows the think end; an answer-looking phrase inside the reasoning must not count
    assert G.extract_on("answer: the cave\n</ifm|think_faster>the mill")[1] == "the mill"
    assert G.extract_on("x</ifm|think_faster>")[1] == ""


def test_score():
    assert G.is_hit("The Mill.", "the mill")
    assert not G.is_hit("", "")  # empty prediction never counts
    assert not G.is_hit("the cave", "the mill")


def test_g0():
    off = [True] * 50 + [False] * 50
    on = [True] * 58 + [False] * 42
    d = G.g0_decision(off, on)
    assert d["g0_pass"] and abs(d["gap"] - 0.08) < 1e-9
    assert not G.g0_decision(off, [True] * 57 + [False] * 43)["g0_pass"]
    assert not G.g0_decision(on, off)["g0_pass"]


def test_traces_filter():
    rows = [dict(ROW, id=f"r{i}") for i in range(4)]
    out = G.filter_traces(rows, ["a", "b", "c", "d"], ["the mill", "the cave", "the mill", "the mill"], [5, 6, 7, 8], [False, False, True, False])
    assert [t["id"] for t in out] == ["r0", "r3"]
    assert out[0] == dict(id="r0", prompt=G.build_user_message(rows[0]), think_text="a", answer="the mill", n_think_tokens=5)


def test_stats_and_len():
    s = G.tok_stats(list(range(1, 101)))
    assert s["mean"] == 50.5 and s["median"] == 50.5 and s["p95"] in (95, 96) and s["max"] == 100
    assert G.tok_stats([])["mean"] is None
    mml, skip = G.pick_model_len([100, 200, 9000], 2048, 4096)
    assert mml == 4096 and skip == {2}
    mml, skip = G.pick_model_len([100, 200], 2048, 8192)
    assert mml == 200 + 2048 + 16 and not skip


def test_template_modes():
    import re
    src = (Path(G.TEMPLATE_PATH)).read_text()
    assert "<ifm|think_faster>" in src and "reasoning_effort | default('none')" in src
    assert G.THINK_END.search("</ifm|think_faster>") and G.THINK_END.search("</ifm|think>")
