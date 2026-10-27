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


# ---------------------------------------------------------------- Gate 0-ev (Addendum B)

OFF = "<|ifm|im_start|>user\nq<|ifm|im_end|>\n<|ifm|im_start|>assistant\n" + G.EMPTY_THINK


def test_ev_prompt_differs_only_in_think_block():
    lines = ["[world] In the mill, Saku is present.", "[action] Saku takes the box."]
    ev = G.ev_prompt(OFF, lines)
    head = OFF[:-len(G.EMPTY_THINK)]
    assert ev == head + "<ifm|think>\n" + lines[0] + "\n" + lines[1] + "\n</ifm|think>"
    assert ev.startswith(head) and ev.endswith("</ifm|think>")
    # blanking the block content gives the off prompt back
    assert ev.replace("\n".join(lines) + "\n", "") == OFF
    assert not ev.endswith("The answer is:")  # nothing is added after the block, same as the off arm


def test_ev_depth0_is_empty_block():
    assert G.ev_prompt(OFF, []) == OFF


def _fake_raw(tmp_path, split="validation"):
    d = tmp_path / "raw" / split
    d.mkdir(parents=True)
    (d / "shard-00000.txt").write_text("l0\nl1  \nl2\nl3\nl4\n")
    (d / "shard-00000.jsonl").write_text(
        '{"id":"validation-0","kind":"visit"}\n'
        '{"id":"validation-0:q0","kind":"question","evidence_text_lines":[3,1],"text_line":4}\n'
        '{"id":"validation-0:q1","kind":"question","evidence_text_lines":[],"text_line":4}\n')
    (d / "shard-00001.txt").write_text("m0\nm1\nm2\n")
    (d / "shard-00001.jsonl").write_text('{"id":"validation-9:q0","kind":"question","evidence_text_lines":[0,2],"text_line":2}\n')
    return tmp_path


def test_evidence_mapping(tmp_path):
    root = _fake_raw(tmp_path)
    rows = [dict(id="validation-0:q0"), dict(id="validation-0:q1"), dict(id="validation-9:q0")]
    m = G.load_evidence_map(root, "validation", rows)
    assert m["validation-0:q0"] == ["l1  ", "l3"]  # story (file) order, exact line text, only the newline stripped
    assert m["validation-0:q1"] == []
    assert m["validation-9:q0"] == ["m0", "m2"]


def test_evidence_mapping_fails_loudly(tmp_path):
    import pytest
    root = _fake_raw(tmp_path)
    with pytest.raises(KeyError):
        G.load_evidence_map(root, "validation", [dict(id="validation-0:q0"), dict(id="validation-77:q0")])
    (root / "raw" / "validation" / "shard-00001.jsonl").write_text('{"id":"validation-9:q0","evidence_text_lines":[0,5]}\n')
    with pytest.raises(IndexError):
        G.load_evidence_map(root, "validation", [dict(id="validation-9:q0")])


def test_g0ev():
    off = [True] * 50 + [False] * 50
    d = G.g0ev_decision(off, [True] * 58 + [False] * 42)
    assert d["g0ev_pass"] and abs(d["gap_ev"] - 0.08) < 1e-9 and d["acc_ev"] == 0.58
    assert not G.g0ev_decision(off, [True] * 57 + [False] * 43)["g0ev_pass"]


class _Tok:
    def apply_chat_template(self, msgs, tokenize, add_generation_prompt, chat_template, **kw):
        if kw.get("reasoning_effort"):
            return "U:" + msgs[0]["content"] + "\nA:<ifm|think_" + kw["reasoning_effort"] + ">"
        return "U:" + msgs[0]["content"] + "\nA:" + G.EMPTY_THINK


def test_prompt_of_prefill_and_effort():
    tok, row = _Tok(), dict(ROW)
    off = G.prompt_of(tok, "", row, None)
    assert off.endswith(G.EMPTY_THINK) and G.prompt_of(tok, "", row, None, prefill=G.PREFILL) == off + G.PREFILL
    on = G.prompt_of(tok, "", row, "medium", prefill=G.PREFILL)
    assert on.endswith("<ifm|think_medium>")  # the prefill never touches the thinking-on prompt
    ev = G.prompt_of(tok, "", row, None, {row["id"]: ["[world] l1"]}, prefill=G.PREFILL)
    assert ev == G.ev_prompt(off, ["[world] l1"]) + G.PREFILL
    assert G.prompt_of(tok, "", row, None, {row["id"]: ["[world] l1"]}) == G.ev_prompt(off, ["[world] l1"])
    assert G.extract_off(" the mill\nBecause ...") == "the mill"  # a prefilled reply: the answer is the first line after the prefill
