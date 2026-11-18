import json, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import tricks1 as t, sheet1 as s1, sheet1_data as sd, sheet_candidates as sc

HERE = Path(__file__).parent

def mkrows(n, pre="g"):
    return [{"id": f"{pre}-{i}", "q": f"question number {i} about widgets", "gold": float(i + 1)} for i in range(n)]

# ---------------- split ----------------
def test_split_rows():
    rows = mkrows(300)
    tr, te = sd.split_rows(rows)
    assert (len(tr), len(te)) == (100, 200)
    assert not {r["id"] for r in tr} & {r["id"] for r in te}
    assert {r["id"] for r in tr + te} == {r["id"] for r in rows}
    pos = {r["id"]: i for i, r in enumerate(rows)}
    for part in (tr, te):
        assert [pos[r["id"]] for r in part] == sorted(pos[r["id"]] for r in part)
    assert (tr, te) == sd.split_rows(rows) == sd.split_rows(list(rows), seed=1, n_train=100)
    assert sd.split_rows(rows, seed=2)[0] != tr and len(sd.split_rows(rows, n_train=7)[0]) == 7

def test_split_matches_random_shuffle():
    import random
    rows = mkrows(300); ids = [r["id"] for r in rows]; random.Random(1).shuffle(ids)
    assert {r["id"] for r in sd.split_rows(rows)[0]} == set(ids[:100])

def test_saved_data_file_is_this_split():
    f = HERE / "sheet1_data.json"
    if not f.exists():
        pytest.skip("sheet1_data.json not built")
    d = json.loads(f.read_text())
    rows = sorted(d["train"] + d["test"], key=lambda r: int(r["id"].split("-")[1]))
    assert d["seed"] == 1 and len(rows) == 300 and sd.split_rows(rows) == (d["train"], d["test"])

# ---------------- pick / ci / verdict ----------------
def st(acc, tok):
    return {"accuracy": acc, "mean_tokens": tok}

def test_pick_best():
    assert s1.pick_best([st(.9, 1), st(.5, 100), st(.6, 100), st(.55, 1)]) == 2          # baseline (idx 0) never picked, even if best
    assert s1.pick_best([st(0, 1), st(.6, 300), st(.6, 200), st(.6, 250)]) == 2          # tie -> fewer tokens
    assert s1.pick_best([st(0, 1), st(.6, 200), st(.6, 200), st(.7, 900)]) == 3          # accuracy beats tokens
    assert s1.pick_best([st(0, 1), st(.6, 200), st(.6, 200), st(.5, 10)]) == 1           # full tie -> lower index
    stats = [st(0, 1), st(.5, 1), st(.6, 1), st(.9, 1), st(.7, 1)]
    assert s1.pick_best(stats, 1, 3) == 2 and s1.pick_best(stats, 3) == 3                 # range limits: quirk sheets never win the primary

def test_paired_ci():
    assert s1.paired_ci([1, 0, 1, 1] * 25, [1, 0, 1, 1] * 25) == [0, 0]
    a = [1] * 60 + [0] * 40; b = [1] * 40 + [0] * 60                                       # +20 points, nested
    lo, hi = s1.paired_ci(a, b)
    assert 0 < lo <= 0.2 <= hi and s1.paired_ci(a, b) == [lo, hi]
    lo, hi = s1.paired_ci([1, 0] * 50, [0, 1] * 50)                                        # mixed flips: CI straddles 0
    assert lo < 0 < hi
    lo, hi = s1.paired_ci(b, a); assert hi < 0

def test_verdict_thresholds():
    assert s1.verdict(5.0, 0.001) == "PASS" and s1.verdict(12.0, 0.04) == "PASS"
    assert s1.verdict(4.99, 0.5) == "INCONCLUSIVE" and s1.verdict(5.0, 0.0) == "INCONCLUSIVE" and s1.verdict(7.0, -0.01) == "INCONCLUSIVE"
    assert s1.verdict(2.0, 0.5) == "INCONCLUSIVE" and s1.verdict(1.99, 0.5) == "OUT" and s1.verdict(-3.0, -0.1) == "OUT"

# ---------------- prompt ----------------
def test_build_prompt_train_only():
    train = mkrows(30, "tr")
    test = [{"id": f"te-{i}", "q": f"SECRET TEST QUESTION {i}", "gold": 5.0 + i} for i in range(10)]
    saved = {}
    for i, r in enumerate(train):
        ok = i % 4 != 0   # 8 failures (0,4,...,28), 22 successes
        saved[r["id"]] = {"id": r["id"], "gold": r["gold"], "correct": ok, "pred": r["gold"] if ok else 777.5, "tool_calls": i % 3, "tokens": 100 + i,
                          "text": f"REPLY<{r['id']}>"}
    for r in test + mkrows(5, "other"):   # saved rows for ids outside train must be ignored
        saved[r["id"]] = {"id": r["id"], "gold": r["gold"], "correct": False, "pred": 1.0, "tool_calls": 0, "tokens": 1, "text": f"LEAK-{r['id']}"}
    p = sc.build_prompt(train, saved, "MY SHEET TEXT")
    fails = [r for r in train if not saved[r["id"]]["correct"]]
    assert len(fails) == 8 and "MY SHEET TEXT" in p and "22/30" in p and "All 8 failures" in p
    for r in fails:
        assert r["q"] in p and f"REPLY<{r['id']}>" in p and f"Gold: {int(r['gold'])}" in p
    assert "Model's parsed answer: 777.5" in p
    assert "SECRET TEST" not in p and "LEAK" not in p and not any(f"{k}-{i}" in p for k in ("other", "te") for i in range(10))
    oks = [r for r in train if saved[r["id"]]["correct"]]
    shown = [r for r in oks if r["q"] in p]
    assert len(shown) == 8 and sc.build_prompt(train, saved, "MY SHEET TEXT") == p   # 8 successes, deterministic
    assert all(f"REPLY<{r['id']}>" not in p for r in oks)    # successes: question, tool calls, tokens only
    assert "Final answer: <number>" in p and "exactly 6" in p and "200 words" in p and "JSON only" in p

def test_build_prompt_fewer_successes_than_eight():
    train = mkrows(3, "tr")
    saved = {r["id"]: {"gold": r["gold"], "correct": i == 0, "pred": None, "tool_calls": 0, "tokens": 5, "text": "x"} for i, r in enumerate(train)}
    p = sc.build_prompt(train, saved, "S")
    assert "Model's parsed answer: none" in p and "1/3" in p

def test_parse_sheets():
    arr = [{"name": f"n{i}", "sheet": f"sheet {i}. Final answer: <number>"} for i in range(6)]
    assert [x["name"] for x in sc.parse_sheets("```json\n" + json.dumps(arr) + "\n```")] == [f"n{i}" for i in range(6)]
    assert len(sc.parse_sheets("Here you go:\n" + json.dumps(arr) + "\nDone.")) == 6
    with pytest.raises(AssertionError):
        sc.parse_sheets(json.dumps(arr[:5]))
    with pytest.raises(AssertionError):
        sc.parse_sheets(json.dumps(arr[:5] + [{"name": "x", "sheet": "  "}]))
    with pytest.raises(AssertionError):
        sc.parse_sheets(json.dumps(arr[:5] + [{"name": "x", "sheet": "a" * 1601}]))

# ---------------- harness ----------------
class FakeTok:
    def apply_chat_template(self, msgs, tools=None, add_generation_prompt=True, tokenize=False, enable_thinking=False):
        return json.dumps(msgs)
    def __call__(self, texts, add_special_tokens=False):  # one "token" per word
        return {"input_ids": [[0] * len(x.split()) for x in texts]}

def test_guard_stubs_long_prompts():
    calls, over = [], [0]
    eng = lambda ps, **kw: calls.append(ps) or [[(p.upper(), 1)] for p in ps]
    g = s1.guard(eng, FakeTok(), limit=3, counter=over)
    assert g(["a b", "a b c d", "c"], n=1) == [[("A B", 1)], [("(context limit)", 0)], [("C", 1)]]
    assert calls == [["a b", "c"]] and over == [1]
    assert g(["a b c d e"]) == [[("(context limit)", 0)]] and calls == [["a b", "c"]] and over == [2]   # nothing sent when all are too long
    assert t.parse_answer("(context limit)") is None and not t.parse_tool_calls("(context limit)")

def test_messages_and_scoring_match_run_arm_set():
    rows = mkrows(3)
    seen = {}
    def mk(tag):
        def eng(prompts, **kw):
            seen.setdefault(tag, []).append((prompts, kw))
            return [[("Final answer: 2", 4)] for _ in prompts]
        return eng
    ref = t.run_arm_set("py", "gsmh", rows, mk("ref"), FakeTok())
    got = s1.run_split([("baseline", t.PY_SYS)], rows, mk("got"), FakeTok())[0]
    assert seen["ref"] == seen["got"] and got == ref
    assert [r["correct"] for r in got] == [False, True, False]

def fake_engine(log):
    gold = {}
    def eng(prompts, **kw):
        log.append((len(prompts), kw))
        outs = []
        for p in prompts:
            m = json.loads(p); q = m[1]["content"].split("\n\n")[0]; g = int(q.split()[2]) + 1   # "question number i about widgets" -> gold i+1
            sysm = m[0]["content"]
            if sysm == t.PY_SYS:
                outs.append([(f"Final answer: {g + 1}", 7)])
            elif sysm == "SHEET A":
                outs.append([(f"<tool_call>\n<function=python>\n<parameter=code>\nprint({g})\n</parameter>\n</function>\n</tool_call>", 10)] if m[-1]["role"] == "user"
                             else [("Final answer: " + m[-1]["content"], 5)])
            else:   # SHEET B: right on even question numbers only
                outs.append([(f"Final answer: {g if (g - 1) % 2 == 0 else g + 1}", 3)])
        return outs
    return eng

def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data.json"; data.write_text(json.dumps({"seed": 1, "train": mkrows(4), "test": mkrows(6)}))
    sheets = tmp_path / "sheets.json"; sheets.write_text(json.dumps({"sheets": [{"name": "alpha", "sheet": "SHEET A"}, {"name": "beta", "sheet": "SHEET B"}]}))
    out = tmp_path / "out" / "sheet1"; log = []
    monkeypatch.setattr(t, "make_engine", lambda model: (fake_engine(log), FakeTok()))
    argv = ["sheet1.py", "--data", str(data), "--sheets", str(sheets), "--out", str(out), "--extra", ""]
    monkeypatch.setattr(sys, "argv", argv)
    s1.main()
    # phase 1: one batched call per round (3 sheets x 4 rows, then only sheet A's 4 tool users); phase 2 likewise with 6 rows
    assert [n for n, _ in log] == [12, 4, 18, 6]
    assert all(kw["temperature"] == 0.0 and kw["max_tokens"] == 2048 and kw["n"] == 1 for _, kw in log)
    for si in range(3):
        for split, n in (("train", 4), ("test", 6)):
            recs = [json.loads(l) for l in (out / f"rows_{si}_{split}.jsonl").read_text().splitlines()]
            assert len(recs) == n and set(recs[0]) == {"id", "gold", "tokens", "tool_calls", "pred", "correct", "text"}
    res = json.loads((out / "result_sheet1.json").read_text())
    assert [x["name"] for x in res["sheets"]] == ["baseline", "alpha", "beta"]
    assert [x["train"]["accuracy"] for x in res["sheets"]] == [0.0, 1.0, 0.5] and [x["test"]["accuracy"] for x in res["sheets"]] == [0.0, 1.0, 0.5]
    assert res["sheets"][1]["train"]["mean_tool_calls"] == 1 and res["sheets"][1]["test"]["mean_tokens"] == 15 and len(res["sheets"][0]["test"]["ci95"]) == 2
    assert res["best"] == {"index": 1, "name": "alpha"} and res["verdict"] == "PASS"
    assert res["primary"]["diff_points"] == 100.0 and res["primary"]["ci95_points"] == [100.0, 100.0]
    ng = res["normal_gold_rows"]
    assert ng["n"] == 6 and ng["diff_points"] == 100.0 and not ng["quirk_driven"] and res["over_limit_prompts"] == 0
    assert res["flips"] == {"wrong_to_right": [r["id"] for r in mkrows(6)], "right_to_wrong": []}
    summ = (out / "summary.txt").read_text().splitlines()
    assert len(summ) == 4 and all(l.startswith("[sum] ") for l in summ) and "verdict=PASS" in summ[-1]
    printed = capsys.readouterr().out
    assert all(l in printed for l in summ)
    # resume: result exists -> print it, no engine, no new calls
    monkeypatch.setattr(t, "make_engine", lambda model: pytest.fail("engine should not be built"))
    s1.main()
    assert json.loads(capsys.readouterr().out) == res and len(log) == 4

def test_main_limit(tmp_path, monkeypatch):
    data = tmp_path / "data.json"; data.write_text(json.dumps({"seed": 1, "train": mkrows(4), "test": mkrows(6)}))
    sheets = tmp_path / "sheets.json"; sheets.write_text(json.dumps({"sheets": [{"name": "alpha", "sheet": "SHEET A"}, {"name": "beta", "sheet": "SHEET B"}]}))
    out = tmp_path / "o"; log = []
    monkeypatch.setattr(t, "make_engine", lambda model: (fake_engine(log), FakeTok()))
    monkeypatch.setattr(sys, "argv", ["sheet1.py", "--data", str(data), "--sheets", str(sheets), "--out", str(out), "--limit", "2", "--extra", ""])
    s1.main()
    res = json.loads((out / "result_sheet1.json").read_text())
    assert (res["n_train"], res["n_test"]) == (2, 2) and [n for n, _ in log] == [6, 2, 6, 2]
    monkeypatch.setattr(sys, "argv", ["sheet1.py", "--data", str(data), "--sheets", str(sheets), "--out", str(out), "--extra", ""])
    with pytest.raises(SystemExit, match="different run"):
        s1.main()

def test_main_extra_sheets_are_exploratory_only(tmp_path, monkeypatch):
    data = tmp_path / "data.json"; data.write_text(json.dumps({"seed": 1, "train": mkrows(4), "test": mkrows(6)}))
    sheets = tmp_path / "sheets.json"; sheets.write_text(json.dumps({"sheets": [{"name": "beta", "sheet": "SHEET B"}]}))
    extra = tmp_path / "extra.json"; extra.write_text(json.dumps({"sheets": [{"name": "alpha", "sheet": "SHEET A"}]}))
    out = tmp_path / "o"; log = []
    monkeypatch.setattr(t, "make_engine", lambda model: (fake_engine(log), FakeTok()))
    monkeypatch.setattr(sys, "argv", ["sheet1.py", "--data", str(data), "--sheets", str(sheets), "--out", str(out), "--extra", str(extra)])
    s1.main()
    res = json.loads((out / "result_sheet1.json").read_text())
    assert [x["group"] for x in res["sheets"]] == ["baseline", "general", "quirk"]
    assert res["best"] == {"index": 1, "name": "beta"} and res["primary"]["diff_points"] == 50.0   # alpha (100%) is better but not eligible
    q = res["exploratory_quirk"]
    assert q["index"] == 2 and q["diff_points"] == 100.0 and q["minus_best_general_points"] == 50.0
    summ = (out / "summary.txt").read_text().splitlines()
    assert len(summ) == 5 and summ[-1].startswith("[sum] quirk best=2")

def test_build_prompt_variants():
    rows = mkrows(4); saved = {r["id"]: {"id": r["id"], "correct": i % 2 == 0, "pred": 1.0, "tool_calls": 1, "tokens": 9, "text": "x"} for i, r in enumerate(rows)}
    g, q = sc.build_prompt(rows, saved, "S", "general"), sc.build_prompt(rows, saved, "S", "quirk")
    assert "Do not write rules aimed at matching odd or wrong gold answers" in g and "Do not write rules aimed" not in q
    assert "negative, fractional or implausible" in q and sc.build_prompt(rows, saved, "S") == g
