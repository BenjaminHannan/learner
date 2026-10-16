"""python3 -m custom_io.tests.test_register_scratch   (CPU, seconds)

The supervised-scratch arm (RegisterLoopScratch): scratch slots are taught the NEXT worked-step value.
Checks the target alignment, the 7-slot truncation, that scratch_weight=0 reproduces the base model's
loss exactly (the arm adds no parameters), that gradients flow, that the scratch lesions run, and that
the scratch readout is shaped right.
"""
import time
import torch
from custom_io.data import EOS, MAX_ANS
from custom_io.models import build
from custom_io.models.register_loop import RegisterLoop
from custom_io.models.register_scratch import RegisterLoopScratch
from custom_io.tests.test_register_loop import MEM, SMALL, batch_of, make_rows, vocab


def expected(value, v, width):
    """The encoding both target builders must produce: value truncated to MAX_ANS chars, units-first, EOS
    appended, then truncated/padded (-100) to `width` slots."""
    ids = v.encode(value[:MAX_ANS][::-1]) + [EOS]
    out = torch.full((width,), -100, dtype=torch.long)
    keep = min(len(ids), width)
    out[:keep] = torch.tensor(ids[:keep], dtype=torch.long)
    return out


def test_scratch_targets_next_value():
    v, rows = vocab(), make_rows(4)
    m = RegisterLoopScratch(v, **SMALL)                       # n_loops=4, 9 registers, 7 scratch slots
    sg = m.scratch_targets(rows)                              # [R,B,7]
    assert sg.shape == (4, 4, 7)
    # rows 0..2 have two step values [v1, ans]: scratch must hold ans from round 0 on (next value, clamped)
    for b in range(3):
        ans = rows[b]['answer']
        for r in range(4):
            assert torch.equal(sg[r, b], expected(ans, v, 7)), (b, r)
    # row 3 is one-step: its only value is the answer, so scratch holds the answer at every round too
    for r in range(4):
        assert torch.equal(sg[r, 3], expected(rows[3]['answer'], v, 7))
    # and the ANSWER targets are untouched vs the base model on the same rows
    base = RegisterLoop(v, **SMALL)
    assert torch.equal(m.targets(rows), base.targets(rows))
    # round-0 answer target for row 0 is its FIRST step value while scratch already holds the answer:
    # the two target streams differ exactly by the one-step shift the arm is built on
    assert torch.equal(base.targets(rows)[0, 0], expected(rows[0]['steps'][0].split()[-1], v, 9))
    print('ok scratch_targets_next_value')


def test_scratch_truncation():
    v = vocab()
    m = RegisterLoopScratch(v, **SMALL)
    # a 9-char step value: truncated to MAX_ANS chars before encoding, so the scratch keeps the 7
    # units-side chars and there is no room for EOS or padding
    row = dict(id='big', prompt='p', answer='123456795',
               steps=['5 + 123456789 = 123456794', '123456794 + 1 = 123456795'])
    sg = m.scratch_targets([row])
    assert torch.equal(sg[0, 0], expected('123456795', v, 7))
    assert (sg[0, 0] != -100).all() and (sg[0, 0] != EOS).all()
    print('ok scratch_truncation')


def test_weight_zero_matches_base():
    v, rows = vocab(), make_rows(8)
    b = batch_of(rows, v)
    torch.manual_seed(3)
    base = RegisterLoop(v, **MEM)
    torch.manual_seed(3)
    arm0 = RegisterLoopScratch(v, **MEM, scratch_weight=0.0)
    assert arm0.n_params() == base.n_params()                 # the arm adds no parameters
    lb, _ = base.loss(b)
    l0, _ = arm0.loss(b)
    assert torch.allclose(lb, l0, atol=1e-6), (lb.item(), l0.item())
    arm1 = RegisterLoopScratch(v, **MEM, scratch_weight=1.0)
    arm1.load_state_dict(base.state_dict())
    l1, parts = arm1.loss(b)
    assert torch.allclose(l1, parts['loss_ans'] + parts['loss_scratch'], atol=1e-5)
    assert parts['loss_scratch'].item() > 0
    print('ok weight_zero_matches_base')


def test_loss_backward():
    v, rows = vocab(), make_rows(8)
    m = RegisterLoopScratch(v, **MEM)
    loss, _ = m.loss(batch_of(rows, v))
    loss.backward()
    g = m.scr.weight.grad
    assert g is not None and torch.isfinite(g).all() and g.abs().sum() > 0   # scratch codes get gradient
    print('ok loss_backward')


def test_lesions_and_readout():
    v, rows = vocab(), make_rows(8)
    m = RegisterLoopScratch(v, **MEM).eval()
    b = batch_of(rows, v)
    assert build('register_scratch', v, **MEM).__class__ is RegisterLoopScratch
    for lesion in (None, 'scratch_zero', 'scratch_shuffle', 'scratch_zero:2', 'scratch_shuffle:0'):
        out = m.generate(b, lesion)
        assert isinstance(out, list) and len(out) == 8 and all(isinstance(s, str) for s in out), lesion
    try:
        m.generate(b, 'bogus_lesion')
        raise AssertionError('bogus lesion accepted')
    except ValueError:
        pass
    ss = m.scratch_strings(b)
    assert len(ss) == MEM['n_loops'] and all(len(r) == 8 for r in ss)
    print('ok lesions_and_readout')


if __name__ == '__main__':
    t0 = time.time()
    test_scratch_targets_next_value(); test_scratch_truncation(); test_weight_zero_matches_base()
    test_loss_backward(); test_lesions_and_readout()
    print(f'ALL OK {time.time() - t0:.0f}s')
