"""Tests for run_mac.py that need no GPU. Tokenizer tests download tokenizer files from the HF hub (skipped if offline);
the run_lookup test needs mlx + mlx_lm (CPU build is enough) and is skipped otherwise. Run: python3 -m pytest tricks/mac/test_run_mac.py -q"""
import argparse, json, random, re, sys
from pathlib import Path
import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import run_mac as R

def hf_tok(repo):
    tf = pytest.importorskip("transformers")
    try:
        return tf.AutoTokenizer.from_pretrained(repo)
    except Exception as e:
        pytest.skip(f"cannot load {repo}: {type(e).__name__}")

# ---------------- scoring ----------------
def test_popqa_match_whole_word():
    assert R.popqa_match("It is Paris, France", ["paris"]) and not R.popqa_match("Rome", ["Paris", "Lyon"])
    assert not R.popqa_match("a custom answer", ["US"]) and R.popqa_match("born in the US.", ["US"])
    assert not R.popqa_match("Croatia", ["ro"]) and R.popqa_match("Actress and fashion model.", ["actor", "model"])
    assert not R.popqa_match("", ["x"]) and not R.popqa_match(None, ["x"]) and not R.popqa_match("anything", [" ", ""])

def test_popqa_match_same_as_tricks1():
    t1 = pytest.importorskip("tricks1")
    rng = random.Random(0)
    words = ["US", "us", "custom", "Paris", "St. Louis", "C++", "ro", "Croatia", "a.b", "naïve", "Ünal", "politician", "(x)", "o'neil", "journo"]
    for _ in range(500):
        text = " ".join(rng.choice(words) for _ in range(rng.randint(0, 6)))
        gold = [rng.choice(words + [" ", ""]) for _ in range(rng.randint(1, 3))]
        assert R.popqa_match(text, gold) == t1.popqa_match(text, gold), (text, gold)

def test_strip_think():
    assert R.strip_think("Paris") == "Paris" and R.strip_think("  Paris \n") == "Paris"
    assert R.strip_think("<think>\nhmm\n</think>\n\nParis") == "Paris"          # full block in the output
    assert R.strip_think("hmm, Rome? no.\n</think>\n\nParis", thinking=True) == "Paris"  # prompt opened the block
    assert R.strip_think("<think>\n\n</think>\n\nParis") == "Paris"
    assert R.strip_think("<think>Paris is maybe", thinking=False) == ""          # started thinking, never closed
    assert R.strip_think("Paris is maybe", thinking=True) == ""                  # budget ran out inside the block
    assert R.strip_think("a</think>b</think> c") == "c"
    assert not R.popqa_match(R.strip_think("Paris, no wait Rome", thinking=True), ["Paris"])  # unfinished reasoning cannot score

# ---------------- prompts ----------------
def test_prompt_qwen35():
    tok = hf_tok("Qwen/Qwen3.5-4B")
    row = {"q": "What is X's occupation?", "evidence": "X: X is a poet."}
    p = R.build_prompt(tok, R.LOOK_SYS, R.user_msg(row))
    assert p.startswith("<|im_start|>system\nAnswer the question in a few words, using the search results.<|im_end|>\n")
    assert "<|im_start|>user\nSearch results:\nX: X is a poet.\n\nQuestion: What is X's occupation?<|im_end|>\n" in p
    assert p.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n") and p.count("</think>") == 1  # enable_thinking=False; no extra prefill
    assert R.build_prompt(tok, "S", "U", thinking=True).endswith("<|im_start|>assistant\n<think>\n")
    pc = R.build_prompt(tok, R.CLOSED_SYS, R.user_msg(row, evidence=False))
    assert "Search results" not in pc and "<|im_start|>user\nWhat is X's occupation?<|im_end|>" in pc
    ids = R.encode(tok, p)
    assert ids and tok.decode(ids) == p

def test_prompt_lfm25_no_think_switch():
    tok = hf_tok("LiquidAI/LFM2.5-24B-A2B-MLX-4bit")
    raw = tok.apply_chat_template([{"role": "user", "content": "U"}], add_generation_prompt=True, tokenize=False, enable_thinking=False)
    assert raw.endswith("<|im_start|>assistant\n<think>")   # fact: the template ignores enable_thinking and always opens <think>
    p = R.build_prompt(tok, "S", "U", thinking=False)
    assert p.startswith(tok.bos_token + "<|im_start|>system\nS<|im_end|>\n") and p.endswith("<|im_start|>assistant\n<think>" + R.CLOSE_THINK)
    assert R.build_prompt(tok, "S", "U", thinking=True).endswith("<|im_start|>assistant\n<think>")  # left open for native reasoning
    ids = R.encode(tok, p)
    assert ids[0] == tok.convert_tokens_to_ids(tok.bos_token) and ids[1] != ids[0]  # BOS once, not doubled
    assert tok.decode(ids).count(tok.bos_token) == 1

def test_encode_never_doubles_bos():
    tok = hf_tok("LiquidAI/LFM2.5-24B-A2B-MLX-4bit")
    bos = tok.convert_tokens_to_ids(tok.bos_token)
    assert R.encode(tok, tok.bos_token + "hello") == tok.encode(tok.bos_token + "hello", add_special_tokens=False)
    assert R.encode(tok, tok.bos_token + "hello").count(bos) == 1
    assert R.encode(tok, "hello") == tok.encode("hello", add_special_tokens=True)

def test_prompt_through_mlx_wrapper():
    mlx_tok = pytest.importorskip("mlx_lm.tokenizer_utils")
    for repo in ("Qwen/Qwen3.5-4B", "LiquidAI/LFM2.5-24B-A2B-MLX-4bit"):
        tok = hf_tok(repo)
        w = mlx_tok.TokenizerWrapper(tok)
        assert R.build_prompt(w, "S", "U") == R.build_prompt(tok, "S", "U")
        assert R.build_prompt(w, "S", "U", thinking=True) == R.build_prompt(tok, "S", "U", thinking=True)

# ---------------- files ----------------
def rows_of(n):
    return [{"id": f"popqa-{i}", "q": f"q{i}?", "gold": [f"a{i}"], "bucket": "rare" if i < n // 2 else "pop", "evidence": f"e{i}"} for i in range(n)]

def test_read_rows_torn_line(tmp_path):
    f = tmp_path / "rows.jsonl"
    assert R.read_rows(f) == []
    f.write_text(json.dumps({"id": "a"}) + "\n" + json.dumps({"id": "b"}) + "\n" + '{"id": "c", "buc')
    assert [r["id"] for r in R.read_rows(f)] == ["a", "b"]
    assert f.read_text() == json.dumps({"id": "a"}) + "\n" + json.dumps({"id": "b"}) + "\n"  # rewritten, so appends stay clean

def test_limit_rows():
    rs = rows_of(10)
    assert R.limit_rows(rs, 0) == rs
    got = R.limit_rows(rs, 4)
    assert [r["id"] for r in got] == ["popqa-0", "popqa-1", "popqa-5", "popqa-6"]

def test_summarize():
    recs = [{"bucket": "rare", "correct": True, "pred": "x", "gtok": 10, "ptok": 100, "sec": 2.0},
            {"bucket": "rare", "correct": False, "pred": "", "gtok": 20, "ptok": 200, "sec": 2.0},
            {"bucket": "pop", "correct": True, "pred": "y", "gtok": 30, "ptok": 300, "sec": 4.0}]
    s = R.summarize(recs, {"tag": "t"})
    assert s["n"] == 3 and s["tag"] == "t" and abs(s["accuracy"] - 2 / 3) < 1e-9 and s["rare_accuracy"] == 0.5 and s["pop_accuracy"] == 1.0
    assert s["mean_gen_tokens"] == 20 and s["mean_prompt_tokens"] == 200 and s["wall_seconds"] == 8.0 and s["gen_tok_per_s"] == 7.5
    assert s["empty_answers"] == 1 and R.summarize([], {})["accuracy"] is None

def test_shipped_lookup_file():
    f = HERE / "popqa_lookup.jsonl"
    if not f.exists():
        pytest.skip("run tricks/prefetch_lookup.py first")
    rows = [json.loads(l) for l in f.open()]
    assert len(rows) == 400 and len({r["id"] for r in rows}) == 400
    assert [r["bucket"] for r in rows] == ["rare"] * 200 + ["pop"] * 200
    assert all(set(r) == {"id", "q", "gold", "bucket", "query", "evidence"} and r["q"] and r["gold"] and r["evidence"] for r in rows)
    assert not any(r["evidence"].startswith("Error:") for r in rows)

# ---------------- run_lookup end to end with a fake model/tokenizer (needs mlx, no weights) ----------------
class FakeTok:
    bos_token = None
    def apply_chat_template(self, msgs, add_generation_prompt, tokenize, enable_thinking):
        return " ".join(m["content"] for m in msgs) + (" <think>\n" if enable_thinking else " <think>\n\n</think>\n\n")
    def encode(self, s, add_special_tokens=True):  # last id carries the row index
        return list(range(len(s.split()))) + [1000 + int(re.search(r"q(\d+)\?", s).group(1))]
    def decode(self, ids):
        return " ".join(map(str, ids))

def args_for(tmp_path, **kw):
    d = dict(part="lookup", model="fake", tag="t", no_evidence=False, think="off", max_tokens=0, batch=4, limit=0, rep_penalty=1.0,
             lookup=str(tmp_path / "lookup.jsonl"), out=str(tmp_path / "out"))
    return argparse.Namespace(**{**d, **kw})

def test_run_lookup_resume_and_scoring(tmp_path, monkeypatch):
    pytest.importorskip("mlx_lm")
    rows = rows_of(120)
    (tmp_path / "lookup.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    calls, kill = [], [True]
    def fake_gen(model, tok, prompts, max_tokens, batch, sampler, procs=None):
        calls.append(len(prompts))
        if kill[0] and len(calls) == 2:
            raise KeyboardInterrupt  # killed during the second chunk
        outs = []
        for p in prompts:  # answer = the row's gold; every 3rd wrapped in a closed think block, every 7th a think block that never closes
            i = p[-1] - 1000
            outs.append(((f"<think>hmm a{i}</think>\n\na{i}" if i % 3 == 0 else f"a{i}") if i % 7 else f"<think>maybe a{i}", 5))
        return outs
    monkeypatch.setattr(R, "generate_all", fake_gen)
    a, rf = args_for(tmp_path), tmp_path / "out" / "rows_t.jsonl"
    with pytest.raises(KeyboardInterrupt):
        R.run_lookup(a, None, FakeTok())
    assert len(R.read_rows(rf)) == 50 and not (tmp_path / "out" / "result_t.json").exists()
    calls.clear(); kill[0] = False
    R.run_lookup(a, None, FakeTok())
    assert calls == [50, 20]  # only the 70 unfinished rows were generated
    done = R.read_rows(rf)
    assert [r["id"] for r in done] == [r["id"] for r in rows]
    res = json.loads((tmp_path / "out" / "result_t.json").read_text())
    unclosed = [i for i in range(120) if i % 7 == 0]
    assert res["n"] == 120 and res["empty_answers"] == len(unclosed) and res["mean_gen_tokens"] == 5 and res["mode"] == "lookup"
    assert abs(res["accuracy"] - (120 - len(unclosed)) / 120) < 1e-9
    assert res["rare_accuracy"] is not None and res["pop_accuracy"] is not None
    assert done[3]["pred"] == "a3" and done[3]["correct"] and "<think>" in done[3]["text"] and done[7]["pred"] == "" and not done[7]["correct"]
    calls.clear()
    R.run_lookup(a, None, FakeTok())
    assert calls == []  # finished run: nothing to generate
    with pytest.raises(SystemExit):  # same tag, different mode
        R.run_lookup(args_for(tmp_path, no_evidence=True), None, FakeTok())
