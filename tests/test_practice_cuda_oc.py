"""Practice-2 on CUDA through the OpenCode harness: argument wiring, the proxy's upstream-model/vLLM options, night lesson encoding of segment (dict) targets,
and a CPU smoke (fake upstream standing in for vLLM, the real `opencode`, a tiny HF model for the night)."""
import argparse
import json
import os
import shutil
import urllib.request
from pathlib import Path

import pytest

from practice import k2_proxy as K, lessons as L
from tests import k2_fake_upstream as F

TOOLS = [{"type": "function", "function": {"name": "bash", "description": "run", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}}]
HIST = [{"role": "system", "content": "S"}, {"role": "user", "content": "1+5?"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "echo 6"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "6"}]


def post(port, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def test_proxy_default_upstream_unchanged(tmp_path):
    up = F.start()
    px = K.Proxy(f"http://127.0.0.1:{up.server_address[1]}", tmp_path / "log")
    port = px.start_thread(0)
    try:
        post(port, {"model": "k2", "messages": HIST, "tools": TOOLS})
        b = up.requests[0]
        assert b["model"] == "default_model" and "tool_choice" not in b and "skip_special_tokens" not in b
        assert b["messages"][2]["tool_calls"][0]["function"]["arguments"] == {"command": "echo 6"}  # dicts: mlx_lm's template needs them
    finally:
        px.stop()
        up.shutdown()


def test_proxy_upstream_model_and_vllm_options(tmp_path):
    up = F.start(script=lambda body: "<answer>6</answer><|ifm|im_end|>")
    px = K.Proxy(f"http://127.0.0.1:{up.server_address[1]}", tmp_path / "log", upstream_model="night1", **K.VLLM_PROXY_OPTS)
    port = px.start_thread(0)
    try:
        r = post(port, {"model": "k2", "messages": HIST, "tools": TOOLS, "temperature": 0.7})
        b = up.requests[0]
        assert b["model"] == "night1" and b["tool_choice"] == "none" and b["skip_special_tokens"] is False  # vLLM's own tool parser is never asked
        assert b["stop"] == ["</ifm|tool_calls>"] and b["temperature"] == 0.7 and b["tools"]
        a = b["messages"][2]["tool_calls"][0]["function"]["arguments"]
        assert isinstance(a, str) and json.loads(a) == {"command": "echo 6"}  # JSON strings, as the OpenAI schema says
        assert r["choices"][0]["message"]["content"] == "<answer>6</answer>"  # a trailing <|ifm|im_end|> kept by the server is cut (lessons add their own)
        log = K.read_try_log(tmp_path / "log", K.first_user_key(HIST))
        assert log[0]["upstream_model"] == "night1" and log[0]["completion_text"] == "<answer>6</answer>"
    finally:
        px.stop()
        up.shutdown()


def test_proxy_cli_flags():
    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with pytest.raises(SystemExit), redirect_stdout(f):
        K.main(["--help"])
    assert "--upstream-model" in f.getvalue() and "--vllm" in f.getvalue()


def test_vllm_cmd_has_no_tool_parser_and_serves_the_adapter(tmp_path):
    from practice import oc_cuda as C
    t = C.template_path(argparse.Namespace(chat_template=None))
    assert Path(t).exists() and Path(t).read_text() == (Path(__file__).parent / "k2_nothink.jinja").read_text()
    c = C.vllm_cmd("/v/bin/python", "IFM/K2-Horizon-3.7B", 18081, t, adapter=str(tmp_path / "night2"), lora_name="night2", max_len=16384, util=0.85)
    assert c[:5] == ["/v/bin/python", "-m", "vllm.entrypoints.cli.main", "serve", "IFM/K2-Horizon-3.7B"]
    assert "--enable-lora" in c and c[c.index("--max-lora-rank") + 1] == "16" and c[c.index("--chat-template") + 1] == t
    assert c[c.index("--lora-modules") + 1] == f"night2={tmp_path / 'night2'}" and c[c.index("--served-model-name") + 1] == "default_model"
    assert not any(x.startswith("--") and "tool" in x for x in c)  # no --enable-auto-tool-choice / --tool-call-parser
    assert "--lora-modules" not in C.vllm_cmd("p", "m", 1, t)


def test_job_cli_opencode_wiring():
    from practice import job
    a = job.build_parser().parse_args(["--rg-skills", "auto", "--harness", "opencode"])
    assert (a.harness, a.oc_concurrency, a.oc_train_tokens, a.oc_max_len, a.web, a.train_bare_answers, a.chat_template) == ("opencode", 32, 6144, 16384, True, False, None)
    assert job.build_parser().parse_args(["--rg-skills", "auto"]).harness == "native"
    b = job.build_parser().parse_args(["--harness", "opencode", "--oc-concurrency", "8", "--no-web", "--oc-util", "0.8"])
    assert (b.oc_concurrency, b.web, b.oc_util) == (8, False, 0.8)
    from practice import rg_run
    la = rg_run.lane_args(a, "/tmp/x", "P", "countdown")  # the phase spec carries every opencode option into the worker subprocess
    assert la.harness == "opencode" and la.oc_concurrency == 32 and la.arc_n == 0


class CharTok:
    bos_token = ""

    def __call__(self, text, add_special_tokens=False):
        return argparse.Namespace(input_ids=[ord(c) % 250 for c in text])


def _oc_try(correct, id_, n_prompt=100):
    return {"id": id_, "try": 0, "correct": correct, "messages": [],
            "segs": [["P" * n_prompt, False], ["Let me check.<ifm|tool_calls>x</ifm|tool_calls><|ifm|im_end|>", True],
                     ["R" * 20, False], ["<answer>6</answer><|ifm|im_end|>", True]]}


def test_night_encodes_dict_targets_with_masked_bare_answers():
    from practice import night
    r = _oc_try(True, "a")
    tgt = L.target_of(r)
    assert isinstance(tgt, dict)
    tr = night.MultiTurnTrainer.__new__(night.MultiTurnTrainer)
    tr.tok = CharTok()
    ex = tr.encode("", tgt)
    n = [len(t) for t, _ in r["segs"]]
    assert len(ex["ids"]) == len(ex["mask"]) == sum(n)
    assert sum(ex["mask"]) == n[1] and ex["mask"][n[0]] == 1 and sum(ex["mask"][-n[3]:]) == 0  # only the tool-call turn is trained; the bare answer is not
    old = L.TRAIN_BARE_ANSWERS
    L.TRAIN_BARE_ANSWERS = True
    try:
        assert sum(tr.encode("", L.target_of(r))["mask"]) == n[1] + n[3]
    finally:
        L.TRAIN_BARE_ANSWERS = old
    assert tr.encode("", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}])["mask"].count(1) > 0  # message lists still work


def test_build_lessons_respects_the_6144_cap():
    store = [_oc_try(True, "a", n_prompt=4000), _oc_try(False, "a", n_prompt=4000), _oc_try(True, "b", n_prompt=100), _oc_try(False, "b", n_prompt=100)]
    for i, r in enumerate(store):
        r["try"] = i
    items, st = L.build_lessons("P", store, CharTok(), 1, 1, 10, 1, 10, 6144, dedup=True)
    assert st["tries_usable"] == 4 and len(items) == 2 + 2  # 2 solved puzzles -> 2 sft, 2 pairs
    items2, st2 = L.build_lessons("P", store, CharTok(), 1, 1, 10, 1, 10, 2048, dedup=True)
    assert st2["tries_usable"] == 2  # the 4000-char prompts do not fit the native 2048 cap
    from practice import night
    import inspect
    assert inspect.signature(night.train_night).parameters["max_tokens"].default == 2048


# ------------------------------------------------------------------ CPU smoke: fake upstream (= vLLM) + real opencode + tiny HF model
@pytest.mark.skipif(shutil.which("opencode") is None, reason="opencode is not installed")
@pytest.mark.parametrize("sub", [False, True])
def test_cpu_smoke_opencode_day_night_day(tmp_path, monkeypatch, sub):
    pytest.importorskip("torch")
    pytest.importorskip("peft")
    from practice import job
    monkeypatch.setenv("PRACTICE_TEST_SUB", "1") if sub else monkeypatch.delenv("PRACTICE_TEST_SUB", raising=False)
    up = F.start()
    try:
        argv = ["--rg-skills", "countdown", "--out", str(tmp_path), "--harness", "opencode", "--oc-upstream", f"http://127.0.0.1:{up.server_address[1]}", "--oc-concurrency", "2",
                "--oc-timeout", "150", "--oc-train-tokens", "60000", "--no-web", "--tries", "2", "--smoke", "--arm", "P", "--backend", "vllm"]
        a = job.build_parser().parse_args(argv)
        a.arc_n, a.deadline_s, a.rg_skill, a.tries, a.seed = 0, 1e9, "countdown", 2, 1
        rd = tmp_path / "rgdata"
        rd.mkdir()
        pz = [{"id": f"p{i}", "kind": "arith", "source": "t", "prompt": "What is 1+5?", "answer": "6", "answer_type": "int"} for i in range(3)]
        (rd / "day1.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pz))
        (rd / "day2.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pz[:1]))
        a.rg_test = "day2"
        lane = job.Lane(a)
        assert lane.oc and lane.modes == ["oc"] and lane.sub == sub
        r1 = lane.day(1, 101, None, puzzles=str(rd / "day1.jsonl"))
        recs = job.jl(lane.out / "day" / "day1.jsonl")
        assert len(recs) == 6 and r1["acc"] == 1.0 and all(r["harness"] == "opencode" and r["segs"] and "proxy_tools" not in r for r in recs)
        assert sorted({(r["id"], r["try"]) for r in recs}) == sorted((p["id"], k) for p in pz for k in range(2))
        assert {b["model"] for b in up.requests} == {"default_model"} and all(b["tool_choice"] == "none" and b["skip_special_tokens"] is False for b in up.requests)
        n_req = len(up.requests)
        lane.day(1, 101, None, puzzles=str(rd / "day1.jsonl"))  # resume: nothing left to run
        assert len(up.requests) == n_req and len(job.jl(lane.out / "day" / "day1.jsonl")) == 6
        st = lane.night(1, 1, auto_steps=True, dedup=True, n_sft=5, n_pairs=2)
        assert st["tries_usable"] == 6 and st["sft_unique"] == 3 and Path(st["adapter"], "adapter_config.json").exists() and st["train"]["opt_steps"] >= 1
        lane.day(2, 102, None, puzzles=str(rd / "day2.jsonl"))
        assert {b["model"] for b in up.requests[n_req:]} == {"night1"}  # the proxy asks upstream for the adapter by name
        ev = lane.phase("eval", "eval_P1", tag="P1", seed=5, tries_map={"test": 2})  # the sealed sibling set (100 puzzles) is not run here
        assert ev["test"]["n"] == 2 and (lane.out / "eval" / "P1_test.jsonl").exists() and (lane.out / "results" / "P1.json").exists()
    finally:
        up.shutdown()
