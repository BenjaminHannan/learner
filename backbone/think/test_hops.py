"""CPU tests for Addendum G (the hops bed: hplain, hloop, hloopi, hloopd, hplains, hloops): python -m pytest backbone/think/test_hops.py

Covers: build_hops.py rows (depth = chain length, the chain links object -> place, hops_path, line, chain and place counts and length do not
depend on depth, determinism, split counts, one-token names), Inject (zero W leaves the model unchanged; a non-zero W changes looped passes
only; cached decode = cache-free), hidden_multi (= hidden at the same loop count; earlier reads), the loop plans (hops_plan, plan_ratio,
hop_target), the greedy log-probability record, the max-confidence halting and oracle readouts, a short run of every hops arm end to end
(hloopd's per-row loop counts equal a fixed-count run when every row has the same depth; hloops' reads add to the loss), eval_adapter's
Inject reload, and summarize_hops' marks and outcomes on synthetic results.
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


def test_pc_hops_pauses_race_mini_and_hands_back(tmp_path):
    """pc_hops.sh B, dry run with stub scripts: it pauses a fake race-mini driver, waits for the running race arm to end, runs pair B with no
    race arm running and its own GPU-BUSY line, then puts race-mini's line back, writes HOPS-B-DONE and resumes the driver, which finishes."""
    import shutil
    import subprocess
    import time
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
            "think1.py": "import sys, pathlib, subprocess\na = sys.argv; arm = a[a.index('--arm') + 1]; p = pathlib.Path(a[a.index('--out') + 1]); p.mkdir(parents=True, exist_ok=True)\n"
                         "racing = subprocess.run(['pgrep', '-f', 'race_mini.py'], capture_output=True).stdout.strip() != b''\n"
                         f"open({str(calls)!r}, 'a').write(f'{{arm}} racing={{racing}} busy={{open({str(busy)!r}).read().strip()}}\\n')\n"
                         "(p / f'result_{arm}_s0.json').write_text('{}')\n",
            "summarize_hops.py": "print('OUTCOME B: stub')\n"}
    for name, body in stub.items():
        (src / "backbone" / "think" / name).write_text(body)
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
