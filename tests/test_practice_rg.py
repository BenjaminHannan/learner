"""Practice-2 (Reasoning Gym) tests: generation, grading, answer parsing, test-set separation, stage-0 pick, lesson dedup, Mac driver with stubs."""
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("reasoning_gym")
from practice import lessons, rg_pool as R, tools  # noqa: E402
from practice.grade import check  # noqa: E402
from tests.test_practice import StubTok, _mac_fixture  # noqa: E402


def test_generation_deterministic_and_json():
    for t in R.CANDIDATES:
        a, b = R.make_puzzles(t, 3, 1001), R.make_puzzles(t, 3, 1001)
        assert a == b and json.loads(json.dumps(a)) == a
        assert a[0]["id"] == f"rg-{t}-1001-0" and a[0]["kind"] == t and a[0]["src"] == "rg" and a[0]["answer_type"] == "str"
        assert all(R.grade(p, p["answer"]) for p in a)
    d1, d2 = R.make_puzzles("countdown", 20, 1001), R.make_puzzles("countdown", 20, 1002)
    assert not {p["prompt"] for p in d1} & {p["prompt"] for p in d2}  # consecutive day seeds do not share puzzles


def test_countdown_grading():
    p = R.make_puzzles("countdown", 1, 1001)[0]
    nums, target = p["entry"]["metadata"]["numbers"], p["entry"]["metadata"]["target"]
    assert R.grade(p, p["answer"]) and check(p, p["answer"])
    assert not R.grade(p, "1+1") and not check(p, None) and not R.grade(p, "garbage ((")
    # an alternative valid expression: search for one different from the reference
    import itertools
    alt = None
    for perm in itertools.permutations(nums):
        for ops in itertools.product("+-*", repeat=len(nums) - 1):
            e = str(perm[0])
            for o, n in zip(ops, perm[1:]):
                e += f"{o}{n}"
            try:
                if eval(e) == target and e.replace(" ", "") != p["answer"].replace(" ", ""):  # noqa: S307
                    alt = e
                    break
            except ZeroDivisionError:
                pass
        if alt:
            break
    if alt:
        assert R.grade(p, alt)


def test_grid_answer_survives_parsing():
    p = R.make_puzzles("mini_sudoku", 1, 1001)[0]
    call = tools.parse_call(f"Done.\n<answer>\n{p['answer']}\n</answer>")
    assert call[0] == "answer" and "\n" in call[1] and R.grade(p, call[1])
    assert check(p, call[1])
    assert tools.user_prompt(p) == p["prompt"]  # no answer-type hint for RG puzzles
    assert tools.user_prompt({"prompt": "q", "answer_type": "int"}).endswith("(The final answer is an integer.)")


def test_test_set_excludes_practice_questions():
    day = R.make_puzzles("family_relationships", 200, 1001)
    ex = {p["prompt"] for p in day}
    ts = R.test_set("family_relationships", 50, 9999, ex)
    assert len(ts) == 50 and not {p["prompt"] for p in ts} & ex
    assert len({p["prompt"] for p in ts}) == 50
    assert R.test_set("family_relationships", 50, 9999, ex) == ts


def test_pick_skills():
    s = {"a": 0.05, "b": 0.28, "c": 0.45, "d": 0.62, "e": 0.33}
    assert R.pick_skills(s) == (["b", "e"], "")
    picked, note = R.pick_skills({"a": 0.0, "b": 0.3, "c": 0.9})
    assert picked == ["b", "a"] and "only 1" in note


def _store():
    msgs = lambda n: [{"role": "user", "content": "q"}, {"role": "assistant", "content": "x" * n}]  # noqa: E731
    out = []
    for i in range(10):
        for k, (ok, n) in enumerate([(True, 400), (True, 40), (False, 100), (i % 2 == 0, 100)]):
            out.append({"id": f"p{i}", "try": k, "correct": ok, "messages": msgs(n)})
    return out


def test_lesson_dedup():
    items, st = lessons.build_lessons("P", _store(), StubTok(), 1, 1, 700, 2, 300, dedup=True)
    assert st["sft_unique"] == 10 and st["sft_examples"] == 20 and st["pairs"] == 10 and st["sft_correct_frac"] == 1.0
    sft = [i for i in items if i["kind"] == "sft"]
    assert all(len(i["target"][1]["content"]) == 40 for i in sft)  # shortest win per puzzle
    _, sc = lessons.build_lessons("C", _store(), StubTok(), 1, 1, 10, 2, 10, dedup=True)
    assert sc["sft_examples"] == 20 and sc["pairs"] == 10
    assert lessons.steps_for(100) == 32 and lessons.steps_for(1700) == 94 and lessons.steps_for(10 ** 6) == lessons.RG_MAX_STEPS


def test_job_cli_parses():
    from practice import job
    with pytest.raises(SystemExit):
        job.main(["--help"])


def test_mac_rg_pilot_with_stubs(tmp_path, monkeypatch):
    mac_run, m0 = _mac_fixture(tmp_path, monkeypatch)
    a = mac_run.parse_args(["--out", str(tmp_path / "o"), "--stage0", "--stage0-n", "3", "--rg-skills", "auto", "--rg-day-n", "4", "--rg-test-n", "3", "--tries", "2",
                            "--test-tries", "1", "--nights", "1", "--sib-n", "0", "--skip-bench", "--no-web"])
    assert a.rg and a.tries == 2
    assert mac_run.parse_args(["--out", "x", "--rg-skills", "countdown"]).tries == 4 and mac_run.parse_args(["--out", "x"]).tries == 2
    m = mac_run.MacRG(a, run=m0.sysrun, server=m0.server)
    m.locate_model = lambda: "/fake/model"
    m.bos, m.strip_bos = "", False
    m.load_tok = lambda model: StubTok()
    import random
    rng = random.Random(1)
    ans = {}
    for t in R.CANDIDATES:
        for seed in (100, 1001, 9999):
            for p in R.make_puzzles(t, 4, seed):
                ans[p["prompt"]] = p["answer"]

    class Be:
        inflight, completion_tokens, gate = 4, 0, None

        def describe(self):
            return "scripted"

        def generate(self, prompts, max_new, temperature, seed):
            outs = []
            for pr in prompts:
                q = re.search(r"<\|ifm\|im_start\|>user\n(.*?)<\|ifm\|im_end\|>", pr, re.S).group(1)
                outs.append(f"<answer>{ans.get(q, 'x') if rng.random() < 0.5 else 'zz'}</answer>")
            return outs
    m.make_backend = lambda conc: Be()

    def train(spec):
        out = Path(spec["out"])
        out.mkdir(parents=True)
        st = {"steps": spec["steps"], "items": 5, "loss_by_step": [1.0, 0.5], "seconds": 1, "peak_gb": 5.0}
        (out / "train_stats.json").write_text(json.dumps(st))
        return st
    m.train_fn = train
    monkeypatch.setattr(mac_run.WEB, "configure", lambda *a, **k: None)
    assert m.run() == 0
    root = tmp_path / "o"
    st = json.loads((root / "stage0.json").read_text())
    assert len(st["picked"]) == 2 and set(st["scores"]) == set(R.CANDIDATES)
    sk = root / st["picked"][0]
    for f in ("rgdata/day1.jsonl", "rgdata/test.jsonl", "A0/eval_A0_test.jsonl", "P/day1.jsonl", "C/day1.jsonl", "P/eval_P1_test.jsonl", "C/eval_C1_test.jsonl", "P/night1_lessons.json"):
        assert (sk / f).exists(), f
    p_l, c_l = (json.loads((sk / x / "night1_lessons.json").read_text()) for x in "PC")
    assert c_l["sft_examples"] == p_l["sft_examples"] and c_l["pairs"] <= p_l["pairs"] + 1


def test_analyze_rg_layouts(tmp_path):
    from practice import analyze_rg
    root = tmp_path / "run"
    (root).mkdir()
    (root / "stage0.json").write_text(json.dumps({"picked": ["countdown"]}))
    sd = root / "countdown"
    (sd / "rgdata").mkdir(parents=True)

    def w(path, accs, calls=2):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps({"id": f"x{i}", "try": 0, "correct": c, "tool_calls": calls, "answered": True, "tools": ["python"], "gen_tokens": 10, "kind": "countdown"}) + "\n"
                                for i, c in enumerate(accs)))
    w(sd / "P" / "eval" / "A0_test.jsonl", [i < 5 for i in range(40)])
    w(sd / "P" / "eval" / "P3_test.jsonl", [i < 20 for i in range(40)])
    w(sd / "C" / "eval" / "C3_test.jsonl", [i < 8 for i in range(40)])
    w(sd / "P" / "eval" / "A0_sibling.jsonl", [i < 5 for i in range(20)])
    w(sd / "P" / "eval" / "P3_sibling.jsonl", [i < 5 for i in range(20)], calls=1)
    w(sd / "P" / "day" / "day1.jsonl", [True, False])
    rep = analyze_rg.analyze(root, 3)
    v = rep["skills"]["countdown"]["v"]
    assert v["S1"]["diff_points"] == 37.5 and v["S1"]["passed"] and v["S2"]["passed"] and v["S3"]["passed"]
    assert rep["skills"]["countdown"]["practice_solve_rate_by_day"] == {"P1": 50.0}
    assert rep["wrong_if"] == {"P_le_A0_plus_3_on_all_skills": False, "P_below_C_on_all_skills": False}
    assert analyze_rg.holm({"a": 0.01, "b": 0.06}) == {"a": True, "b": False} and analyze_rg.holm({"a": 0.03, "b": 0.04}) == {"a": False, "b": False}


def test_oc_segments_chain_and_lessons():
    from practice import lessons as L
    from practice.oc_lessons import oc_segments, render_prompt
    sys_u = [{"role": "system", "content": "Solve."}, {"role": "user", "content": "1+5?"}]
    c1 = "<answer>6</answer>"
    rec = {"proxy_calls": [{"request_messages": sys_u, "tools_hash": None, "completion_text": c1}], "proxy_tools": {}}
    segs = oc_segments(rec, None, None, bos="")
    assert [t for _, t in segs] == [False, True] and segs[1][0].startswith(c1)
    assert segs[0][0] == render_prompt(sys_u, [], None, None)
    r = {"id": "a", "try": 0, "correct": True, "messages": sys_u, "segs": segs}
    assert L.segments(L.target_of(r)) == segs
    assert L.target_of({"messages": sys_u}) is sys_u


def test_run_tries_redoes_errored_tries(tmp_path):
    from practice import mac_run as M

    class Srv:
        stops = 0
        def stop(self): Srv.stops += 1
        def rss_mb(self): return 0

    class H:
        calls = 0
        stats = {"gen_tokens": 1, "gen_s": 1.0}
        def run(self, puzzles, tries, seed=0, on_done=None, label=""):
            H.calls += 1
            for p in puzzles:
                bad = H.calls == 1 and p["id"] == "b"
                on_done({"id": p["id"], "kind": "k", "try": 0, "correct": not bad, "end": "error" if bad else "answer", "error": "generation thread died" if bad else "",
                         "tool_calls": 1, "answered": not bad, "gen_tokens": 1, "messages": []})

    o = M.Mac.__new__(M.Mac)
    o.server, o.peak_rss_mb, o.log = Srv(), 0, lambda *a: None
    o.serve = lambda adapter: 2
    o.harness = lambda conc: H()
    f = tmp_path / "x.jsonl"
    o.run_tries(f, [{"id": "a"}, {"id": "b"}], 1, None, 1, "t")
    recs = M.jl(f)
    assert sorted(r["id"] for r in recs) == ["a", "b"] and all(r["end"] == "answer" for r in recs) and Srv.stops == 1
