"""Board tests T1-T7, T9, T10 (+ TP read patch identity, TC parameter count) for backbone/think/board.py, CPU.

    python backbone/think/test_think1_board.py [--real]      (--real adds T1/TP/TC on the cached Qwen3.5-0.8B and 3 short validation rows)
Real weights need HF_HOME=<cache> HF_HUB_OFFLINE=1. `run(real)` is what test_think1.py calls.
"""
from __future__ import annotations

import argparse
import copy
import sys
import traceback
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import board as B  # noqa: E402
import train as T  # noqa: E402

CPU = torch.device("cpu")
VILLAGE = "/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/village"


# ---------------------------------------------------------------- helpers

def tiny(dtype=torch.float32, std=0.5):
    lm, tok = T.load_model(argparse.Namespace(smoke=True, seed=0, model=""), CPU, dtype)
    torch.nn.init.normal_(lm.model.embed_tokens.weight, std=std)  # tied head: token-dependent logits
    return lm, tok


def rows(lens=(11, 17, 6), alens=(3, 4, 2), seed=0):
    g = torch.Generator().manual_seed(seed)
    prompts = [torch.randint(4, 200, (n,), generator=g).tolist() for n in lens]
    ans = [torch.randint(4, 200, (n - 1,), generator=g).tolist() + [1] for n in alens]
    return prompts, ans


def make_board(lm, tok, K=6, alpha=None, seed=0, dtype=torch.float32):
    torch.manual_seed(seed)
    b = B.ThinkBoard.from_model(lm, tok, K=K).to(dtype)
    with torch.no_grad():
        if alpha is None:
            b.alpha.zero_()
        elif isinstance(alpha, float):
            b.alpha.fill_(alpha)
        else:
            b.alpha.copy_(alpha)
    return b


def setup(runner, prompts):
    C, mask, p = B.prefill(runner, prompts)
    return C, mask, p, B.last_ids(prompts, B.model_device(runner))


def stock_logits(runner, prompts, ans):
    """Arm a's way: Runner.hidden on the full right-padded sequence, logits at the answer positions."""
    ids, mask = T.right_pad([p + a for p, a in zip(prompts, ans)])
    h = runner.hidden(ids, mask, (mask.cumsum(1) - 1).clamp(min=0))
    sb = torch.tensor([b for b, a in enumerate(ans) for _ in a])
    st = torch.tensor([len(prompts[b]) + k - 1 for b, a in enumerate(ans) for k in range(len(a))])
    return runner.logits(h[sb, st]).float()


def snap(C):
    out = []
    for l in C.layers:
        for name in ("keys", "values"):
            if hasattr(l, name) and getattr(l, name) is not None:
                out.append(getattr(l, name).clone())
        for name in ("conv_states", "recurrent_states"):
            if hasattr(l, name):
                out += [t.clone() for t in getattr(l, name).values() if t is not None]
    return out


def same(a, b):
    return len(a) == len(b) and all(torch.equal(x, y) for x, y in zip(a, b))


def rand_alpha(runner_or_board, scale=1.0, seed=1):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(runner_or_board.alpha.shape, generator=g) * scale


# ---------------------------------------------------------------- tests

def test_TC_param_count():
    W = torch.randn(300, 1024) * 0.0195
    b = B.ThinkBoard(1024, 0.0195, W[:16] / 0.0195)
    n = sum(p.numel() for p in b.parameters())
    parts = {k: sum(p.numel() for p in m.parameters()) for k, m in dict(w_in=b.w_in, blocks=b.blocks, norm=b.norm, w_out=b.w_out).items()}
    print("TC params", n, parts, "e0", b.e0_hat.numel(), "gates", b.alpha.numel(), "eta", b.eta.numel())
    assert n == 2_644_016 and parts["blocks"] == 1_576_448 and parts["w_in"] == 786_688 and parts["w_out"] == 263_168


def test_TP_patch_identity():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    ids, mask = T.right_pad([p + a for p, a in zip(prompts, ans)])
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    with torch.no_grad():
        before = r.hidden(ids, mask, pos)
        mods = B.attn_modules(r)
        assert len(mods) == 2 and all(m.board is None for m in mods)
        after = r.hidden(ids, mask, pos)
        b = make_board(lm, tok)
        with B.reading(r, b.gate(), None):  # no board given -> still the plain path
            again = r.hidden(ids, mask, pos)
        B.unpatch(r)
        unpatched = r.hidden(ids, mask, pos)
    print("TP patched == stock bitwise:", torch.equal(before, after), torch.equal(before, again), torch.equal(before, unpatched))
    assert torch.equal(before, after) and torch.equal(before, again) and torch.equal(before, unpatched)


def test_T1_alpha0_equals_arm_a():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    b = make_board(lm, tok, alpha=None)
    with torch.no_grad():
        ref = stock_logits(r, prompts, ans)
        C, mask, p, lt = setup(r, prompts)
        kv, _ = B.think(b, r, C, mask, p, 8, keep=range(9))
        worst = 0.0
        for L in (0, 1, 4, 8):
            lg, tgt, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, kv[L])
            assert torch.equal(lg, B.answer_logits(r, None, C, mask, p, lt, ans, None)[0]), "zero gates are not exactly the no-board path"
            d = (lg - ref).abs().max().item()
            worst = max(worst, d)
            print(f"T1 tiny L={L}: max|diff| vs stock arm a = {d:.2e} (logit scale {ref.abs().max().item():.1f})")
        # nonzero alpha moves the logits (so the equality above is not vacuous)
        b.alpha.data = rand_alpha(b)
        lg, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, kv[8])
        moved = (lg - ref).abs().max().item()
        print(f"T1 control: alpha != 0 moves logits by {moved:.2e}")
    assert worst <= 1e-5 and moved > 1e-3


def test_T2_cache_untouched():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    b = make_board(lm, tok, alpha=rand_alpha(make_board(lm, tok)))
    C, mask, p, lt = setup(r, prompts)
    before = snap(C)
    kv, _ = B.think(b, r, C, mask, p, 8, keep=range(9))
    assert same(before, snap(C)), "think() changed C"
    for t in range(9):
        B.answer_ce(r, b, C, mask, p, lt, ans, kv[t])
    assert same(before, snap(C)), "answer passes changed C"
    B.decode(r, b, C, mask, p, lt, kv[8], max_new=5, eos=1)
    assert same(before, snap(C)), "decode changed C"
    B.think(b, r, C, mask, p, 4, repeat_delta1=True)
    assert same(before, snap(C)), "repeat_delta1 changed C"
    print(f"T2 C bit-identical after think L=8 + 9 answer passes + decode + repeat ({len(before)} tensors)")


def test_T3_slot_pass_equals_no_cache():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, _ = rows()
    b = make_board(lm, tok, K=5)
    torch.manual_seed(3)
    e = torch.randn(3, 5, 64) * 0.05
    t1, t2 = B.tap_layers(r.n)
    with torch.no_grad():
        C, mask, p, lt = setup(r, prompts)
        taps, kv = B.slot_pass(r, e, C, mask, p)
        worst = 0.0
        for i, pr in enumerate(prompts):  # reference: no cache, one row, [embed(prompt[:-1]); e], same position ids
            n = len(pr) - 1
            x = torch.cat([lm.model.embed_tokens(torch.tensor([pr[:-1]])), e[i:i + 1]], 1)
            pos = torch.cat([torch.arange(n), torch.full((5,), n)])[None]
            h, tap = B.run_layers(r, x, torch.ones(1, n + 5, dtype=torch.long), pos, None, taps=(t1, t2))
            ref = torch.cat([B.rms_norm(tap[t1]), B.rms_norm(tap[t2]), h], -1)[:, -5:]
            worst = max(worst, (ref - taps[i:i + 1]).abs().max().item())
    print(f"T3 slot taps (layers {t1}, {t2}, final norm) fork vs no-cache: max|diff| {worst:.2e} (batch of 3 left-padded rows)")
    assert worst <= 1e-4


def _ref_decode(r, gate, prompt, kv_row, max_new, eos=1):
    """No cache: re-forward prompt + generated each step; the board is read by queries from the held-back last prompt token on."""
    gen, margins = [], []
    for _ in range(max_new):
        ids = torch.tensor([prompt + gen])
        with B.reading(r, gate, kv_row, read_from=len(prompt) - 1):
            h, _ = B.run_layers(r, r.lm.model.embed_tokens(ids), torch.ones_like(ids), torch.arange(ids.shape[1])[None], None)
        lg = r.logits(h[:, -1])[0]
        top = lg.topk(2)
        margins.append((top.values[0] - top.values[1]).item())
        t = int(top.indices[0])
        if t == eos:
            break
        gen.append(t)
    return gen, min(margins)


def test_T4_cached_decode_equals_no_cache():
    lm, tok = tiny(std=0.02)  # small logits (like the real model's scale)
    r = T.Runner(lm, loops=1)
    prompts, _ = rows()
    b = make_board(lm, tok, K=5)
    b.alpha.data = rand_alpha(b, 1.0)
    max_new = 8
    strong = 4.0 * torch.ones_like(b.alpha)  # gates forced to 4 so that the read visibly changes the tokens
    with torch.no_grad():
        C, mask, p, lt = setup(r, prompts)
        plain = B.decode(r, b, C, mask, p, lt, None, max_new=max_new, eos=1)
        arm_a = T.greedy(r, prompts, CPU, 1, cache=True)
        changed = []
        for L in (1, 4, 8):
            kv, _ = B.think(b, r, C, mask, p, L)
            lg, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, [[5, 6, 1]] * 3, kv[L])
            lg0, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, [[5, 6, 1]] * 3, None)
            assert (lg - lg0).abs().max() > 1e-2, "vacuous: the board does not change the logits"
            for name, gates in (("learned-size gates", None), ("gates=4", strong)):
                got = B.decode(r, b, C, mask, p, lt, kv[L], max_new=max_new, eos=1, gates=gates)
                g = b.gate() if gates is None else gates
                ok, mg = [], []
                for i, pr in enumerate(prompts):
                    ref, m = _ref_decode(r, g, pr, [(k[i:i + 1], v[i:i + 1]) for k, v in kv[L]], max_new)
                    ok.append(ref == got[i])
                    mg.append(m)
                print(f"T4 L={L} {name}: cached == no-cache per row {ok}; min top1-top2 margin {min(mg):.3f}; differs from no-board decode: {got != plain}; "
                      f"logit shift {(lg - lg0).abs().max().item():.3f}")
                assert all(ok) and min(mg) > 1e-4
                changed.append(got != plain)
    assert any(changed), "vacuous: the board never changed a decode"
    zero = B.decode(r, b, C, mask, p, lt, kv[8], max_new=max_new, eos=1, gates=torch.zeros_like(b.alpha))
    print("T4 slot_kv=None decode == arm a greedy:", [x[:max_new] for x in arm_a] == plain, "; zero gates == arm a:", zero == plain, plain[0])
    assert [x[:max_new] for x in arm_a] == plain and zero == plain
    # rows that hit EOS at different steps: make a token the model emits at step 3 of some rows the EOS
    with torch.no_grad():
        kv, _ = B.think(b, r, C, mask, p, 2)
        base = B.decode(r, b, C, mask, p, lt, kv[2], max_new=6, eos=1, gates=strong)
        eos = base[0][3]
        got = B.decode(r, b, C, mask, p, lt, kv[2], max_new=6, eos=eos, gates=strong)
        refs = [_ref_decode(r, strong, pr, [(k[i:i + 1], v[i:i + 1]) for k, v in kv[2]], 6, eos=eos)[0] for i, pr in enumerate(prompts)]
    print(f"T4 EOS handling (eos={eos}): lengths {[len(x) for x in got]} cached == no-cache: {got == refs}")
    assert got == refs and min(len(x) for x in got) < 6


def _loss_fn(b, r, prompts, ans, L_max=2):
    C, mask, p, lt = setup(r, prompts)
    return B.train_loss(b, r, C, mask, p, lt, ans, L_max)


def test_TR_think_api():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, _ = rows()
    b = make_board(lm, tok, K=5)
    b.alpha.data = rand_alpha(b, 0.7)
    with torch.no_grad():
        C, mask, p, lt = setup(r, prompts)
        kv, st = B.think(b, r, C, mask, p, 6, keep={0, 1, 4, 6})
        assert sorted(kv) == [0, 1, 4, 6] and len(st["pen"]) == 6 and len(st["e"]) == 7 and len(st["cos_slots"]) == 7
        for L in (0, 1, 4):  # one run to the largest L records the same K/V as a run that stops at L
            k1, _ = B.think(b, r, C, mask, p, L)
            assert all(torch.equal(x, y) for (x, _), (y, _) in zip(k1[L], kv[L])), L
        # repeat_delta1: 2 backbone passes for L=6, boards e_t = clamp(e_{t-1} + delta_0)
        calls = []
        orig = B.slot_pass
        B.slot_pass = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
        try:
            kr, sr = B.think(b, r, C, mask, p, 6, repeat_delta1=True)
        finally:
            B.slot_pass = orig
        taps, _ = orig(r, b.start(3), C, mask, p)
        d0 = b.delta(taps)
        e = b.start(3)
        for t in range(6):
            e = b.clamp(e + d0)
        err = (sr["e"][-1] - e).abs().max().item()
        _, kv_e = orig(r, e, C, mask, p)
        err_kv = max((x - y).abs().max().item() for (x, _), (y, _) in zip(kr[6], kv_e))
        print(f"TR repeat_delta1: {len(calls)} backbone passes for L=6 (normal: 7), final board err {err:.1e}, slot K/V err {err_kv:.1e}; "
              f"clamp frac {[round(float(c), 2) for c in st['clamp']]}, step {[round(float(c), 3) for c in st['step']]}, cos within {float(st['cos_slots'][-1]):.3f} across {float(st['cos_rows'][-1]):.3f}")
        assert len(calls) == 2 and err < 1e-6 and err_kv < 1e-6
        # pass count of the normal path
        assert len(B.think(b, r, C, mask, p, 3)[1]["pen"]) == 3


def test_T5_gradients_only_in_board():
    from peft import LoraConfig, get_peft_model
    lm, tok = tiny()
    pm = get_peft_model(lm, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, target_modules=T.LORA_TARGETS))
    for n, p_ in pm.named_parameters():
        if "lora_B" in n:
            torch.nn.init.normal_(p_, std=0.05)  # make the adapter matter
    r = T.Runner(pm.base_model.model, loops=1)
    for p_ in pm.parameters():
        p_.requires_grad_(False)  # think1.py: freeze ALL backbone and LoRA weights
    prompts, ans = rows()
    b = make_board(lm, tok, K=4, alpha=0.5)
    loss, info = _loss_fn(b, r, prompts, ans, L_max=2)
    loss.backward()
    zero = [n for n, p_ in b.named_parameters() if p_.grad is None or not p_.grad.abs().max() > 0]
    leaked = [n for n, p_ in pm.named_parameters() if p_.grad is not None]
    nonboard = sum(p_.numel() for p_ in pm.parameters())
    print(f"T5 loss {loss.item():.4f}; board params {len(list(b.parameters()))} tensors, zero-grad: {zero}; backbone+LoRA tensors with grad: {len(leaked)} of {len(list(pm.parameters()))} ({nonboard} params)")
    print("   grad norms:", {n: round(p_.grad.norm().item(), 5) for n, p_ in b.named_parameters() if n in ("alpha", "e0_hat", "eta", "w_out.weight", "w_in.weight")})
    assert not zero and not leaked
    # the same grads must not appear when the backbone is trainable but we only read board grads (sanity: LoRA would get grads if unfrozen)
    for n, p_ in pm.named_parameters():
        p_.grad = None
    for n, p_ in pm.named_parameters():
        if "lora_B" in n:
            p_.requires_grad_(True)
    loss, _ = _loss_fn(b, r, prompts, ans, L_max=1)
    loss.backward()
    got = sum(p_.grad is not None for n, p_ in pm.named_parameters() if "lora_B" in n)
    print(f"T5 control: with LoRA unfrozen {got} lora_B tensors get grads (so the frozen result above is not vacuous)")
    assert got > 0


def test_T5_finite_difference_fp64():
    """Directional derivatives: for every board parameter tensor k, d loss / d eps along g_k/|g_k| must equal |g_k|; also along the whole gradient."""
    lm, tok = tiny(torch.float64)
    r = T.Runner(lm, loops=1)
    prompts, ans = rows(lens=(7, 9), alens=(2, 3))
    b = make_board(lm, tok, K=3, alpha=rand_alpha(make_board(lm, tok, K=3), 0.5), dtype=torch.float64)
    loss, _ = _loss_fn(b, r, prompts, ans, L_max=2)
    loss.backward()
    names = [n for n, _ in b.named_parameters()]
    params = dict(b.named_parameters())
    grads = {n: params[n].grad.clone() for n in names}

    def fd(dirs, eps):
        with torch.no_grad():
            for n in dirs:
                params[n] += eps * dirs[n]
            lp = _loss_fn(b, r, prompts, ans, 2)[0].item()
            for n in dirs:
                params[n] -= 2 * eps * dirs[n]
            lm_ = _loss_fn(b, r, prompts, ans, 2)[0].item()
            for n in dirs:
                params[n] += eps * dirs[n]
        return (lp - lm_) / (2 * eps)

    tot = torch.sqrt(sum(g.pow(2).sum() for g in grads.values())).item()
    d_all = fd({n: g / tot for n, g in grads.items()}, 1e-2)
    print(f"T5 fd whole board: |g| {tot:.6e}  finite-diff along g/|g| {d_all:.6e}  rel err {abs(d_all - tot) / tot:.1e}")
    assert abs(d_all - tot) <= 1e-2 * tot
    worst, checked = 0.0, 0
    for n in names:
        gn = grads[n].norm().item()
        d = fd({n: grads[n] / gn}, 1e-2)
        rel = abs(d - gn) / gn
        flag = "" if gn > 5e-3 else "  (below the fp32-noise floor of the delta-rule layers; not asserted)"
        print(f"   {n:22s} |g| {gn:.4e}  fd {d:.4e}  rel err {rel:.1e}{flag}")
        if gn > 5e-3:
            worst, checked = max(worst, rel), checked + 1
            assert rel <= 3e-2, n
    print(f"T5 fp64 directional finite-difference check passed on {checked} of {len(names)} parameter tensors (worst rel err {worst:.1e})")


def test_TB_bf16_smoke():
    """GPU dtype path on CPU: bf16 backbone, fp32 board; loss and grads finite, board grads fp32, decode runs."""
    lm, tok = tiny(torch.bfloat16)
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    b = make_board(lm, tok, K=4, alpha=0.5)
    loss, info = _loss_fn(b, r, prompts, ans, L_max=2)
    loss.backward()
    ok = all(p_.grad is not None and p_.grad.dtype == torch.float32 and torch.isfinite(p_.grad).all() and p_.grad.abs().max() > 0 for p_ in b.parameters())
    with torch.no_grad():
        C, mask, p, lt = setup(r, prompts)
        kv, _ = B.think(b, r, C, mask, p, 2)
        gen = B.decode(r, b, C, mask, p, lt, kv[2], max_new=4, eos=1)
    print(f"TB bf16: loss {loss.item():.3f} finite {bool(torch.isfinite(loss))}, all board grads fp32/finite/non-zero: {ok}, slot K dtype {kv[2][0][0].dtype}, decode {gen[0]}")
    assert ok and torch.isfinite(loss) and kv[2][0][0].dtype == torch.bfloat16


def test_T6_batch_invariance():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    b = make_board(lm, tok, K=5)
    b.alpha.data = rand_alpha(b, 0.7)
    with torch.no_grad():
        C, mask, p, lt = setup(r, prompts)
        kv, st = B.think(b, r, C, mask, p, 3, keep=[3])
        lg, tgt, sb = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, kv[3])
        worst = 0.0
        for i in range(3):
            C1, m1, p1, l1 = setup(r, [prompts[i]])
            kv1, st1 = B.think(b, r, C1, m1, p1, 3, keep=[3])
            lg1, _, _ = B.answer_logits(r, b.gate(), C1, m1, p1, l1, [ans[i]], kv1[3])
            d = (lg1 - lg[sb == i]).abs().max().item()
            dk = max((a - c[i:i + 1]).abs().max().item() for (a, _), (c, _) in zip(kv1[3], kv[3]))
            de = (st1["e"][-1] - st["e"][-1][i:i + 1]).abs().max().item()
            print(f"T6 row {i} (prompt len {len(prompts[i])}): logits alone vs in batch {d:.2e}; slot keys {dk:.2e}; final board {de:.2e}")
            worst = max(worst, d, dk, de)
    assert worst <= 1e-4


def test_T7_swap_lesion():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    idx = B.swap_index([0, 0, 1])
    assert idx.tolist() == [2, 2, 0] and B.swap_index([5, 5, 5]) is None
    res = {}
    for name, alpha in (("alpha=0", None), ("alpha!=0", 1.0)):
        b = make_board(lm, tok, K=5)
        if alpha:
            b.alpha.data = rand_alpha(b, alpha)
        with torch.no_grad():
            C, mask, p, lt = setup(r, prompts)
            kv, _ = B.think(b, r, C, mask, p, 2)
            kvs, _ = B.think(b, r, C, mask, p, 2, swap=idx)
            assert all(torch.equal(k2, k[idx]) for (k2, _), (k, _) in zip(kvs[2], kv[2]))
            a, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, kv[2])
            s, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, kvs[2])
            m, _, _ = B.answer_logits(r, b.gate(), C, mask, p, lt, ans, B.mean_kv(kv[2]))
        res[name] = ((a - s).abs().max().item(), (a - m).abs().max().item())
        print(f"T7 {name}: swap changes logits by {res[name][0]:.2e}, mean-board by {res[name][1]:.2e}")
    assert res["alpha=0"][0] == 0.0 and res["alpha=0"][1] == 0.0 and res["alpha!=0"][0] > 1e-3 and res["alpha!=0"][1] > 1e-4


def test_T9_no_leak_from_answer():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    ans2 = [[(t + 17) % 190 + 4 for t in a[:-1]] + [1] for a in ans]
    b = make_board(lm, tok, K=5)
    b.alpha.data = rand_alpha(b, 0.8)

    def interleaved(answers, shared_cache=False):
        """slot pass, answer pass on lap t, refine, ... : the lap t+1 board must not depend on the lap-t answer tokens."""
        C, mask, p, lt = setup(r, prompts)
        Cw = copy.deepcopy(C) if shared_cache else None
        es, kvs, e = [], [], b.start(3)
        for t in range(4):
            taps, kv = B.slot_pass(r, e, Cw if shared_cache else C, mask, p)
            es.append(e), kvs.append(kv)
            if shared_cache:  # the bug this test guards against: the answer pass writes into the cache the next lap reads
                _answer_on(Cw, mask, p, lt, answers, kv)
            else:
                B.answer_ce(r, b, C, mask, p, lt, answers, kv)
            e = b.clamp(e + b.delta(taps))
        return es, kvs, C

    def _answer_on(Cw, mask, p, lt, answers, kv):  # same as answer_logits but directly on the given cache (no fork)
        orig = B.fork_cache
        B.fork_cache = lambda C, clone=False: C
        try:
            return B.answer_logits(r, b.gate(), Cw, mask, p, lt, answers, kv)
        finally:
            B.fork_cache = orig

    with torch.no_grad():
        ea, ka, _ = interleaved(ans)
        eb, kb, _ = interleaved(ans2)
        ref, _ = B.think(b, r, *setup(r, prompts)[:3], 3, keep=range(4))
        d_e = max((x - y).abs().max().item() for x, y in zip(ea, eb))
        d_k = max((x - y).abs().max().item() for kv1, kv2 in zip(ka, kb) for (x, _), (y, _) in zip(kv1, kv2))
        d_ref = max((x - y).abs().max().item() for kv1, kv2 in zip(ka, [ref[t] for t in range(4)]) for (x, _), (y, _) in zip(kv1, kv2))
        print(f"T9 answers A vs B: boards differ by {d_e:.2e}, slot K/V by {d_k:.2e}; interleaved vs think(): {d_ref:.2e}")
        assert d_e == 0.0 and d_k == 0.0 and d_ref <= 1e-6
        # negative control: a shared (unforked) cache DOES leak the answer into later laps
        ea, ka, _ = interleaved(ans, shared_cache=True)
        eb, kb, _ = interleaved(ans2, shared_cache=True)
        leak = max((x - y).abs().max().item() for kv1, kv2 in zip(ka, kb) for (x, _), (y, _) in zip(kv1, kv2))
        print(f"T9 control: with one shared cache the lap-(t+1) slot K/V differ by {leak:.2e} when only the answer changes")
        assert leak > 1e-5


def test_T10_batch_permutation():
    lm, tok = tiny()
    r = T.Runner(lm, loops=1)
    prompts, ans = rows()
    b = make_board(lm, tok, K=5)
    b.alpha.data = rand_alpha(b, 0.7)
    perm = [2, 0, 1]
    out = []
    with torch.no_grad():
        for order in ([0, 1, 2], perm):
            pr, an = [prompts[i] for i in order], [ans[i] for i in order]
            C, mask, p, lt = setup(r, pr)
            kv, st = B.think(b, r, C, mask, p, 3, keep=[3])
            lg, _, sb = B.answer_logits(r, b.gate(), C, mask, p, lt, an, kv[3])
            out.append((st["e"][-1], kv[3], [lg[sb == i] for i in range(3)]))
    (e0, kv0, lg0), (e1, kv1, lg1) = out
    de = (e0[perm] - e1).abs().max().item()
    dk = max((a[perm] - c).abs().max().item() for (a, _), (c, _) in zip(kv0, kv1))
    dl = max((lg0[o] - lg1[j]).abs().max().item() for j, o in enumerate(perm))
    print(f"T10 permuting the batch rows: boards {de:.2e}, slot keys {dk:.2e}, logits {dl:.2e}")
    assert max(de, dk, dl) <= 1e-5


# ---------------------------------------------------------------- real model

def _real_rows(n=3):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    rs = T.read_jsonl(Path(VILLAGE) / "validation.jsonl", limit=400)
    return sorted(rs, key=lambda r: len(r["context"]) + len(r["question"]))[:n]


def load_real():
    lm, tok = T.load_model(argparse.Namespace(smoke=False, seed=0, model="Qwen/Qwen3.5-0.8B"), CPU, torch.float32)
    return lm, tok


def test_real_T1_TP_TC():
    lm, tok = load_real()
    r = T.Runner(lm, loops=1)
    enc = T.Encoder(tok, 2048)
    ex = [enc.train_example(x) for x in _real_rows()]
    prompts, ans = [e[0] for e in ex], [e[1] for e in ex]
    print("real rows: prompt lens", [len(x) for x in prompts], "answer lens", [len(a) for a in ans])
    b = make_board(lm, tok, K=16, alpha=None)
    n = sum(p.numel() for p in b.parameters())
    print(f"real board: rho {b.rho.item():.5f} (spec 0.0195), params {n:,} (spec 2,644,016), tap layers {B.tap_layers(r.n)}, full-attention layers {B.full_idx(r)}")
    assert n == 2_644_016 and abs(b.rho.item() - 0.0195) < 5e-4
    ids, mask = T.right_pad([p + a for p, a in zip(prompts, ans)])
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    with torch.no_grad():
        before = r.hidden(ids, mask, pos)
        B.attn_modules(r)
        after = r.hidden(ids, mask, pos)
        print("real TP patched == stock bitwise:", torch.equal(before, after))
        assert torch.equal(before, after)
        ref = stock_logits(r, prompts, ans)
        noise, off = 0.0, 0  # fp32 noise floor of the stock path itself: each row alone vs in the batch (other padding and chunk alignment)
        for i in range(len(prompts)):
            s1 = stock_logits(r, [prompts[i]], [ans[i]])
            noise, off = max(noise, (s1 - ref[off:off + len(ans[i])]).abs().max().item()), off + len(ans[i])
        tol = max(1e-5, 3 * noise)
        print(f"real fp32 noise floor of the stock path (batch vs single row): {noise:.2e}  -> tolerance {tol:.1e} (spec 1e-5 is below it)")
        C, mask_, p, lt = setup(r, prompts)
        snap0 = snap(C)
        kv, _ = B.think(b, r, C, mask_, p, 8, keep=range(9))
        assert same(snap0, snap(C))
        worst = 0.0
        for L in (0, 1, 4, 8):
            lg, _, _ = B.answer_logits(r, b.gate(), C, mask_, p, lt, ans, kv[L])
            d = (lg - ref).abs().max().item()
            worst = max(worst, d)
            lg0, _, _ = B.answer_logits(r, None, C, mask_, p, lt, ans, None)
            assert torch.equal(lg, lg0), "zero gates are not exactly the no-board path"
            print(f"T1 real 0.8B L={L}: max|diff| vs stock arm a = {d:.2e} (logit scale {ref.abs().max().item():.1f}); argmax equal: {bool((lg.argmax(-1) == ref.argmax(-1)).all())}")
        assert same(snap0, snap(C))
        plain = B.decode(r, b, C, mask_, p, lt, None, max_new=6, eos=enc.eos)
        arm_a = T.greedy(r, prompts, CPU, enc.eos, cache=True)
        print("real decode(slot_kv=None) == arm a greedy (first 6 tokens):", plain == [x[:6] for x in arm_a])
    assert worst <= tol, f"real-model T1 max diff {worst:.2e} > {tol:.1e}"


TESTS = [test_TC_param_count, test_TP_patch_identity, test_T1_alpha0_equals_arm_a, test_T2_cache_untouched, test_T3_slot_pass_equals_no_cache, test_TR_think_api, test_TB_bf16_smoke,
         test_T4_cached_decode_equals_no_cache, test_T5_gradients_only_in_board, test_T5_finite_difference_fp64, test_T6_batch_invariance,
         test_T7_swap_lesion, test_T9_no_leak_from_answer, test_T10_batch_permutation]
REAL_TESTS = [test_real_T1_TP_TC]


def run(real=False, only=None):
    fails = []
    for t in TESTS + (REAL_TESTS if real else []):
        if only and not any(o in t.__name__ for o in only):
            continue
        try:
            t()
            print(f"PASS {t.__name__}", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FAIL {t.__name__}", flush=True)
            fails.append(t.__name__)
    print("board tests:", "ALL PASSED" if not fails else f"FAILED {fails}")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    sys.exit(1 if run(a.real, a.only) else 0)
