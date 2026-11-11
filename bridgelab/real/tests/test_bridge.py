"""CPU tests of the wiring: zero-init == bridge off (bit-identical, slot value fixed), shuffle permutes, no leakage across a batch, slot injection."""
import random

import pytest
import torch

from custom_io.data import CharVocab, ASCII
from custom_io.models.ledger import Ledger
from bridgelab.real import data as D
from bridgelab.real.bridge import D2C, KINDS, SlotLedger, Wire, ablate, shuffle_perm, to_slot_ledger
from bridgelab.real.train import make_batch

D_CFG = dict(d=32, n_heads=2, reader_layers=1, blocks=2, n_loops=4, copy=True)


def tiny_ledger(seed=0):
    torch.manual_seed(seed)
    vocab = CharVocab(set(ASCII))
    return Ledger(vocab, **D_CFG).eval(), vocab


@pytest.fixture(scope="module")
def items():
    D.warm_references(("add", "mult"))
    rng = random.Random(1)
    its = [D.make_prompt(c, rng, ("add", "mult"), uid=f"t{i}") for i, c in enumerate([0, 3, 1, 4, 2, 0, 3, 1])]
    for it in its:
        D.register(it)
    return its


def regs_for(n, seed=0, R=4, d=128):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(n, R, d, generator=g)


def run_out(m, batch):
    with torch.no_grad():
        o = m.run(batch)
    return o


def same(a, b):
    for k in ("R", "vals", "valid", "lmode", "lans", "lword"):
        assert torch.equal(a[k], b[k]), k


def test_class_swap_changes_nothing(items):
    m, vocab = tiny_ledger()
    ref, _ = tiny_ledger()
    to_slot_ledger(m)
    b = make_batch([it["typed"] for it in items], vocab, "cpu")
    same(run_out(m, b), run_out(ref, b))
    assert m.generate(b) == ref.generate(b)


def test_per_item_bridge_in_shape_is_a_broadcast_of_the_shared_vector(items):
    m, vocab = tiny_ledger()
    b = make_batch([it["typed"] for it in items], vocab, "cpu")
    v = torch.randn(m.d)
    m.bridge_in = lambda: v
    o1 = run_out(m, b)
    m.bridge_in = lambda: v[None].expand(len(items), -1)
    same(o1, run_out(m, b))


@pytest.mark.parametrize("kind", KINDS)
def test_zero_init_is_bit_identical_to_bridge_off(kind, items):
    m, vocab = tiny_ledger()
    to_slot_ledger(m)
    b = make_batch([it["row"] for it in items], vocab, "cpu")
    slot = torch.tensor([it["c"] for it in items])
    m.slot_value = slot                                   # the slot value is FIXED in both runs
    off = run_out(m, b)
    gen_off = m.generate(b)
    br = D2C(kind, d_c=m.d, n_core=len(m.core))
    br.eval()
    wire = Wire(m, br).attach()
    wire.set(br(regs_for(len(items))), slot)
    on = run_out(m, b)
    same(off, on)
    assert m.generate(b) == gen_off
    wire.detach()


def test_slot_value_reaches_executor_at_the_query_ordinal(items):
    m, vocab = tiny_ledger()
    to_slot_ledger(m)
    b = make_batch([it["row"] for it in items], vocab, "cpu")
    slot = torch.tensor([7, 8, 9, 11, 12, 13, 14, 15])
    m.slot_value = slot
    o = run_out(m, b)
    assert o["vals"][:, 6].tolist() == slot.tolist()       # 3 examples -> numbers x1 y1 x2 y2 x3 y3 then the query = slot 6
    assert o["valid"][:, 6].all()
    # the other prompt numbers are the real ones
    for i, it in enumerate(items):
        assert o["vals"][i, :6].tolist() == it["nums"][:6]


@pytest.mark.parametrize("kind", ("pooled", "xattn"))
def test_message_changes_output_and_no_leak_across_the_batch(kind, items):
    m, vocab = tiny_ledger()
    to_slot_ledger(m)
    b = make_batch([it["row"] for it in items], vocab, "cpu")
    slot = torch.tensor([it["c"] for it in items])
    br = D2C(kind, d_c=m.d, n_core=len(m.core)).eval()
    for p in br.parameters():                           # un-zero everything so the message really acts
        torch.nn.init.normal_(p, std=0.3) if p.dim() > 1 else torch.nn.init.normal_(p, std=0.1)
    if kind == "xattn":
        for blk in br.blocks:
            blk.gate.data.fill_(1.0)
    wire = Wire(m, br).attach()
    regs = regs_for(len(items), 3)
    wire.set(br(regs), slot)
    base = run_out(m, b)
    j = 2
    regs2 = regs.clone()
    regs2[j] = torch.randn_like(regs2[j]) * 3
    wire.set(br(regs2), slot)
    new = run_out(m, b)
    others = [i for i in range(len(items)) if i != j]
    for k in ("R", "lans", "lmode"):
        assert torch.equal(base[k][others], new[k][others]), f"{k}: another item's message leaked into the batch"
    assert not torch.equal(base["R"][j], new["R"][j]), "the item's own message has no effect"
    # a batch of 8 gives the same state as each item alone
    solo = []
    for i in range(len(items)):
        bi = make_batch([items[i]["row"]], vocab, "cpu")
        wire.set(br(regs[i:i + 1]), slot[i:i + 1])
        solo.append(run_out(m, bi)["R"][0])
    wire.set(br(regs), slot)
    full = run_out(m, b)["R"]
    assert torch.allclose(torch.stack(solo), full, atol=1e-4, rtol=1e-4)
    wire.detach()


def test_shuffle_off_mean_ablations():
    torch.manual_seed(0)
    n = 60
    regs = torch.randn(n, 4, 128)
    c = torch.randint(0, 5, (n,))
    p = shuffle_perm(n, 0, c)
    assert sorted(p.tolist()) == list(range(n))
    assert (p == torch.arange(n)).sum() == 0
    assert (c[p] == c).sum() == 0, "shuffled messages must come from items with a different count"
    s = ablate(regs, "shuffle", 0, c)
    assert torch.equal(s, regs[p]) and not torch.equal(s, regs)
    assert torch.equal(torch.sort(s.flatten(1), 0).values, torch.sort(regs.flatten(1), 0).values)      # same multiset of messages
    assert ablate(regs, "off").abs().sum() == 0
    m = ablate(regs, "mean")
    assert torch.allclose(m[0], regs.mean(0)) and torch.equal(m[0], m[-1])
    assert torch.equal(ablate(regs, "real"), regs)
    assert torch.equal(shuffle_perm(n, 5, c), shuffle_perm(n, 5, c))               # deterministic in the seed


def test_ema_const_is_the_same_vector_for_every_question():
    br = D2C("ema_const")
    br.train()
    br.joint.p_dc.weight.data.normal_()
    br.observe(torch.randn(16, 128))
    br.eval()
    out = br(regs_for(5))
    assert torch.equal(out["v"][0], out["v"][3]) and torch.equal(out["logits"][0], out["logits"][4])
    out2 = br(regs_for(5, seed=9) * 10)                  # different messages, same output: it cannot carry a question
    assert torch.equal(out["v"], out2["v"]) and torch.equal(out["logits"], out2["logits"])


def test_count_head_trains_only_bridge_params_and_none_is_a_bias():
    br = D2C("none")
    out = br(regs_for(3))
    assert out["logits"].shape == (3, D.CMAX + 1) and out["v"] is None
    br = D2C("pooled")
    x = regs_for(4)
    loss = torch.nn.functional.cross_entropy(br(x)["logits"], torch.tensor([0, 1, 2, 3]))
    loss.backward()
    assert all(p.grad is not None for p in br.head.parameters())
