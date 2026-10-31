"""Tests for mac_laps.py (PREREG-think2 Addendum H): python -m pytest backbone/think/test_mac_laps.py
The model tests need MLX (pip install "mlx[cpu]" mlx-lm on Linux) and use a tiny random Qwen3.5-MoE; the rest is plain Python."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_hops as H  # noqa: E402
import mac_laps as L  # noqa: E402


# ---------------------------------------------------------------- data

def test_build_matches_committed_report_and_rows_are_sound(tmp_path):
    assert L.cmd_build(argparse.Namespace(out=str(tmp_path))) == 0
    rep = json.loads((tmp_path / "LAPS_REPORT.json").read_text())
    want = json.loads((HERE.parent / "results" / "laps" / "LAPS_REPORT.json").read_text())
    assert rep == want
    for split, per in (("dev", L.DEV_PER_DEPTH), ("test", L.TEST_PER_DEPTH)):
        rows = L.load_rows(tmp_path, split)
        assert len(rows) == per * L.MAX_DEPTH and {r["depth"] for r in rows} == set(range(1, L.MAX_DEPTH + 1))
        for r in rows[:200]:
            lines = r["context"].split("\n")
            assert len(lines) == L.LINES and len(r["steps"]) == r["depth"] and r["hops_path"][-1] == r["answer"]
            assert len(set(r["places"])) == H.CHAINS
    dev, test = (L.load_rows(tmp_path, s) for s in ("dev", "test"))
    assert not {r["context"] for r in dev} & {r["context"] for r in test}


def test_prompt_ends_in_the_answer_prefix():
    class Tok:
        def apply_chat_template(self, msgs, tokenize, add_generation_prompt, enable_thinking):
            assert not tokenize and add_generation_prompt and enable_thinking is False
            return "<user>" + msgs[0]["content"] + "<assistant>"

        def encode(self, text, add_special_tokens):
            return text
    row = L.build("dev")[0]
    text = L.prompt_ids(Tok(), row)
    obj = row["question"].split("the ")[1].rstrip("?")
    assert text.endswith(f"<assistant>The {obj} is at the") and "[world]" not in text and f"Where is the {obj}?" in text


# ---------------------------------------------------------------- decisions

def rec(i, depth, ans, base_right, lap_right, rmax=4, name="s4k4"):
    """A synthetic record: the plain model and each lap either name the answer (index ans) or index (ans + 1) % 7."""
    def lps(right):
        v = [-5.0] * H.CHAINS
        v[ans if right else (ans + 1) % H.CHAINS] = -0.1
        return v
    laps = lap_right if isinstance(lap_right, list) else [lap_right] * (rmax - 1)
    return dict(id=f"r{i}", depth=depth, ans=ans, base=lps(base_right), base_rms=1.0,
                **{name: {str(k): lps(laps[k - 2]) for k in range(2, rmax + 1)}, name + "_rms": {str(k): float(k) for k in range(2, rmax + 1)}})


def test_deep_slice_and_choose():
    calib = [rec(i, d, 0, i % 10 < {1: 10, 2: 9, 3: 6, 4: 3, 5: 1}[d], False) for d in range(1, 6) for i in range(10)]
    assert L.deep_slice(calib) == [3, 4]  # 60 and 30 lie in [24.3, 80]; 90, 100 and 10 do not
    blocks = [(4, 4), (8, 4), (4, 8)]
    rows = []
    for i in range(10):
        r = rec(i, 3, 2, False, False, name="s4k4")
        r.update({k: v for k, v in rec(i, 3, 2, False, i < 6, name="s8k4").items() if k == "s8k4"})
        r.update({k: v for k, v in rec(i, 3, 2, False, i < 6, name="s4k8").items() if k == "s4k8"})
        rows.append(r)
    sel = L.choose(rows, blocks)
    assert sel["name"] == "s8k4" and sel["dev_gain"] == 60.0  # tie with s4k8 on accuracy and log-prob: the smaller block wins
    assert L.control_block((8, 4), [(4, 4), (8, 4), (12, 4), (24, 4), (4, 8)]) == (24, 4)
    assert L.control_block((16, 4), [(8, 4), (16, 4), (24, 4)]) == (8, 4)  # equal distance: the earlier start


def test_halted():
    r = rec(0, 3, 1, False, [True, True, False])
    assert L.halted(r, "s4k4") == (3, 1)  # laps 1-3 answer wrong, right, right: stops at lap 3 with the right answer
    r = rec(0, 3, 1, True, [True, False, False])
    assert L.halted(r, "s4k4") == (2, 1)
    r = rec(0, 3, 1, True, [False, True, False])
    assert L.halted(r, "s4k4") == (4, 2)  # never stable: lap 4's answer


def test_outcomes():
    def run(base_deep, lap_deep, base_shallow=1.0, lap_shallow=1.0, d1=1.0):
        test, n = [], 0
        for d in range(1, 9):
            for i in range(100):
                if d == 1:
                    b, l = i < 100 * d1, i < 100 * d1
                elif d < 5:
                    b, l = i < 100 * base_shallow, i < 100 * lap_shallow
                else:
                    b, l = i < 100 * base_deep, i < 100 * lap_deep
                test.append(rec(n, d, i % H.CHAINS, b, l))
                n += 1
        res = L.analyse(test, dict(name="s4k4", control=None), [5, 6, 7, 8])
        return L.outcome(res, {}), res
    assert run(0.4, 0.5)[0] == "PASS"
    oc, res = run(0.4, 0.4)
    assert oc.startswith("PROVED WRONG") and res["H1"]["value"] == 0
    assert run(0.4, 0.43)[0] == "NOT SHOWN"
    assert run(0.4, 0.5, lap_shallow=0.9)[0].startswith("TRADE-OFF")
    assert run(0.4, 0.5, d1=0.5)[0].startswith("VOID")
    res = run(0.4, 0.5)[1]
    # a deep row that the laps fix (wrong at lap 1, right from lap 2 on) stops at lap 3; every other row stops at lap 2
    assert res["halt_laps_by_depth"][2] == 2.0 and res["halt_laps_by_depth"][5] == 2.1 and abs(res["halt_mean_laps"] - 2.05) < 1e-9
    assert abs(res["H3_acc"]["value"] - 10.0) < 1e-9 and 0 < res["H3_rho"]["value"] < L.RHO and "NOT ADAPTIVE" in L.adaptive_line(res)
    oc, res = run(0.4, 0.4)
    assert res["halt_mean_laps"] == 2.0 and res["H3_rho"]["value"] is None  # every row is stable at lap 2: no depth trend


def test_read_jsonl_cuts_a_torn_line_and_ends_in_a_newline(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"id": "a"}\n{"id": "b"}\n{"id": "c", "ba')
    assert L.read_jsonl(p) == [{"id": "a"}, {"id": "b"}] and p.read_text() == '{"id": "a"}\n{"id": "b"}\n'
    p.write_text('{"id": "a"}\n\n{"id": "b"}')  # complete last record but no newline: one is added, the blank line stays
    assert L.done_ids(p) == {"a", "b"} and p.read_text() == '{"id": "a"}\n\n{"id": "b"}\n'
    with open(p, "a") as f:
        f.write('{"id": "c"}\n')
    assert L.done_ids(p) == {"a", "b", "c"}
    p.write_text('{"id": "a"}\n')
    assert L.read_jsonl(p) == [{"id": "a"}] and p.read_text() == '{"id": "a"}\n'
    p.write_text('{"id": "a"}\n{"id": "b", "ba')  # a reader of a live file (summarize) never rewrites it
    assert L.read_jsonl(p, repair=False) == [{"id": "a"}] and p.read_text() == '{"id": "a"}\n{"id": "b", "ba'
    assert L.read_jsonl(tmp_path / "missing.jsonl") == []


def test_summarize_partial_and_full(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    sel = dict(D=[5, 6, 7, 8], name="s4k4", control=None, dev_acc=50.0, dev_base=40.0, dev_gain=10.0, table={"s4k4": 50.0})
    (run / "selection.json").write_text(json.dumps(sel))
    rows = [rec(d * 100 + i, d, i % H.CHAINS, d < 5 or i < 40, d < 5 or i < 50) for d in range(1, L.MAX_DEPTH + 1) for i in range(L.TEST_PER_DEPTH)]
    with open(run / "test.jsonl", "w") as f:
        for r in rows[: len(rows) // 2]:
            f.write(json.dumps(r) + "\n")
    a = argparse.Namespace(run=str(run), partial=False)
    assert L.cmd_summarize(a) == 1  # not every row yet, and --partial not given
    a.partial = True
    assert L.cmd_summarize(a) == 0
    out = capsys.readouterr().out
    assert "OUTCOME: PARTIAL (800 of 1600 rows), not a result: PASS" in out and "NEXT:" not in out
    assert not (run / "SUMMARY_laps.txt").exists() and not (run / "analysis.json").exists()
    with open(run / "test.jsonl", "a") as f:  # a duplicated row (two runs on one --out) is counted once
        f.write(json.dumps(rows[0]) + "\n")
    assert L.cmd_summarize(a) == 0 and "PARTIAL (800 of 1600 rows)" in capsys.readouterr().out
    with open(run / "test.jsonl", "a") as f:
        for r in rows[len(rows) // 2:]:
            f.write(json.dumps(r) + "\n")
    a.partial = False
    assert L.cmd_summarize(a) == 0
    text = (run / "SUMMARY_laps.txt").read_text()
    assert "OUTCOME: PASS" in text and "NEXT: (1) same test at 4-bit" in text and (run / "analysis.json").exists()
    assert "hidden-state RMS at the last position, mean by lap (reported, no mark): 1: 1.00, 2: 2.00, 3: 3.00, 4: 4.00" in text
    assert "H3: " in text and "H2 C* lap 2 - plain below D: +0.00" in text


# ---------------------------------------------------------------- model (MLX)

def tiny():
    mx = pytest.importorskip("mlx.core")
    from mlx_lm.models import qwen3_5_moe as Q
    tc = dict(model_type="qwen3_5_moe_text", hidden_size=32, intermediate_size=64, num_hidden_layers=16, num_attention_heads=4,
              num_key_value_heads=2, vocab_size=400, linear_num_value_heads=4, linear_num_key_heads=2, linear_key_head_dim=8,
              linear_value_head_dim=8, head_dim=8, num_experts=4, num_experts_per_tok=2, moe_intermediate_size=16,
              shared_expert_intermediate_size=16, full_attention_interval=4, tie_word_embeddings=False)
    mx.random.seed(0)
    return mx, Q.Model(Q.ModelArgs.from_dict(dict(model_type="qwen3_5_moe", text_config=tc)))


class WordTok:
    """Each whitespace-separated word is one token (ids given out in order of first use); punctuation is split off."""

    def __init__(self):
        self.ids = {}

    def apply_chat_template(self, msgs, tokenize, add_generation_prompt, enable_thinking):
        return "<|user|> " + msgs[0]["content"] + " <|assistant|> "

    def encode(self, text, add_special_tokens=False):
        words = text.replace(".", " .").replace("?", " ?").split()
        return [self.ids.setdefault(w, len(self.ids) % 400) for w in words]


def test_laps_match_a_repeated_layer_list():
    mx, model = tiny()
    lp = L.Laps(model)
    assert lp.blocks() == [(4, 4), (8, 4), (4, 8)]
    ids, cand = [5, 17, 33, 2, 99, 150, 7, 8, 9, 10, 11, 12], [3, 9, 27]
    E = lp.edges(ids)
    tm = model.language_model.model
    full = model(mx.array([ids]))[0, -1].astype(mx.float32)
    want = (full - mx.logsumexp(full))[mx.array(cand)].tolist()
    assert np.allclose(lp.read(E[lp.n], cand)[0], want, atol=2e-3)
    got = lp.laps(E, 4, 8, 3, cand)
    orig = list(tm.layers)
    try:
        for r in (2, 3):
            tm.layers = orig[:12] + orig[4:12] * (r - 1) + orig[12:]
            out = model(mx.array([ids]))[0, -1].astype(mx.float32)
            assert np.allclose(got[r][0], (out - mx.logsumexp(out))[mx.array(cand)].tolist(), atol=2e-3), r
        # the same repeated list decodes token by token with one cache entry per pass, as the docstring says
        tm.layers = orig[:12] + orig[4:12] + orig[12:]
        cache = model.language_model.make_cache()
        assert len(cache) == 24
        model(mx.array([ids[:-1]]), cache=cache)
        step = model(mx.array([ids[-1:]]), cache=cache)[0, -1]
        assert float(mx.abs(step - model(mx.array([ids]))[0, -1]).max()) < 2e-3
    finally:
        tm.layers = orig


def test_selftest(tmp_path, monkeypatch, capsys):
    mx, model = tiny()
    data = tmp_path / "data"
    monkeypatch.setattr(L, "DEV_PER_DEPTH", 1)
    monkeypatch.setattr(L, "TEST_PER_DEPTH", 1)
    monkeypatch.setattr(L, "check_data", lambda d: None)
    L.cmd_build(argparse.Namespace(out=str(data)))
    a = argparse.Namespace(model="tiny", data=str(data), tol=0.01)
    assert L.cmd_selftest(a, load=lambda m: (model, WordTok())) == 0
    assert capsys.readouterr().out.rstrip().endswith("OK") and len(model.language_model.model.layers) == 16


def test_run_end_to_end(tmp_path, monkeypatch):
    mx, model = tiny()
    tok = WordTok()
    data = tmp_path / "data"
    monkeypatch.setattr(L, "DEV_PER_DEPTH", 2)
    monkeypatch.setattr(L, "TEST_PER_DEPTH", 2)
    monkeypatch.setattr(L, "check_data", lambda d: None)
    L.cmd_build(argparse.Namespace(out=str(data)))
    monkeypatch.setattr(L, "D_LO", 0.0)  # a random model sits near the floor: let every depth into D so all stages run
    monkeypatch.setattr(L, "D_HI", 100.0)
    monkeypatch.setattr(L, "CAND_MIN", -1000.0)
    a = argparse.Namespace(model="tiny", data=str(data), out=str(tmp_path / "run"), min_free_gb=0, yes=True)
    assert L.cmd_run(a, load=lambda m: (model, tok)) == 0
    run = tmp_path / "run"
    sel = json.loads((run / "selection.json").read_text())
    assert sel["D"] == list(range(1, L.MAX_DEPTH + 1)) and sel["name"] in {"s4k4", "s8k4", "s4k8"} and len(sel["table"]) == 3
    test = [json.loads(x) for x in open(run / "test.jsonl")]
    assert len(test) == 2 * L.MAX_DEPTH and set(test[0][sel["name"]]) == {"2", "3", "4"}
    assert "OUTCOME:" in (run / "SUMMARY_laps.txt").read_text() and "NEXT:" in (run / "SUMMARY_laps.txt").read_text()
    # resumable: a second run redoes nothing
    n = sum(1 for _ in open(run / "sweep.jsonl"))
    assert L.cmd_run(a, load=lambda m: (model, tok)) == 0 and sum(1 for _ in open(run / "sweep.jsonl")) == n
