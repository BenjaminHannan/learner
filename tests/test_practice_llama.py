"""Practice-2 on llama.cpp (Radeon PC): k2_proxy render_local (request body, BOS handling, /completion parsing), the llama-server command line and lifecycle,
adapter GGUF fallback order, argument wiring, and a CPU smoke (fake llama-server + the real `opencode` + a tiny HF model)."""
import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from practice import k2_proxy as K, oc_llama as OL
from tests import llama_fake_server as LF

TPL = str(Path(__file__).parent / "k2_nothink.jinja")
TOOLS = [{"type": "function", "function": {"name": "bash", "description": "run", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}}}]
MSGS = [{"role": "system", "content": "S"}, {"role": "user", "content": "1+5?"}]
BOS = LF.BOS


def post(port, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def proxy(tmp_path, up, strip=""):
    return K.Proxy(f"http://127.0.0.1:{up.server_address[1]}", tmp_path / "log", render_local={"tokenizer": None, "template": TPL, "bos": BOS, "strip_bos": strip})


def test_completion_body_fields_and_bos():
    b = K.completion_body(BOS + "hello", {"max_tokens": 300, "temperature": 0.7, "repetition_penalty": 1.1, "seed": 3}, strip_bos=BOS)
    assert b["prompt"] == "hello" and b["n_predict"] == 300 and b["stop"] == ["</ifm|tool_calls>", "<|ifm|im_end|>"]
    assert b["cache_prompt"] is True and b["stream"] is False and b["id_slot"] == -1
    assert b["temperature"] == 0.7 and b["repeat_penalty"] == 1.1 and b["seed"] == 3
    assert (b["top_k"], b["top_p"], b["min_p"]) == (0, 1.0, 0.0)  # llama-server's own 40 / 0.95 / 0.05 defaults are pinned off
    assert K.completion_body(BOS + "hello", {}, strip_bos="")["prompt"] == BOS + "hello"
    assert K.completion_body("hello", {}, strip_bos=BOS)["prompt"] == "hello"  # nothing to cut
    assert K.completion_body("x", {})["n_predict"] == K.LLAMA_N_PREDICT


@pytest.mark.parametrize("strip,starts", [("", BOS), (BOS, "<|ifm|")])
def test_render_local_request_and_tool_call_parsing(tmp_path, strip, starts):
    up = LF.start()
    px = proxy(tmp_path, up, strip)
    port = px.start_thread(0)
    try:
        r = post(port, {"model": "k2", "messages": MSGS, "tools": TOOLS, "temperature": 0.7, "max_tokens": 256})
        req = up.requests[0]
        assert set(req) >= {"prompt", "n_predict", "temperature", "stop", "cache_prompt", "id_slot"} and "messages" not in req and "tools" not in req
        assert isinstance(req["prompt"], str) and req["prompt"].startswith(starts) and req["prompt"].count(BOS) == (1 if not strip else 0)
        assert "bash" in req["prompt"] and "1+5?" in req["prompt"] and req["n_predict"] == 256
        # exactly what oc_lessons renders for the lessons (the same function), minus the BOS when it is stripped
        from practice.oc_lessons import render_prompt
        want = render_prompt(MSGS, TOOLS, None, TPL, bos=BOS)
        assert req["prompt"] == (want[len(BOS):] if strip else want)
        msg = r["choices"][0]["message"]
        assert r["choices"][0]["finish_reason"] == "tool_calls" and msg["tool_calls"][0]["function"]["name"] == "bash"
        assert json.loads(msg["tool_calls"][0]["function"]["arguments"])["command"] == "python3 -c 'print(6)'" and msg["content"].strip() == "I will check it."
        log = K.read_try_log(tmp_path / "log", K.first_user_key(MSGS))[0]
        assert log["completion_text"].endswith("</ifm|tool_calls>")  # llama-server cut the stop string; stopping_word put it back
        assert log["usage"]["prompt_tokens"] == len(req["prompt"]) // 3 and log["usage"]["completion_tokens"] == 7 and log["usage"]["stopping_word"] == "</ifm|tool_calls>"
        assert log["upstream_model"] == "llama.cpp" and log["params"]["max_tokens"] == 256 and log["params"]["temperature"] == 0.7
    finally:
        px.stop()
        up.shutdown()


def test_render_local_final_answer_length_and_context(tmp_path):
    hist = MSGS + [{"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command": "x", "description": "print six"}'}}]},
                   {"role": "tool", "tool_call_id": "c1", "content": "6"}]
    up = LF.start()
    px = proxy(tmp_path, up)
    port = px.start_thread(0)
    try:
        r = post(port, {"messages": hist, "tools": TOOLS})
        assert r["choices"][0]["message"]["content"] == "The tool printed 6.\n<answer>6</answer>" and r["choices"][0]["finish_reason"] == "stop"  # stop_type word (im_end) -> no re-append
        up.script = lambda body: "x" * 10_001  # n_predict hit
        r = post(port, {"messages": MSGS, "tools": TOOLS})
        assert r["choices"][0]["finish_reason"] == "length"
        up.fail_ctx = True
        with pytest.raises(urllib.error.HTTPError) as e:
            post(port, {"messages": MSGS, "tools": TOOLS})
        assert e.value.code == 400 and K.CONTEXT_ERR in json.loads(e.value.read())["error"]["message"]  # the harness scores it as a context ending
    finally:
        px.stop()
        up.shutdown()


def test_proxy_default_paths_have_no_render_local(tmp_path):
    assert K.Proxy("http://x", tmp_path / "l").render_local is None


# ------------------------------------------------------------------ server command, lifecycle, probes
def test_llama_cmd_and_winpath(tmp_path):
    assert OL.winpath("/mnt/c/Users/timot/models/k2.gguf") == "C:\\Users\\timot\\models\\k2.gguf" and OL.winpath("relative.gguf") == "relative.gguf"
    c = OL.llama_cmd("/mnt/c/llama/llama-server.exe", "/mnt/c/m/k2.gguf", 18081, 73728, 6)
    assert c == ["/mnt/c/llama/llama-server.exe", "-m", "C:\\m\\k2.gguf", "--host", "127.0.0.1", "--port", "18081", "-ngl", "99", "-c", "73728", "-np", "6", "--cont-batching", "--special"]
    c = OL.llama_cmd("/mnt/c/llama/llama-server.exe", "/mnt/c/m/k2.gguf", 18081, 73728, 6, adapter_gguf="/mnt/c/o/night1/adapter.gguf", host="172.1.2.3", extra=["-fa", "on"])
    assert c[c.index("--lora") + 1] == "C:\\o\\night1\\adapter.gguf" and c[c.index("--host") + 1] == "0.0.0.0" and c[-2:] == ["-fa", "on"]
    assert "--lora" not in OL.llama_cmd("llama-server", "/data/k2.gguf", 1, 8192, 2) and OL.llama_cmd("llama-server", "/data/k2.gguf", 1, 8192, 2)[2] == "/data/k2.gguf"  # native binary: paths untouched


def test_llama_server_lifecycle(tmp_path):
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = OL.LlamaServer([sys.executable, "-m", "tests.llama_fake_server", str(port)], port, tmp_path / "sl" / "llama.log", log=lambda *a: None, wait_s=60)
    try:
        assert srv.start() == {"status": "ok"} and srv.alive()
        srv.start()  # restart (errored tries are redone after a restart)
        assert srv.alive()
    finally:
        srv.stop()
    assert not srv.alive()


def test_bos_probe_and_token_parity():
    for adds in (False, True):
        up = LF.start(adds_bos=adds)
        url = f"http://127.0.0.1:{up.server_address[1]}"
        try:
            assert OL.server_adds_bos(url, BOS) is adds

            class Tok:
                bos_token = BOS

                def __call__(self, text, add_special_tokens=False):
                    return argparse.Namespace(input_ids=([1] if text.startswith(BOS) else []) + [ord(c) % 250 + 2 for c in text.removeprefix(BOS)])
            ok, n_hf, n_srv, diff = OL.token_parity(url, Tok(), TPL, BOS if adds else "")
            assert ok and n_hf == n_srv and diff is None  # one BOS on both sides, whichever side adds it
            ok2 = OL.token_parity(url, Tok(), TPL, "" if adds else BOS)  # the wrong decision is caught: double BOS / no BOS
            assert not ok2[0]
        finally:
            up.shutdown()


def test_adapter_paths_lora_first_then_merged(tmp_path, monkeypatch):
    a = argparse.Namespace(ll_adapter_mode="auto")
    seen = []
    monkeypatch.setattr(OL, "convert_lora", lambda ad, a, log: (seen.append("lora"), "/x/adapter.gguf")[1])
    monkeypatch.setattr(OL, "convert_merged", lambda ad, a, log: (seen.append("merged"), "/x/merged.gguf")[1])
    it = OL.adapter_candidates("/x", a, print)
    assert next(it) == ("lora", "/x/adapter.gguf") and seen == ["lora"]  # lazy: merged is not built unless the server rejects the LoRA GGUF
    assert next(it) == ("merged", "/x/merged.gguf")

    def boom(*x):
        raise RuntimeError("unknown architecture k2-horizon")
    monkeypatch.setattr(OL, "convert_lora", boom)
    assert [k for k, _ in OL.adapter_candidates("/x", a, lambda *m: None)] == ["merged"]  # a conversion failure falls through
    assert [k for k, _ in OL.adapter_candidates("/x", argparse.Namespace(ll_adapter_mode="lora"), lambda *m: None)] == []


def test_convert_lora_command(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(OL, "base_dir", lambda m: "/hf/base")
    monkeypatch.setattr(OL, "_run", lambda cmd, log, what, timeout=0: (calls.append(cmd), Path(cmd[cmd.index("--outfile") + 1]).write_bytes(b"gguf")))
    out = OL.convert_lora(str(tmp_path), argparse.Namespace(ll_src="/ll", model="IFM/K2-Horizon-3.7B"), print)
    assert out == str(tmp_path / "adapter.gguf") and calls[0][1:3] == ["/ll/convert_lora_to_gguf.py", "--base"] and calls[0][-1] == str(tmp_path) and "/hf/base" in calls[0]
    OL.convert_lora(str(tmp_path), argparse.Namespace(ll_src="/ll", model="m"), print)
    assert len(calls) == 1  # cached


def test_llama_setup_with_existing_upstream(tmp_path):
    up = LF.start(adds_bos=True)
    logs = []

    class Tok:
        bos_token = BOS

        def __call__(self, text, add_special_tokens=False):
            return argparse.Namespace(input_ids=([1] if text.startswith(BOS) else []) + [ord(c) % 250 + 2 for c in text.removeprefix(BOS)])
    try:
        a = argparse.Namespace(ll_strip_bos="auto", oc_port=0)
        server, url, kw, alias = OL.llama_setup(a, Tok(), TPL, "/o/adapters/night2", tmp_path, logs.append, upstream=f"http://127.0.0.1:{up.server_address[1]}")
        assert server is None and alias == "night2" and kw["render_local"]["strip_bos"] == BOS and any("parity with HF OK" in m for m in logs)
    finally:
        up.shutdown()


# ------------------------------------------------------------------ argument wiring
def test_cli_wiring(tmp_path):
    from practice import job, rg_run
    a = job.build_parser().parse_args(["--rg-skills", "knights_knaves", "--harness", "opencode", "--server", "llamacpp", "--ll-exe", "/mnt/c/l/llama-server.exe", "--ll-gguf", "/mnt/c/m/k2.gguf",
                                       "--ll-parallel", "6", "--ll-ctx", "73728", "--oc-concurrency", "6", "--rg-day-n", "500"])
    assert OL.use_llama(a) and (a.ll_parallel, a.ll_ctx, a.oc_concurrency, a.rg_day_n, a.ll_adapter_mode, a.ll_strip_bos) == (6, 73728, 6, 500, "auto", "auto")
    assert OL.use_llama(job.build_parser().parse_args(["--harness", "opencode", "--backend", "llamacpp"]))
    assert not OL.use_llama(job.build_parser().parse_args(["--harness", "opencode"])) and job.build_parser().parse_args([]).server == "vllm"
    la = rg_run.lane_args(a, tmp_path, "P", "knights_knaves")  # the phase spec carries the llama options into the worker subprocess
    assert la.server == "llamacpp" and la.ll_exe == "/mnt/c/l/llama-server.exe" and la.ll_ctx == 73728


def test_llamacpp_needs_opencode_and_existing_files(tmp_path):
    from practice import job
    a = job.build_parser().parse_args(["--rg-skills", "knights_knaves", "--backend", "llamacpp", "--out", str(tmp_path), "--arm", "P", "--smoke"])
    a.rg_skill, a.arc_n, a.deadline_s = "knights_knaves", 0, 1e9
    with pytest.raises(SystemExit, match="harness opencode"):
        job.Lane.probe_backends(argparse.Namespace(a=a, oc=False, log=print, modes=["hf"]))
    b = job.build_parser().parse_args(["--harness", "opencode", "--server", "llamacpp", "--ll-exe", str(tmp_path / "nope.exe"), "--ll-gguf", str(tmp_path / "nope.gguf")])
    with pytest.raises(SystemExit, match="ll-exe"):
        job.Lane.probe_backends(argparse.Namespace(a=b, oc=True, log=print, modes=["hf"]))


# ------------------------------------------------------------------ CPU smoke: fake llama-server + real opencode + tiny HF model
@pytest.mark.skipif(shutil.which("opencode") is None, reason="opencode is not installed")
def test_cpu_smoke_opencode_day_against_fake_llama_server(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from practice import job
    monkeypatch.delenv("PRACTICE_TEST_SUB", raising=False)
    up = LF.start()
    try:
        argv = ["--rg-skills", "countdown", "--out", str(tmp_path), "--harness", "opencode", "--server", "llamacpp", "--oc-upstream", f"http://127.0.0.1:{up.server_address[1]}",
                "--ll-strip-bos", "no", "--oc-concurrency", "2", "--oc-timeout", "150", "--no-web", "--tries", "2", "--smoke", "--arm", "P"]
        a = job.build_parser().parse_args(argv)
        a.arc_n, a.deadline_s, a.rg_skill, a.tries, a.seed = 0, 1e9, "countdown", 2, 1
        rd = tmp_path / "rgdata"
        rd.mkdir()
        pz = [{"id": f"p{i}", "kind": "arith", "source": "t", "prompt": "What is 1+5?", "answer": "6", "answer_type": "int"} for i in range(2)]
        (rd / "day1.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pz))
        a.rg_test = "day1"
        lane = job.Lane(a)
        assert lane.oc and lane.modes == ["oc"] and not lane.sub
        r1 = lane.day(1, 101, None, puzzles=str(rd / "day1.jsonl"))
        recs = job.jl(lane.out / "day" / "day1.jsonl")
        assert len(recs) == 4 and r1["acc"] == 1.0 and all(r["segs"] and r["tool_calls"] == 1 for r in recs) and "llamacpp" in r1["backend"]
        bos = lane.tok.bos_token  # the tiny model's tokenizer; the real run uses K2's. Kept (the fake server adds none): exactly one in front of every served prompt
        assert bos and all("prompt" in b and "messages" not in b and b["prompt"].startswith(bos) and b["prompt"].count(bos) == 1 for b in up.requests)
        assert recs[0]["segs"][0][0] == bos and recs[0]["segs"][1][0].startswith("<|ifm|") is not None  # lessons: bos first, then the prompt rendered by the same function
    finally:
        up.shutdown()
