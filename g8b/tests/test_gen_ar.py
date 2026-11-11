#!/usr/bin/env python
"""Checks for the gen_ar option of custom_io.models.ledger.Ledger (8b Fix 3).

Run from the project copy whose custom_io package is under test:
    cd $RUN && python /home/user/learner/g8b/tests/test_gen_ar.py
Each check is also a test_* function, so pytest can collect this file from the same directory.
"""
import importlib.util
import json
import os
import sys
import traceback

sys.path.insert(0, os.getcwd())     # `python <this file>` puts this file's directory on sys.path, not the cwd
import torch

SCRATCH = '/tmp/claude-0/-home-user-learner/88c66c2f-36ea-5698-bb44-b4ab0bb83d1e/scratchpad'
CAPS = os.path.join(SCRATCH, 'caps.json')
SK = os.path.join(SCRATCH, 'sk')
ORIG = os.path.join(SCRATCH, 'ledger_orig.py')
CFG = dict(d=64, n_heads=4, reader_layers=2, blocks=2, n_loops=12, mlp=2.0, copy=True)
N_BATCH = 8

# The ledger module is imported BEFORE caps.apply: apply() only patches modules already in sys.modules
# (N_REG, GEN_MAX, ...), so a ledger imported afterwards would keep the default N_REG = 9.
import custom_io.models.ledger as L
from custom_io.g8a import caps as CP

CAPS_JSON = json.load(open(CAPS))
CP.apply(CAPS_JSON)

from custom_io.g8a.configs import vocab
from custom_io.models import build
from custom_io.models import progparse as pp
from custom_io.data import collate, Dataset, load_rows, to_device, EOS

CHECKS = []
_C = {}


def check(fn):
    CHECKS.append(fn)
    return fn


def build_model(gen_ar=None):
    torch.manual_seed(0)
    kw = dict(CFG)
    if gen_ar is not None:
        kw['gen_ar'] = gen_ar
    return build('ledger', vocab(), **kw)


def make_batch(model):
    """8 dev rows: the first 4 GEN-mode rows and the first 4 other rows of in_dist.jsonl, collated as extra_evals/batches does."""
    rows = load_rows(os.path.join(SK, 'dev', 'in_dist.jsonl'))
    gen_rows, other = [], []
    for r in rows:
        (gen_rows if pp.row_targets(r)['mode'] == 2 else other).append(r)
        if len(gen_rows) >= 4 and len(other) >= 4:
            break
    picked = gen_rows[:4] + other[:4]
    ds = Dataset(picked, model.vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(picked))]), 'cpu')


def ctx():
    if not _C:
        _C['on'] = build_model(True)
        _C['off'] = build_model(False)
        _C['batch'] = make_batch(_C['on'])
    return _C


@check
def test_01_caps_and_build():
    c = ctx()
    on = c['on']
    expect_reg = max(int(CAPS_JSON['n_reg']), int(CAPS_JSON['max_ans']) + 1)
    assert L.N_REG == expect_reg, (L.N_REG, expect_reg)
    assert L.GEN_MAX == L.N_REG - 1, (L.GEN_MAX, L.N_REG)
    assert on.gen_ar is True and hasattr(on, 'ar_type') and on.copy
    return f'ledger file {L.__file__}; N_REG={L.N_REG} GEN_MAX={L.GEN_MAX}; gen_ar model params={on.n_params()}'


@check
def test_02_param_parity():
    c = ctx()
    on, off = c['on'], c['off']
    so, sf = on.state_dict(), off.state_dict()
    missing = set(sf) - set(so)
    extra = set(so) - set(sf)
    assert not missing, sorted(missing)
    assert extra == {'ar_type.weight'}, sorted(extra)
    n_extra = sum(so[k].numel() for k in extra)
    assert n_extra == CFG['d'], n_extra
    assert on.n_params() - off.n_params() == CFG['d'], (on.n_params(), off.n_params())
    diff = [k for k in sf if not torch.equal(so[k], sf[k])]
    assert not diff, diff[:5]
    return (f'extra keys {sorted(extra)} ({n_extra} values); params on {on.n_params()} off {off.n_params()}; '
            f'{len(sf)} shared keys all identical')


@check
def test_03_batch():
    b = ctx()['batch']
    n_gen = sum(pp.row_targets(r)['mode'] == 2 for r in b['rows'])
    assert len(b['rows']) == N_BATCH, len(b['rows'])
    assert n_gen >= 3, n_gen
    return f'{len(b["rows"])} rows, {n_gen} GEN-mode; prompt_ids {tuple(b["prompt_ids"].shape)}'


@check
def test_04_loss_and_backward():
    c = ctx()
    on, b = c['on'], c['batch']
    on.train()
    on.zero_grad()
    loss, _ = on.loss(b)
    assert bool(torch.isfinite(loss)), loss
    loss.backward()
    g = on.ar_type.weight.grad
    assert g is not None, 'ar_type.weight.grad is None'
    gsum = g.abs().sum().item()
    assert gsum > 0, gsum
    return f'loss {loss.item():.6f} finite; ar_type grad |sum| {gsum:.3e}'


@check
def test_05_gen_reads_causal():
    c = ctx()
    on, b = c['on'], c['batch']
    on.eval()
    N, V = L.N_REG, on.reader.tok.weight.shape[0]
    g = torch.Generator().manual_seed(1)
    worst = 0.0
    with torch.no_grad():
        o = on.run(b)
        Z = o['R']
        gen = torch.randint(0, V, (N_BATCH, N), generator=g)
        H = on.gen_reads(Z, gen)
        for i in range(N):
            gen2 = gen.clone()
            gen2[:, i:] = torch.randint(0, V, (N_BATCH, N - i), generator=g)
            H2 = on.gen_reads(Z, gen2)
            head = (H[:, :i + 1] - H2[:, :i + 1]).abs().max().item() if i + 1 > 0 else 0.0
            assert torch.allclose(H[:, :i + 1], H2[:, :i + 1], atol=1e-5), (i, head)
            worst = max(worst, head)
            if i == 0 and N > 1:      # teeth: the slots after 0 DO depend on the letters at 0 and after
                after = (H[:, 1:] - H2[:, 1:]).abs().max().item()
                assert after > 1e-4, after
                tail_dep = after
    return f'N={N} slots, slots 0..i unchanged for every i (max |diff| {worst:.2e}); slot 1+ moves by {tail_dep:.3e} when gen[0:] changes'


@check
def test_06_teacher_forcing_matches_greedy():
    c = ctx()
    on, b = c['on'], c['batch']
    on.eval()
    N = L.N_REG
    with torch.no_grad():
        o = on.run(b)
        Z, X, xm, ids_in = o['R'], o['X'], o['xm'], b['prompt_ids']
        ids = on.ar_decode(Z, X, xm, ids_in)
        p, _ = on.gen_copy(on.gen_reads(Z, ids), X, xm, ids_in)
        am = p.argmax(-1)
    assert tuple(ids.shape) == (N_BATCH, N), tuple(ids.shape)
    checked, eos_rows = 0, 0
    for r in range(N_BATCH):
        eos = (ids[r] == EOS).nonzero()
        last = int(eos[0]) if len(eos) else N - 1
        eos_rows += len(eos) > 0
        ok = am[r, :last + 1] == ids[r, :last + 1]
        assert bool(ok.all()), (r, am[r, :last + 1].tolist(), ids[r, :last + 1].tolist())
        checked += last + 1
    return f'{N_BATCH} rows, {eos_rows} with EOS; {checked} slots up to first EOS all match greedy argmax'


@check
def test_07_generate_variants():
    c = ctx()
    on, b = c['on'], c['batch']
    on.eval()
    lesions = [None, 'zero_state', 'shuffle_state', 'nocopy', 'loops:2']
    sample = None
    with torch.no_grad():
        for name in lesions:
            out = on.generate(b) if name is None else on.generate(b, name)
            assert isinstance(out, list) and len(out) == N_BATCH and all(isinstance(s, str) for s in out), (name, out)
            if name is None:
                sample = out
    return f'8 strings for each of {lesions}; intact first 3: {sample[:3]!r}'


@check
def test_08_gen_ar_off_matches_original():
    spec = importlib.util.spec_from_file_location('custom_io.models.ledger_orig', ORIG)
    orig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(orig_mod)
    # caps.apply patched only the ledger module it found in sys.modules; give the original the same capped globals
    patched = []
    for k in ('N_NUM', 'N_RES', 'W_MAX', 'R0', 'M', 'MAX_PROMPT', 'CAP', 'N_REG', 'GEN_MAX'):
        if hasattr(orig_mod, k) and hasattr(L, k):
            setattr(orig_mod, k, getattr(L, k))
            patched.append(k)
    b = ctx()['batch']
    torch.manual_seed(0)
    orig = orig_mod.Ledger(vocab(), **CFG)
    off = build_model(False)
    orig.train()
    off.train()
    torch.manual_seed(123)
    lo, _ = orig.loss(b)
    torch.manual_seed(123)
    lf, _ = off.loss(b)
    assert lo.item() == lf.item(), (lo.item(), lf.item())
    so, sf = orig.state_dict(), off.state_dict()
    assert set(so) == set(sf), set(so) ^ set(sf)
    assert all(torch.equal(so[k], sf[k]) for k in so), 'state_dict differs'
    return f'loss original {lo.item()!r} == overlay gen_ar=False {lf.item()!r}; state_dicts equal; capped globals copied: {patched}'


def test_all():
    """pytest entry point: runs every check in order (the same ones main() runs)."""
    for fn in CHECKS:
        fn()


def main():
    failed = 0
    for fn in CHECKS:
        try:
            detail = fn()
            print(f'PASS {fn.__name__}: {detail}')
        except Exception as e:
            failed += 1
            print(f'FAIL {fn.__name__}: {type(e).__name__}: {e}')
            traceback.print_exc()
    print(f'{len(CHECKS) - failed}/{len(CHECKS)} checks passed')
    return failed


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
