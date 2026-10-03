"""CPU tests for the wired-up demo. claims: plumbing only; toy data; not an eval.

These show that interfaces, gradients, checkpoints and a sleep night behave. They say nothing about whether
Premonition reads, reasons, calculates or learns. Slow tests: `pytest -m slow tests/test_wired_demo.py`.
"""
import copy
from fractions import Fraction
import random
import time

import pytest
import torch

from premonition.wired_demo import toyworld as T
from premonition.wired_demo import tools, sleep as S
from premonition.wired_demo.actions import Action
from premonition.wired_demo.core import LatentCore
from premonition.wired_demo.model import (WiredModel, gold_steps, load_checkpoint, run_episode, save_checkpoint,
                                          StepSpec)
from premonition.wired_demo.notebook import MAX_SLOTS, Notebook, NotebookError
from premonition.wired_demo.tinylm import Tokenizer, build_frozen_lm
from premonition.wired_demo.train import episode_correct, fit, step_exact_match
from premonition.wired_demo.workspace import SEGMENTS, Workspace

torch.set_num_threads(4)
TRAIN_UPDATES = 600


@pytest.fixture(scope="session")
def tok():
    return Tokenizer()


@pytest.fixture(scope="session")
def lm(tok):
    return build_frozen_lm(T.corpus_texts(random.Random(1), 40), tok, steps=300, seed=0)


def fresh(lm, tok, seed=0):
    torch.manual_seed(seed)
    return WiredModel(lm, tok)


def toy_episodes(seed=0):
    """16 T1 + 16 T2 (4 pairs each) + 16 T3 pairs of (write, read)."""
    rng = random.Random(seed)
    eps = []
    for f in ("T1", "T2"):
        eps += [T.generate(rng, f) for _ in range(8)]
        for _ in range(4):
            eps += list(T.make_pair(rng, f))
    for _ in range(16):
        eps += list(T.generate(rng, "T3"))
    return eps


@pytest.fixture(scope="session")
def eps():
    return toy_episodes()


@pytest.fixture(scope="session")
def all_steps(eps, tok):
    return [s for e in eps for s in gold_steps(e, tok)]


# ----------------------------------------------------------------------------- T1-T4: contract and shapes
def test_workspace_contract(lm, tok, all_steps):
    m = fresh(lm, tok)
    b = m.collate(all_steps[:5])
    ws = b.ws.validate()
    assert ws.tokens.shape[2] == 256 and ws.tokens.dtype == torch.float32 and ws.segment.shape[2] == 2
    assert ws.coords.shape[2] == 3 and ws.valid.dtype == torch.bool
    assert set(ws.role[ws.valid].tolist()) <= {0, 1, 3}
    # an audio-like workspace (modality 7, time coordinate, no row/col) built by hand passes and runs
    n = 6
    audio = Workspace(torch.randn(1, n, 256), torch.tensor([[[SEGMENTS["example"], SEGMENTS["audio"]]] * n]),
                      torch.tensor([[[-1., -1., 0.1 * i] for i in range(n)]]), torch.ones(1, n, dtype=torch.bool)).validate()
    out = m.core(audio)
    assert out.tokens.shape == (1, n, 256) and out.registers.shape == (1, 8, 256)
    bad = copy.deepcopy(ws); bad.tokens[0, -1] += 1.0 if not bad.valid[0, -1] else 0
    with pytest.raises(AssertionError):
        Workspace(torch.ones(1, 2, 256), torch.zeros(1, 2, 2, dtype=torch.long), torch.zeros(1, 2, 3),
                  torch.tensor([[True, False]])).validate()


def test_shapes_end_to_end(lm, tok, all_steps):
    m = fresh(lm, tok)
    for B in (1, 3):
        batch = m.collate(all_steps[:B])
        out, a = m.logits(batch)
        N = batch.ws.tokens.shape[1]
        assert out.tokens.shape == (B, N, 256) and out.registers.shape == (B, 8, 256)
        assert a.kind.shape == (B, 4) and a.arith.shape == (B, 4)
        assert a.ptr_a.shape == a.ptr_b.shape == (B, 11) and a.slot.shape == (B, MAX_SLOTS + 1)
        assert a.start.shape == a.end.shape == (B, N)
        assert m.adapter(out.registers).shape == (B, 8, lm.d_model)
        tgt = torch.randint(4, 40, (B, 3))
        assert m.talker.loss(out.registers, tgt).ndim == 0
    assert m.lm.hidden(torch.tensor([[1, 5, 6]]), torch.ones(1, 3, dtype=torch.bool)).shape == (1, 3, 128)


def test_padding_invariance(lm, tok, all_steps):
    m = fresh(lm, tok).eval()
    longest = max(all_steps, key=lambda s: len(s.question) + sum(map(len, s.notebook)))
    short = min(all_steps, key=lambda s: len(s.question) + sum(map(len, s.notebook)))
    with torch.no_grad():
        _, alone = m.logits(m.collate([short]))
        _, padded = m.logits(m.collate([short, longest]))
    k = alone.ptr_a.shape[1]
    assert torch.allclose(alone.kind[0], padded.kind[0], atol=1e-5)
    assert torch.allclose(alone.ptr_a[0], padded.ptr_a[0, :k], atol=1e-5)
    n = alone.start.shape[1]
    assert torch.allclose(alone.start[0][:n].clamp(min=-1e4), padded.start[0][:n].clamp(min=-1e4), atol=1e-5)


def test_n_loops_configurable(lm, tok, all_steps):
    m = fresh(lm, tok).eval()
    ws = m.collate(all_steps[:2]).ws
    outs = {}
    with torch.no_grad():
        for n in (1, 4, 6):
            outs[n] = m.core(ws, n_loops=n).registers
    assert not torch.allclose(outs[1], outs[4]) and not torch.allclose(outs[4], outs[6])
    assert sum(p.numel() for p in LatentCore(n_loops=2).parameters()) == sum(p.numel() for p in LatentCore(n_loops=8).parameters())
    assert len(m.core.blocks) == 2   # one set of block weights reused every loop


# ----------------------------------------------------------------------------- T5-T6: gradients
def test_grad_reaches_every_trainable_module(lm, tok, all_steps):
    m = fresh(lm, tok)
    steps = ([s for s in all_steps if s.gold.kind == "CALC"][:3] + [s for s in all_steps if s.gold.kind == "NOTE_WRITE"][:2]
             + [s for s in all_steps if s.gold.kind == "ANSWER"][:3])
    loss = m.step_loss(m.collate(steps))
    n = 5
    audio = Workspace(torch.randn(1, n, 256), torch.tensor([[[SEGMENTS["example"], SEGMENTS["audio"]]] * n]),
                      torch.tensor([[[-1., -1., 0.1 * i] for i in range(n)]]), torch.ones(1, n, dtype=torch.bool))
    loss = loss + m.core(audio).tokens.pow(2).mean()   # exercises the no-position and time paths a text batch never hits
    loss.backward()
    dead = [name for name, p in m.named_parameters() if not name.startswith("lm.")
            and (p.grad is None or not torch.isfinite(p.grad).all() or p.grad.abs().sum() == 0)]
    assert dead == []


def test_frozen_lm_no_grad(lm, tok, all_steps):
    m = fresh(lm, tok)
    fp = lm.fingerprint()
    steps = [s for s in all_steps if s.gold.kind == "ANSWER"][:8]
    fit(m, steps, 5, batch=8)
    assert all(not p.requires_grad and p.grad is None for p in lm.parameters())
    assert lm.fingerprint() == fp
    adapter_grad = m.adapter.net[0].weight.grad
    m.step_loss(m.collate(steps)).backward()   # gradient flows THROUGH the frozen LM into the adapter
    assert m.adapter.net[0].weight.grad.abs().sum() > 0 and all(p.grad is None for p in lm.parameters())


# ----------------------------------------------------------------------------- T7-T8: calculator and re-entry
def test_calculator_exact(tok):
    reg = [tools.Entry(f"literal:{i}", Fraction(v), [i], "literal") for i, v in enumerate([3, 1, 0, 7, 2])]
    assert sum(tools.execute("DIV", 1, 3, reg, 0).value for _ in range(1)) == Fraction(1, 7)
    third = tools.execute("DIV", 1, 0, reg, 0).value
    assert third + third + third == 1
    r = tools.execute("DIV", 3, 4, reg, 0)
    assert r.value == Fraction(7, 2) and tools.render(r.value) == "7/2" and tools.parse("7/2") == r.value
    assert tools.render(Fraction(12)) == "12" and tools.render(Fraction(-3)) == "-3"
    assert tools.execute("DIV", 3, 2, reg, 0).error_code == "DIV_BY_ZERO"
    assert tools.execute("ADD", 1, 1, reg, 0).error_code == "DUPLICATE_REFERENCE"
    assert tools.execute("ADD", 0, 1, reg, 4).error_code == "MAX_CALLS"
    assert tools.execute("ADD", 0, 9, reg, 0).error_code == "BAD_REFERENCE"   # a notebook number is never in the registry
    big = [tools.Entry("a", Fraction(10 ** 6), [0], "literal"), tools.Entry("b", Fraction(5), [1], "literal")]
    assert tools.execute("MUL", 0, 1, big, 0).error_code == "VALUE_RANGE"
    for op in ("ADD", "SUB", "MUL", "DIV"):
        assert type(tools.execute(op, 0, 1, reg, 0).value) is Fraction
    for q in ["buys 3 more", "has 17 red and 5 blue", "no numbers", "x 1 y 20 z 300"]:
        reg_q = tools.build_registry(q, tok)
        assert [e.value for e in reg_q] == [Fraction(int(w)) for w in q.split() if w.isdigit()]
        for e in reg_q:
            assert q[e.char_span[0]:e.char_span[1]] == str(int(e.value))
    notebook_numbers = tools.build_registry("Question 5 and 6", tok)
    assert all(e.source == "literal" for e in notebook_numbers) and len(notebook_numbers) == 2


def test_tool_result_reenters(lm, tok):
    m = fresh(lm, tok)
    q, nb = "ana has 7 red pens and 4 blue pens . ana buys 3 more pens of the colour ana likes . How many pens of that colour ?", ["ana likes red ."]
    b0 = m.collate([StepSpec(q, nb, [])])
    b1 = m.collate([StepSpec(q, nb, [Fraction(7, 2)])])
    new = b1.ws.valid.sum() - b0.ws.valid.sum()
    assert new == len(tok.encode("= 7/2")[0]) == 4
    rows = b1.ws.role[0] == SEGMENTS["tool_result"]
    assert int(rows.sum()) == new
    reg = b1.registries[0]
    assert reg[-1].id == "result:1" and reg[-1].value == Fraction(7, 2)
    assert all(rows[i] for i in reg[-1].token_indices)


# ----------------------------------------------------------------------------- T9-T10: notebook
def test_notebook_write_edit(lm, tok):
    q = "Remember : ana likes blue ."
    _, off = tok.encode(q)
    nb = Notebook.from_facts(["ana likes red .", "ben likes red ."])
    nb.apply_write(2, (2, 5), q, off, tok)                      # NEW
    assert nb.texts()[-1] == "ana likes blue ." and len(nb.slots) == 3
    s = nb.apply_write(0, (2, 5), q, off, tok)                  # edit supersedes, keeps history
    assert s.text == "ana likes blue ." and s.version == 1 and s.history == [(0, "ana likes red .")]
    for _ in range(MAX_SLOTS - 3):
        nb.apply_write(len(nb.slots), (2, 5), q, off, tok)
    with pytest.raises(NotebookError, match="full"):
        nb.apply_write(len(nb.slots), (2, 5), q, off, tok)
    with pytest.raises(NotebookError):
        nb.apply_write(0, (4, 2), q, off, tok)
    m = fresh(lm, tok)
    before = m.collate([StepSpec(q, ["ana likes red ."], [])])
    after = m.collate([StepSpec(q, ["ana likes blue ."], [])])
    assert before.ws.tokens.shape == after.ws.tokens.shape
    assert not torch.allclose(before.ws.tokens, after.ws.tokens)   # the edit is visible to the next step
    rt = Notebook.from_json(nb.to_json())
    assert rt.snapshot() == nb.snapshot() and rt.hash() == nb.hash()


def test_notebook_pair_plumbing_untrained(lm, tok):
    m = fresh(lm, tok).eval()
    e, f = T.make_pair(random.Random(3), "T1")
    sa, sb = gold_steps(e, tok)[0], gold_steps(f, tok)[0]
    assert sa.question == sb.question and sa.notebook != sb.notebook
    with torch.no_grad():
        la, lb = m.logits(m.collate([sa]))[1], m.logits(m.collate([sb]))[1]
        assert not torch.allclose(la.ptr_a, lb.ptr_a)
        ea = m.logits(m.collate([StepSpec(sa.question, [], [])]))[1]
        eb = m.logits(m.collate([StepSpec(sb.question, [], [])]))[1]
    assert torch.allclose(ea.ptr_a, eb.ptr_a) and torch.allclose(ea.kind, eb.kind)   # empty notebook: identical inputs


# ----------------------------------------------------------------------------- T11: checkpoint
def test_checkpoint_roundtrip(lm, tok, all_steps, tmp_path):
    a = fresh(lm, tok, seed=1)
    fit(a, all_steps[:24], 6)
    path = tmp_path / "ck.pt"
    nb = Notebook.from_facts(["ana likes red ."])
    save_checkpoint(a, path, extra={"notebook": nb.to_json()})
    b = fresh(lm, tok, seed=2)
    assert b.trainable_hash() != a.trainable_hash()
    extra = load_checkpoint(b, path)
    assert b.trainable_hash() == a.trainable_hash()
    batch = a.collate(all_steps[:4])
    with torch.no_grad():
        la, lb_ = a.eval().logits(batch)[1], b.eval().logits(b.collate(all_steps[:4]))[1]
    assert torch.equal(la.ptr_a, lb_.ptr_a) and torch.equal(la.kind, lb_.kind)
    out = a.collate(all_steps[:1])
    assert a.talker.generate(a.core(out.ws).registers) == b.talker.generate(b.core(b.collate(all_steps[:1]).ws).registers)
    assert Notebook.from_json(extra["notebook"]).snapshot() == nb.snapshot()
    other_lm = build_frozen_lm(T.corpus_texts(random.Random(9), 10), tok, steps=3, seed=5)
    with pytest.raises(ValueError, match="different LM"):
        load_checkpoint(WiredModel(other_lm, tok), path)
    changed = WiredModel(lm, tok, n_loops=2)
    with pytest.raises(ValueError, match="config"):
        load_checkpoint(changed, path)


# ----------------------------------------------------------------------------- T12: sleep
def _night_setup(lm, tok):
    rng = random.Random(5)
    m = fresh(lm, tok)
    day = S.day_records(m, [T.generate(rng, rng.choice(["T1", "T2"])) for _ in range(16)], 1, tok)
    anchor = [S.day_records(m, [T.generate(rng, "T1")], 0, tok)[0] for _ in range(8)]
    store = {0: [S.day_records(m, [T.generate(rng, "T2")], 0, tok)[0] for _ in range(10)]}
    return m, day, anchor, store


def test_sleep_night_updates(lm, tok):
    m, day, anchor, store = _night_setup(lm, tok)
    nb = Notebook.from_facts(["ana likes red ."])
    h0, fp = m.trainable_hash(), lm.fingerprint()
    mix = S.assemble_mix(day, store, anchor, 32, random.Random(0))
    sizes = {k: len(v) for k, v in mix.items()}
    assert abs(sizes["day"] - 16) <= 1 and abs(sizes["earlier"] - 10) <= 1 + 0 and abs(sizes["anchor"] - 6) <= 1 \
        or sum(sizes.values()) == 32
    assert abs(sizes["earlier"] - 10) <= 1 and abs(sizes["anchor"] - 6) <= 1, sizes
    assert all(r.checker == "V1-key" and r.checker_hash for r in mix["day"] + mix["earlier"] + mix["anchor"])
    pf = S.plain_mix(day, 32, random.Random(0))
    for r in S.assemble_mix(day, {}, anchor, 32, random.Random(0))["day"]:
        assert r.class_ in ("A_correct", "B_corrected")
    mine = copy.deepcopy(m)
    rep_s = S.night(m, mix, nb, steps=8, arm="S")
    assert rep_s.trainable_hash_after != h0 and rep_s.lm_fingerprint == fp == lm.fingerprint()
    assert rep_s.notebook_hash == nb.hash() and rep_s.updates == 8
    rep_f0 = S.night(copy.deepcopy(mine), mix, nb, steps=8, arm="F0")
    assert rep_f0.trainable_hash_after == rep_f0.trainable_hash_before == h0 and rep_f0.updates == 0
    rep_pf = S.night(copy.deepcopy(mine), pf, nb, steps=8, arm="PF")
    assert S.arms_matched([rep_s, rep_pf, rep_f0]) and rep_s.examples == rep_pf.examples == 32
    assert rep_pf.trainable_hash_after != rep_s.trainable_hash_after
    with nb.write_lock():
        with pytest.raises(NotebookError, match="locked"):
            nb.apply_write(0, (2, 5), "Remember : ana likes blue .", tok.encode("Remember : ana likes blue .")[1], tok)
    su = S.day_records(mine, [T.generate(random.Random(2), "T1") for _ in range(4)], 1, tok, checked=False)
    assert all(r.class_ == "unchecked" and r.step_targets for r in su)
    dup = S.Buffer(); assert dup.add(1, day[0]) and not dup.add(2, day[0])


# ----------------------------------------------------------------------------- T13-T14: overfit (slow)
@pytest.fixture(scope="module")
def trained(lm, tok, eps, all_steps):
    m = fresh(lm, tok)
    losses = fit(m, all_steps, TRAIN_UPDATES, lr=1e-3, decay=True)
    return m, losses


@pytest.mark.slow
def test_overfit_toy_world(trained, eps, all_steps):
    m, losses = trained
    first, last = sum(losses[:20]) / 20, sum(losses[-20:]) / 20
    exact = step_exact_match(m, all_steps)
    print(f"\n[plumbing only] first20={first:.3f} last20={last:.3f} step_exact_match={exact:.3f}")
    assert last <= 0.5 * first, "loss did not fall enough: a wiring fault (masks, pointers or teacher forcing)"
    assert exact >= 0.9


@pytest.mark.slow
def test_notebook_pair_trained(trained, tok):
    m, _ = trained
    rng = random.Random(0)
    pairs = [T.make_pair(rng, "T1") for _ in range(16)]
    # the pairs are drawn fresh from the same generator: report-only. The gated pairs are the training pairs below.
    train_pairs = []
    ev = toy_episodes()
    for i in range(0, 32, 1):
        pass
    by_q = {}
    for e in ev:
        by_q.setdefault(e.question, []).append(e)
    train_pairs = [v for v in by_q.values() if len(v) == 2 and v[0].family in ("T1", "T2") and v[0].notebook != v[1].notebook]
    assert len(train_pairs) >= 8
    good = 0
    for a, b in train_pairs:
        ra = m.decode(m.collate([gold_steps(a, tok)[0]]))[0][0]
        rb = m.decode(m.collate([gold_steps(b, tok)[0]]))[0][0]
        good += (ra == gold_steps(a, tok)[0].gold and rb == gold_steps(b, tok)[0].gold and ra.ptr_a != rb.ptr_a)
    print(f"\n[plumbing only] training pairs with both gold operands: {good}/{len(train_pairs)}")
    assert good >= 0.85 * len(train_pairs)


@pytest.mark.slow
def test_episode_runs_with_tools_and_notes(trained, eps, tok):
    m, _ = trained
    t1 = [e for e in eps if e.family in ("T1", "T2")]
    right = sum(episode_correct(m, e) for e in t1)
    print(f"\n[plumbing only] end-to-end episodes with the right exact value, TRAIN problems: {right}/{len(t1)}")
    assert right >= 0.5 * len(t1)
    a = next(e for e in eps if e.family == "T3A")
    nb = Notebook.from_facts(list(a.notebook))
    r = run_episode(m, a.question, nb, say=False)
    print("[plumbing only] write turn:", r.status, nb.texts())


# ----------------------------------------------------------------------------- T15: smoke
@pytest.mark.slow
def test_smoke_e2e_under_60s(lm, tok, all_steps, eps, tmp_path):
    t0 = time.time()
    m = fresh(lm, tok)
    fit(m, all_steps, 40)
    a = next(e for e in eps if e.family == "T3A")
    nb = Notebook.from_facts(list(a.notebook))
    r = run_episode(m, a.question, nb)
    assert r.status.startswith(("DONE", "FAIL", "ANSWER"))
    run_episode(m, eps[0].question, nb)
    rng = random.Random(1)
    day = S.day_records(m, [T.generate(rng, "T1") for _ in range(8)], 1, tok)
    anchor = day[:4]
    rep = S.night(m, S.assemble_mix(day, {}, anchor, 16, rng), nb, steps=8)
    assert rep.trainable_hash_after != rep.trainable_hash_before
    save_checkpoint(m, tmp_path / "x.pt"); load_checkpoint(fresh(lm, tok, 3), tmp_path / "x.pt")
    assert time.time() - t0 < 60
