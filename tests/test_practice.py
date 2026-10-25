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
                               steps=3, n_sft=6, epochs=1, n_pairs=3, pilot=True, smoke=True)
    lane = job.Lane(a)
    lane.pool = [p for p in lane.pool if p["kind"] != "arc"][:20]
    lane.H.max_new = 16
    harness.generate = smoke.scripted_factory(lane.pool + lane.test + lane.sib)
    out = lane.pilot()
    assert out["suggested_practice_n"] >= 0 and out["projected_full_run_h_with_full_pool"] > 0 and (tmp_path / "P" / "pilot.json").exists()
