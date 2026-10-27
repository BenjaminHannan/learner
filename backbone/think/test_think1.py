"""All Think-1 CPU tests (IMPL-SPEC section 5):  python backbone/think/test_think1.py [--real] [--only NAME ...]

T1-T7, T9, T10 + TP/TC/TR/TB come from test_think1_board.py, X1-X4 from test_xent.py, S1 from test_summarize.py. Here: T8 (same seed,
same stage-2 losses), TO (data order = train.py's), TH (hits are stored in file order; gates off = arm a), TG (mechanics gate, incl. the
abort path), TR (run_box.sh job order and skips, stub python), TS (spec defaults), SM (`think1.py --smoke` end to end, then summarize prints a verdict line).
Test names for --only: BOARD (T1-T7, T9, T10, TP, TC, TR-api, TB), XENT, S1, S4, T8, TO, TH, TG, TJ, TF, TCTRL, TR, TS, AI, SM.
Needs the venv with torch CPU, transformers 5.20.2 and peft; `--real` adds the real-0.8B checks (HF_HOME=<cache> HF_HUB_OFFLINE=1).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import think1 as K  # noqa: E402
import board as B  # noqa: E402
import train as T  # noqa: E402

VILLAGE = "/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/village"
_FX = {}


def fixture():
    """Shared temp dir with smoke data (village rows if present, else synthetic) and a finished smoke arm a, seed 0 (its adapter feeds the stage-2 arms)."""
    if not _FX:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        data = K.smoke_data(VILLAGE, root)
        _FX.update(tmp=tmp, root=root, data=data)
        rc = K.run_arm(arm_args("a", 0, "base"))
        assert rc == 0
    return _FX


def arm_args(arm, seed, sub, steps=6, extra=()):
    r = Path(_FX["root"]) if _FX else None
    if r is None:
        raise RuntimeError("call fixture() first")
    a = K.parse(["--smoke", "--arm", arm, "--seed", str(seed), "--out", str(r / sub / f"{arm}_s{seed}"), "--data", str(_FX["data"]),
                 "--steps", str(steps), "--limit-eval", "4", "--a-adapter", str(r / "base" / "a_s0" / "adapter"), *extra])
    a.steps1, a.max_len, a.bsz, a.micro_bsz, a.log_every = 6, 256, 8, 4, 10**6
    return a


def load(args):
    return json.loads((Path(args.out) / f"result_{args.arm}_s{args.seed}.json").read_text())


# ---------------------------------------------------------------- T8, TO

def test_t8_same_seed_same_losses():
    fixture()
    out = {}
    for name, arm, seed in (("r1", "t", 0), ("r2", "t", 0), ("r3", "t", 1), ("r4", "a", 0), ("r5", "a", 0)):
        a = arm_args(arm, seed, name, steps=10)
        assert K.run_arm(a) == 0
        out[name] = load(a)
    l1, l2, l3 = (out[k]["train"]["step_losses"] for k in ("r1", "r2", "r3"))
    assert len(l1) == 10 and l1 == l2, "same seed, different stage-2 losses"
    assert l1 != l3, "different seed gave the same losses (the control has no teeth)"
    assert out["r4"]["train"]["step_losses"] == out["r5"]["train"]["step_losses"] and len(out["r4"]["train"]["step_losses"]) == 10
    assert out["r1"]["eval"] == out["r2"]["eval"]
    s1 = torch.load(Path(arm_args("t", 0, "r1").out) / "think_block.pt")["state_dict"]
    s2 = torch.load(Path(arm_args("t", 0, "r2").out) / "think_block.pt")["state_dict"]
    assert all(torch.equal(s1[k], s2[k]) for k in s1), "trained boards differ for the same seed"
    print(f"T8 same seed -> identical 10-step losses {['%.4f' % x for x in l1[:3]]}..., boards equal; seed 1 differs ({l3[0]:.4f} vs {l1[0]:.4f}); stage-1 arm a also identical")


def test_to_data_order():
    """Stage 1 draws rows exactly as train.py does; stage 2 uses Random(seed + 1000) and is the same stream for every stage-2 arm."""
    n, seed, bsz = 100, 3, 16
    rng, order_idx, want = random.Random(seed), [], []
    for _ in range(9):  # train.py's loop, verbatim
        if not order_idx:
            order_idx = list(range(n))
            rng.shuffle(order_idx)
        want.append([order_idx.pop() for _ in range(min(bsz, len(order_idx)))])
    g = K.batches(n, seed, bsz)
    assert [next(g) for _ in range(9)] == want
    g1, g2 = K.batches(n, seed + 1000, bsz), K.batches(n, seed + 1000, bsz)
    assert [next(g1) for _ in range(5)] == [next(g2) for _ in range(5)]
    assert next(K.batches(n, seed, bsz)) != next(K.batches(n, seed + 1000, bsz))
    steps1 = [i for _ in range(0, 1) for i in next(K.batches(86238, 0, 16))]
    print(f"TO data order = train.py's (first stage-1 batch {steps1[:4]}...), stage-2 stream is seed+1000 and shared")


# ---------------------------------------------------------------- TH, TG

def test_th_hits_in_file_order_and_gates_off_is_arm_a():
    fx = fixture()
    from peft import PeftModel
    a = arm_args("t", 0, "th")
    lm, tok = T.load_model(a, torch.device("cpu"), torch.float32)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)  # token-dependent logits, and no all-zero padding row
    pm = PeftModel.from_pretrained(lm, str(Path(fx["root"]) / "base" / "a_s0" / "adapter")).eval()
    r = T.Runner(pm.base_model.model)
    enc = T.Encoder(tok, 256)
    rows = T.read_jsonl(Path(fx["data"]) / "validation.jsonl")
    # make the answers equal to arm a's own greedy output for every other row, so hits are 1 exactly there and the check has teeth
    prompts = [enc.prompt(x)[0] for x in rows]
    preds = [T.greedy(r, [p], torch.device("cpu"), enc.eos)[0] for p in prompts]
    rows = [dict(x, answer=tok.decode(p, skip_special_tokens=True) if i % 2 == 0 else "zzz-never") for i, (x, p) in enumerate(zip(rows, preds))]
    want = "".join("1" if i % 2 == 0 else "0" for i in range(len(rows)))
    args = K.parse(["--smoke", "--out", "/tmp/unused", "--eval-bsz", "4"])
    for rev in (False, True):
        e = K.eval_greedy(r, enc, rows, torch.device("cpu"), args, reverse=rev)
        assert e["hits"] == want and e["n"] == len(rows) and e["row_offset"] == 0, (rev, e["hits"], want)
        eb = K.eval_greedy(r, enc, rows, torch.device("cpu"), args, reverse=rev, board_path=True)  # arm a / aplus path: board.prefill + board.decode, no board
        assert eb["hits"] == e["hits"] == want and eb["n"] == e["n"], ("board path != T.greedy", rev, eb["hits"], e["hits"])
    ids = [T.greedy(r, [p], torch.device("cpu"), enc.eos)[0] for p in prompts[:6]]
    C, mask, pl = B.prefill(r, prompts[:6])
    assert B.decode(r, None, C, mask, pl, B.last_ids(prompts[:6], torch.device("cpu")), None, eos=enc.eos) == ids, "decoded ids differ between the two paths"
    torch.manual_seed(0)
    board = B.ThinkBoard.from_model(r.lm, tok, K=4)
    with torch.no_grad():
        board.alpha.copy_(3 * torch.randn_like(board.alpha))
    tags = {"gatesoff8": ("off", 8, None), "ref0": ("none", 8, None), "L16": ("plain", 16, 6), "swap8": ("swap", 8, None), "mean8": ("mean", 8, None), "rep1_8": ("rep", 8, None)}
    ev = K.eval_board(r, board, enc, rows, tags, args, torch.device("cpu"))
    assert ev["gatesoff8"]["hits"] == want, "gates off must equal arm a, row for row, in file order"
    assert ev["ref0"]["hits"] == ev["gatesoff8"]["hits"], "gates off must equal the board-free decode of the same batches, row for row"
    assert ev["L16"]["n"] == 6 and len(ev["L16"]["hits"]) == 6, "L16 is scored on the first nmax rows only"
    assert all(len(ev[t]["hits"]) == len(rows) for t in ("swap8", "mean8", "rep1_8"))
    # arms a / aplus must see eval_board's exact batches: it sorts rows < HEAD and the rest separately, and no batch spans the boundary
    old_head, seen, real_prefill = K.HEAD, [], B.prefill
    def spy(runner, ps, *x, **y):
        seen[-1].append(tuple(tuple(q) for q in ps))
        return real_prefill(runner, ps, *x, **y)
    try:
        K.HEAD, B.prefill = 5, spy
        assert len(rows) > 5 and (5 % args.eval_bsz) != 0, "the boundary check needs a boundary inside a would-be batch"
        seen.append([])
        eg = K.eval_greedy(r, enc, rows, torch.device("cpu"), args, board_path=True)
        seen.append([])
        er = K.eval_board(r, board, enc, rows, {"ref0": ("none", 0, None)}, args, torch.device("cpu"))
    finally:
        K.HEAD, B.prefill = old_head, real_prefill
    assert seen[0] == seen[1] and len(seen[0]) > 1, "eval_greedy(board_path) and eval_board batches differ"
    assert eg["hits"] == er["ref0"]["hits"] == want, "same batches, same code: hits must match row for row"
    mb = [enc.train_example(x) for x in rows[:3]]  # open gates must move the logits, or the gates-off equality above says nothing
    C, mask, p, lt, ans = K.micro_inputs(r, mb, torch.device("cpu"))
    with torch.no_grad():
        kv = B.think(board, r, C, mask, p, 2, keep={2}, stats=False)[0][2]
        on = B.answer_logits(r, board.gate(), C, mask, p, lt, ans, kv)[0]
        off = B.answer_logits(r, torch.zeros_like(board.alpha), C, mask, p, lt, ans, kv)[0]
    assert (on - off).abs().max() > 1e-3, "open gates change nothing: the gates-off check is vacuous"
    print(f"TH hits in file order (descending and reversed batches); gatesoff8 == arm a on {len(rows)} rows; arm a's batches == eval_board's (HEAD=5); board hits {ev['swap8']['hits']} (swap), {ev['mean8']['hits']} (mean)")


def test_tg_mechanics_gate():
    ok = dict(alpha_mean=0.05, cos_across=0.5, clamp5=0.1)
    assert K.gate_reason(ok) is None
    assert "alpha" in K.gate_reason({**ok, "alpha_mean": 0.019})
    assert K.gate_reason({**ok, "alpha_mean": 0.02}) is None  # threshold is strict
    # amended before any run: board cosine and clamp share are logs, never aborts (they sit at ~0.99 and ~94% at step 0 on the real model)
    assert K.gate_reason({**ok, "cos_across": 0.999, "clamp5": 1.0, "clamp": 1.0}) is None
    assert set(K.GATE) == {"alpha", "div", "window"}
    # a saturated, question-specific one-lap board (e_1 = clamp(e_0 + rho * eta * sign), eta 0.1): its cross-question cosine stays > 0.95, and the gate lets it through
    g = torch.Generator().manual_seed(0)
    rho, e0 = 0.0195, torch.randn(16, 1024, generator=g)
    e0 = B.clamp_rms(e0 / e0.pow(2).mean(-1, keepdim=True).sqrt() * rho, rho)
    e1 = B.clamp_rms(e0[None] + rho * 0.1 * torch.sign(torch.randn(16, 16, 1024, generator=g)), rho)
    cos = float(B._cos(e1)[1])
    assert cos > 0.95, cos
    assert K.gate_reason({**ok, "cos_across": cos}) is None
    assert not K.diverged([1.0] * 20) and not K.diverged([1.0] * 20 + [1.9] * 20) and K.diverged([1.0] * 20 + [2.1] * 20)
    assert not K.diverged([1.0] * 19 + [50.0])  # needs more than 20 steps
    fx = fixture()
    a = arm_args("t", 0, "gate", steps=6, extra=("--gate-step", "2", "--gate-enforce"))
    a.log_every = 10**6
    rc = K.run_arm(a)
    res = load(a)
    assert rc == 3 and res["aborted"] and "mechanics gate at step 2" in res["aborted"], res["aborted"]
    assert res["eval"] == {"validation": {}, "dev": {}} and len(res["train"]["step_losses"]) == 2
    assert (Path(a.out) / "think_block.pt").exists()
    from subprocess import run
    r = run([sys.executable, str(HERE / "think1.py"), "--smoke", "--arm", "t", "--seed", "0", "--out", str(Path(fx["root"]) / "gate2"), "--gate-step", "2",
             "--gate-enforce", "--steps", "4", "--limit-eval", "4"], capture_output=True, text=True, cwd=str(HERE.parent.parent))
    # the CLI path needs the smoke a adapter in gate2/smoke/a_s0, which does not exist: it must fail loudly, not silently
    assert r.returncode != 0 and "needs the stage-1 adapter" in (r.stdout + r.stderr), r.stderr[-300:]
    print(f"TG only the gates-shut check aborts (a saturated one-lap board with cosine {cos:.3f} passes); divergence rule; abort path: exit 3, aborted={res['aborted']!r}, no eval; missing adapter -> clear error")


# ---------------------------------------------------------------- TJ (arm tj, joint LoRA + board)

def test_tj_joint():
    """tj: at step 0 (zero gates) the board read equals arm a; gradients reach the LoRA through the checkpointed slot / answer passes (same as without
    checkpointing); training moves LoRA weights and the gates; both artefacts, params, lmax and tags are recorded."""
    fx = fixture()
    from safetensors.torch import load_file
    cpu, ad = torch.device("cpu"), Path(fx["root"]) / "base" / "a_s0" / "adapter"
    a = arm_args("tj", 0, "tj", steps=6)
    lm, tok = T.load_model(a, cpu, torch.float32)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)
    pm = K.lora_model(lm, ad)
    r = T.Runner(pm.base_model.model)
    enc = T.Encoder(tok, 256)
    rows = T.read_jsonl(Path(fx["data"]) / "train.jsonl")[:4]
    mb = [enc.train_example(x) for x in rows]
    lora = [p for p in pm.parameters() if p.requires_grad]
    assert lora and all(p.requires_grad for n, p in pm.named_parameters() if "lora_" in n), "tj LoRA must be trainable"
    torch.manual_seed(0)
    board = B.ThinkBoard.from_model(r.lm, tok, K=4)
    C, mask, p, lt, ans = K.micro_inputs(r, mb, cpu)
    with torch.no_grad():  # step 0: zero gates -> the answer pass with the board read is arm a's, and so is the greedy decode
        kv = B.think(board, r, C, mask, p, 2, keep={2}, stats=False)[0][2]
        s_b, _ = B.answer_ce(r, board, C, mask, p, lt, ans, kv)
        s_a, _ = K.answer_loss_fixed(r, mb, cpu)
        d0 = B.decode(r, board, C, mask, p, lt, kv, eos=enc.eos)
        d1 = B.decode(r, None, C, mask, p, lt, None, eos=enc.eos)
    assert abs(float(s_a) - float(s_b)) < 1e-4 * max(1.0, abs(float(s_a))) and d0 == d1, (float(s_a), float(s_b))
    # gradient to the LoRA through the closures: open gates, compare with and without checkpointing (the answer pass alone also reaches the LoRA, so compare, not just test > 0)
    with torch.no_grad():
        board.alpha.fill_(1.0)
    g = {}
    for ck in (True, False):
        for q in lora:
            q.grad = None
        loss, _ = B.train_loss(board, r, C, mask, p, lt, ans, 2, lam=0.01, ckpt=ck)
        loss.backward()
        g[ck] = [q.grad.clone() for q in lora if q.grad is not None]
    assert len(g[True]) == len(g[False]) > 0 and sum(float(x.abs().sum()) for x in g[True]) > 0
    assert all(torch.allclose(x, y, rtol=1e-3, atol=1e-6) for x, y in zip(g[True], g[False])), "checkpointed passes give the LoRA different gradients"
    # end to end
    before = {k: v.clone() for k, v in load_file(str(ad / "adapter_model.safetensors")).items()}
    assert K.run_arm(a) == 0
    res = load(a)
    out = Path(a.out)
    after = load_file(str(out / "adapter" / "adapter_model.safetensors"))
    moved = [k for k in before if not torch.equal(before[k], after[k])]
    assert moved, "tj LoRA weights did not change"
    blk = torch.load(out / "think_block.pt")
    assert blk["arm"] == "tj" and float(blk["state_dict"]["alpha"].abs().max()) > 0, "board alpha did not move"
    assert res["lmax"] == 4 and res["k_slots"] == 16 and res["adapter_sha"] and res["adapter_sha"] != res["stage1_adapter_sha"]
    assert res["params_trainable"] == 1_643_656 + 146_176 and len(res["train"]["step_losses"]) == 6 and res["train"]["gate_log"] and all(x["L_max"] == 4 for x in res["train"]["gate_log"])
    assert "lora" in res["train"]["gate_log"][0]["grad_norm"]
    for split, want in EXPECT["tj"].items():
        assert set(res["eval"][split]) == want, (split, set(res["eval"][split]))
    assert K.tags_for("t", "dev") == K.tags_for("t", "dev", 4) and K.tags_for("tj", "validation", 3)["swap3"] == ("swap", 3, None)
    print(f"TJ step 0 board read == arm a (CE {float(s_a):.4f}); checkpointed LoRA gradients == uncheckpointed ({len(g[True])} tensors); 6 joint steps moved {len(moved)} LoRA tensors and alpha; lmax/params/tags recorded")


# ---------------------------------------------------------------- TF (arm tf, forced-then-released blind answer passes)

def test_tf_forced():
    """tf: p_blind schedule; blind answer passes hide the whole prompt (CE differs from the sighted one; logits and decode are unchanged when the prompt
    tokens change, so no leak through attention or DeltaNet state) while the board read still acts; a short run trains, moves LoRA and alpha, logs
    blind_steps (the Random(seed + 3000) draws) and scores blind4; with --blind-p 0 tf's losses equal tj's."""
    fx = fixture()
    from safetensors.torch import load_file
    cpu, ad = torch.device("cpu"), Path(fx["root"]) / "base" / "a_s0" / "adapter"
    a = K.parse(["--arm", "tf", "--out", "x"])
    assert (a.blind_p, a.blind_until) == (0.5, 0.6)
    st = 1000
    got = [K.p_blind(s, st, a) for s in (0, int(0.3 * st), int(0.6 * st), st - 1)]
    assert all(abs(x - y) < 1e-12 for x, y in zip(got, [0.5, 0.25, 0.0, 0.0])) and K.p_blind(900, st, a) == 0.0, got
    assert K.tags_for("tf", "validation", 4)["blind4"] == ("blind", 4, 2000) and set(K.tags_for("tf", "dev")) == {"L4"} and "blind4" not in K.tags_for("tj", "validation")
    # leak test on the random-embedding model (every layer type matters)
    args = arm_args("tf", 0, "tf", steps=6)
    lm, tok = T.load_model(args, cpu, torch.float32)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=0.5)
    pm = K.lora_model(lm, ad)
    r = T.Runner(pm.base_model.model)
    enc = T.Encoder(tok, 256)
    rows = T.read_jsonl(Path(fx["data"]) / "train.jsonl")[:4]
    mb = [enc.train_example(x) for x in rows]
    torch.manual_seed(0)
    board = B.ThinkBoard.from_model(r.lm, tok, K=4)
    with torch.no_grad():
        board.alpha.fill_(1.0)
    C, mask, p, lt, ans = K.micro_inputs(r, mb, cpu)
    g = torch.Generator().manual_seed(5)
    mb2 = [([int(x) for x in torch.randint(5, lm.model.embed_tokens.weight.shape[0], (len(pr) - 1,), generator=g)] + [pr[-1]], an) for pr, an in mb]
    assert all(len(x[0]) == len(y[0]) and x[0][:-1] != y[0][:-1] for x, y in zip(mb, mb2))
    C2, mask2, p2, lt2, _ = K.micro_inputs(r, mb2, cpu)
    assert torch.equal(p, p2) and torch.equal(lt, lt2)
    with torch.no_grad():
        kv = B.think(board, r, C, mask, p, 2, keep={2}, stats=False)[0][2]
        zero = torch.zeros_like(board.alpha)
        for gates in (zero, None):  # gates shut, and open (same slot K/V in both prompts: only the answer-side prompt context may differ)
            sighted = B.answer_logits(r, zero if gates is not None else board.gate(), C, mask, p, lt, ans, kv)[0]
            b1 = B.answer_logits(r, zero if gates is not None else board.gate(), C, mask, p, lt, ans, kv, blind=True)[0]
            b2 = B.answer_logits(r, zero if gates is not None else board.gate(), C2, mask2, p2, lt2, ans, kv, blind=True)[0]
            s2 = B.answer_logits(r, zero if gates is not None else board.gate(), C2, mask2, p2, lt2, ans, kv)[0]
            assert torch.equal(b1, b2), "blind logits depend on the prompt"
            assert not torch.allclose(sighted, s2, atol=1e-4), "test prompts do not change the sighted pass"
            assert not torch.allclose(sighted, b1, atol=1e-4), "blind equals sighted: context not hidden"
        c_blind, _ = B.answer_ce(r, board, C, mask, p, lt, ans, kv, gates=zero, blind=True)
        c_sight, _ = B.answer_ce(r, board, C, mask, p, lt, ans, kv, gates=zero)
        assert abs(float(c_blind) - float(c_sight)) > 1e-3, (float(c_blind), float(c_sight))
        ob = B.answer_logits(r, zero, C, mask, p, lt, ans, kv, blind=True)[0]
        assert not torch.allclose(ob, b1, atol=1e-4), "the board read does not act in the blind pass"
        d1 = B.decode(r, board, C, mask, p, lt, kv, eos=enc.eos, blind=True)
        d2 = B.decode(r, board, C2, mask2, p2, lt2, kv, eos=enc.eos, blind=True)
        assert d1 == d2, "blind decode depends on the prompt"
    # blind decode agrees with the teacher-forced blind pass (greedy continuation of the first token)
    with torch.no_grad():
        lg, tgt, sb = B.answer_logits(r, board.gate(), C, mask, p, lt, ans, kv, blind=True)
        first = [int(lg[(sb == b).nonzero()[0, 0]].argmax()) for b in range(len(ans))]
        d = B.decode(r, board, C, mask, p, lt, kv, eos=enc.eos, blind=True, max_new=1)
        assert all((x[0] if x else enc.eos) == f for x, f in zip(d, first)), (d, first)
    # checkpointed blind gradients == uncheckpointed
    lora = [q for q in pm.parameters() if q.requires_grad]
    gr = {}
    for ck in (True, False):
        for q in lora:
            q.grad = None
        loss, _ = B.train_loss(board, r, C, mask, p, lt, ans, 2, lam=0.01, ckpt=ck, blind=True)
        loss.backward()
        gr[ck] = [q.grad.clone() for q in lora if q.grad is not None]
    assert len(gr[True]) == len(gr[False]) > 0 and all(torch.allclose(x, y, rtol=1e-3, atol=1e-6) for x, y in zip(gr[True], gr[False]))
    # end to end
    extra = ("--blind-p", "1.0", "--blind-until", "1.0")
    af = arm_args("tf", 0, "tf", steps=6, extra=extra)
    before = {k: v.clone() for k, v in load_file(str(ad / "adapter_model.safetensors")).items()}
    assert K.run_arm(af) == 0
    res, out = load(af), Path(af.out)
    after = load_file(str(out / "adapter" / "adapter_model.safetensors"))
    assert [k for k in before if not torch.equal(before[k], after[k])], "tf LoRA weights did not change"
    assert float(torch.load(out / "think_block.pt")["state_dict"]["alpha"].abs().max()) > 0
    rng = random.Random(3000)
    bs = K.batches(len(T.read_jsonl(Path(fx["data"]) / "train.jsonl")), 1000, 8)
    want = [int(rng.random() < 1.0 * max(0.0, 1 - s / 6)) for s in range(6) for _ in range(-(-len(next(bs)) // 4))]  # micro-batches of 4 rows per step
    assert res["train"]["blind_steps"] == want and 0 < sum(want), (res["train"]["blind_steps"], want)
    for split, w in EXPECT["tf"].items():
        assert set(res["eval"][split]) == w, (split, set(res["eval"][split]))
    assert res["eval"]["validation"]["blind4"]["n"] == 4 and res["blind"] == dict(p=1.0, until=1.0, seed=3000) and res["lmax"] == 4
    # blind-p 0: tf is tj
    z = arm_args("tf", 0, "tf0", steps=3, extra=("--blind-p", "0"))
    j = arm_args("tj", 0, "tj3", steps=3)
    assert K.run_arm(z) == 0 and K.run_arm(j) == 0
    lz, lj = load(z), load(j)
    assert lz["train"]["step_losses"] == lj["train"]["step_losses"] and sum(lz["train"]["blind_steps"]) == 0
    print(f"TF schedule {got}; blind logits/decode independent of the prompt, differ from sighted (CE {float(c_blind):.3f} vs {float(c_sight):.3f}), board read acts, ckpt grads equal; 6-step run blind_steps={sum(want)}/{len(want)} blind4 scored; blind-p 0 losses == tj")


# ---------------------------------------------------------------- TC (control: tj with the thinking block off)

def test_tc_control():
    """tc: tj's loop with lmax 0, alpha frozen at 0 and no board parameter in the optimizer. A few steps move the LoRA, leave alpha exactly 0 and every
    board parameter unchanged; the optimizer has only the "lora" group; the step-150 gate is skipped (reason recorded); with the same seed tc's first-step
    LoRA gradient equals tj's run with --lmax 0 (gates are 0 in both at step 0); params_trainable is the LoRA alone; tags are L0 / ref0 (dev L0)."""
    fx = fixture()
    from safetensors.torch import load_file
    ad = Path(fx["root"]) / "base" / "a_s0" / "adapter"
    assert K.tags_for("tc", "validation", 4) == {"L0": ("plain", 0, None), "ref0": ("none", 0, None)} and K.tags_for("tc", "dev", 4) == {"L0": ("plain", 0, None)}
    assert "tc" in K.ARMS and "tc" in K.STAGE2 and "tc" in K.BOARD and "tc" in K.JOINT
    seen = {}
    real_step = torch.optim.AdamW.step

    def spy(self, *a, **k):  # the clipped gradients the first optimizer step uses, and the group names
        if "names" not in seen:
            seen["names"] = [g.get("name") for g in self.param_groups]
            seen["grads"] = [q.grad.clone() for g in self.param_groups if g.get("name") == "lora" for q in g["params"] if q.grad is not None]
        return real_step(self, *a, **k)

    grads = {}
    torch.optim.AdamW.step = spy
    try:
        for arm, extra in (("tc", ()), ("tj", ("--lmax", "0"))):
            seen.clear()
            a = arm_args(arm, 0, arm + "g", steps=1, extra=extra)
            try:
                assert K.run_arm(a) == 0
            except RuntimeError:  # tj at lmax 0 has no refinement stats for its gate probe (after step 1, which is all we need here)
                assert arm == "tj" and "grads" in seen
            grads[arm] = seen["grads"]
            if arm == "tc":
                assert seen["names"] == ["lora"], seen["names"]
    finally:
        torch.optim.AdamW.step = real_step
    assert len(grads["tc"]) == len(grads["tj"]) > 0 and sum(float(x.abs().sum()) for x in grads["tc"]) > 0
    assert all(torch.allclose(x, y, rtol=1e-4, atol=1e-7) for x, y in zip(grads["tc"], grads["tj"])), "tc first-step LoRA gradient differs from tj --lmax 0"
    # a few steps end to end
    before = {k: v.clone() for k, v in load_file(str(ad / "adapter_model.safetensors")).items()}
    a = arm_args("tc", 0, "tc", steps=6)
    assert K.run_arm(a) == 0
    res, out = load(a), Path(a.out)
    after = load_file(str(out / "adapter" / "adapter_model.safetensors"))
    moved = [k for k in before if not torch.equal(before[k], after[k])]
    assert moved, "tc LoRA weights did not change"
    blk = torch.load(out / "think_block.pt")["state_dict"]
    assert float(blk["alpha"].abs().max()) == 0.0, "tc alpha moved"
    cpu = torch.device("cpu")
    torch.manual_seed(a.seed)
    lm2, tok2 = T.load_model(a, cpu, torch.float32)
    pm2 = K.lora_model(lm2, ad)
    torch.manual_seed(a.seed)  # run_arm seeds again right before building the board
    fresh = B.ThinkBoard.from_model(pm2.base_model.model, tok2, K=16).state_dict()
    assert set(fresh) == set(blk) and all(torch.equal(fresh[k], blk[k]) for k in fresh), "a board parameter changed in tc"
    n_lora = sum(p.numel() for p in pm2.parameters() if p.requires_grad)
    assert res["params_trainable"] == n_lora == 146_176 and res["lmax"] == 0 and res["train"]["gate_check"]["reason"] == "skipped (tc)"
    assert len(res["train"]["step_losses"]) == 6 and res["train"]["gate_log"] and all(x["L_max"] == 0 and x["alpha_mean"] == 0 for x in res["train"]["gate_log"])
    assert set(res["train"]["gate_log"][0]["grad_norm"]) == {"lora"}
    for split, want in EXPECT["tc"].items():
        assert set(res["eval"][split]) == want, (split, set(res["eval"][split]))
    assert res["eval"]["validation"]["L0"]["hits"] == res["eval"]["validation"]["ref0"]["hits"], "closed-board L0 differs from the no-read reference"
    print(f"TC first-step LoRA gradient == tj --lmax 0 ({len(grads['tc'])} tensors); 6 steps moved {len(moved)} LoRA tensors, alpha stays 0, board unchanged, optimizer groups ['lora'], gate skipped, params {n_lora:,}")


# ---------------------------------------------------------------- run_box.sh

STUB = r"""#!/usr/bin/env bash
script=$1; shift
echo "$(basename -- "$script") $*" >> "$LOG"
case "$script" in
  -c) [ -z "${NOCUDA:-}" ] || exit 1;;
  *think1.py)
    while [ $# -gt 0 ]; do case "$1" in --arm) arm=$2;; --seed) seed=$2;; --out) out=$2;; esac; shift; done
    case "$FAIL" in *"$arm"*) exit 1;; esac
    mkdir -p "$out"
    case ",${FAILONCE:-}," in *",$arm,"*) [ -f "$out/.failed" ] || { touch "$out/.failed"; exit 1; };; esac   # out of memory once, fine on the retry
    case ",${FAILLATE:-}," in *",$arm,"*) mkdir -p "$out/adapter"; echo '{}' > "$out/adapter/adapter_config.json"; exit 1;; esac   # adapter saved, then the eval crashed
    case "$arm" in aplus|t|t1|tw|tj|tf|tc|ws|wsham|tsd|tsd1) [ -f "$out/../a_s$seed/adapter/adapter_config.json" ] || { echo "no a adapter" >&2; exit 4; };;
                   bplus) [ -f "$out/../b_s$seed/adapter/adapter_config.json" ] || exit 4;; esac
    if [ -n "${PARDIR:-}" ]; then touch "$PARDIR/run.$$"; ls "$PARDIR" | grep -c '^run\.' >> "$PARDIR/counts"; sleep 0.4; fi
    mkdir -p "$out"; echo '{}' > "$out/result_${arm}_s${seed}.json"
    case "$arm" in a|b) mkdir -p "$out/adapter"; echo '{}' > "$out/adapter/adapter_config.json";; esac
    [ -z "${PARDIR:-}" ] || { echo "end --arm $arm --seed $seed" >> "$LOG"; rm -f "$PARDIR/run.$$"; };;
  *preflight.py) [ -z "${PFAIL:-}" ] || exit 1; mkdir -p "$OUT/preflight";;
  *summarize.py) echo "VERDICT: INCOMPLETE";;
esac
"""


def test_box_script():
    """run_box.sh drives think1.py for every arm, in dependency order, skipping finished jobs (stub python; no torch)."""
    import os
    import shutil
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stub, log = tmp / "fakepy", tmp / "log"
        stub.write_text(STUB)
        stub.chmod(0o755)
        (tmp / "out" / "data").mkdir(parents=True)
        (tmp / "out" / "data" / "DATA_REPORT.json").write_text("{}")

        def box(jobs, fail="", flags="", rc=0, **extra):
            log.write_text("")
            env = dict(os.environ, THINK_JOBS=jobs, PYTHON=str(stub), OUT=str(tmp / "out"), TARBALL="0", LOG=str(log), FAIL=fail, THINK_FLAGS=flags, **extra)
            r = subprocess.run(["bash", str(HERE / "run_box.sh")], env=env, capture_output=True, text=True)
            assert r.returncode == rc, r.stdout + r.stderr
            return [l.split() for l in log.read_text().splitlines()], r.stdout

        def runs(calls):
            return [(c[c.index("--arm") + 1], c[c.index("--seed") + 1]) for c in calls if c[0] == "think1.py"]

        calls, out = box("t:0,bplus:0,aplus:1,tw:0")
        assert runs(calls) == [("a", "0"), ("t", "0"), ("b", "0"), ("bplus", "0"), ("a", "1"), ("aplus", "1"), ("tw", "0")], runs(calls)
        assert calls[-1][0] == "summarize.py" and "--data" in calls[-1] and not any(c[0] == "train.py" for c in calls)
        assert all("--steps" not in c for c in calls if c[0] == "think1.py"), "no global STEPS"
        calls, _ = box("t:0,bplus:0,aplus:1")
        assert runs(calls) == [], ("finished jobs must be skipped", runs(calls))
        calls, _ = box("ws:3,wsham:3,tsd:3,tsd1:3")  # P1 / P2b arms: stage-1 a first, then the preflight (once), then each arm
        assert runs(calls) == [("a", "3"), ("ws", "3"), ("wsham", "3"), ("tsd", "3"), ("tsd1", "3")], runs(calls)
        names = [c[0] for c in calls]
        assert names.count("preflight.py") == 1 and names.index("preflight.py") < names.index("think1.py", 1 + names.index("think1.py")), names
        pf = calls[names.index("preflight.py")]
        assert "--a-adapter" in pf and pf[pf.index("--a-adapter") + 1].endswith("think/a_s3/adapter") and pf[pf.index("--alpha-init") + 1] == "0", pf
        shutil.rmtree(tmp / "out" / "preflight"), [shutil.rmtree(tmp / "out" / "think" / f"{x}_s3") for x in ("ws", "wsham", "tsd", "tsd1")]
        calls, out = box("ws:3,tsd:3", flags="--alpha-init+0.3", PFAIL="1")  # a failed preflight stops every P1 / P2b job
        assert runs(calls) == [] and "preflight failed" in out and [c[0] for c in calls].count("preflight.py") >= 1, (runs(calls), out)
        assert calls[[c[0] for c in calls].index("preflight.py")][-1] == "0.3"
        calls, out = box("ws:3,tsd:3", PARALLEL="1", PFAIL="1")
        assert runs(calls) == [] and [c[0] for c in calls].count("preflight.py") == 1, (runs(calls), out)
        calls, _ = box("ws:3,tsd:3,aplus:3")  # no failure: the preflight runs once even with two jobs
        assert [c[0] for c in calls].count("preflight.py") == 1 and sorted(runs(calls)) == [("aplus", "3"), ("tsd", "3"), ("ws", "3")], runs(calls)
        import shutil
        shutil.rmtree(tmp / "out" / "think" / "a_s1" / "adapter")
        calls, _ = box("aplus:1")
        assert runs(calls) == [("a", "1")], "result without adapter: retrain the stage-1 arm, then the (finished) job is skipped"
        calls, out = box("t:5,a:6,zz:0", fail="a")
        assert runs(calls) == [("a", "5"), ("a", "6")] and "t seed 5 skipped" in out and "unknown arm zz" in out, (runs(calls), out)
        calls, _ = box("t1:7", flags="--limit-eval+10")
        assert [c for c in calls if c[0] == "think1.py" and "t1" in c][0][-2:] == ["--limit-eval", "10"]
        # no CUDA: stop with exit 2 before any job runs; ALLOW_CPU=1 runs anyway
        calls, out = box("t1:8", rc=2, NOCUDA="1")
        assert runs(calls) == [] and "no CUDA" in out, (runs(calls), out)
        calls, _ = box("a:9", NOCUDA="1", ALLOW_CPU="1")
        assert runs(calls) == [("a", "9")]
        assert "== think run_box" in (tmp / "out" / "think" / "run.log").read_text() and "no CUDA" in (tmp / "out" / "think" / "run.log").read_text(), "run.log"
        r = subprocess.run(["bash", "-n", str(HERE / "run_box.sh")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        # PARALLEL=1: all stage-1 jobs at once, then all stage-2 jobs once their adapters exist, at most MAXPAR at a time, one run.log per job
        import shutil
        shutil.rmtree(tmp / "out" / "think")
        par = tmp / "par"

        def pbox(jobs, **extra):
            shutil.rmtree(par, ignore_errors=True)
            par.mkdir()
            calls, out = box(jobs, fail=extra.pop("fail", ""), PARALLEL="1", PARDIR=str(par), **extra)
            peak = max([int(x) for x in (par / "counts").read_text().split()] if (par / "counts").exists() else [0])
            return calls, out, peak

        def at(calls, kind, arm, seed):  # position in the log of a job's start ("think1.py") or end ("end")
            return next(i for i, c in enumerate(calls) if c[0] == kind and c[c.index("--arm") + 1] == arm and c[c.index("--seed") + 1] == seed)

        calls, out, peak = pbox("aplus:0,t:0,a:0,b:0,t1:0")
        assert sorted(runs(calls)) == sorted([(x, "0") for x in ("a", "b", "aplus", "t", "t1")]), runs(calls)
        assert {r[0] for r in runs(calls)[:2]} == {"a", "b"} and peak == 3, (runs(calls), peak)  # stage 1 first, both at once; stage 2 reaches the cap
        for arm in ("aplus", "t", "t1"):
            assert at(calls, "think1.py", arm, "0") > at(calls, "end", "a", "0"), f"{arm} started before the a adapter existed"
        assert max(at(calls, "end", x, "0") for x in "ab") < min(at(calls, "think1.py", x, "0") for x in ("aplus", "t", "t1")), "stage 2 starts only after stage 1"
        for arm in ("a", "b", "aplus", "t", "t1"):
            d = tmp / "out" / "think" / f"{arm}_s0"
            assert (d / f"result_{arm}_s0.json").exists() and (d / "run.log").exists(), arm
        assert calls[-1][0] == "summarize.py" and "-- done t1 seed 0" in out and "-- parallel: stage 1" in out
        calls, out, peak = pbox("a:1,b:1,bplus:1,tw:1,t:1,a:2", MAXPAR="2")
        assert peak == 2, peak  # the cap holds in both stages (stage 1: a:1, b:1, a:2 -> 2 at a time; stage 2: bplus, tw, t -> 2 at a time)
        assert sorted(runs(calls)) == sorted([(x, "1") for x in ("a", "b", "bplus", "tw", "t")] + [("a", "2")]), runs(calls)
        assert at(calls, "think1.py", "bplus", "1") > at(calls, "end", "b", "1")
        calls, out, peak = pbox("t:3,bplus:4,a:5", fail="a", MAXPAR="1")  # no result: stage-2 jobs are skipped (a:3 is added and fails, and fails again alone), failures are isolated, cap 1
        assert peak == 1 and sorted(runs(calls)) == [("a", "3"), ("a", "3"), ("a", "5"), ("a", "5"), ("b", "4"), ("bplus", "4")] and "t seed 3 skipped: a seed 3 did not finish" in out, (runs(calls), out)
        calls, out, peak = pbox("a:1,b:1,aplus:1,t:1,a:2")  # a:1, b:1, a:2, t:1 have results: skipped; aplus:1 runs (a_s1/adapter exists)
        assert runs(calls) == [("aplus", "1")] and "skip a seed 1" in (tmp / "out" / "think" / "a_s1" / "run.log").read_text(), runs(calls)
        calls, out, peak = pbox("a:7,aplus:7,t:7", FAILONCE=",aplus,")  # a job that dies once with the others alive is rerun alone and keeps its seed
        assert sorted(runs(calls)) == [("a", "7"), ("aplus", "7"), ("aplus", "7"), ("t", "7")] and "retry aplus seed 7 alone" in out, (runs(calls), out)
        assert (tmp / "out" / "think" / "aplus_s7" / "result_aplus_s7.json").exists()
        calls, out, peak = pbox("a:8,aplus:8,t:8", FAILLATE=",a,")  # a's adapter exists but its eval crashed: no result, so aplus and t must not start
        assert runs(calls) == [("a", "8"), ("a", "8")] and "aplus seed 8 skipped: a seed 8 did not finish" in out and "t seed 8 skipped" in out, (runs(calls), out)
    print("TR run_box.sh: every arm via think1.py, a/b run first when an adapter is missing, finished jobs skipped, failures isolated, flags passed, CUDA check (exit 2 unless ALLOW_CPU=1), run.log; PARALLEL=1: stage 1 then stage 2, MAXPAR cap, per-job run.log, a dead job rerun alone once, no dependents on a stage-1 job without a result")


# ---------------------------------------------------------------- SM, TS

EXPECT = {
    "a": {"validation": {"main", "main_repeat"}, "dev": {"main"}},
    "b": {"validation": {"main", "pass1"}, "dev": {"main", "pass1"}},
    "aplus": {"validation": {"main"}, "dev": {"main"}}, "bplus": {"validation": {"main"}, "dev": {"main"}},
    "t": {"validation": {"L0", "L1", "L2", "L4", "L8", "L12", "L16", "L24", "swap8", "mean8", "rep1_8", "gatesoff8", "ref0"}, "dev": {"L0", "L1", "L8"}},
    "t1": {"validation": {"L0", "L1", "L8"}, "dev": {"L1"}}, "tw": {"validation": {"L1"}, "dev": set()},
    "tj": {"validation": {"L0", "L1", "L4", "swap4", "gatesoff4", "ref0"}, "dev": {"L4"}},
    "tf": {"validation": {"L0", "L1", "L4", "swap4", "gatesoff4", "ref0", "blind4"}, "dev": {"L4"}},
    "tc": {"validation": {"L0", "ref0"}, "dev": {"L0"}},
    "ws": {"validation": {"T", "C1", "fmt"}, "dev": {"T", "C1"}}, "wsham": {"validation": {"T", "C1", "fmt"}, "dev": {"T", "C1"}},
    "tsd": {"validation": {"L0", "L1", "L4", "swap4", "random4", "zero4", "gatesoff4", "ref0"}, "dev": {"L4"}},
    "tsd1": {"validation": {"L0", "L1", "swap1", "random1", "zero1", "gatesoff1", "ref0"}, "dev": {"L1"}},
}


def test_ts_spec_defaults():
    """Per-arm step defaults, learning-rate groups, warm-ups, gate thresholds and eval tags, as in IMPL-SPEC section 3 / PREREG."""
    assert (K.STEPS1, K.STEPS2) == (418, 1254) and K.STAGE1 == ("a", "b") and set(K.STAGE2) == {"aplus", "bplus", "t", "t1", "tw", "tj", "tf", "tc", "ws", "wsham", "tsd", "tsd1", "br", "aplong"}
    a = K.parse(["--arm", "t", "--out", "x"])
    assert (a.bsz, a.micro_bsz, a.max_len, a.eval_bsz, a.eval_tokens, a.steps, a.k, a.gate_step, a.log_every) == (16, 4, 2048, 64, 32768, None, None, 150, 250)
    assert (K.LR, K.LR_ALPHA, K.LR_BOARD, K.LAMBDA) == (2e-4, 3e-3, 5e-4, 0.01)
    assert K.GATE == dict(alpha=0.02, div=2.0, window=20)
    assert min(100, 418 // 10) == 41 and min(100, 6 // 10 or 1) == 1  # stage-1 warm-up rule as coded: min(100, steps // 10 or 1)
    board = B.ThinkBoard(1024, 0.0195, torch.randn(16, 1024))
    g = {x["name"]: x for x in K.board_groups(board)}
    assert [x["base"] for x in g.values()] == [3e-3, 5e-4, 5e-4] and list(g) == ["alpha", "e0eta", "refiner"]
    assert sum(p.numel() for x in g.values() for p in x["params"]) == sum(p.numel() for p in board.parameters()) == 2_644_016
    assert len({id(p) for x in g.values() for p in x["params"]}) == len(list(board.parameters()))
    assert [p.numel() for p in g["alpha"]["params"]] == [48] and sorted(p.numel() for p in g["e0eta"]["params"]) == [1024, 16384]
    assert abs(T.cosine_lr(0, 1254, 5e-4, 60) - 5e-4 / 60) < 1e-12 and abs(T.cosine_lr(1253, 1254, 5e-4, 60)) < 1e-8
    t = K.tags_for("t", "validation")
    assert set(t) == EXPECT["t"]["validation"] and t["L16"][2] == 2000 and t["L24"][2] == 2000 and all(v[2] is None for k, v in t.items() if k not in ("L16", "L24"))
    assert set(K.tags_for("t", "dev")) == {"L0", "L1", "L8"} and set(K.tags_for("t1", "validation")) == {"L0", "L1", "L8"}
    assert set(K.tags_for("t1", "dev")) == {"L1"} and set(K.tags_for("tw", "validation")) == {"L1"} and K.tags_for("tw", "dev") == {}
    assert {k: v[:2] for k, v in t.items() if k in ("swap8", "mean8", "rep1_8", "gatesoff8", "ref0")} == \
        {"swap8": ("swap", 8), "mean8": ("mean", 8), "rep1_8": ("rep", 8), "gatesoff8": ("off", 8), "ref0": ("none", 8)}
    assert K.parse(["--arm", "t", "--out", "x"]).no_lap_ckpt is False and K.parse(["--arm", "t", "--out", "x", "--no-lap-ckpt"]).no_lap_ckpt is True
    print("TS step defaults 418 / 1,254, lr groups 3e-3 / 5e-4 / 5e-4 (each board parameter in exactly one group), gate thresholds and eval tags as in the spec")



def test_sm_smoke_all_arms():
    src = VILLAGE if Path(VILLAGE).exists() else "/nonexistent"
    with tempfile.TemporaryDirectory() as tmp:
        buf, t0 = io.StringIO(), time.time()
        with contextlib.redirect_stdout(buf):
            rc = K.main(["--smoke", "--seed", "0", "--data", src, "--out", tmp])
        out, root = buf.getvalue(), Path(tmp) / "smoke"
        assert rc == 0, out[-2000:]
        res = {}
        for arm, want in EXPECT.items():
            f = root / f"{arm}_s0" / f"result_{arm}_s0.json"
            assert f.exists(), f"missing {f}"
            r = res[arm] = json.loads(f.read_text())
            assert r["arm"] == arm and r["seed"] == 0 and r["aborted"] is None, (arm, r["aborted"])
            assert {s: set(r["eval"][s]) for s in ("validation", "dev")} == want, (arm, {s: set(r["eval"][s]) for s in ("validation", "dev")})
            for split in want:
                for tag, e in r["eval"][split].items():
                    assert e["n"] == len(e["hits"]) and set(e["hits"]) <= {"0", "1"} and e["row_offset"] == 0 and 0 <= e["acc"] <= 1, (arm, split, tag)
            assert r["train"]["loss_curve"] and len(r["train"]["step_losses"]) == 6 and r["label_nums"]
            ev = r["env"]
            assert ev["gpu"] == "cpu" and ev["dtype"] == "float32" and ev["torch"] == torch.__version__ and set(ev) == {"gpu", "dtype", "torch", "transformers", "peft", "flash_linear_attention"}, ev
            assert ev["transformers"] and ev["peft"], ev
            assert r["steps_stage1"] == 6 and r["steps_stage2"] == (0 if arm in ("a", "b") else 6)
        for arm in ("a", "b", "aplus", "bplus"):
            assert (root / f"{arm}_s0" / "adapter" / "adapter_config.json").exists()
        for arm in ("t", "t1", "tw", "tj", "tf", "tsd", "tsd1"):
            assert (root / f"{arm}_s0" / "think_block.pt").exists()
        assert (root / "tj_s0" / "adapter" / "adapter_config.json").exists() and res["tj"]["lmax"] == 4 and res["tj"]["adapter_sha"] != res["a"]["adapter_sha"]
        assert res["tw"]["k_slots"] == 144 and res["t"]["k_slots"] == 16 and res["t1"]["k_slots"] == 16
        assert res["aplus"]["stage1_adapter"].endswith("a_s0/adapter") and res["bplus"]["stage1_adapter"].endswith("b_s0/adapter")
        assert all(res[a]["stage1_adapter"].endswith("a_s0/adapter") for a in ("t", "t1", "tw"))
        assert res["b"]["loops"] == 3 and res["b"]["loop_block"] == [0, 4] and res["a"]["loops"] == 1
        assert res["a"]["adapter_sha"] and res["b"]["adapter_sha"] and res["aplus"]["adapter_sha"] and res["bplus"]["adapter_sha"]
        assert all(res[x]["stage1_adapter_sha"] == res["a"]["adapter_sha"] for x in ("aplus", "t", "t1", "tw", "tj", "tf", "ws", "wsham", "tsd", "tsd1")) and res["bplus"]["stage1_adapter_sha"] == res["b"]["adapter_sha"]
        assert res["a"]["stage1_adapter_sha"] is None and res["t"]["adapter_sha"] is None
        gl = res["t"]["train"]["gate_log"][0]
        assert all(k in gl for k in ("cos_across", "cos_within", "cos_update_across", "cos_update_within", "clamp", "clamp5"))
        assert len(res["t"]["train"]["gate_log"]) >= 1 and len(res["t"]["train"]["dev_log"]) >= 1 and res["t"]["train"]["gate_check"]["step"] == 4
        if (HERE / "summarize.py").exists():
            m = re.search(r"^VERDICT: (PASS|WRONG|PARTIAL|FUTILE-STOP|INCOMPLETE)\b", out, re.M)
            assert m, "summarize printed no verdict line:\n" + out[-1500:]
            verdict = m.group(0)
        else:
            verdict = "summarize.py absent: skipped"
        print(f"SM smoke ran {len(EXPECT)} arms in {time.time() - t0:.0f}s, adapters handed on, result tags as in the spec; {verdict}")


def test_ai_alpha_init():
    """--alpha-init: default 0 keeps zero gates (nothing changes for existing arms); 0.3 starts every gate at tanh(0.3) = 0.291; the value is recorded in the
    result JSON and think_block.pt, survives a short run, and tc (closed block) refuses a non-zero start."""
    assert K.parse(["--arm", "tj", "--out", "x"]).alpha_init == 0.0 and K.parse(["--arm", "tj", "--out", "x", "--alpha-init", "0.3"]).alpha_init == 0.3
    lm, tok = T.load_model(argparse.Namespace(smoke=True, seed=0, model=""), torch.device("cpu"), torch.float32)
    b0, b3 = B.ThinkBoard.from_model(lm, tok, K=4), B.ThinkBoard.from_model(lm, tok, K=4, alpha_init=0.3)
    assert torch.equal(b0.alpha, torch.zeros_like(b0.alpha)) and torch.equal(B.ThinkBoard(64, 0.02, torch.randn(4, 64)).alpha, torch.zeros(6, 8))
    assert b3.alpha.shape == b0.alpha.shape and b3.alpha.requires_grad and torch.allclose(b3.alpha, torch.full_like(b3.alpha, 0.3))
    assert abs(float(b3.gate().mean()) - 0.2913) < 1e-3 and torch.allclose(b3.gate(), torch.tanh(torch.tensor(0.3)).expand_as(b3.gate()))
    fx = fixture()
    a0 = arm_args("tj", 0, "ai0", steps=2)
    assert K.run_arm(a0) == 0
    a3 = arm_args("tj", 0, "ai3", steps=2, extra=("--alpha-init", "0.3"))
    assert K.run_arm(a3) == 0
    r0, r3 = load(a0), load(a3)
    assert r0["alpha_init"] == 0.0 and r3["alpha_init"] == 0.3
    assert torch.load(Path(a3.out) / "think_block.pt")["alpha_init"] == 0.3
    assert r0["train"]["gate_log"][-1]["alpha_mean"] < 0.01 and abs(r3["train"]["gate_log"][-1]["alpha_mean"] - 0.2913) < 0.01, (r0["train"]["gate_log"][-1]["alpha_mean"], r3["train"]["gate_log"][-1]["alpha_mean"])
    try:
        K.run_arm(arm_args("tc", 0, "ai_tc", steps=2, extra=("--alpha-init", "0.3")))
        raise AssertionError("tc accepted --alpha-init 0.3")
    except SystemExit:
        pass
    print("AI --alpha-init: default 0 keeps zero gates, 0.3 gives tanh 0.2913, recorded in result JSON and think_block.pt, kept through a run; tc refuses it")


# ---------------------------------------------------------------- runner

def board_tests(TB, real):
    fails = TB.run(real)
    assert not fails, f"board tests failed: {fails}"


def run_all(real=False, only=None):
    import test_think1_board as TB
    import test_xent as TX
    import test_summarize as TS
    import test_from_label as TFL
    tests = [("BOARD", lambda: board_tests(TB, real)),
             ("XENT", TX.run_all), ("S1", TS.test_s1), ("S2", TS.test_s2), ("S4", TS.test_s4), ("FL", TFL.test_fl), ("T8", test_t8_same_seed_same_losses), ("TO", test_to_data_order),
             ("TH", test_th_hits_in_file_order_and_gates_off_is_arm_a), ("TG", test_tg_mechanics_gate), ("TJ", test_tj_joint), ("TF", test_tf_forced), ("TCTRL", test_tc_control), ("TR", test_box_script), ("TS", test_ts_spec_defaults), ("AI", test_ai_alpha_init), ("SM", test_sm_smoke_all_arms)]
    fails = []
    for name, fn in tests:
        if only and name.lower() not in [o.lower() for o in only]:
            continue
        t0 = time.time()
        try:
            fn()
            print(f"PASS {name} ({time.time() - t0:.0f}s)", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FAIL {name}", flush=True)
            fails.append(name)
    print("think1 tests:", "ALL PASSED" if not fails else f"FAILED {fails}")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    sys.exit(1 if run_all(a.real, a.only) else 0)
