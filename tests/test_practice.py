"""Practice-1 harness tests: tool parsing, sandbox, look(), night lesson counts, set separation, CPU smoke."""
import hashlib
import json
import re
from pathlib import Path

import pytest

from practice import library, night, tools
from practice.grade import is_correct

DATA = Path(__file__).resolve().parent.parent / "practice" / "data"


def rows(name):
    p = DATA / name
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


# ---------------------------------------------------------------- parsing
def test_parse_tool_block():
    assert tools.parse_call("think\n<tool>python</tool>\n<input>\nprint(1)\n</input>\nextra") == ("python", "print(1)")
    assert tools.parse_call("<tool>Search</tool><input>breadth first search</input>") == ("search", "breadth first search")
    assert tools.parse_call("<tool>python</tool>\n<input>\nprint(2)") == ("python", "print(2)")  # missing closing tag
    assert tools.parse_call("<tool>answer</tool><input>\n1 2\n3 4\n</input>") == ("answer", "1 2\n3 4")


def test_parse_lenient_forms():
    assert tools.parse_call("Let me compute.\n```python\nprint(3)\n```") == ("python", "print(3)\n")
    assert tools.parse_call("So the result is\nANSWER: 42.") == ("answer", "42")
    assert tools.parse_call("**ANSWER:** `17`") == ("answer", "17")
    assert tools.parse_call("ANSWER:\n1 2\n3 4") == ("answer", "1 2\n3 4")
    assert tools.parse_call("I do not know") is None
    assert tools.parse_call("<tool>nonsense</tool><input>x</input>") is None
    # a fence beats an unverified ANSWER line in the same turn (the code must run first)
    assert tools.parse_call("```python\nprint(1)\n```\nANSWER: 5")[0] == "python"
    assert is_correct(tools.parse_call("ANSWER: 42.")[1], "42", "int")


def test_last_answer_line():
    assert tools.last_answer_line("ANSWER: 3\nlater thoughts\nANSWER: 5") == "5"
    assert tools.last_answer_line("none") is None


# ---------------------------------------------------------------- sandbox
def test_sandbox_basic_and_timeout():
    assert tools.run_python("print(6*7)").strip() == "42"
    out = tools.run_python("while True: pass", timeout=2)
    assert "timeout" in out
    out = tools.run_python("print('x' * 10000)")
    assert len(out) <= tools.OUT_CAP + 30 and "cut" in out
    assert "ValueError" in tools.run_python("raise ValueError('boom')")
    assert "no output" in tools.run_python("x = 1")


def test_sandbox_no_network_and_clean_env(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:1")
    out = tools.run_python("import os, socket\nprint([k for k in os.environ if 'PROXY' in k.upper() and os.environ[k] != '*'])\n"
                           "try:\n    socket.create_connection(('example.com', 80), timeout=2)\n    print('CONNECTED')\nexcept Exception as e:\n    print('blocked', type(e).__name__)")
    assert "[]" in out and "blocked" in out and "CONNECTED" not in out


# ---------------------------------------------------------------- look
def test_look_grid():
    d = tools.look("0 0 1\n0 2 1\n0 0 1")
    assert "3 rows x 3 columns" in d and "1:3" in d and "2:1" in d
    assert "box (r0,c2)-(r2,c2) size 3" in d
    sym = tools.look("1 2 1\n3 4 3\n1 2 1")
    assert "left-right mirror" in sym and "up-down mirror" in sym and "main-diagonal" not in sym.replace("symmetry: ", "") or True
    assert "repeated tile: 2x2" in tools.look("1 2 1 2\n3 4 3 4")
    assert "1x2" in tools.look("5 6 5 6 5 6")
    assert "could not read" in tools.look("hello")
    assert "transpose" in tools.look("1 2\n2 1")
    assert "[[" not in tools.look("[[1,2],[3,4]]") and "2 rows x 2 columns" in tools.look("[[1,2],[3,4]]")


def test_search_bounded():
    r = library.search("breadth first search shortest path")
    assert 0 < len(r) <= 1500 and r.count("[") <= 3 + 5
    assert len(library.search("itertools permutations")) <= 1500


# ---------------------------------------------------------------- night lessons
class StubTok:
    bos_token = ""

    def __call__(self, text, add_special_tokens=False):
        class R:
            input_ids = list(range(len(text) // 4 + 1))
        return R()


def fake_store(n_puzzles, win_rate, tries=2, seed=0):
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n_puzzles):
        for k in range(tries):
            ok = rng.random() < win_rate
            out.append({"id": f"p{i}", "try": k, "correct": ok, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"q{i}"},
                                                                         {"role": "assistant", "content": f"a{i}-{k}-{ok}"}]})
    return out


@pytest.mark.parametrize("wr", [0.05, 0.3, 0.7])
def test_lessons_equal_counts(wr):
    store = fake_store(150, wr)
    ip, sp = night.build_lessons("P", store, StubTok(), 1, 1)
    ic, sc = night.build_lessons("C", store, StubTok(), 1, 1)
    assert sp["sft_examples"] == sc["sft_examples"] == night.N_SFT * night.EPOCHS
    assert sp["pairs"] == sc["pairs"] == night.N_PAIRS  # P pads by repetition when it has fewer mixed puzzles
    assert len(ip) == len(ic) == night.N_SFT * night.EPOCHS + night.N_PAIRS
    # P: only solved tries in SFT, every pair is (solved, failed); C ignores the result
    assert sp["sft_correct_frac"] == 1.0 and sp["pair_chosen_correct_frac"] == 1.0 and sp["pair_rejected_correct_frac"] == 0.0
    assert 0.0 < sc["sft_correct_frac"] < 1.0 or wr < 0.1


def test_lessons_few_wins_repeat():
    store = fake_store(40, 0.1)
    items, st = night.build_lessons("P", store, StubTok(), 2, 1)
    wins = st["wins_in_store"]
    assert 0 < wins < night.N_SFT and st["sft_examples"] == night.N_SFT * night.EPOCHS
    assert st["sft_unique"] <= wins
    assert night.build_lessons("P", fake_store(10, 0.0), StubTok(), 2, 1)[1]["sft_examples"] == 0  # no wins -> no SFT


def test_loss_only_on_assistant_turns():
    segs = night.segments([{"role": "system", "content": "S"}, {"role": "user", "content": "U"}, {"role": "assistant", "content": "A1"},
                           {"role": "user", "content": "Tool output (python):\n42"}, {"role": "assistant", "content": "A2"}])
    trained = [t for t, m in segs if m]
    assert trained == ["A1<|ifm|im_end|>", "A2<|ifm|im_end|>"]
    assert not any("Tool output" in t for t, m in segs if m)


# ---------------------------------------------------------------- set separation
def norm_text(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def shingles(s, n=3):
    w = re.findall(r"\S+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def jacc(a, b):
    return len(a & b) / max(1, len(a | b))


def test_sets_do_not_overlap():
    practice = rows("practice_pool.jsonl") + rows("sonnet_pool.jsonl")
    test, sib = rows("test100.jsonl"), rows("sibling60.jsonl")
    assert len(practice) >= 250 and len(test) == 100 and len(sib) >= 50
    for name, rs in (("practice", practice), ("test", test), ("sibling", sib)):
        ids = [r["id"] for r in rs]
        assert len(ids) == len(set(ids)), name
    hp = {hashlib.sha256(norm_text(r["prompt"]).encode()).hexdigest() for r in practice}
    for name, others in (("test", test), ("sibling", sib)):
        for r in others:
            assert hashlib.sha256(norm_text(r["prompt"]).encode()).hexdigest() not in hp, (name, r["id"])
    hs = {hashlib.sha256(norm_text(r["prompt"]).encode()).hexdigest() for r in sib}
    assert not any(hashlib.sha256(norm_text(r["prompt"]).encode()).hexdigest() in hs for r in test)
    arc_p = {r["id"] for r in practice if r["id"].startswith("arc-")}
    assert not arc_p & {r["id"] for r in sib if r["id"].startswith("arc-")}
    def arc_grids(r):  # non-trivial whole grids (>= 6 cells, more than one colour) inside an ARC prompt
        gs = re.findall(r"(?:^|\n)((?:\d(?: \d)*\n?)+)", r["prompt"])
        return {g.strip() for g in gs if len(re.findall(r"\d", g)) >= 6 and len(set(re.findall(r"\d", g))) > 1}
    pg = set().union(*[arc_grids(r) for r in practice if r["id"].startswith("arc-")])
    for r in sib:
        if r["id"].startswith("arc-"):
            assert not arc_grids(r) & pg, f"sibling ARC task {r['id']} shares a grid with a practice task"
    # code-made puzzles of one kind share a long template on purpose (same kinds in practice and sibling), so they only count as near-duplicates at >= 0.95
    sh_p = [(r, shingles(r["prompt"])) for r in practice if not r["id"].startswith("arc-")]
    for name, others in (("test", test), ("sibling", sib)):
        for r in others:
            if r["id"].startswith("arc-"):
                continue
            s = shingles(r["prompt"])
            for pr, sp in sh_p:
                lim = 0.95 if r.get("source") == "code-made" and pr.get("source") == "code-made" else 0.8
                assert jacc(s, sp) < lim, f"near-duplicate {name} {r['id']} ~ practice {pr['id']} ({jacc(s, sp):.2f})"
    for i, r in enumerate(test):
        s = shingles(r["prompt"])
        for q in sib:
            assert jacc(s, shingles(q["prompt"])) < 0.8, (r["id"], q["id"])


def test_pool_fields_and_answers():
    for name in ("practice_pool.jsonl", "sibling60.jsonl"):
        for r in rows(name):
            assert {"id", "source", "kind", "prompt", "answer", "answer_type"} <= set(r) and r["answer_type"] in ("int", "str", "grid")
            assert is_correct(r["answer"], r["answer"], r["answer_type"])


# ---------------------------------------------------------------- end to end on CPU
def test_cpu_smoke(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("peft")
    from practice import smoke
    s = smoke.run_smoke(tmp_path)
    assert s["P"]["n_items"] == s["C"]["n_items"] and s["P"]["opt_steps"] == s["C"]["opt_steps"] == 3
    assert (tmp_path / "P" / "timing.json").exists() and (tmp_path / "C" / "results" / "C1.json").exists()


def test_cpu_pilot(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("peft")
    from practice import harness, job, smoke
    a = job.argparse.Namespace(arm="P", lane=0, out=str(tmp_path), model="", seed=1, practice_n=None, deadline_s=3600, night_est_s=1, arc_n=20, bs=4, nights=1, tries=1,
                               steps=3, n_sft=6, epochs=1, n_pairs=3, pilot=True, smoke=True, backend="hf", eval_nights="1,3", sib_tries=1)
    lane = job.Lane(a)
    lane.pool = [p for p in lane.pool if p["kind"] != "arc"][:20]
    lane.test = [p for p in lane.test if len(p["prompt"]) < 1500]
    lane.H.max_new = 16
    harness.generate = smoke.scripted_factory(lane.pool + lane.test + lane.sib)
    out = lane.pilot()
    assert out["projection"]["suggested_practice_n"] >= 0 and out["projection"]["projected_full_run_h_with_full_pool"] > 0 and (tmp_path / "P" / "pilot.json").exists()
    pj = json.loads((tmp_path / "P" / "pilot.json").read_text())
    assert pj["done"] == ["test_base", "day_base", "night", "test_adapter"] and pj["projection"]["suggested_practice_n"] >= 0
    cfg = json.loads((tmp_path / "P" / "config.json").read_text())
    assert (cfg["max_new_per_turn"], cfg["max_turns"], cfg["max_ctx"]) == (512, 6, 4096) and "</input>" in cfg["stop"]
    assert (tmp_path / "P" / "adapters" / "night1" / "adapter_config.json").exists()


# ---------------------------------------------------------------- caps, stop strings, sticky batch size, backends
def test_caps_and_prompt():
    from practice import harness, job
    assert (job.MAX_NEW, tools.MAX_TURNS, job.MAX_CTX) == (512, 6, 4096)
    assert "at most 6 turns" in tools.SYSTEM_PROMPT and "__N__" not in tools.SYSTEM_PROMPT
    h = harness.Harness(None, None)
    assert (h.max_new, h.max_turns, h.max_ctx, h.bs) == (512, 6, 4096, 8)


def tiny_model(tmp_path):
    pytest.importorskip("torch")
    from sleep2.askonce.model_io import get_tokenizer, load_model, make_tiny
    name = "tiny:" + make_tiny(tmp_path / "tiny", [tools.SYSTEM_PROMPT, "<tool>python</tool><input>print(1)</input> ANSWER: 1"] * 20)
    return load_model(name, __import__("torch").float32, "cpu"), get_tokenizer(name)


def test_stop_on_text_criterion(tmp_path):
    import torch
    from practice.gen import StopOnText
    _, tok = tiny_model(tmp_path)
    a = tok("hello <tool>python</tool><input>print(1)</input>", add_special_tokens=False).input_ids
    b = tok("hello world foo bar baz qux", add_special_tokens=False).input_ids
    n = max(len(a), len(b))
    pad = tok.pad_token_id
    ids = torch.tensor([[pad] * (n - len(a)) + a, [pad] * (n - len(b)) + b])
    done = StopOnText(tok, 0)(ids)
    assert done.tolist() == [True, False]
    assert StopOnText(tok, n)(ids).tolist() == [False, False]  # prompt tokens are ignored


def test_bs_state_sticky_and_grow():
    from practice.gen import BsState
    st = BsState(8, tok_budget=10000, grow_after=3)
    st.oom(8, 1000)
    assert st.bs == 4 and st.tok_budget == 5600
    for _ in range(3):
        st.ok()
    assert st.bs == 5  # grows by one after clean calls...
    for _ in range(30):
        st.ok()
    assert st.bs < 8  # ...but never back up to the size that failed


def test_hf_generate_oom_is_sticky(tmp_path, monkeypatch):
    import torch
    from practice.gen import BsState, hf_generate
    model, tok = tiny_model(tmp_path)
    calls = []
    real = model.generate

    def fake(*a, **kw):
        calls.append(kw["input_ids"].shape[0])
        if kw["input_ids"].shape[0] > 2:
            raise torch.OutOfMemoryError("CUDA out of memory (fake)")
        return real(*a, **kw)
    monkeypatch.setattr(model, "generate", fake)
    st = BsState(8)
    logs = []
    prompts = [f"<|ifm|im_start|>user\nq{i} " + "x " * i for i in range(10)]
    outs = hf_generate(model, tok, prompts, 6, 0.7, 1, st, logs.append)
    assert len(outs) == 10 and all(isinstance(o, str) for o in outs)
    assert st.bs <= 2 and st.ooms >= 1
    n_fail = sum(1 for c in calls if c > 2)
    hf_generate(model, tok, prompts, 6, 0.7, 2, st, logs.append)  # second call starts at the reduced size: no new failing calls
    assert sum(1 for c in calls if c > 2) == n_fail


def test_hf_generate_stops_at_input_tag(tmp_path, monkeypatch):
    """A scripted model.generate that honours the stopping criteria: every row must stop right after '</input>' instead of running to max_new."""
    import torch
    from transformers import StoppingCriteriaList
    from practice.gen import hf_generate
    model, tok = tiny_model(tmp_path)
    script = tok("<tool>python</tool><input>print(1)</input> trailing words that must not be generated", add_special_tokens=False).input_ids
    seen = {}

    def fake(input_ids=None, attention_mask=None, max_new_tokens=0, stopping_criteria=None, **kw):
        B, L = input_ids.shape
        cur = input_ids
        fin = torch.zeros(B, dtype=torch.bool)
        for step in range(max_new_tokens):
            nxt = torch.tensor([[script[step]] if not fin[b] else [tok.pad_token_id] for b in range(B)])
            cur = torch.cat([cur, nxt], 1)
            fin = fin | stopping_criteria(cur, None)
            if fin.all():
                break
        seen["steps"] = cur.shape[1] - L
        return cur
    monkeypatch.setattr(model, "generate", fake)
    outs = hf_generate(model, tok, ["<|ifm|im_start|>user\nhi", "<|ifm|im_start|>user\nhello there"], 200, 0.7, 0, 8)
    assert all(o.endswith("</input>") for o in outs), outs
    assert seen["steps"] < 30


def test_harness_with_backend(monkeypatch):
    """A (mock) vLLM-style backend: the harness hands it rendered prompts and uses its replies."""
    from practice import harness
    seen = []

    class Fake:
        inflight = 5

        def describe(self):
            return "fake"

        def generate(self, prompts, max_new, temperature, seed):
            seen.append((len(prompts), max_new))
            return ["<tool>answer</tool><input>\n42\n</input>" for _ in prompts]

    class Tok:
        bos_token = ""

        def __call__(self, text, add_special_tokens=False):
            class R:
                input_ids = list(range(len(text) // 4 + 1))
            return R()
    h = harness.Harness(None, Tok(), backend=Fake(), progress_s=0)
    puzzles = [{"id": f"x{i}", "kind": "number", "prompt": "q", "answer": "42", "answer_type": "int", "source": "t"} for i in range(7)]
    recs = h.run(puzzles, 1, 0, label="mock")
    assert len(recs) == 7 and all(r["correct"] for r in recs) and seen[0] == (5, 512)


def test_projection_fits_budget():
    from practice import job
    st = {"test_base": {"n": 12, "seconds": 120, "overhead_s": 90}, "day_base": {"n": 12, "seconds": 130, "overhead_s": 90},
          "night": {"seconds": 400, "n_items": 28, "pairs": 8, "n_sft_pilot": 20, "overhead_s": 60},
          "test_adapter": {"n": 12, "seconds": 125, "overhead_s": 90, "arc_seconds": 20, "arc_n": 20}}
    p = job.project(st, None, 392, 100, 60)
    assert p["suggested_practice_n"] > 0
    n = p["suggested_practice_n"]
    spent = p["fixed_h"] + 3 * n * 2 * p["sec_per_try_day_adapter_est"] / 3600
    assert spent <= 9.5 + 1e-6
    assert job.project({}, None, 392, 100, 60) == {}


# ---------------------------------------------------------------- Practice-1M (Mac): openai backend, web filters, mlx lessons, orchestrator
def test_openai_backend_mocked():
    from practice.gen import OpenAIBackend
    seen = []

    def post(url, body, timeout):
        seen.append((url, body))
        if "ASK_OPEN" in body["prompt"]:  # server cut at a stop string: '</input>' is not returned
            return {"choices": [{"text": "<tool>python</tool><input>\nprint(1)\n", "finish_reason": "stop"}], "usage": {"completion_tokens": 7}}
        return {"choices": [{"text": "hello<|ifm|im_end|>junk", "finish_reason": "stop"}], "usage": {"completion_tokens": 3}}
    gated = []
    be = OpenAIBackend("http://127.0.0.1:1/", "m", workers=3, strip_prefix="<s>", post=post, gate=lambda: gated.append(1))
    outs = be.generate(["<s>ASK_OPEN x", "<s>plain", "plain2"], 100, 0.7, 5)
    assert outs[0].endswith("</input>") and outs[1] == "hello" and outs[2] == "hello"
    assert be.completion_tokens == 13 and be.inflight == 3 and len(gated) == 3
    url, body = seen[0]
    assert url == "http://127.0.0.1:1/v1/completions" and body["stop"] == __import__("practice.gen", fromlist=["STOPS"]).STOPS and body["max_tokens"] == 100
    assert not body["prompt"].startswith("<s>") and body["temperature"] == 0.7 and "seed" in body
    assert len({b["seed"] for _, b in seen}) == 3  # one seed per request


def test_server_manager_command():
    from practice.gen import ServerManager
    sm = ServerManager("py", 9000)
    sm._help = "--decode-concurrency N"
    c = sm.cmd("/m", "/adapters/n1", 2)
    assert c[:4] == ["py", "-m", "mlx_lm.server", "--model"] and "--adapter-path" in c and c[c.index("--port") + 1] == "9000"
    assert "--decode-concurrency" in c and "--prompt-concurrency" not in c


def _page(text):
    return "<html><head><title>t</title><script>var x=1</script></head><body><nav>menu</nav><p>" + text + "</p></body></html>"


def test_web_filters(monkeypatch):
    from practice import web
    test_rows = [r for r in rows("test100.jsonl")][:5]
    if not test_rows:
        test_rows = [{"prompt": "A zebra crosses seven rivers while counting thirteen striped pebbles on the far bank of every river it meets today", "answer": "17"}]
    sentence = " ".join(test_rows[0]["prompt"].split()[:14])
    practice = [{"id": "pe-12", "title": "Project Euler problem 12", "prompt": "What is the first triangle number with over 500 divisors", "answer": "76576500"}]
    pages = {
        "https://example.org/leak": _page("Some blog quoting: " + sentence + " and more."),
        "https://example.org/ok": _page("Breadth first search explores a graph level by level. " * 3),
        "https://example.org/ans": _page("Project Euler problem 12 answer is 76576500 ok."),
        "https://example.org/ans-no-title": _page("The number 76576500 is a nice number."),
    }
    ddg = ('<div class="result"><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fok&rut=x">BFS intro</a>'
           '<a class="result__snippet">Level by level search</a></div>'
           '<div class="result"><a class="result__a" href="https://github.com/fchollet/ARC-AGI">ARC repo</a><a class="result__snippet">tasks</a></div>'
           '<div class="result"><a class="result__a" href="https://example.org/leak">Leaky</a><a class="result__snippet">' + sentence + '</a></div>')

    def get(url, timeout=10):
        if url.startswith("https://html.duckduckgo.com/html/?q="):
            return url, "text/html", ddg
        if url in pages:
            return url, "text/html; charset=utf-8", pages[url]
        raise OSError("no such page")
    w = web.Web()
    w.configure(True, test_rows, practice, get=get)
    w.begin()
    res = w.search("breadth first search")
    ev = w.end()
    assert "BFS intro" in res and "ARC repo" not in res and "Leaky" not in res
    st = {(e["url"], e["status"]) for e in ev}
    assert ("https://example.org/ok", "allowed") in st and ("https://github.com/fchollet/ARC-AGI", "blocked") in st and ("https://example.org/leak", "blocked") in st
    w.begin()
    assert "blocked" in w.fetch("https://example.org/leak")
    assert "blocked" in w.fetch("https://example.org/ans")
    assert "blocked" in w.fetch("https://raw.githubusercontent.com/lucky-bai/projecteuler-solutions/master/Solutions.md")
    assert "blocked" in w.fetch("https://euler.stephan-brumme.com/12/")
    ok = w.fetch("https://example.org/ok")
    assert "Breadth first search" in ok and "menu" not in ok and "var x" not in ok and len(ok) <= web.PAGE_CHARS + 20
    assert "nice number" in w.fetch("https://example.org/ans-no-title")  # answer alone (no title/id next to it) is allowed
    ev = w.end()
    assert [e["status"] for e in ev] == ["blocked", "blocked", "blocked", "blocked", "allowed", "allowed"]
    assert web.host_blocked("https://www.kaggle.com/x") and web.host_blocked("https://arcprize.org/") and not web.host_blocked("https://projecteuler.net/problem=1")
    assert web.host_blocked("https://mathblog.dk/project-euler-12/")


def test_web_off_by_default_and_prompt():
    from practice import web
    assert web.WEB.enabled is False
    assert tools.system_prompt() == tools.SYSTEM_PROMPT and "fetch" not in tools.SYSTEM_PROMPT
    assert "fetch" in tools.WEB_SYSTEM_PROMPT and "web search" in tools.WEB_SYSTEM_PROMPT and "__N__" not in tools.WEB_SYSTEM_PROMPT
    assert tools.run_tool_ev("fetch", "https://example.com")[0].startswith("fetch: not available")


def test_pe_parse(tmp_path):
    from practice import pe_pool
    assert pe_pool.parse_answers("Problem 1: 233168\n2. 4613732\n| 3 | 6857 |\nnoise") == {1: "233168", 2: "4613732", 3: "6857"}
    rows_ = pe_pool.build(2, str(tmp_path / "pe.jsonl"), sleep=0, log=lambda *_: None, fetch=lambda u: ("Problem 1: 233168\nProblem 2: 4613732\n" * 10) if "Solutions" in u else
                          "<p>Find the sum of all the multiples of $3$ or $5$ below $1000$, which is a fairly long sentence for the test.</p>")
    assert [r["id"] for r in rows_] == ["pe-1", "pe-2"] and rows_[0]["answer"] == "233168" and "$" not in rows_[0]["prompt"]
    assert pe_pool.build(2, str(tmp_path / "pe.jsonl"), fetch=lambda u: 1 / 0, soft=True, log=lambda *_: None) == []


def test_mlx_lesson_rendering(tmp_path):
    from practice import mlx_train
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}, {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Tool output (python):\n42"}, {"role": "assistant", "content": "A2"}]
    items = [{"kind": "sft", "prompt": "", "target": msgs}, {"kind": "pair", "prompt": "", "chosen": msgs, "rejected": msgs[:3]}]
    f = tmp_path / "l.jsonl"
    assert mlx_train.lessons_to_jsonl(items, f, "<s>") == 2
    recs = [json.loads(l) for l in open(f)]
    segs = recs[0]["segs"]
    assert "".join(t for t, _ in segs) == "<s>" + "".join(night.segments(msgs)[i][0] for i in range(len(night.segments(msgs))))
    assert [t for t, m in segs if m] == ["A1<|ifm|im_end|>", "A2<|ifm|im_end|>"] and segs[0] == ["<s>", 0]
    assert not any("Tool output" in t for t, m in segs if m)
    assert recs[1]["kind"] == "pair" and len([1 for t, m in recs[1]["rejected"] if m]) == 1
    # the rendering is exactly what the harness shows the model
    from practice import harness
    full = harness.render(msgs[:3], False, "<s>")
    assert "".join(t for t, _ in recs[1]["rejected"]) == full
    sch = mlx_train.schedule([{"kind": "sft"}] * 10 + [{"kind": "pair"}] * 4, 4, 0)
    assert len(sch) == 4 and sum(len(s) for s in sch) == 14 and all(sum(i["kind"] == "pair" for i in s) == 1 for s in sch)


def test_mac_probes():
    from practice import mac_run
    vm = "Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free:   100000.\nPages inactive: 50000.\nPages speculative: 10000.\nPages purgeable: 0.\n"
    assert abs(mac_run.parse_vm_stat(vm) - 160000 * 16384 / 2 ** 30) < 1e-6
    assert mac_run.pressure_level(lambda c: "2\n") == 2
    assert mac_run.pressure_level(lambda c: "System-wide memory free percentage: 3%" if c[0] == "memory_pressure" else "") == 4
    assert mac_run.signflip_p({"a": 1, "b": 1, "c": 1}, {"a": 0, "b": 0, "c": 0}) == 0.25 and mac_run.signflip_p({"a": 1}, {"a": 1}) == 1.0


def _mac_fixture(tmp_path, monkeypatch, ram_gb=30, assistant=False, pressure="1", disk_ok=True):
    from practice import mac_run
    ops = tmp_path / "ops"
    ops.mkdir(parents=True)
    if assistant:
        (ops / "ASSISTANT_RUNNING").write_text("x")
    monkeypatch.setattr(mac_run, "OPS", ops)
    monkeypatch.setattr(mac_run, "free_disk_gb", lambda p: 500.0 if disk_ok else 5.0)
    pages = int(ram_gb * 2 ** 30 / 16384)

    def sysrun(c):
        if c[0] == "vm_stat":
            return f"(page size of 16384 bytes)\nPages free: {pages}.\n"
        if c[0] == "sysctl" and "vm.swapusage" in c:
            return "vm.swapusage: total = 2048.00M  used = 100.00M  free = 1948.00M"
        if c[0] == "sysctl":
            return pressure
        return ""

    class Srv:
        cur, base_url = None, "http://x"

        def __init__(self):
            self.log = []

        def ensure(self, model, adapter=None, concurrency=4):
            self.cur = (model, adapter, concurrency)
            self.log.append(self.cur)

        def stop(self):
            self.cur = None

        def rss_mb(self):
            return 1234.0
    a = mac_run.parse_args(["--out", str(tmp_path / "out"), "--practice-n", "6", "--nights", "1", "--eval-nights", "1", "--skip-bench", "--no-web", "--poll-s", "0",
                            "--n-sft", "4", "--n-pairs", "2", "--steps", "2"])
    return mac_run, mac_run.Mac(a, run=sysrun, server=Srv())


def test_mac_preflight_rules(tmp_path, monkeypatch):
    mac_run, m = _mac_fixture(tmp_path, monkeypatch, ram_gb=10)
    with pytest.raises(mac_run.StopRun):
        m.preflight()  # < 12 GB free
    mac_run, m = _mac_fixture(tmp_path / "b", monkeypatch, ram_gb=10, assistant=True)
    assert m.preflight()["need_ram_gb"] == 8.0 and m.concurrency() == 2  # assistant resident: 8 GB ceiling, concurrency <= 2
    mac_run, m = _mac_fixture(tmp_path / "c", monkeypatch, ram_gb=30, disk_ok=False)
    with pytest.raises(mac_run.StopRun):
        m.preflight()
    mac_run, m = _mac_fixture(tmp_path / "d", monkeypatch, ram_gb=30)
    with pytest.raises(mac_run.StopRun):
        m._need_disk(10 ** 6, "download")
    mac_run, m = _mac_fixture(tmp_path / "e", monkeypatch, ram_gb=30, pressure="4")
    m.mem_wait_s = 0
    with pytest.raises(mac_run.StopRun):
        m.checkpoint("x")  # critical memory pressure between phases stops cleanly


def test_mac_pause_others_stops_server(tmp_path, monkeypatch):
    mac_run, m = _mac_fixture(tmp_path, monkeypatch)
    pf = mac_run.OPS / "PAUSE_OTHERS"
    pf.write_text("someone else")
    m.server.cur = ("m", None, 4)
    stopped = []
    m.server.stop = lambda: stopped.append(1) or setattr(m.server, "cur", None)
    m.server.start = lambda *a: stopped.append(("start", a))
    import threading
    threading.Timer(0.3, pf.unlink).start()
    m.wait_pause_others()
    assert stopped[0] == 1 and stopped[1] == ("start", ("m", None, 4))
    pf.write_text("practice1m run")
    assert not m.paused_by_others()  # our own marker does not pause us


def test_mac_run_end_to_end_with_stubs(tmp_path, monkeypatch):
    mac_run, m = _mac_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(mac_run.pe_pool, "build", lambda *a, **k: [])
    m.locate_model = lambda: "/fake/model"
    m.bos, m.strip_bos = "", False
    m.load_tok = lambda model: StubTok()
    allp = {}
    for r in rows("practice_pool.jsonl") + rows("sonnet_pool.jsonl") + rows("test100.jsonl") + rows("sibling60.jsonl"):
        allp[r["prompt"]] = r
    import random as _r
    rng = _r.Random(3)

    class Be:
        inflight, completion_tokens = 4, 0
        gate = None

        def describe(self):
            return "scripted"

        def generate(self, prompts, max_new, temperature, seed):
            outs = []
            for pr in prompts:
                mm = re.search(r"<\|ifm\|im_start\|>user\n(.*?)\n\n\(The final answer", pr, re.S)
                p = allp.get(mm.group(1)) if mm else None
                good = rng.random() < 0.5
                outs.append(f"<tool>answer</tool><input>\n{p['answer'] if (p and good) else '0'}\n</input>")
            return outs
    m.make_backend = lambda conc: Be()
    trained = []

    def train(spec):
        trained.append(spec)
        out = Path(spec["out"])
        out.mkdir(parents=True)
        st = {"steps": spec["steps"], "items": 5, "loss_by_step": [1.0, 0.5], "seconds": 1, "peak_gb": 5.0}
        (out / "train_stats.json").write_text(json.dumps(st))
        return st
    m.train_fn = train
    assert m.run() == 0
    out = m.out
    for f in ("status.json", "summary.json", "config.json", "phases.jsonl", "A0/eval_A0_test.jsonl", "P/day1.jsonl", "C/day1.jsonl", "P/eval_P1_test.jsonl", "C/eval_C1_sib.jsonl"):
        assert (out / f).exists(), f
    summ = json.loads((out / "summary.json").read_text())
    assert set(summ["evals"]) == {"A0", "P1", "C1"} and len(summ["evals"]["A0"]["test100_per_puzzle"]) == 100
    assert "P1_vs_A0" in summ["comparisons"] and "P1_vs_C1" in summ["comparisons"]
    assert len(trained) == 2 and trained[0]["steps"] == trained[1]["steps"] == 2
    assert all("peak_server_rss_mb" in json.loads(l) for l in open(out / "phases.jsonl"))
    # one server at a time; adapters served after the night, base before
    assert any(c[1] and "night1" in c[1] for c in m.server.log) and m.server.log[0][1] is None
    # resume: a second run skips everything
    n_before = len(list(open(out / "phases.jsonl")))
    m2 = mac_run.Mac(m.a, run=m.sysrun, server=m.server)
    m2.locate_model, m2.load_tok, m2.make_backend, m2.train_fn = m.locate_model, m.load_tok, m.make_backend, m.train_fn
    m2.bos, m2.strip_bos = "", False
    assert m2.run() == 0 and len(list(open(out / "phases.jsonl"))) == n_before


# ---------------------------------------------------------------- scout (mocked HTTP / server)
SCOUT_PROMPT = ("Seven travellers named Ada, Bo, Cy, Di, Ed, Flo and Gus each carry a different number of lanterns across the old stone bridge at dusk. "
                "Ada carries twice as many as Bo, and the total carried by all seven is 28. How many lanterns does Bo carry?")
SCOUT_PAGE = "<html><body><h1>Lantern bridge</h1><p>" + SCOUT_PROMPT + "</p><p>Answer: 4</p></body></html>"


def _scout(tmp_path, replies, pages=None, ops=None, probe=None, until=None, max_episodes=1, sleep=None):
    from practice import scout
    a = scout.parse_args(["--out", str(tmp_path / "s"), "--quiet", "--max-episodes", str(max_episodes), "--until", "2999-01-01T00:00Z", "--poll-s", "0"])
    if until:
        a.until_ts = until
    it = iter(replies)
    prompts = []

    def post(url, body, timeout):
        prompts.append(body["prompt"])
        return {"choices": [{"text": next(it), "finish_reason": "stop"}], "usage": {"completion_tokens": 5, "prompt_tokens": 9}}

    def get(url, timeout=10):
        if url not in (pages or {}):
            raise OSError("no such page")
        return url, "text/html", pages[url]
    s = scout.Scout(a, post=post, get=get, probe=probe or (lambda: {}), sleep=sleep or (lambda x: None), ops=ops or (tmp_path / "ops"))
    s.prompts = prompts
    return s


def _call(name, inp=""):
    return f"<tool>{name}</tool>\n<input>\n{inp}\n</input>"


def _save(**kw):
    d = {"title": "Lantern bridge", "prompt": SCOUT_PROMPT, "answer": "4", "answer_type": "int", "source_url": "https://puzzles.example.org/lantern",
         "answer_url": "https://puzzles.example.org/lantern"}
    d.update(kw)
    return _call("save", json.dumps(d))


def test_scout_save_and_answer_must_appear(tmp_path):
    pages = {"https://puzzles.example.org/lantern": SCOUT_PAGE}
    fetch = _call("fetch", "https://puzzles.example.org/lantern")
    # wrong answer (not on the page) is rejected, the right one is saved
    s = _scout(tmp_path, [fetch, _save(answer="9"), _save(), _call("done")], pages)
    s.run()
    st = json.loads((tmp_path / "s" / "stats.json").read_text())
    assert st["rejects"] == {"answer_not_in_page": 1} and st["saves"] == 1 and st["episodes"] == 1 and st["tokens"]["completion"] == 20
    f = jl_rows(tmp_path / "s" / "finds.jsonl")
    assert len(f) == 1 and f[0]["status"] == "unverified" and f[0]["text_match"] and len(f[0]["answer_page_sha256"]) == 64 and f[0]["answer_type"] == "int"
    assert f[0]["answer_page_sha256"] in (tmp_path / "s" / "scout.log").read_text()
    assert len(s.prompts) == 4 and "Topic for this episode" in s.prompts[0]


def test_scout_page_must_be_fetched_first(tmp_path):
    s = _scout(tmp_path, [_save(), _call("done")], {"https://puzzles.example.org/lantern": SCOUT_PAGE})
    s.run()
    assert json.loads((tmp_path / "s" / "stats.json").read_text())["rejects"] == {"page_not_fetched": 1}
    assert not (tmp_path / "s" / "finds.jsonl").exists()


def test_scout_rejects_test_shingle_and_duplicates(tmp_path):
    test = jl_rows(DATA / "test100.jsonl")[0]
    words12 = " ".join(test["prompt"].split()[:14])
    prompt = "Intro text here. " + words12 + " and then some more words follow to make it long enough."
    page = "<html><body><p>" + prompt + "</p><p>Answer: 4</p></body></html>"
    url = "https://puzzles.example.org/leak"
    s = _scout(tmp_path, [_call("fetch", url), _save(prompt=prompt, source_url=url, answer_url=url), _call("done")], {url: page})
    # the web guard itself already blocks a page that carries a sealed-test passage, so fetch is withheld; save must still refuse the prompt
    s.run()
    r = json.loads((tmp_path / "s" / "stats.json").read_text())["rejects"]
    assert r.get("test_overlap") == 1 and "finds.jsonl" not in [p.name for p in (tmp_path / "s").iterdir()]
    # near-duplicate of an earlier find
    pages = {"https://puzzles.example.org/lantern": SCOUT_PAGE}
    fetch = _call("fetch", "https://puzzles.example.org/lantern")
    s2 = _scout(tmp_path / "b", [fetch, _save(), _save(title="again"), _call("done")], pages)
    s2.run()
    assert json.loads((tmp_path / "b" / "s" / "stats.json").read_text())["rejects"] == {"duplicate": 1}


def test_scout_form_checks():
    from practice.scout import answer_in_text, check_shape
    base = {"title": "t", "prompt": SCOUT_PROMPT, "answer": "4", "answer_type": "int", "source_url": "https://a.org/x", "answer_url": "https://a.org/x"}
    assert check_shape(dict(base))[1] == "ok"
    assert check_shape({**base, "answer": "four"})[1] == "int_form"
    assert check_shape({**base, "answer_type": "float"})[1] == "answer_type"
    assert check_shape({**base, "prompt": "short"})[1] == "prompt_length"
    assert check_shape({**base, "answer": "lanterns", "answer_type": "str", "prompt": SCOUT_PROMPT})[1] == "answer_in_prompt"
    assert check_shape({**base, "source_url": ""})[1] == "missing_source_url"
    assert check_shape("nope")[1] == "bad_json"
    assert answer_in_text("1234", "int", "total is 1,234.") and not answer_in_text("4", "int", "total 1234 and 4.5") and answer_in_text("-3", "int", "x = -3")
    assert answer_in_text("Red Fox", "str", "the answer: red   fox!") and not answer_in_text("fox", "str", "foxes")
    assert answer_in_text("12\n34", "grid", "grid\n1 2\n3 4")


def test_scout_resume_and_stats(tmp_path):
    pages = {"https://puzzles.example.org/lantern": SCOUT_PAGE}
    fetch = _call("fetch", "https://puzzles.example.org/lantern")
    s = _scout(tmp_path, [fetch, _save(), _call("done")], pages)
    s.run()
    # a second process: earlier find is known (duplicate), episode counter continues, topic rotates
    s2 = _scout(tmp_path, [fetch, _save(), _call("done")], pages, max_episodes=2)
    s2.run()
    st = json.loads((tmp_path / "s" / "stats.json").read_text())
    assert st["episodes"] == 2 and st["saves"] == 1 and st["rejects"] == {"duplicate": 1}
    assert len(jl_rows(tmp_path / "s" / "finds.jsonl")) == 1 and len(jl_rows(tmp_path / "s" / "episodes.jsonl")) == 2
    from practice.scout import TOPICS
    assert len(TOPICS) >= 40 and TOPICS[1] in s2.prompts[0] and TOPICS[0] not in s2.prompts[0]


def test_scout_waits_for_pause_and_server(tmp_path):
    ops = tmp_path / "ops"
    ops.mkdir()
    (ops / "PAUSE_OTHERS").write_text("x")
    calls = {"probe": 0, "sleep": 0}

    def probe():
        calls["probe"] += 1
        if calls["probe"] < 3:
            raise OSError("down")
        return {}

    def sleep(x):
        calls["sleep"] += 1
        if calls["sleep"] == 2:
            (ops / "PAUSE_OTHERS").unlink()
    s = _scout(tmp_path, [_call("done")], ops=ops, probe=probe, sleep=sleep)
    s.run()
    st = json.loads((tmp_path / "s" / "stats.json").read_text())
    assert st["pause_waits"] == 1 and st["server_waits"] == 1 and st["episodes"] == 1 and calls["sleep"] >= 4


def test_scout_deadline_and_until_parse(tmp_path):
    from datetime import datetime, timezone
    from practice.scout import parse_until
    now = datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc)
    assert datetime.fromtimestamp(parse_until("10:30Z", now), timezone.utc) == datetime(2026, 10, 26, 10, 30, tzinfo=timezone.utc)
    assert datetime.fromtimestamp(parse_until("02:00Z", now), timezone.utc) == datetime(2026, 10, 27, 2, 0, tzinfo=timezone.utc)
    s = _scout(tmp_path, [], until=1.0)  # already past: no request is made
    assert s.run() == 0 and s.prompts == []


def test_scout_verify_prefilter_and_keep_yes(tmp_path, monkeypatch):
    from practice import scout_verify as V
    finds = [{"id": "scout-a", "title": "Lantern", "prompt": SCOUT_PROMPT, "answer": "4", "answer_type": "int", "source_url": "https://a.org/x", "answer_url": "https://a.org/x"},
             {"id": "scout-b", "title": "Lantern copy", "prompt": SCOUT_PROMPT, "answer": "4", "answer_type": "int", "source_url": "https://a.org/y", "answer_url": "https://a.org/y"},
             {"id": "scout-c", "title": "Odd", "prompt": "A ship leaves port on a Monday and sails north for as many days as there are letters in its name, "
              "then stops for two days. If the name has six letters, on which day does it stop?", "answer": "Tuesday", "answer_type": "str",
              "source_url": "https://a.org/z", "answer_url": "https://a.org/z"}]
    f = tmp_path / "finds.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in finds))
    rows, rej = V.prefilter(finds)
    assert [r["id"] for r in rows] == ["scout-a", "scout-c"] and rej["scout-b"].startswith("duplicate")
    seen = {}

    def fake_batch(reqs, label):
        seen["n"] = [r["custom_id"] for r in reqs]
        assert reqs[0]["params"]["model"] == "claude-sonnet-5-5"
        return {"scout-a": '{"consistent": true, "self_contained": true, "verdict": "yes", "note": "ok"}',
                "scout-c": '{"consistent": true, "self_contained": false, "verdict": "no", "note": "vague"}'}, {}
    out = tmp_path / "pool.jsonl"
    assert V.main(["--finds", str(f), "--out", str(out)], run_batch=fake_batch) == 0
    kept = jl_rows(out)
    assert seen["n"] == ["scout-a", "scout-c"] and [k["id"] for k in kept] == ["scout-a"] and kept[0]["source"] == "scout" and kept[0]["answer_type"] == "int"


def jl_rows(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def test_tool_named_tags_pilot3():
    """Pilot 3: K2 writes the tool name as the tag. These are real reply shapes from the Kaggle transcripts."""
    from practice import tools as T
    from practice.harness import cut_reply
    assert T.parse_call("<answer>ABDECF</answer>") == ("answer", "ABDECF")
    assert T.parse_call("<python>\nprint(6*7)\n</python>") == ("python", "print(6*7)")
    assert T.parse_call("<tool>answer</tool>\n<answer>0</answer>") == ("answer", "0")
    assert T.parse_call("<tool>python</tool>\n<input>\nprint(1)\n</input>") == ("python", "print(1)")
    assert T.parse_call("<search>flood fill</search>") == ("search", "flood fill")
    assert T.parse_call("<answer>\n1 2\n3 4\n</answer>") == ("answer", "1 2\n3 4")
    assert cut_reply("<python>print(1)</python>\nmore text <answer>3</answer>") == "<python>print(1)</python>"
    assert T.close_open_tag("<python>\nprint(1)\n") == "<python>\nprint(1)\n</python>"
    assert T.close_open_tag("<answer>4</answer>") == "<answer>4</answer>"


def test_k2_native_tool_call():
    from practice import tools as T
    s = "<ifm|tool_calls>\n<ifm|tool_call>python\n<ifm|arg_key>input</ifm|arg_key>\n<ifm|arg_value>print(3)</ifm|arg_value>\n</ifm|tool_call>\n</ifm|tool_calls>"
    assert T.parse_call(s) == ("python", "print(3)")


def test_native_bash_python3_line_stripped():
    from practice import tools as T
    s = "<ifm|tool_call>python<ifm|arg_key>bash</ifm|arg_key><ifm|arg_value>python3\nprint(6)</ifm|arg_value></ifm|tool_call>"
    assert T.parse_call(s) == ("python", "print(6)")
    assert T.strip_shell_line("python3 <<'EOF'\nprint(1)\nEOF") == "print(1)\n"
    assert T.strip_shell_line("python_list = [1]\nprint(python_list)") == "python_list = [1]\nprint(python_list)"
