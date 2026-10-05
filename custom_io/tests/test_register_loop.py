"""python3 -m custom_io.tests.test_register_loop   (CPU, about a minute)"""
import copy, json, os, random, tempfile, time
import torch
from custom_io.data import CharVocab, Dataset, collate
from custom_io.evalx import donor_eval, evaluate
from custom_io import diag_register as dg
from custom_io.models.register_loop import RegisterLoop

S_CFG = dict(d_model=256, n_heads=4, reader_layers=2, core_blocks=3, n_loops=6, mlp=2.25)
M_CFG = dict(d_model=384, n_heads=6, reader_layers=2, core_blocks=5, n_loops=6, mlp=2.2)
SMALL = dict(d_model=64, n_heads=2, reader_layers=2, core_blocks=2, n_loops=4, mlp=2.0)
MEM = dict(d_model=64, n_heads=2, reader_layers=1, core_blocks=1, n_loops=3, mlp=2.0)      # smaller, for the training test


def make_rows(n, seed=0):
    """Synthetic rows in the dataset format: chain_ops, state_update, var_chain (2 step values) and arith_bare (1)."""
    rng, rows = random.Random(seed), []
    for i in range(n):
        a, b, c = rng.randint(20, 99), rng.randint(1, 19), rng.randint(2, 9)
        k = i % 4
        if k == 0:
            st, p, f = [f'{a} - {b} = {a - b}', f'{a - b} + {c} = {a - b + c}'], f'Al has {a} nuts. Then Al gives away {b}. Then Al gets {c} more. How many nuts does Al have at the end?', 'chain_ops'
        elif k == 1:
            st, p, f = [f'-{b} -> {a - b}', f'+{c} -> {a - b + c}'], f'A jar holds {a} marbles. {b} are removed. {c} are added. How many marbles are in the jar now?', 'state_update'
        elif k == 2:
            st, p, f = [f'p = {a} * {c} = {a * c}', f'n = {a * c} - {b} = {a * c - b}'], f'Facts: q = {a}. p = q * {c}. n = p - {b}. Question: What is n?', 'var_chain'
        else:
            st, p, f = [f'{a} - {b} = {a - b}'], f'Subtract {b} from {a}. State the result only.', 'arith_bare'
        ans = st[-1].split()[-1]
        rows.append(dict(id=f'r{i}', prompt=p, answer=ans, accepted=[ans], family=f, level=1, variant='v', steps=st))
    return rows


def vocab():
    return CharVocab.build(make_rows(4))


def batch_of(rows, v):
    return collate([Dataset(rows, v, strict=False)[i] for i in range(len(rows))])


def test_no_leak():
    v, rows = vocab(), make_rows(8)
    m = RegisterLoop(v, **SMALL).eval()
    stripped = [{k: x for k, x in r.items() if k not in ('answer', 'steps', 'accepted')} for r in rows]
    b1, b2 = batch_of(rows, v), batch_of(rows, v)
    b2['rows'], b2['ans_ids'], b2['ans_mask'] = stripped, torch.zeros_like(b2['ans_ids']), torch.zeros_like(b2['ans_mask'])
    for loops in (None, 0, 1):
        assert torch.equal(m.state(b1, loops), m.state(b2, loops))
    assert torch.equal(m.state(b1, blind=True), m.state(b2, blind=True))
    print('ok no_leak')


def test_memorise():
    v, rows = vocab(), make_rows(16, 1)
    torch.manual_seed(0)
    m = RegisterLoop(v, **MEM)
    opt = torch.optim.AdamW(m.parameters(), lr=5e-3, weight_decay=0.0)
    b = batch_of(rows, v)
    t0 = time.time()
    for s in range(500):
        loss, _ = m.loss(b)
        loss.backward(); opt.step(); opt.zero_grad()
        if s % 100 == 0:
            print('  step', s, round(loss.item(), 4))
        if loss.item() < 0.01:
            break
    r = evaluate(m, rows, 16)
    print(f'ok memorise exact {r["exact"]:.0f}% loss {loss.item():.4f} steps {s + 1} {time.time() - t0:.0f}s')
    assert r['exact'] == 100, r['exact']
    return m, rows, v


def test_targets_a_vs_a0():
    v, rows = vocab(), make_rows(12)
    a, a0 = RegisterLoop(v, **SMALL), RegisterLoop(v, steps=False, **SMALL)
    ta, t0 = a.targets(rows), a0.targets(rows)
    assert ta.shape == t0.shape == (4, 12, 9)
    for b, r in enumerate(rows):
        multi = len(dg.step_values(r)) >= 2
        assert torch.equal(ta[:, b], t0[:, b]) != multi, (r['family'], multi)
    r = rows[0]                                     # chain_ops: round 1 = v1 (reversed + EOS), rounds 2.. = answer
    dec = lambda t: v.decode(t.tolist())[::-1]
    v1 = r['steps'][0].split()[-1]
    assert [dec(ta[i, 0]) for i in range(4)] == [v1, r['answer'], r['answer'], r['answer']]
    assert all(dec(t0[i, 0]) == r['answer'] for i in range(4))
    long = dict(rows[3], answer='123456789012', steps=None)         # truncated to 8 chars + EOS, as the harness does
    assert dec(a.targets([long])[0, 0]) == '12345678'
    one = dict(rows[3], steps=['12 * 8 = 96'], answer='8')
    assert torch.equal(a.targets([one]), a0.targets([one]))
    assert torch.equal(a.targets(rows), ta)                                         # cached path identical
    print('ok targets')


def test_param_counts():
    v = vocab()
    for name, cfg, ref in (('S', S_CFG, 3_244_544), ('M', M_CFG, 10_775_040)):
        n = RegisterLoop(v, **cfg).n_params()
        print(f'  {name}: {n:,} vs {ref:,} ({100 * (n / ref - 1):+.2f}%)')
        assert abs(n / ref - 1) <= 0.03
    assert RegisterLoop(v, steps=False, **S_CFG).n_params() == RegisterLoop(v, **S_CFG).n_params()
    print('ok params')


def test_lesions():
    v, rows = vocab(), make_rows(8)
    m = RegisterLoop(v, **SMALL).eval()
    b = batch_of(rows, v)
    for les in [None] + m.LESIONS + ['loops:0', 'loops:1', 'loops:2', 'loops:8']:
        out = m.generate(b, les)
        assert len(out) == 8 and all(isinstance(o, str) for o in out), les
    assert len(set(m.generate(b, 'loops:0'))) == 1                  # round 0: registers cannot depend on the prompt
    assert torch.equal(m.state(b, 0)[0], m.state(b, 0)[1])
    assert not torch.equal(m.state(b), m.state(b, blind=True))
    assert not torch.equal(m.state(b, 2), m.state(b, 3))
    n_blind = sum(1 for _ in m.rounds(b, blind=True))
    assert n_blind == 4
    print('ok lesions')


def test_counterfactual():
    r = dict(steps=['36 - 16 = 20', '20 - 6 = 14'], answer='14')
    assert dg.counterfactual(r, 50) == (44, None)
    r = dict(steps=['10 - 5 = 5', '5 * 5 = 25'], answer='25')       # both operands equal the running value: left one is replaced
    assert dg.counterfactual(r, 7) == (35, None)
    r = dict(steps=['27 / 3 = 9', '9 + 6 = 15'], answer='15')
    assert dg.counterfactual(r, -4) == (2, None)
    r = dict(steps=['-4 -> 28', '+7 -> 35', '-9 -> 26'], answer='26')
    assert dg.counterfactual(r, 40) == (38, None)
    r = dict(steps=['p = 8 * 4 = 32', 'n = 32 + 9 = 41'], answer='41')
    assert dg.counterfactual(r, 10) == (19, None)
    r = dict(steps=['q = 20 / 4 = 5', 'n = 100 - 5 = 95'], answer='95')     # running value is the right operand
    assert dg.counterfactual(r, 10) == (90, None)
    r = dict(steps=['10 + 8 = 18', '18 / 3 = 6'], answer='6')               # inexact division from the donor value
    assert dg.counterfactual(r, 11) == (None, 'inexact_division')
    r = dict(steps=['23+17-8=32', 'compare 32 64'], answer='friend')
    assert dg.counterfactual(r, 5)[0] is None
    r = dict(steps=['+6 -> 41', '-1 -> 40', '-7 -> 33', '33 + 33'], answer='66')
    assert dg.counterfactual(r, 5)[0] is None
    assert dg.counterfactual(dict(steps=['36 - 16 = 20', '20 - 6 = 14'], answer='15'), 5)[0] is None
    assert dg.step_values(dict(steps=['23+17-8=32', 'compare 32 64'], answer='friend')) == ['32', 'friend']
    assert dg.step_values(dict(steps=['2 + 2 = 4'], answer='4')) == ['4']
    assert dg.step_values(dict(steps=['12 * 8 = 96'], answer='8')) == ['8']          # one line: never a separate round-1 target
    assert dg.step_values(dict(steps=['n = 23'], answer='2')) == ['2']
    assert dg.step_values(dict(steps=['2 + 2 = 4', '4 * 3 = 12'], answer='12'), use_steps=False) == ['12']
    assert dg.step_values(dict(steps=['2 + 2 = 4', '4 * 3 = 12'], answer='12')) == ['4', '12']
    rows = make_rows(40)
    pairs, skipped = dg.pick_donors(rows)
    assert pairs and sum(len(dg.step_values(r)) >= 2 for r in rows) == len(pairs) + sum(skipped.values())
    for i, j, cf in pairs:
        assert rows[i]['family'] == rows[j]['family'] and i != j and cf != rows[i]['answer']
        assert dg.step_values(rows[i])[0] != dg.step_values(rows[j])[0]
        assert dg.counterfactual(rows[i], int(dg.step_values(rows[j])[0]))[0] == int(cf)
    assert dg.pick_donors(rows) == (pairs, skipped)             # deterministic
    print('ok counterfactual')


def test_donor_eval(m=None, rows=None, v=None):
    v = v or vocab()
    rows = rows or make_rows(16, 1)
    m = m or RegisterLoop(v, **SMALL)
    assert m.supports_donor()
    r = donor_eval(m, rows, 8)
    assert r['n'] + r['skipped'] == 16 and 'donor_match' in r
    print('ok donor_eval', {k: r[k] for k in ('exact', 'donor_match', 'n', 'skipped')})


def test_extra_evals(m=None, v=None):
    v = v or vocab()
    m = m or RegisterLoop(v, **MEM)
    rows = [r for r in make_rows(60, 2) if r['family'] != 'arith_bare']
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'dev'))
        with open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w') as f:
            f.writelines(json.dumps(r) + '\n' for r in rows)
        ctx = dict(data=d, big=None, device=torch.device('cpu'), batch_size=16, amp=lambda: torch.autocast('cpu', enabled=False))
        out = m.extra_evals(ctx)
        out2 = m.extra_evals(dict(ctx, big=d))
    json.dumps(out)
    st, ic = out['staircase'], out['interchange']
    assert out['n_rows'] == st['n'] == len(rows) == 45 and len(st['by_round']) == 3
    assert ic['n_scored'] + ic['n_skipped'] == 45 and ic['n_scored'] > 0, ic
    assert out2['interchange'] == ic and 'cf_match_full' in ic
    # plumbing: donor = the row itself reproduces the intact answer
    b = batch_of(rows[:6], v)
    S1 = next(iter(m.eval().rounds(b, loops=1)))
    S = None
    for S in m.rounds(b, S0=S1, start=1):
        pass
    assert torch.equal(S[:, :9], m.state(b))
    # register-only swap: the continued state is the donor's registers + the current row's own round-1 scratch
    seen, orig = [], m.rounds
    def spy(bb, loops=None, S0=None, start=0, blind=False):
        if S0 is not None:
            seen.append((bb, S0))
        return orig(bb, loops, S0, start, blind)
    m.rounds = spy
    dg.interchange(m, rows, torch.device('cpu'), 16)
    m.rounds = orig
    bb, S0 = seen[0]
    own = next(iter(orig(bb, loops=1)))
    assert torch.equal(S0[:, 9:], own[:, 9:]) and not torch.equal(S0[:, :9], own[:, :9])
    assert not torch.equal(seen[1][1][:, 9:], own[:, 9:])                       # the second (full-swap) state is the donor's
    print('ok extra_evals', {k: ic[k] for k in ('n_scored', 'n_skipped', 'cf_match', 'own_match')})


if __name__ == '__main__':
    t0 = time.time()
    test_no_leak(); test_targets_a_vs_a0(); test_param_counts(); test_lesions(); test_counterfactual()
    m, rows, v = test_memorise()
    test_donor_eval(m, rows, v); test_extra_evals(m, v)
    print(f'ALL OK {time.time() - t0:.0f}s')
