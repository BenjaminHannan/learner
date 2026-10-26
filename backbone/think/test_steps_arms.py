"""CPU tests for the P1 / P2b arms (ws, wsham, tsd, tsd1; steps.py): python -m pytest backbone/think/test_steps_arms.py

Tiny random Qwen3.5-style config, as test_think1.py. Covers: the written format and the sham, ws batches = aplus batches + the duplicated written copies,
the T / format-check scoring, the step decoder (isolation from everything but the notes, main LoRA off, gradients), tsd vs tsd1 (equal parameters, passes and
targets), the random / zero lesions and the decoder accuracy under swapped notes. The data-side tests are in test_steps_data.py, the summarize marks in test_summarize.py.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import test_think1 as TK  # noqa: E402

K, B, T, S = TK.K, TK.B, TK.T, TK.K.S
CPU = torch.device("cpu")


def tiny(max_len=2048):
    a = K.parse(["--smoke", "--arm", "ws", "--out", "x"])
    lm, tok = T.load_model(a, CPU, torch.float32)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)
    return a, lm, tok, T.Encoder(tok, max_len)


def rows_with_steps(n=12):
    rows = K.synth_rows("validation", n)
    for i, r in enumerate(rows):
        r["steps"] = [f"[world] Step line {i}a.", f"[world] Step line {i}b"][: i % 3]
    return rows


# ---------------------------------------------------------------- the written format

def test_written_format_and_sham():
    _, lm, tok, enc = tiny()
    r2 = dict(rows_with_steps()[2], answer="the mill")
    r0 = dict(rows_with_steps()[0], answer="the mill")
    assert r2["steps"] == ["[world] Step line 2a.", "[world] Step line 2b"] and r0["steps"] == []
    st, an = S.written_target(enc, r2)
    assert tok.decode(st + an) == " Step 1: [world] Step line 2a. Step 2: [world] Step line 2b. The answer is: the mill"  # a final full stop is added to a line without one
    assert an[-1] == enc.eos
    st0, an0 = S.written_target(enc, r0)
    assert st0 == [] and tok.decode(an0) == " The answer is: the mill"
    sh, an_sh = S.written_target(enc, r2, sham=True)
    assert len(sh) == len(st) > 0 and an_sh == an and tok.decode(sh).replace(" ", "").strip(".") == ""  # same number of tokens, only dots
    assert S.written_target(enc, r0, sham=True)[0] == []  # nothing to replace
    p, tgt = S.written_example(enc, r2)
    pd, ad = enc.prompt(r2)[0], enc.train_example(r2)[1]
    assert tgt == st + an and tgt[-len(ad):] == ad
    assert p[: len(p) - len(enc.ids(r2["question"] + S.STEPS_TAIL))] == pd[: len(pd) - len(enc.ids(r2["question"] + T.PROMPT_TAIL))], "the context is the direct example's"
    assert p[-len(enc.ids(S.STEPS_TAIL)):] == enc.ids(S.STEPS_TAIL) and pd[-len(enc.ids(T.PROMPT_TAIL)):] == enc.ids(T.PROMPT_TAIL) and p != pd
    g = S.gold_prompt(enc, r2)
    assert g[-len(enc.ids(" " + S.ANSWER_MARK)):] == enc.ids(" " + S.ANSWER_MARK) and tok.decode(g).endswith(" Step 2: [world] Step line 2b. The answer is:")
    assert S.parse_answer(" Step 1: x. The answer is: the mill") == " the mill" and S.parse_answer("no marker") is None
    assert S.parse_answer("The answer is: a. The answer is: b") == " b"
    dt = S.decoder_targets(enc, r2)
    assert [d[2] for d in dt] == [True, True, False, False] and tok.decode(dt[0][0]) == "Step 1:" and tok.decode(dt[1][1]) == " [world] Step line 2b."
    assert dt[2][0] == [] and tok.decode(dt[2][1]) == "The answer is: the mill" and dt[2] == dt[3][:2] + (False,)
    assert all(d[2] is False for d in S.decoder_targets(enc, r0))


# ---------------------------------------------------------------- ws / wsham training and evaluation

def spy_batches(arm, steps, extra=()):
    fx = TK.fixture()
    calls, real = [], K.answer_loss_fixed

    def spy(runner, batch, device):
        calls.append(list(batch))
        return real(runner, batch, device)

    K.answer_loss_fixed = spy
    try:
        a = TK.arm_args(arm, 0, "sb_" + arm, steps=steps, extra=("--limit-eval", "4", *extra))
        assert K.run_arm(a) == 0
    finally:
        K.answer_loss_fixed = real
    return a, calls, fx


def test_ws_batches_are_aplus_batches_plus_written_copies():
    a_ap, calls_ap, fx = spy_batches("aplus", 2)
    a_ws, calls_ws, _ = spy_batches("ws", 2)
    a_sh, calls_sh, _ = spy_batches("wsham", 2)
    per = lambda calls, k: [sum(calls[i * k:(i + 1) * k], []) for i in range(2)]  # (20 smoke rows: two full batches of 8) micro-batches of 4 sequences: 8 -> 2 per step, 16 -> 4 per step
    ap, ws, sh = per(calls_ap, 2), per(calls_ws, 4), per(calls_sh, 4)
    assert len(calls_ap) == 4 and len(calls_ws) == 8
    rows = T.read_jsonl(Path(fx["data"]) / "train.jsonl")
    _, _, _, enc = tiny(256)  # the smoke run's max_len
    stream = K.batches(len(rows), 0 + 1000, 8)  # stage 2: Random(seed + 1000), the same stream aplus uses
    for s in range(2):
        ids = next(stream)
        direct = [enc.train_example(rows[i]) for i in ids]
        assert ap[s] == direct and ws[s][:8] == direct and sh[s][:8] == direct, "the direct half of a ws step is aplus's batch, row for row"
        assert ws[s][8:] == [S.written_example(enc, rows[i]) for i in ids] and sh[s][8:] == [S.written_example(enc, rows[i], sham=True) for i in ids]
        for (p, t), (_, t_sham), i in zip(ws[s][8:], sh[s][8:], ids):
            assert len(t) == len(t_sham) and t[-len(enc.ids(" " + rows[i]["answer"])) - 1:] == t_sham[-len(enc.ids(" " + rows[i]["answer"])) - 1:], "sham: same length, same answer"
        assert any(S.steps_of(rows[i]) for i in ids) and any(not S.steps_of(rows[i]) for i in range(len(rows)))
    res = {k: json.loads((Path(a.out) / f"result_{a.arm}_s0.json").read_text()) for k, a in (("ap", a_ap), ("ws", a_ws), ("sh", a_sh))}
    assert res["ws"]["params_trainable"] == res["sh"]["params_trainable"] == res["ap"]["params_trainable"] == 146_176
    assert res["ws"]["written"]["tail"] == S.STEPS_TAIL and res["sh"]["written"]["sham"] is True and res["ws"]["written"]["train_rows_with_steps"] > 0
    assert res["ws"]["stage1_adapter_sha"] == res["ap"]["stage1_adapter_sha"]
    for arm in ("ws", "sh"):
        ev = res[arm]["eval"]
        assert set(ev["validation"]) == {"T", "C1", "fmt"} and set(ev["dev"]) == {"T", "C1"}
        t = ev["validation"]["T"]
        assert t["n"] == len(t["hits"]) == 4 and 0 <= t["mean_gen_tokens"] <= K.MAX_NEW_STEPS and t["marker_rate"] is not None
        assert ev["validation"]["fmt"]["marker_rate"] is None and len(ev["validation"]["fmt"]["row_idx"]) == ev["validation"]["fmt"]["n"]
    # C1 is the existing direct eval of the same weights (arm aplus's path)
    assert res["ws"]["eval"]["validation"]["C1"]["n"] == 4


def test_eval_written_scoring(monkeypatch):
    a, lm, tok, enc = tiny()
    runner = T.Runner(lm)
    long = " ".join("abcdefghijklmnopqrstuvwxyz")
    rows = [dict(r, answer=ans) for r, ans in zip(rows_with_steps(6), ["the mill", "the cave", "the hut", "yes", "the pond", long])]
    gen = {0: " Step 1: x. The answer is: the mill", 1: " Step 1: y. The answer is: the cave.", 2: "no marker the hut", 3: "The answer is: no",
           4: "The answer is: the harbour", 5: "The answer is: " + long}
    gold = {0: " the mill", 1: " the cave.", 2: " the hut", 3: " no", 4: " wrong", 5: " " + long}
    table = {**{tuple(enc.prompt(r, tail=S.STEPS_TAIL)[0]): gen[i] for i, r in enumerate(rows)}, **{tuple(S.gold_prompt(enc, r)): gold[i] for i, r in enumerate(rows)}}
    seen, cur = [], {}

    def prefill(runner_, ps):
        cur["ps"] = ps
        return None, None, None

    def decode(runner_, board, C, mask, p, last, kv, max_new=None, eos=1, **kw):
        seen.append(max_new)
        return [enc.ids(table[tuple(q)]) for q in cur["ps"]]

    monkeypatch.setattr(B, "prefill", prefill)
    monkeypatch.setattr(B, "decode", decode)
    a.eval_bsz = 100
    e = K.eval_written(runner, enc, rows, CPU, a)
    # 0 hit; 1 hit (the final full stop is normalised away); 2 no marker; 3 wrong ("no" for "yes"); 4 wrong; 5 the answer is cut at MAX_NEW tokens, as eval_greedy would cut it: a miss
    assert e["hits"] == "110000" and e["n"] == 6 and e["row_offset"] == 0
    assert abs(e["marker_rate"] - 5 / 6) < 1e-9 and abs(e["mean_gen_tokens"] - sum(len(enc.ids(gen[i])) for i in range(6)) / 6) < 1e-9 and seen == [K.MAX_NEW_STEPS]
    g = K.eval_written(runner, enc, rows, CPU, a, gold=True)  # the format check reads the tokens after the given "The answer is:"; no marker needed
    assert g["hits"] == "111000" and g["marker_rate"] is None and seen[-1] == T.MAX_NEW


def test_ws_needs_rows_with_steps():
    fx = TK.fixture()
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "data"
        d.mkdir()
        for sp in ("train", "dev", "validation"):
            rows = T.read_jsonl(Path(fx["data"]) / f"{sp}.jsonl")
            (d / f"{sp}.jsonl").write_text("".join(json.dumps({k: v for k, v in r.items() if k not in ("steps", "steps_src")}) + "\n" for r in rows))
        for arm in ("ws", "tsd"):
            a = TK.arm_args(arm, 0, "nosteps_" + arm, steps=1)
            a.data = str(d)
            with pytest.raises(SystemExit, match="needs rows with a 'steps' field"):
                K.run_arm(a)


# ---------------------------------------------------------------- the step decoder

def decoder_fixture():
    fx = TK.fixture()
    a, lm, tok, enc = tiny()
    pm = K.lora_model(lm, Path(fx["root"]) / "base" / "a_s0" / "adapter")
    runner = T.Runner(pm.base_model.model)
    torch.manual_seed(0)
    board = B.ThinkBoard.from_model(runner.lm, tok, K=4)
    sd = K.build_decoder(pm, runner, board, CPU, 0)
    with torch.no_grad():  # LoRA B starts at 0 (= no effect): give both adapters real weights so that switching them has teeth
        for n, p in pm.named_parameters():
            if "lora_B" in n:
                p.normal_(std=0.1)
        sd.proj.weight.add_(0.05 * torch.randn_like(sd.proj.weight))
    return a, pm, runner, board, sd, enc, tok


def active(pm):
    return {tuple(m._active_adapter) for m in pm.modules() if hasattr(m, "lora_A") and hasattr(m, "_active_adapter")}


def test_decoder_reads_only_the_notes_with_its_own_adapter():
    a, pm, runner, board, sd, enc, tok = decoder_fixture()
    rows = rows_with_steps(12)
    notes = torch.randn(3, 4, 64) * 0.1
    seqs = [S.decoder_targets(enc, rows[i])[0][:2] for i in (1, 2, 4)]
    seqs[0] = ([], seqs[0][1])  # an answer-style target without a prefix
    lg0 = sd.logits(pm, runner, notes, seqs)[0].detach()
    assert active(pm) == {("default",)}, "the main adapter must be active again after a decoder pass"
    n_main = sum(p.requires_grad for n, p in pm.named_parameters() if ".default." in n)
    n_dec = sum(p.requires_grad for n, p in pm.named_parameters() if ".dec." in n)
    assert n_main == n_dec > 0, "both adapters are trainable"
    # (1) main LoRA off during the pass: perturbing it changes nothing; the decoder's own adapter does
    saved = {n: p.detach().clone() for n, p in pm.named_parameters() if "lora_" in n}
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if ".default." in n:
                p.add_(torch.randn_like(p))
    assert torch.equal(sd.logits(pm, runner, notes, seqs)[0], lg0), "main LoRA leaked into the decoder pass"
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if ".default." in n:
                p.copy_(saved[n])
            if ".dec." in n:
                p.add_(torch.randn_like(p))
    assert (sd.logits(pm, runner, notes, seqs)[0] - lg0).abs().max() > 1e-3, "the decoder's adapter has no effect"
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if ".dec." in n:
                p.copy_(saved[n])
    # (2) the decoder adapter does not touch the answer path
    mb = [enc.train_example(r) for r in rows[:3]]
    s0 = float(K.answer_loss_fixed(runner, mb, CPU)[0])
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if ".dec." in n:
                p.add_(torch.randn_like(p))
    assert float(K.answer_loss_fixed(runner, mb, CPU)[0]) == s0
    with torch.no_grad():
        for n, p in pm.named_parameters():
            if ".dec." in n:
                p.copy_(saved[n])
    # (3) logits depend on the notes alone: other stories (different prompts, different notes from think) with the notes held fixed give the same logits
    ctx_a, ctx_b = [enc.prompt(rows[i])[0] for i in (1, 2, 3)], [enc.prompt(rows[i + 4])[0] for i in (1, 2, 3)]
    for ctx in (ctx_a, ctx_b):
        C, mask, p = B.prefill(runner, ctx)
        e = B.think(board, runner, C, mask, p, 2, keep=(), stats=False)[1]["e"]
        assert e[-1].shape == (3, 4, 64)
        assert torch.equal(sd.logits(pm, runner, notes, seqs)[0], lg0), "decoder logits changed with the story while the notes were fixed"
    # a row's logits do not depend on the other rows of the batch (right padding is masked) ...
    one = sd.logits(pm, runner, notes[:1], seqs[:1])[0]
    assert torch.allclose(one, lg0[: len(one)], atol=1e-5)
    # ... nor on tokens after the position (causal)
    t = seqs[1][1]
    seq_x = [(seqs[1][0], t[:1] + [t[1] ^ 1] + t[2:])]  # change the second target token: predictions 0 and 1 cannot see it, later ones can
    base = sd.logits(pm, runner, notes[1:2], [seqs[1]])[0]
    alt = sd.logits(pm, runner, notes[1:2], seq_x)[0]
    assert torch.allclose(alt[:2], base[:2], atol=1e-5) and (alt[2:] - base[2:]).abs().max() > 1e-4, "not causal"
    # (4) gradients: the step loss alone reaches the decoder adapter, the Linear and the notes, and not the main LoRA
    for q in pm.parameters():
        q.grad = None
    nt = notes.clone().requires_grad_(True)
    ce, n = sd.step_ce(pm, runner, nt, seqs)
    ce.backward()
    assert n == sum(len(s[1]) for s in seqs) and nt.grad.abs().sum() > 0 and sd.proj.weight.grad.abs().sum() > 0
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for n_, p in pm.named_parameters() if ".dec." in n_)
    assert all(p.grad is None for n_, p in pm.named_parameters() if ".default." in n_), "main LoRA got a gradient from the decoder pass"


def test_step_loss_reaches_refiner_and_main_lora():
    """Through the notes, a step loss with shut gates still trains the refiner and (via the backbone states it reads) the main LoRA."""
    a, pm, runner, board, sd, enc, tok = decoder_fixture()
    rows = rows_with_steps(12)[1:5]
    assert float(board.alpha.abs().max()) == 0.0
    C, mask, p, lt, ans = K.micro_inputs(runner, [enc.train_example(r) for r in rows], CPU)
    for q in pm.parameters():
        q.grad = None
    lb, info = B.train_loss(board, runner, C, mask, p, lt, ans, 4, n_norm=sum(len(x) for x in ans), lam=0.0, ckpt=True)
    dts = [S.decoder_targets(enc, r) for r in rows]
    n_lap = [sum(len(d[k][1]) for d in dts) for k in range(4)]
    ls = K.sd_micro_loss(sd, pm, runner, info, dts, n_lap)
    assert len(info["e"]) == 5 and ls.requires_grad
    lb.backward(retain_graph=True)
    assert all(q.grad is None or float(q.grad.abs().sum()) == 0 for q in board.blocks.parameters()), "with shut gates the answer loss should not reach the refiner"
    ls.backward()
    assert any(q.grad is not None and float(q.grad.abs().sum()) > 0 for q in board.blocks.parameters()), "step loss did not reach the refiner"
    assert any(q.grad is not None and float(q.grad.abs().sum()) > 0 for n, q in pm.named_parameters() if ".default." in n), "step loss did not reach the main LoRA"


def test_lap_notes_and_sd_loss_normalisation():
    e = [torch.full((2, 3), float(k)) for k in range(5)]
    assert [float(x[0, 0]) for x in S.lap_notes(e, 4)] == [1.0, 2.0, 3.0, 4.0]
    one = S.lap_notes(e[:2], 1)
    assert len(one) == 4 and all(x is e[1] for x in one), "tsd1: the lap-1 notes feed all four decoder passes"
    a, pm, runner, board, sd, enc, tok = decoder_fixture()
    rows = rows_with_steps(12)[1:5]
    dts = [S.decoder_targets(enc, r) for r in rows]
    n_lap = [sum(len(d[k][1]) for d in dts) for k in range(4)]
    info = {"e": [torch.randn(4, 4, 64) * 0.1 for _ in range(5)]}
    whole = K.sd_micro_loss(sd, pm, runner, info, dts, n_lap)
    halves = sum(K.sd_micro_loss(sd, pm, runner, {"e": [x[i:i + 2] for x in info["e"]]}, dts[i:i + 2], n_lap) for i in (0, 2))
    assert abs(float(whole) - float(halves)) < 1e-4, "micro-batch step losses must add up to the optimizer-step loss"
    manual = [sd.step_ce(pm, runner, info["e"][k + 1], [(d[k][0], d[k][1]) for d in dts])[0] / n_lap[k] for k in range(4)]
    assert abs(float(whole) - float(torch.stack(manual).mean())) < 1e-5, "loss = mean over the 4 laps of the per-lap token-mean CE, weight 1"


# ---------------------------------------------------------------- tsd vs tsd1, lesions, decoder accuracy

def run_sd(arm, steps=2, sub=None):
    TK.fixture()
    seen = []
    real = K.sd_micro_loss

    def spy(sd, pm, runner, info, dts, n_lap):
        seen.append(dict(n_e=len(info["e"]), dts=dts, n_lap=n_lap))
        return real(sd, pm, runner, info, dts, n_lap)

    K.sd_micro_loss = spy
    try:
        a = TK.arm_args(arm, 0, sub or "sd_" + arm, steps=steps, extra=("--limit-eval", "6"))
        assert K.run_arm(a) == 0
    finally:
        K.sd_micro_loss = real
    return a, json.loads((Path(a.out) / f"result_{arm}_s0.json").read_text()), seen


def test_tsd_and_tsd1_match_except_the_number_of_laps():
    a4, r4, s4 = run_sd("tsd")
    a1, r1, s1 = run_sd("tsd1")
    assert r4["params_trainable"] == r1["params_trainable"] and r4["sd_params"] == r1["sd_params"], (r4["sd_params"], r1["sd_params"])
    p = r4["sd_params"]
    assert r4["params_trainable"] == p["board"] + p["lora"] + p["dec_lora"] + p["proj"] and p["dec_lora"] == p["lora"] == 146_176
    assert r4["lmax"] == 4 and r1["lmax"] == 1 and all(x["L_max"] == 4 for x in r4["train"]["gate_log"]) and all(x["L_max"] == 1 for x in r1["train"]["gate_log"])
    assert [x["n_e"] for x in s4] == [5] * len(s4) and [x["n_e"] for x in s1] == [2] * len(s1) and len(s4) == len(s1) == 2 * 2  # 2 steps x 2 micro-batches
    assert [x["dts"] for x in s4] == [x["dts"] for x in s1] and [x["n_lap"] for x in s4] == [x["n_lap"] for x in s1], "same rows, same decoder targets, same normalisation"
    assert len(r4["train"]["sd_losses"]) == len(r1["train"]["sd_losses"]) == 2 and all(x > 0 for x in r4["train"]["sd_losses"])
    for r, arm in ((r4, "tsd"), (r1, "tsd1")):
        for split, want in TK.EXPECT[arm].items():
            assert set(r["eval"][split]) == want, (arm, split, set(r["eval"][split]))
        d = r["decoder"]
        assert 0 <= d["true"] <= 100 and 0 <= d["swap"] <= 100 and abs(d["gap"] - (d["true"] - d["swap"])) < 1e-9 and d["tokens"] > 0 and d["partner_same_story_rows"] == 0
        assert set(d["by_lap"]) == {"1", "2", "3", "4"}
    blk = torch.load(Path(a4.out) / "think_block.pt")
    assert "decoder" in blk and set(blk["decoder"]) == {"proj.weight", "proj.bias"}
    ad = Path(a4.out) / "adapter"
    assert (ad / "adapter_config.json").exists() and (ad / "dec" / "adapter_config.json").exists() and r4["adapter_sha"]
    assert r4["train"]["loss_curve"] and r4["train"]["gate_log"] and "declora" in r4["train"]["gate_log"][0]["grad_norm"] and "decproj" in r4["train"]["gate_log"][0]["grad_norm"]
    # the lesions: zero notes read 0, so zero4 equals gates-off row for row; random notes are a real change
    v = r4["eval"]["validation"]
    assert v["zero4"]["hits"] == v["gatesoff4"]["hits"] == v["ref0"]["hits"]
    with pytest.raises(SystemExit, match="--lmax must be 4"):
        K.run_arm(TK.arm_args("tsd", 0, "sd_bad", steps=1, extra=("--lmax", "3")))


def test_random_lesion_has_the_real_notes_norm(monkeypatch):
    a, pm, runner, board, sd, enc, tok = decoder_fixture()
    rows = rows_with_steps(12)[:4]
    C, mask, p = B.prefill(runner, [enc.prompt(r)[0] for r in rows])
    e = B.think(board, runner, C, mask, p, 2, keep=(), stats=False)[1]["e"][2]
    got = {}
    real = B.slot_pass
    monkeypatch.setattr(B, "slot_pass", lambda runner_, x, *a_, **k_: (got.update(x=x), real(runner_, x, *a_, **k_))[1])
    K.random_notes_kv(runner, e, C, mask, p, 5)
    x = got["x"]
    assert x.shape == e.shape and not torch.allclose(x, e)
    assert torch.allclose(x.norm(dim=-1), e.norm(dim=-1), rtol=1e-4), "random notes must have the real notes' per-slot norm"
    got.clear()
    K.random_notes_kv(runner, e, C, mask, p, 5)
    assert torch.equal(got["x"], x), "same seed, same random notes"
    got.clear()
    K.random_notes_kv(runner, e, C, mask, p, 6)
    assert not torch.equal(got["x"], x)


def test_decoder_eval_swaps_in_another_stories_notes(monkeypatch):
    a, pm, runner, board, sd, enc, tok = decoder_fixture()
    a.eval_bsz = 5
    rows = [r for r in rows_with_steps(24) if r["steps"]]
    assert len({r["visit_id"] for r in rows}) >= 3
    calls = []
    real = sd.token_hits
    monkeypatch.setattr(sd, "token_hits", lambda pm_, runner_, notes, seqs: (calls.append((notes.clone(), seqs)), real(pm_, runner_, notes, seqs))[1])
    d = K.eval_decoder(runner, pm, board, sd, enc, rows, a, CPU, 4)
    assert d["rows"] == len(rows) and d["partner_same_story_rows"] == 0 and d["tokens"] > 0 and set(d["by_lap"]) == {"1", "2", "3", "4"}
    # recompute every row's lap notes independently, then identify the row each swapped call used
    prompts = [enc.prompt(r)[0] for r in rows]
    C, mask, p = B.prefill(runner, prompts)
    e = B.think(board, runner, C, mask, p, 4, keep=(), stats=False)[1]["e"]
    notes = [x for x in S.lap_notes(e, 4)]
    true_calls, swap_calls = calls[0::2], calls[1::2]
    assert len(true_calls) == len(swap_calls) > 0
    for (nt, seq_t), (ns, seq_s) in zip(true_calls, swap_calls):
        assert seq_t == seq_s
        lap = next(k for k in range(4) if all(any(torch.allclose(nt[i], notes[k][j], atol=1e-4) for j in range(len(rows))) for i in range(len(nt))))
        for i in range(len(nt)):
            own = next(j for j in range(len(rows)) if torch.allclose(nt[i], notes[lap][j], atol=1e-4))
            other = next(j for j in range(len(rows)) if torch.allclose(ns[i], notes[lap][j], atol=1e-4))
            assert rows[other]["visit_id"] != rows[own]["visit_id"], "swapped notes must come from another story"
            assert min(len(rows[other]["steps"]), 4) == min(len(rows[own]["steps"]), 4)
            assert not torch.allclose(nt[i], ns[i])
    # all-equal rows from one story: nothing to swap with (counted, not hidden)
    one = [dict(r, visit_id="v0") for r in rows]
    assert K.eval_decoder(runner, pm, board, sd, enc, one, a, CPU, 4)["partner_same_story_rows"] == len(one)
