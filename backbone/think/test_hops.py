"""CPU tests for Addendum G (the hops bed: hplain, hloop, hloopi, hloopd, hplains, hloops): python -m pytest backbone/think/test_hops.py

Covers: build_hops.py rows (depth = chain length, the chain links object -> place, hops_path, line, chain and place counts and length do not
depend on depth, determinism, split counts, one-token names), Inject (zero W leaves the model unchanged; a non-zero W changes looped passes
only; cached decode = cache-free), hidden_multi (= hidden at the same loop count; earlier reads), the loop plans (hops_plan, plan_ratio,
hop_target), the greedy log-probability record, the max-confidence halting and oracle readouts, a short run of every hops arm end to end
(hloopd's per-row loop counts equal a fixed-count run when every row has the same depth; hloops' reads add to the loss), eval_adapter's
Inject reload, and summarize_hops' marks and outcomes on synthetic results.

Addendum I (round 2): summarize_hops' round-2 outcomes (STOPS ITSELF, WORKS ONLY, PROVED WRONG, NOT SHOWN, NOT INSTALLED, VOID, not computed), pair A's
seed-1 marks A4-A6 and the seed-0 "not a test" lines, the one-change readouts, --split fresh, and that the round-1 text still reproduces the committed
seed-0 SUMMARY_hops.txt; fresh_hops.py with eval_adapter stubbed (and once end to end on the tiny CPU model); pc_hops.sh R with ARMS / NAME and mode F in
the CPU dry-run harness.
"""
import json
import math
import random
import statistics
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_hops as H  # noqa: E402
import test_think1 as TK  # noqa: E402

K, T = TK.K, TK.T


def link(line):
    """(located item, container or "@place") names of one chain line, whichever phrasing it uses."""
    s = line.replace("[world] ", "").rstrip(".")
    if " is inside the " in s:
        a, b = s[4:].split(" is inside the ")
        return a, b
    if " holds the " in s:
        b, a = s[4:].split(" holds the ")
        return a, b
    for sep in (" is at the ", " sits by the "):
        if sep in s:
            a, p = s[4:].split(sep)
            return a, "@" + p
    raise AssertionError(line)


def test_rows_chain_and_shape():
    for d in range(1, H.MAX_DEPTH + 1):
        for i in range(30):
            r = H.make_row("validation", 0, i, d)
            ctx = r["context"].split("\n")
            assert len(ctx) == H.LINES and len(r["steps"]) == d == r["depth"] and set(r["steps"]) <= set(ctx)
            obj = r["question"][len("[question] Where is the "):-1]
            cur = obj
            for k, st in enumerate(r["steps"]):  # each step moves one link along the chain, the last one reaches the place
                a, b = link(st)
                assert a == cur, (k, st, cur)
                cur = b
            assert cur == "@" + r["answer"] and r["hops_path"] == [link(x)[1].lstrip("@") for x in r["steps"]]
            assert K.hop_target(r, d) == r["answer"] == K.hop_target(r, d + 3) and (d == 1 or K.hop_target(r, 1) == r["hops_path"][0])
            subj = [link(x)[0] for x in ctx]
            assert len(subj) == len(set(subj)), "a name is the located item of two lines"
            places = [link(x)[1] for x in ctx if link(x)[1][:1] == "@"]
            assert len(places) == H.CHAINS == len(set(places))  # CHAINS chains at every depth, each ending at its own place: no count cue
            assert sum(obj in x for x in ctx) == 1  # the object is named once
    a, b = H.make_row("train", 0, 5, 3), H.make_row("train", 0, 5, 3)
    assert a == b and a != H.make_row("train", 1, 5, 3) and a != H.make_row("dev", 0, 5, 3)


def test_length_and_wording_do_not_track_depth():
    m = {d: statistics.mean(len(H.make_row("validation", 0, i, d)["context"]) for i in range(200)) for d in range(1, H.MAX_DEPTH + 1)}
    assert max(m.values()) - min(m.values()) < 0.03 * statistics.mean(m.values()), m
    holds = {d: statistics.mean(H.make_row("validation", 0, i, d)["context"].count(" holds the ") for i in range(200)) for d in (1, H.MAX_DEPTH)}
    assert abs(holds[1] - holds[H.MAX_DEPTH]) < 1.5, holds  # phrasing is chosen per line, not per depth


def test_names_are_one_token():
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
    except Exception as e:  # no tokenizer cache offline: the build on the PC is checked by preflight instead
        import pytest
        pytest.skip(f"Qwen3.5 tokenizer not available: {e}")
    for w in (*H.OBJECTS, *H.BOXES, *H.PLACES):
        assert len(tok(" " + w, add_special_tokens=False)["input_ids"]) == 1, w
    assert not set(H.OBJECTS) & set(H.BOXES) and not set(H.BOXES) & set(H.PLACES) and not set(H.OBJECTS) & set(H.PLACES)


def test_build_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "TRAIN_N", 40)
    monkeypatch.setattr(H, "DEV_N", 8)
    monkeypatch.setattr(H, "VAL_PER_DEPTH", 3)
    assert H.main([str(tmp_path)]) == 0
    rep = json.loads((tmp_path / "HOPS_REPORT.json").read_text())
    assert rep["files"]["train"]["by_depth"] == {str(d): 10 for d in H.TRAIN_DEPTHS}
    assert rep["files"]["validation"]["by_depth"] == {str(d): 3 for d in range(1, H.MAX_DEPTH + 1)} == rep["files"]["fresh"]["by_depth"]
    val = [json.loads(x) for x in (tmp_path / "validation.jsonl").read_text().splitlines()]
    fresh = [json.loads(x) for x in (tmp_path / "fresh.jsonl").read_text().splitlines()]
    assert not {r["context"] for r in val} & {r["context"] for r in fresh}


def tiny_runner(seed=0):
    TK.fixture()
    a = TK.arm_args("a", 0, "unused")
    lm, tok = T.load_model(a, torch.device("cpu"), torch.float32)
    torch.manual_seed(seed)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)
    return T.Runner(lm), tok


def test_inject_zero_is_identity_and_heads():
    r, _ = tiny_runner()
    assert T.pass_heads(24, 8, 4, 24) == set() and T.pass_heads(24, 8, 4, 32) == {12, 16} and T.pass_heads(8, 0, 4, 16) == {4, 8}
    ids = torch.randint(4, 200, (2, 12))
    mask = torch.ones_like(ids)
    pos = (mask.cumsum(1) - 1)
    with torch.no_grad():
        want = {k: r.hidden(ids, mask, pos, order=T.block_order(r.n, r.start, k, r.size)) for k in (1, 3)}
        r.inject = T.Inject(r.cfg.hidden_size)
        for k in (1, 3):
            assert torch.equal(r.hidden(ids, mask, pos, order=T.block_order(r.n, r.start, k, r.size)), want[k]), "zero W changed the model"
        torch.nn.init.normal_(r.inject.proj.weight, std=0.5)
        assert torch.equal(r.hidden(ids, mask, pos, order=T.block_order(r.n, r.start, 1, r.size)), want[1]), "one pass has no injection"
        assert not torch.allclose(r.hidden(ids, mask, pos, order=T.block_order(r.n, r.start, 3, r.size)), want[3])


def test_inject_cache_matches_no_cache():
    """The cached decode (eval) and the cache-free path give the same greedy tokens with a non-zero W (injection reaches the virtual layers)."""
    r, tok = tiny_runner(1)
    r.inject = T.Inject(r.cfg.hidden_size)
    with torch.no_grad():
        torch.nn.init.normal_(r.inject.proj.weight, std=0.3)
    prompts = [[4 + (7 * i + j) % 150 for j in range(9 + i)] for i in range(3)]
    order = T.block_order(r.n, r.start, 3, r.size)
    with torch.no_grad():
        assert T.greedy(r, prompts, torch.device("cpu"), 1, cache=True, order=order) == T.greedy(r, prompts, torch.device("cpu"), 1, cache=False, order=order)


def test_hidden_multi_matches_hidden():
    r, _ = tiny_runner(3)
    ids = torch.randint(4, 200, (2, 10))
    mask = torch.ones_like(ids)
    pos = mask.cumsum(1) - 1
    for inj in (False, True):
        if inj:
            r.inject = T.Inject(r.cfg.hidden_size)
            with torch.no_grad():
                torch.nn.init.normal_(r.inject.proj.weight, std=0.3)
        with torch.no_grad():
            hs = r.hidden_multi(ids, mask, pos, 3, {1, 2, 3})
            for k in (1, 2, 3):
                assert torch.allclose(hs[k], r.hidden(ids, mask, pos, order=T.block_order(r.n, r.start, k, r.size)), atol=1e-5), (inj, k)


def test_plans():
    rows = [dict(depth=1 + i % 4) for i in range(40)]
    p, q = K.hops_plan(rows, 7, 0, 8, 6000), K.hops_plan(rows, 7, 0, 8, 6000)
    assert p == q and len(p) == 7 and all(len(st) == 8 for st in p)
    assert [list(st) for st in p] == [b for b, _ in zip(K.batches(40, 0, 8), range(7))]  # the stream train_lora draws
    assert all(rows[i]["depth"] <= r <= min(K.BR_TRAIN_MAX, rows[i]["depth"] + K.HOPS_EXTRA) for st in p for i, r in st.items())
    assert math.isclose(K.plan_ratio([{0: 1, 1: 3}], 24, 4), (24 + 32) / 48) and math.isclose(K.plan_ratio([{0: 1, 1: 3}], 24, 4, 12), (24 + 44) / 48)


def test_greedy_logp():
    r, _ = tiny_runner(2)
    prompts = [[4 + (5 * i + j) % 150 for j in range(8)] for i in range(3)]
    lp = []
    with torch.no_grad():
        a = T.greedy(r, prompts, torch.device("cpu"), 1, logp=lp)
        b = T.greedy(r, prompts, torch.device("cpu"), 1)
    assert a == b and len(lp) == 3 and all(v <= 0 for v in lp)
    with torch.no_grad():  # one prompt alone: its summed log-prob, recomputed step by step
        ids = list(prompts[0])
        want = 0.0
        for _ in range(len(a[0]) + (len(a[0]) < T.MAX_NEW)):
            x = torch.tensor([ids])
            h = r.hidden(x, torch.ones_like(x), torch.arange(len(ids))[None])
            lsm = torch.log_softmax(r.logits(h[:, -1]).float(), -1)[0]
            t = int(lsm.argmax())
            want += float(lsm[t])
            ids.append(t)
    assert math.isclose(lp[0], want, rel_tol=1e-4, abs_tol=1e-4)


def test_conf_and_oracle_readouts():
    rows = [dict(depth=1), dict(depth=2), dict(depth=3)]
    loops = (1, 2, 3)
    logps = {1: [-0.1, -2.0, -3.0], 2: [-0.5, -0.2, -2.5], 3: [-0.1, -1.0, -0.4]}
    hits = {1: ["1", "0", "0"], 2: ["0", "1", "0"], 3: ["1", "0", "1"]}
    h = K.halting_conf(rows, logps, hits, loops)
    # row 0: r1 and r3 tie at -0.1 -> fewest loops (1); row 1 -> 2; row 2 -> 3
    assert h["by_depth"]["1"]["mean_loops"] == 1 and h["by_depth"]["2"]["mean_loops"] == 2 and h["by_depth"]["3"]["mean_loops"] == 3
    assert h["acc"] == 1.0 and math.isclose(h["spearman_depth_loops"], 1.0) and math.isclose(h["mean_loops"], 2.0)
    o = K.oracle_depth(rows + [dict(depth=7)], {1: hits[1] + ["0"], 2: hits[2] + ["0"], 3: hits[3] + ["0"]})
    assert o["n"] == 3 and o["acc"] == 1.0 and o["by_depth"] == {"1": dict(n=1, acc=1.0), "2": dict(n=1, acc=1.0), "3": dict(n=1, acc=1.0)}


def hops_fixture(tmp, depths=(1, 2, 3, 4), n_train=24, per_depth=2):
    d = Path(tmp) / "hops"
    d.mkdir(parents=True, exist_ok=True)
    rows = {"train": [H.make_row("train", 0, i, depths[i % len(depths)]) for i in range(n_train)],
            "dev": [H.make_row("dev", 0, i, depths[i % len(depths)]) for i in range(4)],
            "validation": [H.make_row("validation", 0, i * 10 + k, k) for k in range(1, H.MAX_DEPTH + 1) for i in range(per_depth)]}
    for s, rs in rows.items():
        (d / f"{s}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs))
    return d


def hops_args(arm, data, out, steps=6):
    TK.fixture()
    a = K.parse(["--smoke", "--arm", arm, "--seed", "0", "--out", str(out), "--data", str(data), "--steps", str(steps), "--eval-bsz", "8"])
    a.max_len, a.bsz, a.micro_bsz, a.log_every = 256, 8, 4, 10**6
    return a


def test_hops_arms_end_to_end(tmp_path):
    data = hops_fixture(tmp_path)
    out = {}
    for arm in K.HOPS:
        a = hops_args(arm, data, tmp_path / arm)
        assert K.run_arm(a) == 0
        out[arm] = json.loads((Path(a.out) / f"result_{arm}_s0.json").read_text())
    p, lo, li, ld, ps, ls = (out[k] for k in ("hplain", "hloop", "hloopi", "hloopd", "hplains", "hloops"))
    assert p["stage1_adapter"] is None and lo["stage1_adapter"] is None
    ratio = lo["loop_schedule"]["compute_ratio"]
    assert p["steps_stage1"] == round(6 * ratio) and len(p["train"]["step_losses"]) == round(6 * ratio) and set(p["eval"]["validation"]) == {"main"}
    rs = ls["loop_schedule"]["compute_ratio"]
    assert rs > ld["loop_schedule"]["compute_ratio"] and ps["steps_stage1"] == round(6 * rs) and len(ps["train"]["step_losses"]) == round(6 * rs)
    assert ld["train"]["loops_hist_rows"] == ls["train"]["loops_hist_rows"]  # same plan
    nval = 2 * H.MAX_DEPTH
    for r in (lo, li, ld, ls):
        v = r["eval"]["validation"]
        assert {f"r{k}" for k in K.HOPS_EVAL_LOOPS} <= set(v) and all(len(v[f"r{k}"]["logp"]) == nval for k in K.HOPS_EVAL_LOOPS)
        assert set(r["eval"]["dev"]) == {f"r{K.HOPS_MAIN}", "main"} and v["main"]["hits"] == v[f"r{K.HOPS_MAIN}"]["hits"]
        assert {"halting", "halting_conf", "oracle_depth"} <= set(r) and r["oracle_depth"]["n"] == nval
    assert "inject" not in lo and f"r{K.HOPS_MAIN}_w0" not in lo["eval"]["validation"]
    for r in (li, ld, ls):
        assert r["inject"]["roundtrip_equal"] and r["inject"]["weight_norm"] > 0 and f"r{K.HOPS_MAIN}_w0" in r["eval"]["validation"]
        assert r["params_trainable"] == lo["params_trainable"] + 64 * 64
    hist = {int(k): v for k, v in ld["train"]["loops_hist_rows"].items()}
    assert sum(hist.values()) == 6 * 8 and min(hist) >= 1 and max(hist) <= 6 and "loops_hist" not in ld["train"] and ld["loop_schedule"]["plan"].startswith("depth")
    assert (tmp_path / "hloopi" / "inject.pt").exists()
    import eval_adapter as EA  # the fresh-row path: rescoring hloops' saved adapter must load its W and give the run's own answers
    q = tmp_path / "ea_hloops.json"
    assert EA.main(["--smoke", "--adapter", str(tmp_path / "hloops" / "adapter"), "--data", str(data), "--max-len", "256", "--loops", "1,6",
                    "--keep-preds", "--ref", str(tmp_path / "hloops" / "result_hloops_s0.json"), "--ref-tag", "r1", "--out", str(q)]) == 0
    e, v = json.loads(q.read_text()), ls["eval"]["validation"]
    assert e["inject"]["weight_norm"] == ls["inject"]["weight_norm"] and e["ref"]["same_hit"] == 1.0
    assert e["eval"]["r6"]["preds"] == v["r6"]["preds"] and e["eval"]["r6"]["hits"] == v["r6"]["hits"] and len(e["eval"]["r6"]["logp"]) == nval


def test_hloopd_equals_fixed_loops_when_depth_is_constant(tmp_path, monkeypatch):
    """Every train row at depth 2 and no extra loops: hloopd's per-row loop counts must give exactly the losses of hloopi run at 2 loops on every
    step; hloops' extra reads must change them (they add a loss term)."""
    data = hops_fixture(tmp_path, depths=(2,))
    plan = K.hops_plan
    monkeypatch.setattr(K, "hops_plan", lambda *x, **y: plan(*x, **(y | dict(extra=0))))
    a = hops_args("hloopd", data, tmp_path / "d")
    assert K.run_arm(a) == 0
    monkeypatch.setattr(K, "loop_schedule", lambda steps, seed, **kw: [2] * steps)
    b = hops_args("hloopi", data, tmp_path / "i")
    assert K.run_arm(b) == 0
    ld = json.loads((tmp_path / "d" / "result_hloopd_s0.json").read_text())["train"]["step_losses"]
    li = json.loads((tmp_path / "i" / "result_hloopi_s0.json").read_text())["train"]["step_losses"]
    assert ld == li and len(ld) == 6
    c = hops_args("hloops", data, tmp_path / "s")
    assert K.run_arm(c) == 0
    ls = json.loads((tmp_path / "s" / "result_hloops_s0.json").read_text())["train"]["step_losses"]
    assert ls != ld and len(ls) == 6


def test_read_loss_without_read_is_answer_loss(tmp_path):
    r, tok = tiny_runner(4)
    enc = T.Encoder(tok, 256)
    rows = [H.make_row("train", 0, i, 2) for i in range(3)]
    batch = [enc.train_example(x) for x in rows]
    r.loops = 2
    with torch.no_grad():
        a, na = K.answer_loss_fixed(r, batch, torch.device("cpu"))
        b, nb = K.answer_loss_read(r, batch, 2, None, None, torch.device("cpu"))
        c, nc = K.answer_loss_read(r, batch, 2, 1, [enc.ids(" " + K.hop_target(x, 1))[0] for x in rows], torch.device("cpu"))
    assert na == nb and torch.allclose(a, b, atol=1e-5) and nc == nb + 3 and float(c) > float(b)


def synth_results(rows, plain_deep=0.2, loop_gain=False, stops=True):
    """Result dicts for the summarizer: plain arms hit depth <= 2 always, depth 3-4 80%, deep rows plain_deep. hloop copies hplain at every
    loop count (loop_gain: from r2 on it gets every row right). hloops names hop r after loop r and the place from loop = depth on
    (stops=False: it never repeats an answer)."""
    rng = random.Random(0)
    plain = ["1" if r["depth"] <= 2 or rng.random() < (0.8 if r["depth"] <= 4 else plain_deep) else "0" for r in rows]
    loops = K.HOPS_EVAL_LOOPS
    ent = lambda h, k: dict(hits="".join(h), acc=h.count("1") / len(h), n=len(h), row_offset=0, preds=["x"] * len(h), logp=[0.0] * len(h)) | ({} if k else {})
    res = {("hplain", 0): dict(arm="hplain", seed=0, eval=dict(validation=dict(main=ent(plain, 0)))),
           ("hplains", 0): dict(arm="hplains", seed=0, eval=dict(validation=dict(main=ent(plain, 0))))}
    lv = {f"r{k}": ent(plain, k) | dict(preds=[r["answer"] if h == "1" else "x" for r, h in zip(rows, plain)]) for k in loops}
    if loop_gain:  # one pass = plain; two or more passes get every row right
        lv |= {f"r{k}": ent(["1"] * len(rows), k) | dict(preds=[r["answer"] for r in rows]) for k in loops if k > 1}
    res[("hloop", 0)] = dict(arm="hloop", seed=0, eval=dict(validation=lv | dict(main=lv["r6"])))
    sv = {}
    for k in loops:
        preds = [r["hops_path"][k - 1] if k < r["depth"] else r["answer"] if stops or k == r["depth"] else f"{r['answer']}{k}" for r in rows]
        hits = ["1" if p == r["answer"] else "0" for p, r in zip(preds, rows)]
        sv[f"r{k}"] = ent(hits, k) | dict(preds=preds, logp=[-float(k)] * len(rows))
    res[("hloops", 0)] = dict(arm="hloops", seed=0, eval=dict(validation=sv | dict(main=sv["r6"])))
    return res


def test_summarize_hops():
    import summarize_hops as SH
    rows = [H.make_row("validation", 0, d * 100 + i, d) for d in range(1, H.MAX_DEPTH + 1) for i in range(40)]
    o = SH.analyse(synth_results(rows), rows)
    assert o["A"]["validity"]["valid"] and o["A"]["outcome"].startswith("FAILS, PROVED WRONG") and not o["A"]["pass_A1"]
    b = o["B"]
    assert b["key"] == "PASS" and "seed-1 replicate" in b["outcome"] and b["pass_B1"] and b["pass_B3"] and b["pass_B4"] and b["rho"] > 0.9
    assert b["pass_V3"] and b["V3_trained_at_depth"] == 100.0 and b["next"] == SH.NEXT["PASS"]
    assert b["stable"]["loops_by_depth"]["3"] == 4 and b["stable"]["loops_by_depth"]["10"] == 11 and all(v == 100.0 for v in b["step_acc"].values())
    o2 = SH.analyse(synth_results(rows, loop_gain=True, stops=False), rows)
    assert o2["A"]["outcome"].startswith("PASS") and o2["B"]["key"] == "TOLD ONLY"  # never repeats: the stop rule runs to 12
    o3 = SH.analyse(synth_results(rows, plain_deep=0.9), rows)
    assert o3["A"]["outcome"].startswith("VOID") and o3["B"]["key"] == "VOID"
    txt = SH.report(o)
    assert "OUTCOME A" in txt and "OUTCOME B" in txt and "NEXT (fixed in Addendum G)" in txt and "floor" in txt


def test_summarize_hops_edge_outcomes():
    """The cases the review found unlabelled or mislabelled: a missing loop tag or an aborted arm (not computed), a loop that fits nothing
    (NOT INSTALLED), and B3 between +1 and +5 (not shown, never PROVED WRONG)."""
    import summarize_hops as SH
    rows = [H.make_row("validation", 0, d * 100 + i, d) for d in range(1, H.MAX_DEPTH + 1) for i in range(40)]
    res = synth_results(rows)
    del res[("hloops", 0)]["eval"]["validation"]["r11"]
    res[("hloop", 0)]["aborted"] = "test"
    o = SH.analyse(res, rows)
    assert "A" not in o and "B" not in o and "hloop aborted" in o["not_computed"]["A"] and "hloops:r11" in o["not_computed"]["B"]
    assert o["aborted"] == ["hloop"] and SH.report(o).count("OUTCOME") == 2 and "NOT COMPUTED" in SH.report(o)
    res = synth_results(rows)  # hloops wrong at every loop count: V3 fails
    for k, e in res[("hloops", 0)]["eval"]["validation"].items():
        e["hits"] = "0" * len(rows)
    assert SH.analyse(res, rows)["B"]["key"] == "NOT INSTALLED"
    res = synth_results(rows)  # near rows (80): plain right on the first 16, hloops on the first 19, at every loop count: +3.75, between the bars
    near = [i for i, r in enumerate(rows) if 5 <= r["depth"] <= 6]
    for (arm, _), r in res.items():
        first = set(near[:19 if arm == "hloops" else 16])
        for e in r["eval"]["validation"].values():
            e["hits"] = "".join(("1" if i in first else "0") if i in near else h for i, h in enumerate(e["hits"]))
    b = SH.analyse(res, rows)["B"]
    assert math.isclose(b["B1"]["value"], 3.75) and math.isclose(b["B3"]["value"], 3.75) and not b["pass_B1"] and not b["pass_B3"]
    assert b["key"] == "NOT SHOWN" and "PROVED WRONG" not in b["outcome"], b["outcome"]


def looped_eval(rows, mode, plain):
    """Per-lap entries (r1..r12 with answers and log-probs, and main) of a looped arm that behaves as `mode`:
    graded: names hop k at lap k, the place from lap = depth on (the answer-stable rule stops at depth + 1);
    fixed: wrong at lap 1, right from lap 2 on, whatever the depth (the rule stops at lap 3 for every row);
    never: right only at lap = depth, junk after it (the rule never stops: it runs to 12); plain: the plain arm's hit at every lap."""
    ent = lambda h, p, lp: dict(hits="".join(h), acc=h.count("1") / len(h), n=len(h), row_offset=0, preds=p, logp=lp)
    v = {}
    for k in K.HOPS_EVAL_LOOPS:
        if mode == "graded":
            preds = [r["hops_path"][k - 1] if k < r["depth"] else r["answer"] for r in rows]
        elif mode == "fixed":
            preds = [r["answer"] if k >= 2 else "x" for r in rows]
        elif mode == "never":
            preds = [r["hops_path"][k - 1] if k < r["depth"] else r["answer"] if k == r["depth"] else f"{r['answer']}{k}" for r in rows]
        else:
            preds = [r["answer"] if h == "1" else "x" for r, h in zip(rows, plain)]
        v[f"r{k}"] = ent(["1" if p == r["answer"] else "0" for p, r in zip(preds, rows)], preds, [-float(k)] * len(rows))
    return v | dict(main={k: x for k, x in v["r6"].items() if k != "preds"})


def synth_plain(rows, plain_deep=0.2):
    """A plain arm's hits: depth <= 2 always right, depth 3-4 80%, deeper plain_deep."""
    rng = random.Random(0)
    return ["1" if r["depth"] <= 2 or rng.random() < (0.8 if r["depth"] <= 4 else plain_deep) else "0" for r in rows]


def synth_round2(rows, seed=0, split="validation", plain_deep=0.2, **modes):
    """Result dicts at one seed: the plain arms hplain and hplains (depth <= 2 always right, depth 3-4 80%, deeper plain_deep), and each looped arm named
    in `modes` (arm -> looped_eval mode). Injection arms carry |W| and the W = 0 lesion."""
    plain = synth_plain(rows, plain_deep)
    pe = dict(hits="".join(plain), acc=plain.count("1") / len(plain), n=len(plain), row_offset=0)
    res = {(a, seed): dict(arm=a, seed=seed, eval={split: dict(main=dict(pe))}) for a in ("hplain", "hplains")}
    for arm, mode in modes.items():
        v = looped_eval(rows, mode, plain)
        r = dict(arm=arm, seed=seed, steps_stage1=4000, eval={split: v})
        if arm in ("hloopi", "hloopd", "hloops"):
            r["inject"] = dict(weight_norm=3.5)
            v["r6_w0"] = dict(hits="0" * len(rows), acc=0.0, n=len(rows), row_offset=0)
        res[(arm, seed)] = r
    return res


def val_rows(per_depth=40):
    return [H.make_row("validation", 0, d * 100 + i, d) for d in range(1, H.MAX_DEPTH + 1) for i in range(per_depth)]


def test_summarize_hops_constants_follow_think1():
    import summarize_hops as SH
    assert SH.LOOPED == K.HOPS_LOOPED and SH.LOOPS == K.HOPS_EVAL_LOOPS and SH.MAIN == f"r{K.HOPS_MAIN}" and set(SH.CONTROL) == {"hloopi", "hloopd"}
    rows = val_rows(2)
    res = synth_round2(rows, hloop="plain", hloopi="graded", hloopd="graded", hloops="graded")
    assert SH.missing({a: r for (a, _), r in res.items()}, ("hloop", "hloopi", "hloopd", "hloops", "hplain")) == []
    for arm in ("hloop", "hloopi", "hloopd", "hloops"):  # every looped arm needs r1..r12 with its answers and log-probs, not only hloop / hloops
        bad = {a: json.loads(json.dumps(r)) for (a, _), r in res.items()}
        del bad[arm]["eval"]["validation"]["r12"]
        del bad[arm]["eval"]["validation"]["r3"]["logp"]
        assert SH.missing(bad, (arm,)) == [f"{arm}:r3", f"{arm}:r12"], arm
    assert SH.missing({"hplain": {"eval": {}}}, ("hplain",)) == ["hplain:main"]  # no eval at all reads as missing, not as a crash


def test_summarize_hops_round2_outcomes():
    """Addendum I's round-2 marks: hloopi against hplain, hloopd against hplains; every outcome with its fixed next step."""
    import summarize_hops as SH
    rows = val_rows()
    run = lambda **kw: SH.analyse(synth_round2(rows, **kw), rows)
    o = run(hloopi="graded")  # laps follow depth: the answer-stable rule stops at depth + 1
    x = o["R2"]["hloopi"]
    assert x["key"] == "STOPS ITSELF" and x["works"] and x["stops_itself"] and x["pass_installed"] and x["installed"] == 100.0 and x["control"] == "hplain"
    assert x["F1"]["value"] > 50 and x["F1"]["lo"] > 0 and x["S1"]["value"] > 50 and x["rho"] > 0.9 and x["next"] == SH.NEXT2[("hloopi", "STOPS ITSELF")]
    assert x["stable"]["loops_by_depth"]["3"] == 4 and x["lesion"]["weight_norm"] == 3.5 and x["lesion"]["r6_w0"] == 0.0 and "hloopd" not in o["R2"]
    txt = SH.report(o)
    for want in ("-- round 2 (Addendum I): hloopi", "Installed: hloopi at r6", "F1 near hloopi(r6) - hplain", "S3 Spearman(depth 1-6, halting loops)",
                 "WORKS (F1 and F2): PASS;  STOPS ITSELF (S1, S2 and S3): PASS", "W = 0 lesion", "OUTCOME hloopi: hloopi STOPS ITSELF", "NEXT (fixed in Addendum I)"):
        assert want in txt, want
    o = run(hloopi="fixed")  # right from lap 2 on, but the rule stops at lap 3 for every row: works at fixed laps, no stop that follows depth
    x = o["R2"]["hloopi"]
    assert x["key"] == "WORKS ONLY" and x["works"] and not x["stops_itself"] and x["pass_S1"] and x["pass_S2"] and not x["pass_S3"] and x["rho"] is None
    assert x["next"] == SH.NEXT2[("hloopi", "WORKS ONLY")] and "read hloopd" in x["next"] and "S3: Spearman" in x["outcome"]
    o = run(hloopi="plain")  # injection arm that gains nothing over plain: F1 = 0, below +1
    x = o["R2"]["hloopi"]
    assert x["key"] == "PROVED WRONG" and not x["works"] and x["F1"]["value"] == 0.0 and x["next"] == SH.NEXT2[("hloopi", "PROVED WRONG")] and "hloop" in x["next"]
    res = synth_round2(rows, hloopi="plain")  # between the bars: near +3.75 (plain right on 16 of the 80 near rows, hloopi on 19), at every lap
    near = [i for i, r in enumerate(rows) if 5 <= r["depth"] <= 6]
    for (arm, _), r in res.items():
        first = set(near[:19 if arm == "hloopi" else 16])
        for e in r["eval"]["validation"].values():
            e["hits"] = "".join(("1" if i in first else "0") if i in near else h for i, h in enumerate(e["hits"]))
    x = SH.analyse(res, rows)["R2"]["hloopi"]
    assert math.isclose(x["F1"]["value"], 3.75) and x["key"] == "NOT SHOWN" and "PROVED WRONG" not in x["outcome"] and x["next"] == SH.NEXT2[("hloopi", "NOT SHOWN")]
    res = synth_round2(rows, hloopi="fixed")  # F1 passes (right at r6 on the near rows) but r6 is wrong on 26 of the 160 trained rows: installed (83.75), F2 fails
    train = [i for i, r in enumerate(rows) if r["depth"] <= 4]
    e = res[("hloopi", 0)]["eval"]["validation"]["r6"]
    e["hits"] = "".join("0" if i in set(train[-26:]) else h for i, h in enumerate(e["hits"]))
    x = SH.analyse(res, rows)["R2"]["hloopi"]
    assert x["pass_installed"] and x["pass_F1"] and not x["pass_F2"] and not x["stops_itself"] and x["key"] == "TRADE-OFF", x["outcome"]
    assert x["next"] == SH.NEXT2[("hloopi", "TRADE-OFF")] and "fixes no step" in x["next"] and "gain held" in x["next"] and "loses its fixed-lap gain" not in x["next"]
    assert "F2 fails" in x["outcome"] and "loses more than 2 points on the trained depths" in x["outcome"] and x["F2"]["value"] < -2
    res = synth_round2(rows, hloopi="graded")  # zero everywhere: the loop is not installed
    for e in res[("hloopi", 0)]["eval"]["validation"].values():
        e["hits"] = "0" * len(rows)
    x = SH.analyse(res, rows)["R2"]["hloopi"]
    assert x["key"] == "NOT INSTALLED" and x["installed"] == 0.0 and "not a refutation" in x["outcome"] and x["next"] == SH.NEXT2[("hloopi", "NOT INSTALLED")]
    assert SH.analyse(synth_round2(rows, plain_deep=0.9, hloopi="graded", hloopd="graded"), rows)["R2"]["hloopi"]["key"] == "VOID"  # the control fails V2
    o = run(hloopd="graded")  # hloopd against hplains, installed at r = depth
    x = o["R2"]["hloopd"]
    assert x["key"] == "STOPS ITSELF" and x["control"] == "hplains" and x["installed_rule"] == "at r = depth" and x["installed"] == 100.0
    assert x["near_depth_minus_control"]["value"] > 50 and "hloopi" not in o["R2"] and x["next"] == SH.NEXT2[("hloopd", "STOPS ITSELF")]
    assert "no mark: near r = depth - hplains" in SH.report(o) and "OUTCOME hloopd: hloopd STOPS ITSELF" in SH.report(o)
    x = run(hloopd="never")["R2"]["hloopd"]  # right only at r = depth, the rule runs to 12
    assert x["key"] == "DOES NOT STOP ITSELF" and x["pass_installed"] and not x["stops_itself"] and not x["works"] and "does not WORK at fixed laps either" in x["outcome"]
    assert x["next"] == SH.NEXT2[("hloopd", "DOES NOT STOP ITSELF")] and "pair B's seed-1 replicate" in x["next"] and x["stable"]["loops_by_depth"]["3"] == 12
    o = run(hloopi="graded", hloopd="never")
    assert o["R2"]["hloopi"]["key"] == "STOPS ITSELF" and o["R2"]["hloopd"]["key"] == "DOES NOT STOP ITSELF" and SH.report(o).count("-- round 2 (Addendum I)") == 2
    o = run()  # neither round-2 arm: no section
    assert o["R2"] == {} and o["readouts"] == {} and "round 2" not in SH.report(o) and "readouts" not in SH.report(o)


def test_summarize_hops_round2_not_computed():
    import summarize_hops as SH
    rows = val_rows()
    res = synth_round2(rows, hloopi="graded", hloopd="graded")
    del res[("hplain", 0)]  # hloopi's control is gone
    o = SH.analyse(res, rows)
    assert "hloopi" not in o["R2"] and o["not_computed"]["hloopi"] == "hplain missing" and o["R2"]["hloopd"]["key"] == "STOPS ITSELF"
    txt = SH.report(o)
    assert "-- round 2: hloopi vs hplain: not computed (hplain missing)" in txt and "OUTCOME hloopi: not computed" in txt and "OUTCOME hloopd: hloopd STOPS" in txt
    res = synth_round2(rows, hloopi="graded", hloopd="graded")
    del res[("hloopd", 0)]["eval"]["validation"]["r11"]  # a lap count missing
    del res[("hloopi", 0)]["eval"]["validation"]["r3"]["preds"]  # answers missing
    o = SH.analyse(res, rows)
    assert o["R2"] == {} and o["not_computed"]["hloopd"] == "hloopd:r11" and o["not_computed"]["hloopi"] == "hloopi:r3"
    res = synth_round2(rows, hloopi="graded", hloopd="graded")
    res[("hloopd", 0)]["aborted"] = "test"
    o = SH.analyse(res, rows)
    assert o["aborted"] == ["hloopd"] and o["not_computed"]["hloopd"] == "hloopd aborted" and o["R2"]["hloopi"]["key"] == "STOPS ITSELF" and "hloopd" not in o["arms"]
    assert "not computed (hloopd aborted)" in SH.report(o) and "ABORTED: hloopd" in SH.report(o)
    assert "hloopd" not in SH.analyse(synth_round2(rows, hloopi="graded"), rows)["not_computed"]  # an arm that was never run is not a gap


def test_summarize_hops_pair_a_stop_marks():
    """Pair A at seed >= 1: A1-A3 label REPLICATES, A4-A6 label STOPS ITSELF. At seed 0 A4-A6 are values only."""
    import summarize_hops as SH
    rows = val_rows()
    a = SH.analyse(synth_round2(rows, seed=1, hloop="graded"), rows, seed=1)["A"]
    assert a["stop_marked"] and a["key"] == "REPLICATES" and a["replicates"] and a["stops_itself"] and a["stop_key"] == "STOPS ITSELF"
    assert a["pass_A4"] and a["pass_A5"] and a["pass_A6"] and a["A4"]["value"] > 50 and a["A4"]["lo"] > 0 and a["A6"]["value"] > 0.9
    assert a["next"] == SH.NEXT_A["REPLICATES + STOPS ITSELF"] and a["outcome"].startswith("REPLICATES") and "seed 1" in a["outcome"]
    o = SH.analyse(synth_round2(rows, seed=1, hloop="fixed"), rows, seed=1)
    a = o["A"]
    assert a["key"] == "REPLICATES" and a["pass_A4"] and a["pass_A5"] and not a["pass_A6"] and not a["stops_itself"] and a["stop_key"] == "DOES NOT STOP ITSELF"
    assert a["stop_wrong"] == ["A6: Spearman(depth 1-6, laps) <= 0.1"] and a["next"] == SH.NEXT_A["REPLICATES"]
    txt = SH.report(o)
    for want in ("PASS A4 near halting - hplain", "PASS A5 trained halting - hplain", "FAIL A6 Spearman(depth 1-6, halting loops)", "OUTCOME A: REPLICATES",
                 "OUTCOME A (stop rule): does not stop itself (PROVED WRONG: A6", "NEXT (fixed in Addendum I): " + SH.NEXT_A["REPLICATES"]):
        assert want in txt, want
    a = SH.analyse(synth_round2(rows, seed=1, hloop="plain"), rows, seed=1)["A"]  # the fixed-lap gain is not there
    assert a["key"] == "DOES NOT REPLICATE" and not a["replicates"] and a["outcome"].startswith("DOES NOT REPLICATE, PROVED WRONG") and a["next"] == SH.NEXT_A["DOES NOT REPLICATE"]
    assert not a["pass_A4"] and a["stop_key"] == "DOES NOT STOP ITSELF"
    a = SH.analyse(synth_round2(rows, seed=1, plain_deep=0.9, hloop="graded"), rows, seed=1)["A"]
    assert a["key"] == "VOID" and a["stop_key"] == "VOID" and not a["stops_itself"] and a["next"] == SH.NEXT["VOID"]
    # seed 0 was seen before the marks were fixed: the values are printed with the note, never marked
    o = SH.analyse(synth_round2(rows, hloop="graded"), rows)
    a = o["A"]
    assert not a["stop_marked"] and "pass_A4" not in a and "stops_itself" not in a and a["A4"]["value"] > 50 and a["A6"]["value"] > 0.9 and a["outcome"].startswith("PASS: br's recipe")
    assert not {"pass_rho", "wrong_rho", "pass_A5", "pass_A6", "stop_key", "next"} & set(a) and a["rho"] > 0.9  # no PASS / FAIL-shaped flag leaks into --json at seed 0
    txt = SH.report(o).split("\n")
    lines = [x for x in txt if x.startswith(("   A4 ", "   A5 ", "   A6 "))]
    assert len(lines) == 3 and all(SH.SEED0_NOTE in x and "PASS" not in x and "FAIL" not in x for x in lines)
    assert SH.SEED0_NOTE == "seed 0: read before Addendum I's marks, not a test" and not any("OUTCOME A (stop rule)" in x for x in txt)
    # Addendum I fixes REPLICATES and A4-A6 at seed 1 only: a seed-2 run (the village reading's) gets values and no label, however seed 1 went
    for mode in ("graded", "plain"):
        o = SH.analyse(synth_round2(rows, seed=2, hloop=mode), rows, seed=2)
        a = o["A"]
        assert a["seed"] == 2 and not a["stop_marked"] and a["key"] == "NO LABEL" and "no label fixed for seed 2" in a["outcome"] and "REPLICATES" not in a["outcome"].replace("REPLICATES at seed 1", "")
        assert not {"pass_rho", "wrong_rho", "pass_A4", "pass_A5", "pass_A6", "replicates", "stops_itself", "stop_key", "next"} & set(a) and a["A4"]["value"] is not None
        txt = SH.report(o).split("\n")
        lines = [x for x in txt if x.startswith(("   A4 ", "   A5 ", "   A6 "))]
        assert len(lines) == 3 and all("no mark fixed for seed 2" in x and "PASS" not in x and "FAIL" not in x for x in lines)
        assert not any(("NEXT" in x or "STOPS ITSELF" in x or "OUTCOME A (stop rule)" in x or "OUTCOME A: REPLICATES" in x) for x in txt), txt
    a = SH.analyse(synth_round2(rows, seed=2, plain_deep=0.9, hloop="graded"), rows, seed=2)["A"]
    assert a["key"] == "VOID" and a["stop_marked"] is False and "next" not in a  # an invalid control is still void at any seed


def test_summarize_hops_a6_is_b4_s3():
    """A6, B4 and S3 are one function (rho_marks) on the answer-stable laps: the same laps give the same numbers."""
    import summarize_hops as SH
    rows = val_rows()
    o = SH.analyse(synth_round2(rows, hloop="graded", hloops="graded", hloopi="graded", hloopd="graded"), rows)
    a, b, i, d = o["A"], o["B"], o["R2"]["hloopi"], o["R2"]["hloopd"]
    for k in ("rho", "rho_lo", "rho_hi", "rho_d1_10"):
        assert a[k] == b[k] == i[k] == d[k] and a[k] is not None
    assert "pass_rho" not in a and b["pass_B4"] and i["pass_S3"] and a["A6"] == i["S3"] == {"value": a["rho"], "lo": a["rho_lo"], "hi": a["rho_hi"]}  # seed 0: A6 is a value
    a1 = SH.analyse(synth_round2(rows, seed=1, hloop="graded"), rows, seed=1)["A"]  # seed 1: the mark, from the same function
    assert a1["pass_rho"] and a1["pass_A6"] and all(a1[k] == b[k] for k in ("rho", "rho_lo", "rho_hi", "rho_d1_10"))


def test_summarize_hops_one_change_readouts():
    import numpy as np
    import summarize_hops as SH
    rows = val_rows()
    d = np.array([r["depth"] for r in rows])
    o = SH.analyse(synth_round2(rows, hloop="plain", hloopi="graded", hloopd="never", hloops="graded"), rows)
    assert set(o["readouts"]) == {"hloopi - hloop", "hloopd - hloopi", "hloops - hloopd"} and not any(" - " in k for k in o["not_computed"])
    ph = synth_plain(rows)
    plain_near = 100 * np.mean([ph[i] == "1" for i in np.flatnonzero((d >= 5) & (d <= 6))])
    r = o["readouts"]["hloopi - hloop"]
    assert r["what"] == "injection" and math.isclose(r["r6"]["near"]["value"], 100 - plain_near) and math.isclose(r["stable"]["near"]["value"], 100 - plain_near)
    assert r["r6"]["near"]["lo"] is not None and r["stable"]["far"]["lo"] is not None and r["rho"]["hloopi"]["rho"] > 0.9 and r["rho"]["hloop"]["rho"] is None
    r = o["readouts"]["hloopd - hloopi"]  # never: right only at r = depth; r6 near = depth-6 rows only (half), the rule runs to 12 and is wrong there
    assert r["what"] == "laps tied to depth" and math.isclose(r["r6"]["near"]["value"], 50 - 100) and math.isclose(r["stable"]["near"]["value"], -100)
    assert o["readouts"]["hloops - hloopd"]["what"] == "graded laps" and o["readouts"]["hloops - hloopd"]["rho"]["hloops"]["rho"] > 0.9
    txt = SH.report(o)
    assert "-- one-change readouts, Addendum I (no mark" in txt and "hloopi - hloop (injection): at r6: near +" in txt and "answer-stable: near +" in txt
    assert "Spearman(depth 1-6, answer-stable laps): hloopi 1.00" in txt and "hloops - hloopd (graded laps)" in txt
    res = synth_round2(rows, hloop="plain", hloopi="graded", hloopd="never", hloops="graded")  # one arm of a readout incomplete or aborted, one never run
    del res[("hloopd", 0)]["eval"]["validation"]["r5"]
    res[("hloops", 0)]["aborted"] = "x"
    o = SH.analyse(res, rows)
    assert set(o["readouts"]) == {"hloopi - hloop"} and o["not_computed"]["hloopd - hloopi"] == "hloopd:r5" and o["not_computed"]["hloops - hloopd"] == "hloops aborted"
    assert "hloopd - hloopi (laps tied to depth): not computed (hloopd:r5)" in SH.report(o)
    assert SH.analyse(synth_round2(rows, hloopi="graded", hloops="graded"), rows)["readouts"] == {}  # no hloop / hloopd: nothing to compare


def test_summarize_hops_split_fresh(tmp_path, capsys, monkeypatch):
    """--split fresh: rows from DATA/fresh.jsonl, every eval from eval["fresh"], the header names the split; the same marks. Addendum I item 4: each mark is held
    against the same mark on validation ("held on fresh rows" / "did not hold on fresh rows"), and the validation read's OUTCOME and NEXT lines are not printed."""
    import pytest
    import summarize_hops as SH
    rows = val_rows(10)
    kw = dict(hloop="graded", hloops="graded", hloopi="fixed")
    res = synth_round2(rows, split="fresh", **kw)
    ref = SH.analyse(synth_round2(rows, **kw), rows)  # the validation read of the same arms
    o = SH.analyse(res, rows, 0, "fresh", ref)
    assert o["split"] == "fresh" and o["A"]["key"] == "PASS" and o["B"]["key"] == "PASS" and o["R2"]["hloopi"]["key"] == "WORKS ONLY"
    assert all(x.get("next") is None for x in (o["A"], o["B"], o["R2"]["hloopi"]))  # no step follows from the fresh rows
    h = o["held"]
    assert set(h) == {"A", "B", "hloopi"} and not any(g["not_held"] for g in h.values()) and h["B"]["held"] == ["V1", "V2", "V3", "B1", "B2", "B3", "B4"]
    assert h["A"]["held"] == ["V1", "V2", "A1", "A2", "A3"] and "A4" not in h["A"]["marks"]  # seed 0: A4-A6 are values
    assert h["hloopi"]["held"] == ["V1", "V2", "Installed", "F1", "F2", "S1", "S2"] and h["hloopi"]["marks"]["S3"]["status"] == "did not pass on validation: no claim either way"
    txt = SH.report(o)
    assert txt.startswith("SPLIT: fresh rows, scored once") and "seed 0, 100 fresh rows;" in txt and "validation rows" not in txt
    body = lambda t: t.split("\n", 1)[1]  # all but the SPLIT line, which names the decision lines it leaves out
    assert "NEXT" not in body(txt) and "(stop rule)" not in txt and not any(x in txt for x in ("OUTCOME A: PASS", "OUTCOME B: PASS", "OUTCOME hloopi: hloopi"))
    assert "OUTCOME B (fresh rows): every mark that passed on validation held on fresh rows" in txt and "      B1: validation PASS, fresh PASS: held on fresh rows" in txt
    assert "OUTCOME A (fresh rows)" in txt and "OUTCOME hloopi (fresh rows)" in txt and "      S3: validation FAIL, fresh FAIL: did not pass on validation" in txt
    # a mark that passed on validation and fails on the fresh rows: "did not hold on fresh rows", whatever the validation-style label of the fresh numbers is
    bad = SH.analyse(synth_round2(rows, split="fresh", hloop="graded", hloops="plain", hloopi="fixed"), rows, 0, "fresh", ref)
    assert bad["B"]["key"] == "PROVED WRONG" and bad["B"]["next"] is None and bad["held"]["B"]["not_held"] == ["B1", "B3", "B4"] and bad["held"]["B"]["held"] == ["V1", "V2", "V3", "B2"]
    txt = SH.report(bad)
    assert "OUTCOME B (fresh rows): B1, B3, B4 did not hold on fresh rows; no claim rests on it (V1, V2, V3, B2 held)" in txt
    assert "      B1: validation PASS, fresh FAIL: did not hold on fresh rows" in txt
    assert not any(x in body(txt) for x in ("PROVED WRONG", "NEXT", "retrofitting", "seed-1 replicate of hloops")) and "OUTCOME A (fresh rows): every mark" in txt
    # a mark that did not pass on validation says nothing, whatever it does on fresh rows
    up = SH.analyse(synth_round2(rows, split="fresh", hloop="graded", hloops="graded", hloopi="graded"), rows, 0, "fresh", ref)
    assert up["held"]["hloopi"]["marks"]["S3"] == {"validation": False, "fresh": True, "status": "did not pass on validation: no claim either way"}
    assert "S3" not in up["held"]["hloopi"]["held"] + up["held"]["hloopi"]["not_held"]
    # no validation read given: plain PASS / FAIL values, nothing called held or not held, no step
    solo = SH.analyse(res, rows, 0, "fresh")
    assert all(m["status"] == "no validation read to compare with" and m["validation"] is None for g in solo["held"].values() for m in g["marks"].values())
    txt = SH.report(solo)
    assert "OUTCOME B (fresh rows): no validation read of this group was given (--validation)" in txt and "NEXT" not in body(txt) and ": held on fresh rows" not in txt
    monkeypatch.setattr(SH, "mark_flags", lambda f: f)  # compare_fresh on bare flags: nothing passed on validation, so nothing for the fresh rows to confirm
    c = SH.compare_fresh({"B": {"B1": True, "B2": False}}, {"B": {"B1": False, "B2": False}})["B"]
    assert c["summary"] == "no mark passed on validation: nothing for the fresh rows to confirm" and c["held"] == c["not_held"] == []
    assert SH.compare_fresh({"B": {"B1": False}}, {"B": {"B1": True}})["B"]["summary"].startswith("B1 did not hold on fresh rows; no claim rests on it")
    monkeypatch.undo()
    assert SH.report(SH.analyse(synth_round2(rows, hloop="graded", hloops="graded"), rows)).startswith("ADDENDUM G, ROUND 1")  # validation: no split line, decisions as before
    assert "NEXT (fixed in Addendum G)" in SH.report(SH.analyse(synth_round2(rows, hloop="graded", hloops="graded"), rows)) and "held" not in SH.analyse(res, rows)
    nofresh = SH.analyse(res, rows)  # the same files read as validation: nothing there
    assert nofresh["split"] == "validation" and "A" not in nofresh and "B" not in nofresh and "hloop:main" in nofresh["not_computed"]["A"] and "hloops:r1" in nofresh["not_computed"]["B"]
    # the whole pipeline through main: FRESH/<arm>_s<seed>/result_<arm>_s<seed>.json as fresh_hops.py lays them out, VALID/ the validation runs
    for d, rs in (("fresh", res), ("valid", synth_round2(rows, **kw))):
        for (arm, seed), r in rs.items():
            (tmp_path / d / f"{arm}_s{seed}").mkdir(parents=True)
            (tmp_path / d / f"{arm}_s{seed}" / f"result_{arm}_s{seed}.json").write_text(json.dumps(r | dict(source=d)))
    (tmp_path / "data").mkdir()
    for f in ("fresh", "validation"):
        (tmp_path / "data" / f"{f}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    base = [str(tmp_path / "fresh"), "--data", str(tmp_path / "data"), "--split", "fresh"]
    assert SH.main(base + ["--validation", str(tmp_path / "valid")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("SPLIT: fresh rows") and "OUTCOME A (fresh rows): every mark" in out and "OUTCOME B (fresh rows): every mark" in out and "NEXT" not in out.split("\n", 1)[1]
    assert "      F1: validation PASS, fresh PASS: held on fresh rows" in out
    assert SH.main(base) == 0 and "no validation read" in capsys.readouterr().out
    assert SH.main(base + ["--validation", str(tmp_path / "valid"), "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["split"] == "fresh" and {"A4", "A5", "A6", "stop_marked", "rho"} <= set(j["A"]) and j["R2"]["hloopi"]["key"] == "WORKS ONLY" and "readouts" in j
    assert not {"pass_rho", "wrong_rho"} & set(j["A"])  # seed 0: A6 is a value
    assert {"F1", "F2", "S1", "S2", "S3", "works", "stops_itself", "installed", "next"} <= set(j["R2"]["hloopi"]) and j["R2"]["hloopi"]["works"] is True
    assert j["R2"]["hloopi"]["next"] is None and j["B"]["next"] is None and j["held"]["B"]["marks"]["B1"] == {"validation": True, "fresh": True, "status": "held on fresh rows"}
    with pytest.raises(SystemExit):  # DATA has no validation.jsonl for the default split, --validation needs one, and it only goes with --split fresh
        (tmp_path / "data" / "validation.jsonl").rename(tmp_path / "data" / "v.jsonl")
        SH.main([str(tmp_path / "fresh"), "--data", str(tmp_path / "data")])
    with pytest.raises(SystemExit):
        SH.main(base + ["--validation", str(tmp_path / "valid")])
    (tmp_path / "data" / "v.jsonl").rename(tmp_path / "data" / "validation.jsonl")
    with pytest.raises(SystemExit):
        SH.main([str(tmp_path / "valid"), "--data", str(tmp_path / "data"), "--validation", str(tmp_path / "valid")])
    capsys.readouterr()


def test_summarize_hops_round1_text_reproduces_committed_seed0_summary():
    """The round-1 part of the report is exactly the committed seed-0 SUMMARY_hops.txt (Addendum I's lines come after it, nothing in it moved)."""
    import pytest
    import summarize as SU
    import summarize_hops as SH
    pc = HERE.parent / "results" / "hops" / "pc"
    if not (pc / "SUMMARY_hops.txt").exists() or not list((pc / "runs").rglob("result_*.json")):
        pytest.skip("the committed seed-0 hops results are not in this checkout")
    res, _ = SU.load_results(pc / "runs")
    want = (pc / "SUMMARY_hops.txt").read_text().rstrip("\n").split("\n")
    want = want[:next(i for i, x in enumerate(want) if x.startswith("accuracy by depth")) + 1]
    got = SH.report(SH.analyse(res, H.build("validation"), 0)).split("\n")
    assert got[:len(want)] == want, [(i, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b][:3]
    assert all(x.startswith(("-- ", "   ")) for x in got[len(want):]) and any(SH.SEED0_NOTE in x for x in got[len(want):])


def _fresh_setup(tmp_path, monkeypatch, arms=("hplains", "hloops"), seeds=(0,)):
    """fresh_hops.py with eval_adapter.main stubbed: RUNS laid out as think1 saves them (adapter/, inject.pt for injection arms, the validation result), a
    tiny fresh.jsonl whose sha256 the (patched) committed report names, and a stub that writes what eval_adapter writes (r-tags with answers and log-probs
    under --loops, else main) and records its argv."""
    import fresh_hops as FH
    runs, data, calls = tmp_path / "runs", tmp_path / "data", []
    data.mkdir()
    rows = [H.make_row("validation", 0, i, 1 + i % 3) for i in range(6)]
    (data / "fresh.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    report = tmp_path / "HOPS_REPORT.json"
    report.write_text(json.dumps({"files": {"fresh": {"sha256": FH.sha256(data / "fresh.jsonl")}}}))
    monkeypatch.setattr(FH, "REPORT", report)
    for arm in arms:
        for seed in seeds:
            d, inj = runs / f"{arm}_s{seed}", arm in ("hloopi", "hloopd", "hloops")
            (d / "adapter").mkdir(parents=True)
            (d / "adapter" / "adapter_config.json").write_text("{}")
            (d / "adapter" / "adapter_model.safetensors").write_bytes(f"weights of {arm} {seed}".encode())
            if inj:
                (d / "inject.pt").write_bytes(b"W")
            (d / f"result_{arm}_s{seed}.json").write_text(json.dumps(dict(
                arm=arm, seed=seed, steps_stage1=7495 if arm == "hplains" else 4000, model="the-model", max_len=512, adapter_sha=K.adapter_sha(d / "adapter"),
                inject=dict(weight_norm=3.97, roundtrip_equal=True) if inj else None, eval={"validation": {}})))

    def stub(argv):
        g = lambda k: argv[argv.index(k) + 1]
        calls.append(argv)
        adapter, n = Path(g("--adapter")), len(rows)
        tags = [f"r{r}" for r in map(int, g("--loops").split(","))] if "--loops" in argv else ["main"]
        ent = lambda t: dict(acc=0.5, n=n, row_offset=0, by_depth={}, hits=("1" * (int(t[1:]) % 5 + 1) if t != "main" else "1").ljust(n, "0"))
        ev = {t: ent(t) | (dict(preds=[f"p{t}"] * n, logp=[-0.5] * n) if "--loops" in argv else {}) for t in tags}
        inj = adapter.parent / "inject.pt"
        Path(g("--out")).parent.mkdir(parents=True, exist_ok=True)
        Path(g("--out")).write_text(json.dumps(dict(adapter=str(adapter), adapter_sha=K.adapter_sha(adapter), n=n, env=dict(gpu="cpu"), eval=ev,
                                                    inject=dict(path=str(inj), weight_norm=3.97) if inj.exists() else None)))
        return int(getattr(stub, "rc", 0))
    monkeypatch.setattr(FH.EA, "main", stub)
    return FH, runs, data, calls, stub


def fresh_run(FH, runs, data, tmp_path, arms="hplains,hloops", seeds="0", *more):
    return FH.main([str(runs), "--data", str(data), "--out", str(tmp_path / "fresh"), "--arms", arms, "--seeds", seeds, *more])


def test_fresh_hops_shape_and_main_tag(tmp_path, monkeypatch, capsys):
    import summarize as SU
    FH, runs, data, calls, _ = _fresh_setup(tmp_path, monkeypatch, seeds=(0, 1))
    assert fresh_run(FH, runs, data, tmp_path, "hplains,hloops", "0,1") == 0
    assert [Path(c[c.index("--adapter") + 1]) for c in calls] == [runs / f"{a}_s{s}" / "adapter" for a in ("hplains", "hloops") for s in (0, 1)]
    plain, looped = calls[0], calls[2]  # eval_adapter is called as the spec says: the fresh file, 1..12 with answers kept for looped arms, one pass for plain
    g = lambda c, k: c[c.index(k) + 1]
    assert g(plain, "--file") == g(looped, "--file") == "fresh.jsonl" and Path(g(plain, "--data")) == data and g(plain, "--model") == "the-model" and g(looped, "--max-len") == "512"
    assert "--loops" not in plain and "--keep-preds" not in plain and "--smoke" not in plain
    assert g(looped, "--loops") == ",".join(map(str, range(1, 13))) == ",".join(map(str, K.HOPS_EVAL_LOOPS)) and "--keep-preds" in looped
    assert g(looped, "--out") == str(tmp_path / "fresh" / "hloops_s0" / "eval_hloops_s0.json")  # eval_adapter's own output is kept, not named result_*.json
    f = lambda arm, seed: json.loads((tmp_path / "fresh" / f"{arm}_s{seed}" / f"result_{arm}_s{seed}.json").read_text())
    keys = {"arm", "seed", "source", "steps_stage1", "inject", "adapter_sha", "data_sha256", "env", "eval"}
    p, lo = f("hplains", 1), f("hloops", 0)
    assert set(p) == set(lo) == keys and p["arm"] == "hplains" and p["seed"] == 1 and p["source"] == lo["source"] == "fresh" and set(p["eval"]) == {"fresh"}
    assert p["steps_stage1"] == 7495 and lo["steps_stage1"] == 4000 and p["inject"] is None and lo["inject"]["weight_norm"] == 3.97  # steps from the validation result
    assert p["adapter_sha"] == K.adapter_sha(runs / "hplains_s1" / "adapter") and p["data_sha256"] == FH.sha256(data / "fresh.jsonl") and p["env"] == dict(gpu="cpu")
    assert set(p["eval"]["fresh"]) == {"main"} and set(lo["eval"]["fresh"]) == {f"r{k}" for k in range(1, 13)} | {"main"}
    m, r6 = lo["eval"]["fresh"]["main"], lo["eval"]["fresh"]["r6"]  # looped main = its r6 entry without the answers, as think1 builds it
    assert "preds" not in m and m == {k: x for k, x in r6.items() if k != "preds"} and len(r6["preds"]) == 6 and len(m["logp"]) == 6
    assert all("preds" in lo["eval"]["fresh"][f"r{k}"] for k in range(1, 13))
    res, notes = SU.load_results(tmp_path / "fresh")  # summarize.load_results takes them as think1 results (and ignores eval_adapter's own files)
    assert set(res) == {(a, s) for a in ("hplains", "hloops") for s in (0, 1)} and notes == []
    assert "4 scored, 0 already done, 0 failed" in capsys.readouterr().out


def test_fresh_hops_skips_what_is_scored_and_runs_the_rest(tmp_path, monkeypatch, capsys):
    FH, runs, data, calls, _ = _fresh_setup(tmp_path, monkeypatch, seeds=(0, 1))
    assert fresh_run(FH, runs, data, tmp_path, "hplains", "0") == 0 and len(calls) == 1
    first = (tmp_path / "fresh" / "hplains_s0" / "result_hplains_s0.json").read_text()
    capsys.readouterr()
    assert fresh_run(FH, runs, data, tmp_path, "hplains,hloops", "0,1") == 0
    assert [Path(c[c.index("--adapter") + 1]).parent.name for c in calls] == ["hplains_s0", "hplains_s1", "hloops_s0", "hloops_s1"]  # hplains_s0 not scored twice
    assert (tmp_path / "fresh" / "hplains_s0" / "result_hplains_s0.json").read_text() == first
    assert "SKIPPED: hplains seed 0: already scored" in capsys.readouterr().out
    assert fresh_run(FH, runs, data, tmp_path, "hplains,hloops", "0,1") == 0 and len(calls) == 4  # all done: nothing is scored


def test_fresh_hops_refuses_other_fresh_rows(tmp_path, monkeypatch, capsys):
    FH, runs, data, calls, _ = _fresh_setup(tmp_path, monkeypatch)
    (data / "fresh.jsonl").write_text((data / "fresh.jsonl").read_text() + "\n")  # one byte more than the committed file
    assert fresh_run(FH, runs, data, tmp_path) == 2 and calls == [] and not (tmp_path / "fresh").exists()
    assert "REFUSED" in capsys.readouterr().err
    (data / "fresh.jsonl").unlink()
    assert fresh_run(FH, runs, data, tmp_path) == 2 and calls == [] and "fresh.jsonl not found" in capsys.readouterr().err


def test_fresh_hops_committed_sha_is_the_built_fresh_file(tmp_path):
    """The committed HOPS_REPORT.json names the file build_hops.py makes for fresh (seed + 1); validation rows are refused."""
    import fresh_hops as FH
    assert FH.REPORT == HERE.parent / "results" / "hops" / "HOPS_REPORT.json"
    (tmp_path / "fresh.jsonl").write_text("".join(json.dumps(r) + "\n" for r in H.build("fresh", H.SEED + 1)))
    sha, why = FH.fresh_sha(tmp_path)
    assert why is None and sha == json.loads(FH.REPORT.read_text())["files"]["fresh"]["sha256"]
    (tmp_path / "fresh.jsonl").write_text("".join(json.dumps(r) + "\n" for r in H.build("validation")))
    sha, why = FH.fresh_sha(tmp_path)
    assert sha is None and "committed HOPS_REPORT.json" in why


def test_fresh_hops_reports_a_missing_adapter_and_scores_the_rest(tmp_path, monkeypatch, capsys):
    import shutil
    FH, runs, data, calls, _ = _fresh_setup(tmp_path, monkeypatch, arms=("hplains", "hloops", "hloopi"), seeds=(0, 1))
    shutil.rmtree(runs / "hloops_s0" / "adapter")  # no adapter
    (runs / "hloopi_s1" / "inject.pt").unlink()  # eval_adapter would load no W and score the arm without it, silently
    (runs / "hplains_s1" / "result_hplains_s1.json").unlink()  # no validation result: steps_stage1 cannot be copied
    (runs / "hloopi_s0" / "adapter" / "adapter_model.safetensors").write_bytes(b"another adapter")  # not the adapter the validation result describes
    assert fresh_run(FH, runs, data, tmp_path, "hloops,hplains,hloopi", "0,1") == 1  # nonzero, after everything that could run did
    err = capsys.readouterr().err
    for want in (f"no adapter at {runs / 'hloops_s0' / 'adapter'}", f"{runs / 'hloopi_s1' / 'inject.pt'} is missing", "no validation result", "adapter_sha differs"):
        assert want in err, want
    ok = sorted(p.parent.name for p in (tmp_path / "fresh").glob("*/result_*.json"))
    assert ok == ["hloops_s1", "hplains_s0"] and len(calls) == 2  # the failures were all caught before eval_adapter ran
    stub = FH.EA.main
    stub.rc = 1  # eval_adapter itself fails: no result file for it
    (runs / "hplains_s1" / "result_hplains_s1.json").write_text(json.dumps(dict(arm="hplains", seed=1, steps_stage1=1, adapter_sha=K.adapter_sha(runs / "hplains_s1" / "adapter"), eval={})))
    assert fresh_run(FH, runs, data, tmp_path, "hplains", "1") == 1 and "eval_adapter exited 1" in capsys.readouterr().err
    assert not (tmp_path / "fresh" / "hplains_s1" / "result_hplains_s1.json").exists()
    import pytest
    with pytest.raises(SystemExit):
        fresh_run(FH, runs, data, tmp_path, "hplains,br", "0")  # not a hops arm
    capsys.readouterr()


def test_fresh_hops_scores_the_rest_when_eval_adapter_raises(tmp_path, monkeypatch, capsys):
    """eval_adapter.main raising (a corrupt adapter, CUDA out of memory, an argparse exit) or leaving junk is one failed (arm, seed), not the end of the run: the
    other arms are still scored, the exit code is 1, no result file is left for the failures (a rerun scores them), and Ctrl-C still stops everything."""
    import pytest
    FH, runs, data, calls, stub = _fresh_setup(tmp_path, monkeypatch, arms=("hplains", "hloops", "hloopi", "hplain"), seeds=(0,))
    mode = {"hplains": "oom", "hloops": "exit", "hloopi": None, "hplain": "junk"}

    def flaky(argv):
        arm = Path(argv[argv.index("--adapter") + 1]).parent.name.split("_s")[0]
        if mode[arm] == "oom":
            raise RuntimeError("CUDA out of memory")
        if mode[arm] == "exit":
            raise SystemExit(2)
        if mode[arm] == "int":
            raise KeyboardInterrupt
        rc = stub(argv)
        if mode[arm] == "junk":
            Path(argv[argv.index("--out") + 1]).write_text("{not json")
        return rc
    monkeypatch.setattr(FH.EA, "main", flaky)
    assert fresh_run(FH, runs, data, tmp_path, "hplains,hloops,hloopi,hplain", "0") == 1
    cap = capsys.readouterr()
    assert "hplains seed 0: eval_adapter raised RuntimeError('CUDA out of memory')" in cap.err and "hloops seed 0: eval_adapter raised SystemExit(2)" in cap.err
    assert "hplain seed 0: eval_adapter's output" in cap.err and "unreadable or incomplete" in cap.err and "1 scored, 0 already done, 3 failed" in cap.out
    assert sorted(p.parent.name for p in (tmp_path / "fresh").glob("*/result_*.json")) == ["hloopi_s0"]  # scored after two arms raised
    mode.update(hplains=None, hloops=None, hplain=None)  # fixed: a rerun scores the three that failed and leaves hloopi alone
    assert fresh_run(FH, runs, data, tmp_path, "hplains,hloops,hloopi,hplain", "0") == 0
    assert "3 scored, 1 already done, 0 failed" in capsys.readouterr().out
    mode["hplains"] = "int"
    (tmp_path / "fresh" / "hplains_s0" / f"result_hplains_s0.json").unlink()
    with pytest.raises(KeyboardInterrupt):
        fresh_run(FH, runs, data, tmp_path, "hplains,hloops", "0")


def test_fresh_hops_end_to_end_on_the_tiny_model(tmp_path, monkeypatch):
    """Two arms trained for a few steps, then scored by fresh_hops.py with the real eval_adapter on the tiny CPU model. The fresh file here is the validation
    file, so every tag must give the arm's own validation answers (adapter found, inject.pt loaded), and summarize_hops --split fresh must read the files."""
    import shutil
    import fresh_hops as FH
    import summarize as SU
    import summarize_hops as SH
    data = hops_fixture(tmp_path)
    shutil.copy(data / "validation.jsonl", data / "fresh.jsonl")
    (tmp_path / "HOPS_REPORT.json").write_text(json.dumps({"files": {"fresh": {"sha256": FH.sha256(data / "fresh.jsonl")}}}))
    monkeypatch.setattr(FH, "REPORT", tmp_path / "HOPS_REPORT.json")
    runs = tmp_path / "runs"
    for arm in ("hplains", "hloops"):
        assert K.run_arm(hops_args(arm, data, runs / f"{arm}_s0")) == 0
    assert FH.main([str(runs), "--data", str(data), "--out", str(tmp_path / "fresh"), "--arms", "hplains,hloops", "--seeds", "0", "--smoke"]) == 0
    v = {a: json.loads((runs / f"{a}_s0" / f"result_{a}_s0.json").read_text()) for a in ("hplains", "hloops")}
    f = {a: json.loads((tmp_path / "fresh" / f"{a}_s0" / f"result_{a}_s0.json").read_text()) for a in ("hplains", "hloops")}
    assert f["hplains"]["eval"]["fresh"]["main"]["hits"] == v["hplains"]["eval"]["validation"]["main"]["hits"] and f["hplains"]["inject"] is None
    lv, lf = v["hloops"]["eval"]["validation"], f["hloops"]["eval"]["fresh"]
    assert set(lf) == {f"r{k}" for k in K.HOPS_EVAL_LOOPS} | {"main"} and f["hloops"]["steps_stage1"] == v["hloops"]["steps_stage1"] == 6
    assert all(lf[t]["hits"] == lv[t]["hits"] for t in lf) and all(lf[f"r{k}"]["preds"] == lv[f"r{k}"]["preds"] for k in K.HOPS_EVAL_LOOPS) and "preds" not in lf["main"]
    assert f["hloops"]["inject"]["weight_norm"] == v["hloops"]["inject"]["weight_norm"] > 0 and f["hloops"]["adapter_sha"] == v["hloops"]["adapter_sha"]
    res, notes = SU.load_results(tmp_path / "fresh")
    o = SH.analyse(res, SU.load_rows(data / "fresh.jsonl"), 0, "fresh")
    assert notes == [] and o["split"] == "fresh" and "B" in o and o["B"]["lesion"] is None and "fresh rows" in SH.report(o)
    assert SH.main([str(tmp_path / "fresh"), "--data", str(data), "--split", "fresh"]) == 0


def test_spearman_numpy_matches_think1():
    import numpy as np
    import summarize_hops as SH
    rng = random.Random(3)
    for _ in range(20):
        x = [rng.randint(1, 6) for _ in range(50)]
        y = [rng.choice([1, 2, 2, 3, 12]) for _ in range(50)]
        assert math.isclose(SH.spearman(np.array(x), np.array(y)), K.spearman(x, y), abs_tol=1e-9)
    assert SH.spearman(np.array([1, 2, 3]), np.array([4, 4, 4])) is None


def test_preflight_hops_worst_case(tmp_path):
    """preflight.py --arms hloops,hplains (no stage-1 adapter): hloops forced to the largest loop count on every row, then hplains."""
    import preflight as PF
    data = hops_fixture(tmp_path)
    TK.fixture()
    assert PF.main(["--smoke", "--data", str(data), "--out", str(tmp_path / "pf"), "--arms", "hloops,hplains", "--steps", "3"]) == 0
    rep = json.loads((tmp_path / "pf" / "preflight.json").read_text())
    assert set(rep) == {"hloops", "hplains"} and all(x["final_loss"] == x["final_loss"] for x in rep.values())
    assert PF.main(["--smoke", "--data", str(data), "--out", str(tmp_path / "pf2"), "--arms", "ws"]) == 1  # a village arm still needs arm a's adapter


def _pc_stubs(tmp_path):
    """Stub build_hops / preflight / think1 / summarize_hops / fresh_hops for the pc_*.sh dry runs; think1 logs each arm, whether a race arm runs, and
    GPU-BUSY (env FAIL_ARM makes that arm fail); fresh_hops logs its arms, seeds, the runs directory it is given and GPU-BUSY (env FRESH_RC is its exit code);
    summarize_hops prints the directory it reads and the --validation one."""
    import shutil
    src, out, race, jobs = (tmp_path / x for x in ("src", "out", "race", "jobs"))
    (src / "backbone" / "think").mkdir(parents=True)
    (src / "backbone" / "results" / "hops").mkdir(parents=True)
    report = HERE.parent / "results" / "hops" / "HOPS_REPORT.json"
    shutil.copy(report, src / "backbone" / "results" / "hops" / "HOPS_REPORT.json")
    (jobs / "handoff").mkdir(parents=True)
    race.mkdir()
    busy, calls = tmp_path / "GPU-BUSY.txt", tmp_path / "calls.txt"
    busy.write_text("race-mini (sleep race, both sides) since test\n")
    stub = {"build_hops.py": f"import sys, shutil, pathlib\np = pathlib.Path(sys.argv[1]); p.mkdir(parents=True, exist_ok=True)\nshutil.copy({str(report)!r}, p / 'HOPS_REPORT.json')\n",
            "preflight.py": "import sys, pathlib\np = pathlib.Path(sys.argv[sys.argv.index('--out') + 1]); p.mkdir(parents=True, exist_ok=True)\n"
                            "(p / 'preflight.json').write_text('{}'); print('PREFLIGHT OK: stub')\n",
            "think1.py": "import sys, pathlib, subprocess\na = sys.argv; arm = a[a.index('--arm') + 1]; seed = a[a.index('--seed') + 1]; p = pathlib.Path(a[a.index('--out') + 1]); p.mkdir(parents=True, exist_ok=True)\n"
                         f"racing = subprocess.run(['pgrep', '-f', {str(race / 'race_mini.py')!r}], capture_output=True).stdout.strip() != b''\n"
                         f"open({str(calls)!r}, 'a').write(f'{{arm}} racing={{racing}} busy={{open({str(busy)!r}).read().strip()}} seed={{seed}}\\n')\n"
                         "import os\nif os.environ.get('FAIL_ARM') == arm: sys.exit(3)\n"
                         "(p / f'result_{arm}_s{seed}.json').write_text('{}')\n",
            "summarize_hops.py": "import sys, pathlib\na = sys.argv\nprint('OUTCOME B: stub, seed', a[a.index('--seed') + 1])\nprint('split', a[a.index('--split') + 1] if '--split' in a else 'validation')\n"
                                 "print('reads', pathlib.Path(a[1]).name)\nprint('validation', pathlib.Path(a[a.index('--validation') + 1]).name if '--validation' in a else '-')\n",
            "fresh_hops.py": "import os, sys, pathlib\na = sys.argv\ng = lambda k: a[a.index(k) + 1]\n"  # logs the call and GPU-BUSY, writes one result file per arm and seed
                             f"open({str(calls)!r}, 'a').write(f'fresh arms={{g(\"--arms\")}} seeds={{g(\"--seeds\")}} runs={{pathlib.Path(a[1]).name}} data={{pathlib.Path(g(\"--data\")).name}} '\n"
                             f"                                f'busy={{open({str(busy)!r}).read().strip()}}\\n')\n"
                             "for arm in g('--arms').split(','):\n    for s in g('--seeds').split(','):\n"
                             "        d = pathlib.Path(g('--out')) / f'{arm}_s{s}'; d.mkdir(parents=True, exist_ok=True); (d / f'result_{arm}_s{s}.json').write_text('{}')\n"
                             "sys.exit(int(os.environ.get('FRESH_RC', '0')))\n"}
    for name, body in stub.items():
        (src / "backbone" / "think" / name).write_text(body)
    return src, out, race, jobs, busy, calls


def test_pc_hops_pauses_race_mini_and_hands_back(tmp_path):
    """pc_hops.sh B, dry run with stub scripts: it pauses a fake race-mini driver, waits for the running race arm to end, runs pair B with no
    race arm running and its own GPU-BUSY line, then puts race-mini's line back, writes HOPS-B-DONE and resumes the driver, which finishes."""
    import subprocess
    import time
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    (race / "race_mini.py").write_text("import time\ntime.sleep(3)\n")
    (race / "pc_race_mini.sh").write_text(f"for i in 1 2 3; do python3 {race}/race_mini.py $i; echo \"arm $i done\" >> {race}/job.log; done\n"
                                          f"echo end >> {race}/job.log\n")
    drv = subprocess.Popen(["bash", str(race / "pc_race_mini.sh")])
    try:
        time.sleep(1)  # race arm 1 is running
        env = dict(**__import__("os").environ, JOBS=str(jobs), BUSY=str(busy), CDRIVE=str(tmp_path), RACE_LOG=str(race / "job.log"), PY=sys.executable,
                   MIN_FREE_MB="1", POLL="1")
        r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "B", str(src), str(out)], env=env, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stdout + r.stderr
        drv.wait(timeout=60)
    finally:
        drv.kill()
    lines = calls.read_text().splitlines()
    assert [x.split()[0] for x in lines] == ["hplains", "hloops"] and all("racing=False" in x and "busy=hops pair B" in x for x in lines), lines
    assert busy.read_text().startswith("race-mini (sleep race, both sides) resumed") and (jobs / "handoff" / "HOPS-B-DONE").read_text().startswith("0 ")
    assert (race / "job.log").read_text().split("\n")[:4] == ["arm 1 done", "arm 2 done", "arm 3 done", "end"] and not (jobs / "hops-B.md").exists()
    log = (out / "pairB.log").read_text()
    assert log.index("paused") < log.index("start hplains") < log.index("resumed") and "OUTCOME B: stub" in log


def test_pc_hops_pair_a_runs_b_first_and_hands_to_race_mini(tmp_path):
    """pc_hops.sh A with DONE_FLAG=handoff/GO-RACE-MINI (PC order of 19:35Z Oct 27): on GO-LOOP-P1 it runs pair B (never run) and then pair A
    under its own GPU-BUSY line, empties GPU-BUSY, then writes GO-RACE-MINI reading 0 and HOPS-A-DONE, and never SEG2-DONE."""
    import os
    import subprocess
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    busy.write_text("")
    (jobs / "handoff" / "GO-LOOP-P1").write_text("go\n")
    env = dict(**os.environ, JOBS=str(jobs), BUSY=str(busy), CDRIVE=str(tmp_path), PY=sys.executable, MIN_FREE_MB="1", POLL="1",
               DONE_FLAG=str(jobs / "handoff" / "GO-RACE-MINI"))
    r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "A", str(src), str(out)], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = calls.read_text().splitlines()
    assert [x.split()[0] for x in lines] == ["hplains", "hloops", "hplain", "hloop"] and all("busy=hops pair A" in x for x in lines), lines
    assert busy.read_text() == "" and not (jobs / "hops-A.md").exists()
    assert (jobs / "handoff" / "GO-RACE-MINI").read_text().startswith("0 ") and (jobs / "handoff" / "HOPS-A-DONE").read_text().startswith("0 ")
    assert not (jobs / "think2-p1" / "SEG2-DONE").exists()


def test_pc_hops_replicate_holds_race_mini_back(tmp_path):
    """The seed-1 slot (coordinator, 04:48Z Oct 28): a directory named GO-RACE-MINI holds race-mini back, so pair A's write of that flag fails
    while HOPS-A-DONE is still written; pc_hops.sh R then waits for HOPS-A-DONE and an empty GPU-BUSY, runs pair B at seed 1 under its own
    GPU-BUSY line, writes SUMMARY_hops_s1.txt, empties GPU-BUSY, writes HOPS-S1-DONE, then swaps the directory for the GO-RACE-MINI file."""
    import os
    import subprocess
    import time
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    hand = jobs / "handoff"
    busy.write_text("")
    (hand / "GO-RACE-MINI").mkdir()
    env = _pc_r_env(tmp_path, jobs, busy)  # NAME=BENSPC, ARMS=hplain, SEEDS="9 z" are in the environment, as a WSL shell may have them: none of them is read
    renv = dict(env, GO_FLAG=str(hand / "HOPS-A-DONE"), DONE_FLAG=str(hand / "HOPS-S1-DONE"), THEN_FLAG=str(hand / "GO-RACE-MINI"))
    with subprocess.Popen(["bash", str(HERE / "pc_hops.sh"), "R", str(src), str(out)], env=renv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as rp:
        time.sleep(3)
        assert rp.poll() is None and not calls.exists()  # waiting for pair A
        (hand / "GO-LOOP-P1").write_text("go\n")
        a = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "A", str(src), str(out)], env=dict(env, DONE_FLAG=str(hand / "GO-RACE-MINI")),
                           capture_output=True, text=True, timeout=120)
        assert a.returncode == 0 and "Is a directory" in a.stderr, a.stdout + a.stderr
        assert (hand / "HOPS-A-DONE").read_text().startswith("0 ") and (hand / "GO-RACE-MINI").is_dir()
        rp.wait(timeout=120)
        assert rp.returncode == 0, rp.stdout.read()
    lines = calls.read_text().splitlines()
    assert [x.split()[0] for x in lines] == ["hplains", "hloops", "hplain", "hloop", "hplains", "hloops"], lines
    assert all("seed=1" in x and "busy=hops pair R seed 1" in x for x in lines[4:]) and all("seed=0" in x for x in lines[:4]), lines
    assert busy.read_text() == "" and (hand / "HOPS-S1-DONE").read_text().startswith("0 ") and (hand / "GO-RACE-MINI").is_file()
    assert "OUTCOME B: stub, seed 1" in (out / "SUMMARY_hops_s1.txt").read_text() and (out / "runs" / "hloops_s1" / "result_hloops_s1.json").exists()
    assert "reads runs" in (out / "SUMMARY_hops_s1.txt").read_text() and sorted(x.name for x in out.glob("SUMMARY_*")) == ["SUMMARY_hops.txt", "SUMMARY_hops_s1.txt"]  # not SUMMARY_BENSPC.txt
    assert (out / "hloops_s1.log").exists() and (out / "hloops.log").exists() and not (jobs / "think2-p1" / "SEG2-DONE").exists()


def _pc_r_env(tmp_path, jobs, busy, **more):
    """The environment of an R / F dry run. NAME, ARMS and SEEDS are set to what a login shell may already hold (WSL sets NAME to the Windows computer name):
    pc_hops.sh must ignore them, its own variables are HOPS_NAME, HOPS_ARMS and HOPS_SEEDS."""
    import os
    return {**os.environ, "NAME": "BENSPC", "ARMS": "hplain", "SEEDS": "9 z", "JOBS": str(jobs), "BUSY": str(busy), "CDRIVE": str(tmp_path), "PY": sys.executable,
            "MIN_FREE_MB": "1", "POLL": "1", **more}


def test_pc_hops_replicate_runs_the_arms_it_is_given(tmp_path):
    """pc_hops.sh R with HOPS_ARMS and HOPS_NAME (Addendum I): round-2 arm hloopi at seed 0, then pair A's seed-1 replicate, each in order with no preflight and
    its own summary file and its own DONE_FLAG, never the committed SUMMARY_hops.txt / SUMMARY_hops_s1.txt (not even with no HOPS_NAME); stops at the first failing
    arm; refuses a name that is not a hops arm. The default (no HOPS_ARMS) is pair B with its preflight, as before (test_pc_hops_replicate_holds_race_mini_back).
    The shell's own NAME, ARMS and SEEDS (set by _pc_r_env, as WSL sets NAME) are never read."""
    import subprocess
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    hand = jobs / "handoff"
    busy.write_text("")
    (hand / "GO").write_text("go\n")
    run = lambda **kw: subprocess.run(["bash", str(HERE / "pc_hops.sh"), "R", str(src), str(out)], env=_pc_r_env(tmp_path, jobs, busy, GO_FLAG=str(hand / "GO"), **kw),
                                      capture_output=True, text=True, timeout=120)
    r = run(HOPS_ARMS="hloopi", SEED="0", HOPS_NAME="round2_hloopi")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [x.split()[0] for x in calls.read_text().splitlines()] == ["hloopi"] and "seed=0" in calls.read_text() and "busy=hops pair R seed 0" in calls.read_text()
    assert not (out / "preflight").exists() and (out / "runs" / "hloopi_s0" / "result_hloopi_s0.json").exists() and (out / "hloopi.log").exists()
    assert "OUTCOME B: stub, seed 0" in (out / "SUMMARY_round2_hloopi.txt").read_text() and "reads runs" in (out / "SUMMARY_round2_hloopi.txt").read_text()
    assert [x.name for x in out.glob("SUMMARY_*")] == ["SUMMARY_round2_hloopi.txt"]  # not SUMMARY_hops.txt, not SUMMARY_BENSPC.txt
    assert "hops replicate seed 0 rc=0" in (hand / "HOPS-R-round2_hloopi-DONE").read_text() and not (hand / "HOPS-R-DONE").exists()  # a per-run flag
    assert busy.read_text() == "" and not (jobs / "hops-R.md").exists()
    calls.write_text("")
    r = run(HOPS_ARMS="hplain hloop", SEED="1", HOPS_NAME="pairA_s1")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = calls.read_text().splitlines()
    assert [x.split()[0] for x in lines] == ["hplain", "hloop"] and all("seed=1" in x and "busy=hops pair R seed 1" in x for x in lines)
    assert "OUTCOME B: stub, seed 1" in (out / "SUMMARY_pairA_s1.txt").read_text() and not (out / "SUMMARY_hops_s1.txt").exists() and not (out / "preflight").exists()
    assert (out / "hplain_s1.log").exists() and (out / "hloop_s1.log").exists() and (hand / "HOPS-R-pairA_s1-DONE").is_file() and not (hand / "HOPS-R-DONE").exists()
    # no HOPS_NAME with other arms: the committed names (pair B's seed-1 and seed-0 summaries) are never overwritten, the name and the flag come from the arms
    (out / "SUMMARY_hops_s1.txt").write_text("PAIR B SEED 1 SUMMARY (committed)\n")
    (out / "SUMMARY_hops.txt").write_text("PAIR B SEED 0 SUMMARY (committed)\n")
    for n in ("hplain_s1", "hloop_s1", "hloopi_s0"):  # run them again, under the default names
        (out / "runs" / n / f"result_{n}.json").unlink()
    calls.write_text("")
    assert run(HOPS_ARMS="hplain hloop", SEED="1").returncode == 0
    assert (out / "SUMMARY_hops_s1.txt").read_text() == "PAIR B SEED 1 SUMMARY (committed)\n" and "seed 1" in (out / "SUMMARY_hops_hplain-hloop_s1.txt").read_text()
    assert (hand / "HOPS-R-hops_hplain-hloop_s1-DONE").is_file() and not (hand / "HOPS-R-DONE").exists()
    assert run(HOPS_ARMS="hloopi", SEED="0").returncode == 0
    assert (out / "SUMMARY_hops.txt").read_text() == "PAIR B SEED 0 SUMMARY (committed)\n" and "seed 0" in (out / "SUMMARY_hops_hloopi.txt").read_text()
    calls.write_text("")
    r = run(HOPS_ARMS="hplain hloop hloopi", SEED="2", FAIL_ARM="hplain", THEN_FLAG=str(hand / "NEXT"))  # the first arm fails: the rest do not run
    assert r.returncode == 3, r.stdout + r.stderr
    assert [x.split()[0] for x in calls.read_text().splitlines()] == ["hplain"] and not (out / "runs" / "hloop_s2").exists()
    flag = hand / "HOPS-R-hops_hplain-hloop-hloopi_s2-DONE"
    assert flag.read_text().startswith("0 ") and "rc=3" in flag.read_text() and (hand / "NEXT").is_file() and busy.read_text() == ""
    assert (out / "SUMMARY_hops_hplain-hloop-hloopi_s2.txt").exists()  # no HOPS_NAME: a name made from the arms
    calls.write_text("")
    r = run(HOPS_ARMS="hloopi bogus", SEED="0")
    assert r.returncode == 2 and "bogus is not a hops arm" in r.stderr and calls.read_text() == ""
    r = run(HOPS_ARMS=" \t ", SEED="0")
    assert r.returncode == 2 and "names no arm" in r.stderr and calls.read_text() == ""
    r = run(HOPS_ARMS="hplains  hloops", SEED="5")  # the default pair, however spaced, is pair B with its preflight, under the default names
    assert r.returncode == 0 and (out / "preflight" / "preflight.json").exists() and [x.split()[0] for x in calls.read_text().splitlines()] == ["hplains", "hloops"]
    assert (out / "SUMMARY_hops_s5.txt").exists() and (hand / "HOPS-R-DONE").read_text().startswith("0 ") and not list(out.glob("SUMMARY_BENSPC*"))


def test_pc_hops_fresh_mode(tmp_path):
    """pc_hops.sh F (Addendum I, item 4): waits for GO_FLAG and an empty GPU-BUSY, runs fresh_hops.py once on HOPS_ARMS and HOPS_SEEDS (from OUT/runs, the arms'
    adapters) under its own GPU-BUSY line, writes SUMMARY_fresh_<name>_s<seed>.txt per seed through summarize_hops --split fresh (reading OUT/fresh, held against
    --validation OUT/runs), empties GPU-BUSY, then DONE_FLAG (reading 0 whatever happened, the exit code after it) and THEN_FLAG (a directory holding the next job
    back is replaced by the flag). A seed list that is not numbers exits 2 before the GPU is taken; tabs and newlines in the lists never glue two names together."""
    import subprocess
    import time
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    hand = jobs / "handoff"
    busy.write_text("held by someone\n")
    (hand / "NEXT").mkdir()
    env = _pc_r_env(tmp_path, jobs, busy, GO_FLAG=str(hand / "GO-FRESH"), THEN_FLAG=str(hand / "NEXT"), HOPS_ARMS="hplains hloops", HOPS_SEEDS="0 1")
    with subprocess.Popen(["bash", str(HERE / "pc_hops.sh"), "F", str(src), str(out)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as p:
        time.sleep(3)
        assert p.poll() is None and not calls.exists()  # no GO flag yet
        (hand / "GO-FRESH").write_text("go\n")
        time.sleep(3)
        assert p.poll() is None and not calls.exists()  # the flag is there, but GPU-BUSY is not empty
        busy.write_text("")
        p.wait(timeout=120)
        assert p.returncode == 0, p.stdout.read()
    assert calls.read_text().splitlines() == ["fresh arms=hplains,hloops seeds=0,1 runs=runs data=data busy=hops pair F seed 0 1 (loop thread, Addendum G) since "
                                              + calls.read_text().split(" since ")[1].strip()]  # the arms' adapters are in OUT/runs
    assert busy.read_text() == "" and not (jobs / "hops-F.md").exists() and (hand / "NEXT").is_file()
    for s in (0, 1):
        t = (out / f"SUMMARY_fresh_hops_s{s}.txt").read_text()
        assert f"OUTCOME B: stub, seed {s}" in t and "split fresh" in t and "reads fresh" in t and "validation runs" in t  # the fresh results, held against the validation ones
    assert sorted(x.name for x in out.glob("SUMMARY_*")) == ["SUMMARY_fresh_hops_s0.txt", "SUMMARY_fresh_hops_s1.txt"]  # not SUMMARY_fresh_BENSPC_*, not SUMMARY_hops.txt
    assert (out / "fresh" / "hloops_s1" / "result_hloops_s1.json").exists() and not (out / "runs" / "hplains_s0").exists()
    assert "hops fresh rows seeds 0 1 rc=0" in (hand / "HOPS-F-DONE").read_text() and (hand / "HOPS-F-DONE").read_text().startswith("0 ")  # the default pair: the default flag
    assert "after hops fresh rows" in (hand / "NEXT").read_text() and "fresh summary seed 1: OUTCOME B: stub, seed 1" in (out / "pairF.log").read_text()
    first_flag = (hand / "HOPS-F-DONE").read_text()
    out2 = tmp_path / "out2"  # HOPS_NAME, a failing fresh_hops.py (an arm without an adapter): the summaries are still written, the flag still reads 0, the code goes after it
    r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "F", str(src), str(out2)], env=dict(env, HOPS_NAME="pairB", HOPS_SEEDS="1", FRESH_RC="1", HOPS_ARMS="hloops",
                                                                                              DONE_FLAG=str(hand / "F2"), THEN_FLAG=""), capture_output=True, text=True, timeout=120)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "OUTCOME B: stub, seed 1" in (out2 / "SUMMARY_fresh_pairB_s1.txt").read_text() and not (out2 / "SUMMARY_fresh_hops_s1.txt").exists()
    assert (hand / "F2").read_text().startswith("0 ") and "rc=1" in (hand / "F2").read_text() and busy.read_text() == ""
    calls.write_text("")
    out3 = tmp_path / "out3"  # other arms, no HOPS_NAME, no DONE_FLAG: names and flag made from the arms; a tab and a newline in the lists, not a space
    r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "F", str(src), str(out3)], env=dict(env, HOPS_ARMS="hloopi\thplain", HOPS_SEEDS="0\n1", THEN_FLAG=""),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert calls.read_text().startswith("fresh arms=hloopi,hplain seeds=0,1 runs=runs ") and sorted(x.name for x in (out3 / "fresh").iterdir()) == \
        ["hloopi_s0", "hloopi_s1", "hplain_s0", "hplain_s1"]
    assert sorted(x.name for x in out3.glob("SUMMARY_*")) == ["SUMMARY_fresh_hops_hloopi-hplain_s0.txt", "SUMMARY_fresh_hops_hloopi-hplain_s1.txt"]
    assert (hand / "HOPS-F-hops_hloopi-hplain-DONE").read_text().startswith("0 ") and "seeds 0 1" in (hand / "HOPS-F-hops_hloopi-hplain-DONE").read_text()
    assert (hand / "HOPS-F-DONE").read_text() == first_flag  # the earlier run's default flag was not touched by this one
    calls.write_text("")
    busy.write_text("untouched\n")  # a bad seed list stops at launch: nothing is waited for, no GPU is taken, fresh_hops.py is never run
    for bad in ("0,1", "0 x", "-1", " "):
        r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "F", str(src), str(tmp_path / "out4")], env=dict(env, HOPS_SEEDS=bad), capture_output=True, text=True, timeout=60)
        assert r.returncode == 2 and ("is not a number" in r.stderr or "names no seed" in r.stderr) and calls.read_text() == "" and busy.read_text() == "untouched\n", (bad, r.stderr)
    assert not (tmp_path / "out4" / "fresh").exists() and not (tmp_path / "out4" / "pairF.log").exists()
    r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "F", str(src), str(tmp_path / "out5")], env=dict(env, HOPS_ARMS="hplains br"), capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "br is not a hops arm" in r.stderr
    r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), "Z", str(src), str(tmp_path / "out6")], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "unknown pair Z (use A, B, R or F)" in r.stdout


def test_pc_hops_clears_gpu_busy_before_any_flag(tmp_path):
    """R and F: GPU-BUSY is empty when DONE_FLAG is written, so a job waiting on the flag finds the GPU free and its own line is never wiped. DONE_FLAG is a named
    pipe here: the script's write blocks until a reader opens it, and the reader looks at GPU-BUSY the moment the flag arrives. The log order says the same."""
    import os
    import subprocess
    import threading
    for pair, extra in (("R", dict(HOPS_ARMS="hloopi", SEED="0", HOPS_NAME="x")), ("F", dict(HOPS_ARMS="hplains", HOPS_SEEDS="0"))):
        d = tmp_path / pair
        src, out, race, jobs, busy, calls = _pc_stubs(d)
        hand, fifo = jobs / "handoff", jobs / "handoff" / "THE-FLAG"
        busy.write_text("")
        (hand / "GO").write_text("go\n")
        os.mkfifo(fifo)
        seen = {}

        def watch():
            with open(fifo) as fh:  # opens when the script reaches its write of DONE_FLAG
                seen["flag"] = fh.read()
            seen["busy"] = busy.read_text()
        t = threading.Thread(target=watch, daemon=True)
        t.start()
        r = subprocess.run(["bash", str(HERE / "pc_hops.sh"), pair, str(src), str(out)], env=_pc_r_env(d, jobs, busy, GO_FLAG=str(hand / "GO"), DONE_FLAG=str(fifo),
                           THEN_FLAG=str(hand / "NEXT"), **extra), capture_output=True, text=True, timeout=120)
        t.join(timeout=30)
        assert r.returncode == 0 and not t.is_alive(), r.stdout + r.stderr
        assert seen["flag"].startswith("0 ") and seen["busy"] == "", (pair, seen)  # GPU-BUSY was already empty when the flag arrived
        log = (out / f"pair{pair}.log").read_text()
        assert log.index("released GPU-BUSY") < log.index(f"wrote {fifo}") < log.index(f"wrote {hand / 'NEXT'}"), log
        assert "busy=hops pair" in calls.read_text()  # and the job did hold it while it ran


def test_pc_race_bridge(tmp_path):
    """pc_race_bridge.sh writes SEG2-DONE (first field 0) after a fresh RACE-MINI-DONE; with hops pair A done and no race-mini driver it gives
    up after STALL_S; stale flags from before its start are ignored."""
    import os
    import subprocess
    import time
    jobs = tmp_path / "jobs"
    (jobs / "handoff").mkdir(parents=True)
    seg2 = jobs / "think2-p1" / "SEG2-DONE"
    env = dict(**os.environ, JOBS=str(jobs), LOG=str(tmp_path / "bridge.log"), POLL="1", STALL_S="2")
    run = ["bash", str(HERE / "pc_race_bridge.sh")]
    for f in ("RACE-MINI-DONE", "HOPS-A-DONE"):  # stale: written before the bridge starts
        (jobs / "handoff" / f).write_text("old\n")
    time.sleep(0.05)
    with subprocess.Popen(run, env=env) as p:
        time.sleep(4)
        assert not seg2.exists()  # stale flags do not count
        (jobs / "handoff" / "RACE-MINI-DONE").write_text("rc 0\n")
        p.wait(timeout=30)
    assert p.returncode == 0 and seg2.read_text().startswith("0 ") and "race-mini v2 done" in seg2.read_text()
    seg2.unlink()
    with subprocess.Popen(run, env=env) as p:
        time.sleep(1.5)
        (jobs / "handoff" / "HOPS-A-DONE").write_text("0\n")  # no pc_race_mini.sh driver runs in this test
        p.wait(timeout=30)
    assert seg2.read_text().startswith("0 ") and "race-mini skipped" in seg2.read_text()


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# The PC order of Oct 28 (coordinator): seed-1 replicate (running, an OLDER pc_hops.sh) -> hloopi seed 0 -> race-mini -> pair A seed 1 + fresh rows -> hloopd
# seed 0 -> SEG2-DONE. Hold directory, bridge AFTER_FLAG / THEN_CMD, pc_hops_chain.sh, and the whole order on stubs. Stub scripts only: no GPU, no ssh.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
OLD_PC_HOPS_COMMIT = "5d892429a5"  # the pc_hops.sh that runs on BensPC now (seed-1 replicate, started before hand_on knew HOLD)


def _old_pc_hops(tmp_path):
    """The pc_hops.sh of OLD_PC_HOPS_COMMIT, written to a temp file (the copy that is running on BensPC); the test is skipped if this checkout lacks that commit."""
    import subprocess
    import pytest
    r = subprocess.run(["git", "-C", str(HERE), "show", f"{OLD_PC_HOPS_COMMIT}:backbone/think/pc_hops.sh"], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"commit {OLD_PC_HOPS_COMMIT} is not in this checkout: {r.stderr.strip()}")
    p = tmp_path / "old_pc_hops.sh"
    p.write_text(r.stdout)
    return p


def _wait_until(pred, timeout=120, step=0.05):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(step)
    return pred()


def test_pc_hops_hold_directory_old_and_new(tmp_path):
    """THEN_FLAG naming a directory holds the next job back (its waiter wants a FILE). With a file HOLD inside: the OLD R script (commit 5d892429a5, running on
    the PC) cannot remove the directory nor write into it, so it stays a directory and no file appears (race-mini stays held); the new hand_on removes exactly
    HOLD, removes the directory and writes the flag (R and F alike). A directory with anything else inside is left alone (HOLD too), nothing is deleted, and the
    log says it could not write THEN_FLAG; DONE_FLAG is still written and GPU-BUSY is still emptied."""
    import subprocess
    old = _old_pc_hops(tmp_path)
    new = HERE / "pc_hops.sh"
    cases = [("old", old, "R", {}), ("new", new, "R", {}), ("newF", new, "F", dict(HOPS_ARMS="hplains", HOPS_SEEDS="0")), ("other", new, "R", {}), ("nested", new, "R", {})]
    for tag, script, pair, extra in cases:
        d = tmp_path / tag
        src, out, race, jobs, busy, calls = _pc_stubs(d)
        hand = jobs / "handoff"
        busy.write_text("")
        (hand / "GO").write_text("go\n")
        hold = hand / "GO-RACE-MINI"
        hold.mkdir()
        (hold / "HOLD").write_text("keep race-mini back\n")
        if tag == "other":
            (hold / "notes.txt").write_text("someone else's file\n")
        if tag == "nested":  # HOLD that is not a file (a directory with a file in it) is not the mark: nothing under it is ever removed
            (hold / "HOLD").unlink()
            (hold / "HOLD").mkdir()
            (hold / "HOLD" / "deep.txt").write_text("deep\n")
        r = subprocess.run(["bash", str(script), pair, str(src), str(out)], env=_pc_r_env(d, jobs, busy, GO_FLAG=str(hand / "GO"), DONE_FLAG=str(hand / "HOPS-S1-DONE"),
                                                                                    THEN_FLAG=str(hold), **extra), capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, (tag, r.stdout + r.stderr)
        assert (hand / "HOPS-S1-DONE").read_text().startswith("0 ") and busy.read_text() == "", tag  # the done flag and GPU-BUSY do not depend on THEN_FLAG
        log = (out / f"pair{pair}.log").read_text()
        if tag == "old":
            assert hold.is_dir() and sorted(x.name for x in hold.iterdir()) == ["HOLD"], tag  # race-mini's waiter (wants a file) is still held back
            assert "Directory not empty" in r.stderr and "Is a directory" in r.stderr, r.stderr  # the failures the old script prints and goes on from
        elif tag in ("new", "newF"):
            assert hold.is_file() and hold.read_text().startswith("go ") and "after hops" in hold.read_text(), tag
            assert f"wrote {hold}" in log and "could not write" not in log and not r.stderr.strip(), (tag, log, r.stderr)
            assert log.index(f"wrote {hand / 'HOPS-S1-DONE'}") < log.index(f"wrote {hold}")  # as before: DONE_FLAG first, then THEN_FLAG
        elif tag == "other":
            assert hold.is_dir() and sorted(x.name for x in hold.iterdir()) == ["HOLD", "notes.txt"], tag  # left alone, HOLD included
            assert (hold / "notes.txt").read_text() == "someone else's file\n" and (hold / "HOLD").read_text() == "keep race-mini back\n"
            assert f"could not write THEN_FLAG {hold}" in log and "notes.txt" in log and f"wrote {hold}" not in log, log
        else:
            assert (hold / "HOLD" / "deep.txt").read_text() == "deep\n" and hold.is_dir()
            assert f"could not write THEN_FLAG {hold}" in log and f"wrote {hold}" not in log, log
    # an empty hold directory and a plain missing flag behave as before (the earlier tests cover them end to end); a write that fails is not reported as written
    d = tmp_path / "ro"
    src, out, race, jobs, busy, calls = _pc_stubs(d)
    hand = jobs / "handoff"
    busy.write_text("")
    (hand / "GO").write_text("go\n")
    r = subprocess.run(["bash", str(new), "R", str(src), str(out)], env=_pc_r_env(d, jobs, busy, GO_FLAG=str(hand / "GO"), DONE_FLAG=str(hand / "D"),
                                                                                  THEN_FLAG=str(hand / "no-such-dir" / "GO-NEXT")), capture_output=True, text=True, timeout=120)
    log = (out / "pairR.log").read_text()
    assert r.returncode == 0 and f"could not write THEN_FLAG {hand / 'no-such-dir' / 'GO-NEXT'}" in log and f"wrote {hand / 'no-such-dir'}" not in log, log


def test_pc_race_bridge_after_flag_and_then_cmd(tmp_path):
    """pc_race_bridge.sh with AFTER_FLAG and THEN_CMD: THEN_CMD does not run before RACE-MINI-DONE (nor on a stale one, nor on hops pair A's flag once AFTER_FLAG
    names another), runs to its end in the foreground, and only then is OUTFLAG written, with its exit code ("... ; then rc=N"). The stall rule counts from AFTER_FLAG.
    With neither setting, the text of OUTFLAG is what it always was (the old test checks the behaviour)."""
    import os
    import re
    import subprocess
    import time
    jobs = tmp_path / "jobs"
    hand = jobs / "handoff"
    hand.mkdir(parents=True)
    seg2 = jobs / "think2-p1" / "SEG2-DONE"
    marker, after = tmp_path / "then.txt", hand / "HOPS-R-round2_hloopi-DONE"
    base = dict(**os.environ, JOBS=str(jobs), LOG=str(tmp_path / "bridge.log"), POLL="1", STALL_S="2")
    run = ["bash", str(HERE / "pc_race_bridge.sh")]
    # 1. race-mini done -> THEN_CMD (rc 7) -> OUTFLAG with "then rc=7"
    env = dict(base, AFTER_FLAG=str(after), THEN_CMD=f"echo started > {marker}; sleep 3; echo finished >> {marker}; exit 7")
    (hand / "RACE-MINI-DONE").write_text("stale\n")
    time.sleep(0.05)
    with subprocess.Popen(run, env=env) as p:
        time.sleep(1)
        (hand / "HOPS-A-DONE").write_text("0\n")  # the default AFTER_FLAG: with AFTER_FLAG set, it starts no stall check (STALL_S is 2 s, no driver runs)
        time.sleep(4)
        assert p.poll() is None and not marker.exists() and not seg2.exists()  # nothing ran: stale RACE-MINI-DONE, HOPS-A-DONE is not AFTER_FLAG
        (hand / "RACE-MINI-DONE").write_text("rc 0\n")
        assert _wait_until(marker.exists, 20) and not seg2.exists()  # THEN_CMD runs first, OUTFLAG is not there while it runs
        assert _wait_until(seg2.exists, 30)
        assert marker.read_text() == "started\nfinished\n"  # OUTFLAG came after THEN_CMD's last line
        p.wait(timeout=30)
    t = seg2.read_text()
    assert p.returncode == 0 and re.fullmatch(r"0 \S+Z race-mini v2 done: rc 0 ; then rc=7\n", t), t
    log = (tmp_path / "bridge.log").read_text()
    assert "AFTER_FLAG=" in log and log.index("then-command start") < log.index("then-command end rc=7") < log.index("wrote")
    # 2. AFTER_FLAG there, no race-mini driver: the stall rule gives up on race-mini, THEN_CMD still runs before OUTFLAG
    seg2.unlink()
    marker.unlink()
    (hand / "RACE-MINI-DONE").unlink()
    env = dict(base, AFTER_FLAG=str(after), THEN_CMD=f"echo ran > {marker}")
    with subprocess.Popen(run, env=env) as p:
        time.sleep(1.5)
        after.write_text("0 hloopi\n")
        p.wait(timeout=30)
    t = seg2.read_text()
    assert re.fullmatch(r"0 \S+Z no race-mini driver for 2 s after HOPS-R-round2_hloopi-DONE; race-mini skipped; then rc=0\n", t), t
    assert marker.read_text() == "ran\n"
    # 3. defaults: exactly the old text, no "then", the stall rule on HOPS-A-DONE
    seg2.unlink()
    (hand / "HOPS-A-DONE").write_text("stale\n")
    time.sleep(0.05)
    with subprocess.Popen(run, env=base) as p:
        time.sleep(1.5)
        (hand / "HOPS-A-DONE").write_text("0\n")
        p.wait(timeout=30)
    assert re.fullmatch(r"0 \S+Z no race-mini driver for 2 s after hops pair A; race-mini skipped\n", seg2.read_text()), seg2.read_text()
    seg2.unlink()
    with subprocess.Popen(run, env=base) as p:
        time.sleep(1.5)
        (hand / "RACE-MINI-DONE").write_text("rc 0\n")
        p.wait(timeout=30)
    assert re.fullmatch(r"0 \S+Z race-mini v2 done: rc 0 \n", seg2.read_text()), seg2.read_text()


def _chain_setup(tmp_path, s0=None, s1=None, **more):
    """A src with the stubs of _pc_stubs plus the real pc_hops.sh (the chain runs it from SRC), and a summarize_hops stub whose --json prints the file named by
    $SUMJSON_<seed> (exit 1 if there is none). s0 / s1 are the summaries the stub gives at seed 0 / 1: dicts, a raw string, or None (no summary: the stub fails).
    Returns (src, out, jobs, busy, calls, env)."""
    import shutil
    src, out, race, jobs, busy, calls = _pc_stubs(tmp_path)
    think = src / "backbone" / "think"
    for name in ("pc_hops.sh", "pc_hops_chain.sh"):
        shutil.copy(HERE / name, think / name)
    sj = think / "summarize_hops.py"
    sumlog = tmp_path / "summaries.txt"
    sj.write_text("import os, sys, pathlib\na = sys.argv\nif '--json' in a:\n    s = a[a.index('--seed') + 1]\n"
                  f"    open({str(sumlog)!r}, 'a').write(f'json seed={{s}} runs={{pathlib.Path(a[1]).name}} data={{pathlib.Path(a[a.index(\"--data\") + 1]).name}}\\n')\n"
                  "    f = os.environ.get('SUMJSON_' + s)\n"
                  "    if not f or not os.path.exists(f):\n        sys.stderr.write('stub: no summary for seed ' + s + '\\n'); sys.exit(1)\n"
                  "    sys.stdout.write(open(f).read()); sys.exit(0)\n" + sj.read_text())
    busy.write_text("")
    extra = {}
    for seed, s in ((0, s0), (1, s1)):
        if s is not None:
            p = tmp_path / f"sum_s{seed}.json"
            p.write_text(s if isinstance(s, str) else json.dumps(s))
            extra[f"SUMJSON_{seed}"] = str(p)
    # what a shell or the bridge may leave in the environment: the chain must clear every one of them
    junk = dict(GO_FLAG=str(tmp_path / "no-such" / "GO"), DONE_FLAG=str(jobs / "handoff" / "STRAY-DONE"), THEN_FLAG=str(jobs / "handoff" / "STRAY-NEXT"),
                HOPS_ARMS="hplains", HOPS_SEEDS="7", HOPS_NAME="bogus", SEED="9")
    env = _pc_r_env(tmp_path, jobs, busy, **junk, **extra, **more)
    return src, out, jobs, busy, calls, env


def _summ(b=None, a=None, hloopi=None, hloopd=None, drop_r2=False):
    """What summarize_hops.py --json carries that the chain reads: B.key, A.key, R2.<arm>.works / stops_itself (a mark left out is a key that is missing)."""
    o = {"seed": 0, "n": 10, "arms": []}
    if b:
        o["B"] = {"key": b}
    if a:
        o["A"] = {"key": a}
    o["R2"] = {} if drop_r2 else {x: {"works": v[0], "stops_itself": v[1]} for x, v in (("hloopi", hloopi), ("hloopd", hloopd)) if v is not None}
    return o


def _run_chain(src, out, env, rc=0):
    import subprocess
    r = subprocess.run(["bash", str(src / "backbone" / "think" / "pc_hops_chain.sh"), str(src), str(out)], env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == rc, r.stdout + r.stderr
    return r


def test_pc_hops_chain_runs_every_step_in_order(tmp_path):
    """pc_hops_chain.sh with B PASS at seeds 0 and 1, A REPLICATES at seed 1, hloopi works, hloopd stops itself: pc_hops.sh runs in the order a (R pair A seed 1),
    F pairB, F pairA, F hloopi, R hloopd, F hloopd, each with its own HOPS_NAME, DONE_FLAG default, go flag and the arms / seeds fixed for it, holding the GPU under its
    own GPU-BUSY line; the environment's GO_FLAG, DONE_FLAG, THEN_FLAG, HOPS_ARMS, HOPS_SEEDS, HOPS_NAME and SEED are cleared first (and set here to junk);
    chain.log has every decision, HOPS-CHAIN-DONE the list of what ran; exit 0."""
    src, out, jobs, busy, calls, env = _chain_setup(tmp_path, s0=_summ(b="PASS", a="FAILS", hloopi=(True, False), hloopd=(False, True)), s1=_summ(b="PASS", a="REPLICATES"))
    hand = jobs / "handoff"
    r = _run_chain(src, out, env)
    lines = calls.read_text().splitlines()
    assert [x.split()[0] for x in lines] == ["hplain", "hloop", "fresh", "fresh", "fresh", "hloopd", "fresh"], lines
    assert all("racing=False busy=hops pair R seed 1 " in x and x.endswith("seed=1") for x in lines[:2]), lines  # pair A's seed-1 replicate
    want = [("arms=hplains,hloops seeds=0,1", "pair F seed 0 1"), ("arms=hplain,hloop seeds=0,1", "pair F seed 0 1"), ("arms=hloopi,hplain seeds=0 ", "pair F seed 0 ")]
    for x, (a, b) in zip(lines[2:5], want):
        assert x.startswith(f"fresh {a}") and f"runs=runs data=data busy=hops {b}" in x, x
    assert "hloopd racing=False busy=hops pair R seed 0 " in lines[5] and lines[5].endswith("seed=0"), lines[5]
    assert lines[6].startswith("fresh arms=hloopd,hplains seeds=0 ") and "busy=hops pair F seed 0 " in lines[6]
    flags = ["HOPS-R-pairA_s1-DONE", "HOPS-F-pairB-DONE", "HOPS-F-pairA-DONE", "HOPS-F-hloopi-DONE", "HOPS-R-round2_hloopd-DONE", "HOPS-F-hloopd-DONE"]
    for f in flags:
        assert (hand / f).read_text().startswith("0 ") and "rc=0" in (hand / f).read_text(), f
    assert sorted(x.name for x in hand.iterdir()) == sorted(flags + ["HOPS-CHAIN-GO", "HOPS-CHAIN-DONE"]), sorted(x.name for x in hand.iterdir())  # no STRAY-*, no bogus, no HOPS-R-DONE
    assert (hand / "HOPS-CHAIN-GO").read_text().startswith("go ") and busy.read_text() == "" and not (tmp_path / "no-such").exists()
    assert sorted(x.name for x in out.glob("SUMMARY_*")) == ["SUMMARY_fresh_hloopd_s0.txt", "SUMMARY_fresh_hloopi_s0.txt", "SUMMARY_fresh_pairA_s0.txt", "SUMMARY_fresh_pairA_s1.txt",
                                                            "SUMMARY_fresh_pairB_s0.txt", "SUMMARY_fresh_pairB_s1.txt", "SUMMARY_pairA_s1.txt", "SUMMARY_round2_hloopd.txt"]
    assert (out / "runs" / "hloopd_s0" / "result_hloopd_s0.json").exists() and (out / "runs" / "hloop_s1" / "result_hloop_s1.json").exists()
    done = (hand / "HOPS-CHAIN-DONE").read_text()
    assert done.startswith("0 ") and done.count("\n") == 1 and "ran: R pairA_s1 rc=0; F pairB rc=0; F pairA rc=0; F hloopi rc=0; R round2_hloopd rc=0; F hloopd rc=0; skipped: nothing; exit 0" in done, done
    clog = (out / "chain.log").read_text()
    for needle in ("decision F pairB: yes", "decision F pairA: yes", "decision F hloopi: yes", "decision R round2_hloopd: yes", "decision F hloopd: yes", "pair B key PASS at seed 0",
                   "pair A key REPLICATES at seed 1", "hloopi works=True stops_itself=False at seed 0", "hloopd works=False stops_itself=True at seed 0"):
        assert needle in clog, (needle, clog)
    assert "json seed=1 runs=runs data=data" in (tmp_path / "summaries.txt").read_text() and (out / "pairR.log").exists() and "exit 0" in clog
    assert r.stdout.count("pc_hops_chain.sh start") == 1


def test_pc_hops_chain_skips_what_is_not_met_or_not_readable(tmp_path):
    """The chain decides each group from the summary it can read and never guesses. B failing at seed 1: no pairB group and no hloopd. B failing at seed 0: the same.
    A summary that fails, is not JSON, or lacks the key: the groups that need it are skipped and logged as not readable (the others still run). hloopd that neither works
    nor stops itself: its run happens, its fresh group does not. A step that fails does not stop the later ones (exit 1), and a failed hloopd run has no fresh group."""
    def run(tag, s0, s1, rc=0, **more):
        d = tmp_path / tag
        src, out, jobs, busy, calls, env = _chain_setup(d, s0=s0, s1=s1, **more)
        _run_chain(src, out, env, rc)
        import re
        short = lambda x: re.sub(r"^(\w+) racing=\w+ busy=.* seed=(\d+)$", r"\1 seed=\2", x).split(" busy=")[0]  # think1 lines: arm and seed; fresh lines: without GPU-BUSY
        lines = [short(x) for x in calls.read_text().splitlines()]
        return lines, (out / "chain.log").read_text(), (jobs / "handoff" / "HOPS-CHAIN-DONE").read_text(), jobs / "handoff"
    ok0, ok1 = _summ(b="PASS", a="FAILS", hloopi=(True, True), hloopd=(True, True)), _summ(b="PASS", a="REPLICATES")
    # B fails at seed 1: a, F pairA, F hloopi; no F pairB, no hloopd at all
    lines, clog, done, hand = run("b1", ok0, _summ(b="NOT SHOWN", a="REPLICATES"))
    assert lines == ["hplain seed=1", "hloop seed=1", "fresh arms=hplain,hloop seeds=0,1 runs=runs data=data", "fresh arms=hloopi,hplain seeds=0 runs=runs data=data"], lines
    assert "decision F pairB: no (seed 0: yes" in clog and "pair B key NOT SHOWN at seed 1" in clog and "skip R round2_hloopd" in clog and "skip F hloopd" in clog
    assert not (hand / "HOPS-F-pairB-DONE").exists() and not (hand / "HOPS-R-round2_hloopd-DONE").exists() and "skipped: F pairB (" in done and "R round2_hloopd (" in done and done.endswith("exit 0\n")
    # B fails at seed 0 (seed 1 passes): the same
    lines, clog, done, hand = run("b0", _summ(b="TOLD ONLY", a="FAILS", hloopi=(False, False)), ok1)
    assert lines == ["hplain seed=1", "hloop seed=1", "fresh arms=hplain,hloop seeds=0,1 runs=runs data=data"], lines  # hloopi neither works nor stops itself: no group
    assert "decision F hloopi: no" in clog and "mark not met" in clog and "pair B key TOLD ONLY at seed 0" in clog
    # seed 0 has no summary (the stub exits 1): pairB, hloopi and hloopd are skipped as not readable, pair A (seed 1) still runs
    lines, clog, done, hand = run("nos0", None, ok1)
    assert lines == ["hplain seed=1", "hloop seed=1", "fresh arms=hplain,hloop seeds=0,1 runs=runs data=data"], lines
    assert sum(1 for x in clog.splitlines() if " skip " in x and "not readable, not guessed" in x) == 3 and "exited 1" in clog and "stub: no summary for seed 0" in clog and "decision F pairB: unreadable" in clog
    # seed 1 is not JSON: pair A is skipped, hloopi (seed 0) still runs, and pair B is unreadable so no hloopd
    lines, clog, done, hand = run("junk1", ok0, "this is not json {")
    assert lines == ["hplain seed=1", "hloop seed=1", "fresh arms=hloopi,hplain seeds=0 runs=runs data=data"], lines
    assert "decision F pairA: unreadable" in clog and "decision F pairB: unreadable" in clog and "decision R round2_hloopd: unreadable" in clog
    # the key is missing: no B in the seed-0 summary (pair B not computed), no hloopi among its round-2 arms
    lines, clog, done, hand = run("nokey", _summ(a="FAILS", drop_r2=True), ok1)
    assert lines == ["hplain seed=1", "hloop seed=1", "fresh arms=hplain,hloop seeds=0,1 runs=runs data=data"], lines
    assert "seed 0 summary has no B mark (KeyError: 'B')" in clog and "seed 0 summary has no R2:hloopi mark (KeyError: 'hloopi')" in clog
    # hloopd neither works nor stops itself: its run happens, no fresh group
    lines, clog, done, hand = run("d0", _summ(b="PASS", a="FAILS", hloopi=(False, False), hloopd=(False, False)), ok1)
    assert [x.split()[0] for x in lines] == ["hplain", "hloop", "fresh", "fresh", "hloopd"] and lines[-1] == "hloopd seed=0", lines  # pairB and pairA groups ran, hloopi's did not
    assert "decision F hloopd: no" in clog and "skip F hloopd: mark not met" in clog and "R round2_hloopd rc=0; skipped: F hloopi (" in done
    # step failures: a (hplain) fails -> the later steps still run, exit 1, the code is in the flag text; the flag still reads 0 in its first field
    lines, clog, done, hand = run("faila", ok0, ok1, rc=1, FAIL_ARM="hplain")
    assert [x.split()[0] for x in lines] == ["hplain", "fresh", "fresh", "fresh", "hloopd", "fresh"], lines  # hloop is not run after hplain failed (stop at the first failure)
    assert "R pairA_s1 rc=3; F pairB rc=0" in done and done.startswith("0 ") and done.endswith("exit 1\n"), done
    # hloopd's own run fails: its fresh group does not run, exit 1, the others are unaffected
    lines, clog, done, hand = run("faild", ok0, ok1, rc=1, FAIL_ARM="hloopd")
    assert [x.split()[0] for x in lines] == ["hplain", "hloop", "fresh", "fresh", "fresh", "hloopd"], lines
    assert "R round2_hloopd rc=3" in done and "skip F hloopd: the hloopd run did not exit 0" in clog and not (hand / "HOPS-F-hloopd-DONE").exists()
    assert (hand / "HOPS-R-round2_hloopd-DONE").read_text().startswith("0 ") and "rc=3" in (hand / "HOPS-R-round2_hloopd-DONE").read_text()


def test_pc_planned_order_end_to_end_on_stubs(tmp_path):
    """The whole order of Oct 28 on stubs. GO-RACE-MINI is a directory holding HOLD. The OLD R (commit 5d892429a5, seed 1) runs and writes HOPS-S1-DONE, fails to
    release GO-RACE-MINI; the new hloopi R (GO_FLAG=HOPS-S1-DONE, THEN_FLAG=GO-RACE-MINI) runs next and swaps the directory for the flag file; only then does a fake
    race-mini waiter (a pc_race_mini.sh driver that polls for the file and an empty GPU-BUSY) start; the new bridge (AFTER_FLAG, THEN_CMD=the chain) sees
    RACE-MINI-DONE, runs the chain, and writes SEG2-DONE only after HOPS-CHAIN-DONE. Two owners never hold GPU-BUSY at once."""
    import subprocess
    import threading
    old = _old_pc_hops(tmp_path)
    src, out, jobs, busy, calls, env = _chain_setup(tmp_path, s0=_summ(b="PASS", a="FAILS", hloopi=(True, False), hloopd=(False, True)), s1=_summ(b="PASS", a="REPLICATES"))
    for k in ("GO_FLAG", "DONE_FLAG", "THEN_FLAG", "HOPS_ARMS", "HOPS_SEEDS", "HOPS_NAME", "SEED"):
        env.pop(k)  # the jobs below get their own; the bridge is started without any of them
    hand, seg2 = jobs / "handoff", jobs / "think2-p1" / "SEG2-DONE"
    race = tmp_path / "race"
    hold = hand / "GO-RACE-MINI"
    hold.mkdir()
    (hold / "HOLD").write_text("held\n")  # arming step 1
    # race-mini's waiter: polls for the flag FILE and an empty GPU-BUSY, then takes GPU-BUSY (it must find it empty), runs ~3 s, empties it, writes RACE-MINI-DONE
    (race / "pc_race_mini.sh").write_text(
        f"until [ -f {hold} ] && [ ! -s {busy} ]; do sleep 1; done\n"
        f"echo \"race-mini start go=$(head -c 2 {hold}) hloopi_done=$(test -f {hand / 'HOPS-R-round2_hloopi-DONE'} && echo yes || echo no) busy_was=[$(cat {busy})]\" >> {calls}\n"
        f"echo \"race-mini (sleep race, both sides) since $(date -u +%FT%TZ)\" > {busy}\n"
        f"sleep 3\n"
        f"echo \"race-mini end busy=$(cat {busy})\" >> {calls}\n"
        f": > {busy}\n"
        f"echo \"0 $(date -u +%FT%TZ) rc 0\" > {hand / 'RACE-MINI-DONE'}\n")
    seen, bad, stop = [], [], threading.Event()
    watch = {"HOPS-S1-DONE": lambda: (hand / "HOPS-S1-DONE").exists(), "HOPS-R-round2_hloopi-DONE": lambda: (hand / "HOPS-R-round2_hloopi-DONE").exists(),
             "GO-RACE-MINI file": lambda: hold.is_file(), "RACE-MINI-DONE": lambda: (hand / "RACE-MINI-DONE").exists(), "HOPS-CHAIN-GO": lambda: (hand / "HOPS-CHAIN-GO").exists(),
             "HOPS-CHAIN-DONE": lambda: (hand / "HOPS-CHAIN-DONE").exists(), "SEG2-DONE": seg2.exists}

    def sampler():  # order of first sight; two facts checked in the order that cannot race: the later flag first, then the one that must already be there
        while not stop.is_set():
            if hold.is_file() and not (hand / "HOPS-R-round2_hloopi-DONE").exists():
                bad.append("GO-RACE-MINI was a file before hloopi's done flag")
            if seg2.exists() and not (hand / "HOPS-CHAIN-DONE").exists():
                bad.append("SEG2-DONE before HOPS-CHAIN-DONE")
            if hold.is_file() and not (hand / "HOPS-S1-DONE").exists():
                bad.append("GO-RACE-MINI file before the seed-1 replicate was done")
            for k, f in watch.items():
                if k not in seen and f():
                    seen.append(k)
            stop.wait(0.02)
    th = threading.Thread(target=sampler, daemon=True)
    procs = []
    try:
        th.start()
        mk = lambda argv, e: procs.append(subprocess.Popen(argv, env=e, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)) or procs[-1]
        mk(["bash", str(race / "pc_race_mini.sh")], env)
        old_r = mk(["bash", str(old), "R", str(src), str(out)], dict(env, GO_FLAG=str(hand / "HOPS-A-DONE"), DONE_FLAG=str(hand / "HOPS-S1-DONE"), THEN_FLAG=str(hold)))
        new_r = mk(["bash", str(HERE / "pc_hops.sh"), "R", str(src), str(out)], dict(env, GO_FLAG=str(hand / "HOPS-S1-DONE"), HOPS_ARMS="hloopi", SEED="0", HOPS_NAME="round2_hloopi",
                                                                                      THEN_FLAG=str(hold)))
        bridge = mk(["bash", str(HERE / "pc_race_bridge.sh")], dict(env, LOG=str(tmp_path / "bridge.log"), STALL_S="2",
                                                                      AFTER_FLAG=str(hand / "HOPS-R-round2_hloopi-DONE"),
                                                                      THEN_CMD=f"bash {src}/backbone/think/pc_hops_chain.sh {src} {out}"))
        import time
        time.sleep(3)
        assert old_r.poll() is None and new_r.poll() is None and bridge.poll() is None and not calls.exists()  # all waiting: nothing has the GPU yet
        (hand / "HOPS-A-DONE").write_text("0\n")  # the seed-1 replicate gets its go
        assert _wait_until(seg2.exists, 170), (calls.read_text() if calls.exists() else "", (out / "chain.log").read_text() if (out / "chain.log").exists() else "")
        assert _wait_until(lambda: "SEG2-DONE" in seen, 10)  # the sampler has seen it too
        for p in (old_r, new_r, bridge):
            p.wait(timeout=30)
        assert old_r.returncode == 0 and new_r.returncode == 0 and bridge.returncode == 0
    finally:
        stop.set()
        th.join(timeout=5)
        for p in procs:
            if p.poll() is None:
                p.kill()
            p.wait()
    assert not bad, sorted(set(bad))
    assert seen == list(watch), seen  # first sight in the order of the plan (the dict's order is the plan's; the checks above are the ones that cannot race)
    lines = calls.read_text().splitlines()
    names = [x.split()[0] if not x.startswith("race-mini") else " ".join(x.split()[:2]) for x in lines]
    assert names == ["hplains", "hloops", "hloopi", "race-mini start", "race-mini end", "hplain", "hloop", "fresh", "fresh", "fresh", "hloopd", "fresh"], names
    assert "busy=hops pair R seed 1 " in lines[0] and "busy=hops pair R seed 1 " in lines[1] and "busy=hops pair R seed 0 " in lines[2]  # each held GPU-BUSY under its own line
    assert "go=go hloopi_done=yes busy_was=[]" in lines[3]  # race-mini started on the flag FILE, after hloopi, and found GPU-BUSY empty
    assert lines[4].startswith("race-mini end busy=race-mini (sleep race") and "busy=hops pair R seed 1 " in lines[5] and "busy=hops pair R seed 1 " in lines[6]
    assert all("busy=hops pair F seed " in x for x in lines[7:10]) and "busy=hops pair R seed 0 " in lines[10] and "busy=hops pair F seed 0 " in lines[11]
    assert not hold.is_dir() and hold.read_text().startswith("go ") and "after hops replicate seed 0" in hold.read_text() and busy.read_text() == ""
    assert (hand / "HOPS-S1-DONE").read_text().startswith("0 ") and "rc=0" in (hand / "HOPS-R-round2_hloopi-DONE").read_text()
    t = seg2.read_text()
    assert t.startswith("0 ") and "race-mini v2 done: 0 " in t and t.endswith("rc 0 ; then rc=0\n"), t  # the fake race-mini's own flag text, then the chain's code
    assert "exit 0" in (hand / "HOPS-CHAIN-DONE").read_text() and "F hloopd rc=0" in (hand / "HOPS-CHAIN-DONE").read_text()
    blog = (tmp_path / "bridge.log").read_text()
    assert blog.index("then-command start") < blog.index("then-command end rc=0") < blog.index("wrote")
