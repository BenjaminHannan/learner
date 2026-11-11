"""python3 -m custom_io.tests.test_tool   (CPU; the real-data checks need the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
T1 = B2 with the calculator outside (models/tool.py, PASS-MARKS.md addendum 17): size and shared init, the calculator, gold calls equal what the
calculator returns, no look-ahead under teacher forcing, every lesion runs, the replay used by opswap / write_copy, the extra eval, and the
mechanism: a small T1 learns to write calls whose operands it copies and to copy the result back as its answer, on numbers it never saw."""
import contextlib, json, os, random, tempfile, time
import torch
from custom_io.data import DEFAULT_DATA, Dataset, collate, load_rows
from custom_io.evalx import donor_eval, evaluate
from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger
from custom_io.models.tool import CELLS, LE, NAMES, Tool, calc, entry
from custom_io.tests.test_ledger import S_CFG, SMALL, batch_of, train_rows, vocab
from custom_io.train import lesion_names

T1_PARAMS, B2_PARAMS = 3277393, 3302481
GONE = ('vcode', 'res_from_z', 'op_emb', 'q_a', 'q_b', 'q_ans', 'k_slot', 'ln_k')
NEW = ('W_a', 'W_b', 'tape_emb')


def seeded(cfg, seed=0, v=None):
    torch.manual_seed(seed)
    return Tool(v or vocab(), **cfg)


def test_size_and_init():
    v = vocab()
    m = seeded(S_CFG, v=v)
    torch.manual_seed(0)
    b2 = Ledger(v, copy=True, **S_CFG)
    assert m.n_params() == T1_PARAMS and b2.n_params() == B2_PARAMS, (m.n_params(), b2.n_params())
    assert abs(T1_PARAMS / 3.24e6 - 1) <= 0.03
    s1, s2 = m.state_dict(), b2.state_dict()
    assert {k.split('.')[0] for k in s1 if k not in s2} == set(NEW), [k for k in s1 if k not in s2]
    assert {k.split('.')[0] for k in s2 if k not in s1} == set(GONE), [k for k in s2 if k not in s1]
    assert all(torch.equal(s1[k], s2[k]) for k in s1 if k in s2), 'a weight shared with B2 starts differently'
    assert m.LESIONS == ['shuffle_state', 'zero_state', 'noexec', 'opswap', 'nocopy', 'nowordc'] and m.copy
    print('ok size_and_init', m.n_params())


def test_calc():
    cases = [(('add', '12', '5'), '17'), (('sub', '5', '12'), '-7'), (('mul', '-3', '4'), '-12'), (('div', '12', '4'), '3'), (('div', '7', '2'), '?'),
             (('div', '7', '0'), '?'), (('mod', '7', '3'), '1'), (('mod', '7', '0'), '?'), (('min', '3', '9'), '3'), (('max', '3', '9'), '9'),
             (('cmp', '3', '9'), '-1'), (('cmp', '9', '9'), '0'), (('add', '1 2', '3'), '?'), (('add', '', '3'), '?'), (('noop', '1', '2'), '?'),
             (('add', '999999999', '1'), '?'), (('add', '1000000000', '0'), '?'), (('mul', '40000', '30000'), '?'), (('add', '-', '3'), '?')]
    for (op, a, b), want in cases:
        assert calc(op, a, b) == want, (op, a, b, calc(op, a, b), want)
    assert calc('add', '12', '5', swap=True) == '7' and calc('sub', '12', '5', swap=True) == '17' and calc('mul', '2', '3', swap=True) == '6'
    assert entry('add', '12', '5', '17') == 'add 12 5 = 17' and len(entry('add', '1' * 10, '2' * 10, '3' * 10)) <= LE
    print('ok calc')


def test_gold_tape_matches_calc():
    """Teacher forcing shows exactly the text calc() returns for the gold call; every operand fits the cells."""
    m, n = seeded(SMALL), 0
    for r in train_rows(4000, 3):
        ops, opd, tape, md, _ = m.row_gold(r)
        for k, (o, (a, b)) in enumerate(zip(ops, opd)):
            assert tape[k] == entry(NAMES[o], a, b, calc(NAMES[o], a, b)), (r['id'], tape[k], calc(NAMES[o], a, b))
            assert len(a) < CELLS and len(b) < CELLS
            n += 1
        assert tape[len(ops):] == [''] * (len(tape) - len(ops)) and md in (1, 2)
    assert n > 300, n
    print(f'ok gold_tape_matches_calc ({n} calls)')


def prog_rows(n, min_steps, seed=0):
    out = [r for r in train_rows(6000, seed) if len(pp.row_targets(r)['prog']) >= min_steps]
    assert len(out) >= n, len(out)
    return out[:n]


def test_no_lookahead():
    """Teacher forcing: the round-t call (step t-1) sees entries 0..t-2 only; changing entry 1 changes nothing at steps 0 and 1, does change
    step 2 of the rows that show entry 1, and changes the final talker's context."""
    v = vocab()
    m = seeded(SMALL, 1, v).eval()
    rows = prog_rows(16, 3)
    b = batch_of(rows, v)
    with torch.no_grad():
        g = m.gold(rows, 'cpu')
        o1 = m.run(b, gold=g)
        bump = lambda e: e.split(' = ')[0] + ' = ' + ''.join(str((int(c) + 1) % 10) if c.isdigit() else c for c in e.split(' = ')[1])
        g2 = dict(g, tape=[[e if k != 1 else bump(e) for k, e in enumerate(tp)] for tp in g['tape']])       # same length: same tape layout
        o2 = m.run(b, gold=g2)
    for s in (0, 1):
        assert torch.equal(o1['steps'][s][0], o2['steps'][s][0]) and torch.equal(o1['steps'][s][1], o2['steps'][s][1]), s
    shown = g['op'][:, 1] > 0
    assert shown.all()
    d2 = (o1['steps'][2][1] - o2['steps'][2][1]).abs().flatten(1).amax(1)
    assert (d2[shown] > 0).all(), d2
    assert not torch.equal(o1['R'], o2['R'])
    print('ok no_lookahead')


def test_tape_layout():
    """The trimmed teacher-forced tape (only the entries the batch uses, each as long as the longest) gives the same loss as the free-run layout."""
    v = vocab()
    m = seeded(SMALL, 4, v).eval()
    b = batch_of(prog_rows(32, 1, 4), v)
    with torch.no_grad():
        l1, a1 = m.loss(b)
        m._full_tape = True
        l2, a2 = m.loss(b)
        m._full_tape = False
    assert abs(float(l1) / float(l2) - 1) < 1e-5 and all(abs(float(a1[k]) - float(a2[k])) < 1e-4 for k in a1), (float(l1), float(l2), a1, a2)
    print('ok tape_layout', float(l1))


def test_runs_and_lesions():
    v = vocab()
    m = seeded(SMALL, 2, v)
    rows = train_rows(48, 5)
    loss, aux = m.loss(batch_of(rows, v))
    assert torch.isfinite(loss) and {'prog', 'op_acc', 'call', 'mode', 'word', 'gen', 'copy_share'} <= set(aux)
    loss.backward()
    assert all(p.grad is not None for p in m.parameters()), [k for k, p in m.named_parameters() if p.grad is None]
    m.eval()
    b = batch_of(rows, v)
    for les in [None] + lesion_names(m) + ['ctl27']:
        out = m.generate(b, les)
        assert len(out) == len(rows) and all(isinstance(x, str) for x in out), les
    with torch.no_grad():
        o = m.run(b)
    assert len(o['calls']) == len(rows) and o['X'].shape[1] == b['prompt_ids'].shape[1] + 7 * LE
    for calls in o['calls']:
        for t, op, a, bb, r in calls:
            assert 1 <= t <= 7 and op in NAMES[1:] and r == calc(op, a, bb)
    with torch.no_grad():
        on = m.run(b, lesion='noexec')
    assert all(c[4] == '?' for cs in on['calls'] for c in cs)
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    res = donor_eval(m, random.Random(0).sample(dev, 64), 32)
    assert res['n'] > 0 and 0 <= res['exact'] <= 100
    print('ok runs_and_lesions', lesion_names(m))


def test_replay():
    calls = [(1, 'add', '12', '5', '17'), (2, 'sub', '17', '3', '14'), (3, 'mul', '14', '2', '28')]
    src = Tool.sources(calls, 'What is 12 plus 5 minus 3 times 2?')
    assert src == [[('v', 12), ('v', 5)], [('e', 0), ('v', 3)], [('e', 1), ('v', 2)]], src
    assert Tool.replay(calls, src) == [17, 14, 28]
    assert Tool.replay(calls, src, swap=True) == [7, 10, 20]
    assert Tool.sources([(1, 'add', 'x', '5', '?')], '') == [[None, ('v', 5)]] and Tool.replay([(1, 'add', 'x', '5', '?')], [[None, ('v', 5)]]) == [None]
    print('ok replay')


def test_extra_evals():
    v = vocab()
    m = seeded(SMALL, 3, v).eval()
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    with open(tmp + '/dev/in_dist.jsonl', 'w') as f:
        for r in random.Random(1).sample(dev, 200):
            f.write(json.dumps(r) + '\n')
    ctx = dict(data=tmp, big=None, device=torch.device('cpu'), batch_size=64, amp=contextlib.nullcontext)
    ex = m.extra_evals(ctx)
    json.dumps(ex)
    assert {'coverage', 'op_acc', 'noexec', 'chain5_lesions', 'opswap', 'write_copy', 'copy_gate', 'size'} <= set(ex), set(ex)
    assert set(ex['op_acc']) == {'teacher_forced', 'free_run', 'n'} and 'answer' in ex['op_acc']['free_run']
    print('ok extra_evals', json.dumps({k: ex[k] for k in ('op_acc', 'write_copy')})[:400])


# ---- the mechanism: the whole chain through the outside calculator, on numbers never seen in training ----------------------------
MECH_CFG = dict(d=64, n_heads=2, reader_layers=2, blocks=1, n_loops=4, mlp=2.0)
MECH_STEPS, MECH_CAP_S = 1500, 900       # about 270 s on 2 busy CPU cores; curve (held-out exact): 79 at 500 steps, 84 at 1000, 96 at 1250, 99 at 1500


def tool_rows(n, tag, seed, lo=1, hi=5):
    """'What is A plus B?' (one call) and 'Start with A, add B, then take away C.' (two calls, the second copies the first result)."""
    rng, out = random.Random(seed), []
    num = lambda: int(rng.choice('123456789') + ''.join(rng.choice('0123456789') for _ in range(rng.randint(lo, hi) - 1)))
    for i in range(n):
        a, b = num(), num()
        if i % 2:
            out.append(dict(id=f'syn_tool_{tag}_{i}', prompt=f'What is {a} plus {b}?', answer=str(a + b), accepted=[str(a + b)], family='syn_add',
                            level=1, steps=[f'{a} + {b} = {a + b}']))
        else:
            c = rng.randint(1, a + b)
            out.append(dict(id=f'syn_tool_{tag}_{i}', prompt=f'Start with {a}, add {b}, then take away {c}.', answer=str(a + b - c),
                            accepted=[str(a + b - c)], family='syn_chain', level=2, steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    assert all(len(pp.row_targets(r)['prog']) == 1 + (int(r['id'].split('_')[-1]) % 2 == 0) for r in out), 'progparse'
    return out


def test_mechanism_tool():
    v = vocab()
    torch.manual_seed(0)
    m = Tool(v, **MECH_CFG)
    rows = tool_rows(20000, 'tr', 0)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=0.0)
    ds, rng, t0 = Dataset(rows, v), random.Random(0), time.time()
    for step in range(MECH_STEPS):
        loss, aux = m.loss(collate([ds[i] for i in rng.sample(range(len(rows)), 64)]))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        if time.time() - t0 > MECH_CAP_S:
            break
    m.eval()
    test = tool_rows(400, 'te', 1)
    seen = {r['prompt'] for r in rows}
    test = [r for r in test if r['prompt'] not in seen]
    res = evaluate(m, test, 100)
    off = evaluate(m, test, 100, lesion='noexec')
    print(f"  {step + 1} steps, {time.time() - t0:.0f}s, loss {loss.item():.3f}: held-out exact {res['exact']:.1f} "
          f"(one call {res['by_family']['syn_add']}, two calls {res['by_family']['syn_chain']}); tool off {off['exact']:.1f}")
    assert step + 1 == MECH_STEPS and res['exact'] >= 90 and off['exact'] <= 5, (step + 1, res['exact'], off['exact'])
    print('ok mechanism_tool')


def synth_t1(b2, d_correct=0, c5=None, wc=100.0, tool_off=0.0, swap=100.0, loops0=0.0, donor=0.0):
    """A fake T1 RESULT.json made from a q33 B2 run: the same scores shifted by d_correct rows on every pooled split."""
    import copy
    r = copy.deepcopy(b2)
    r['config'] = dict(r['config'], model='tool', cfg={})
    r['n_params'] = T1_PARAMS
    for sp in ('in_dist', 'answer', 'frame', 'vocab', 'variant'):
        fe = r['final_eval'][sp]
        fe['correct'] += d_correct
        fe['exact'] = 100 * fe['correct'] / fe['n']
    if c5 is not None:
        r['chain5']['intact']['exact'] = c5
    r['lesions']['loops:0']['in_dist']['exact'] = loops0
    r['lesions']['donor']['in_dist']['exact'] = donor
    r['extra'] = dict(write_copy=dict(operand_copy=wc, answer_copy=wc, op_n=100, ans_n=100, path_changed=0, too_long=0, op_by_len={}, ans_by_len={}),
                      noexec=dict(program_families=tool_off, chain5=0.0), opswap=dict(swap_match=swap, n_affected=50),
                      op_acc=dict(teacher_forced=dict(call=99.0), free_run=dict(call=98.0, program=97.0, answer=90.0)), copy_gate=dict(overall=0.9))
    return r


def test_judge():
    """analyze_t1 computes the sealed marks as written, on fake T1 runs built from q33's B2 results."""
    from custom_io import analyze_t1 as A
    from custom_io.analyze import load
    runs, _ = load(['custom_io/results/33-pc-confirm-b2'])
    b2 = {s: runs[('B2', s)] for s in A.CONFIRM}

    def with_t1(**kw):
        rr = {k: v for k, v in runs.items() if k[0] == 'B2'}
        for s in A.CONFIRM:
            rr[('T1', s)] = synth_t1(b2[s], **{k: (v[s] if isinstance(v, dict) else v) for k, v in kw.items()})
        return rr
    sc, cf = A.screen(with_t1()), A.confirm(with_t1())
    assert sc['verdict'].startswith('PASS') and cf['verdict'].startswith('PASS'), (sc['verdict'], cf['verdict'], {k: x['ok'] for k, x in cf['marks'].items()})
    assert A.screen(with_t1(wc=98.9))['verdict'].startswith('NOT SHOWN')                     # the D0 writing tightening
    assert A.screen(with_t1(c5=94.9))['verdict'].startswith('NOT SHOWN')
    n5 = sum(b2[200]['final_eval'][sp]['n'] for sp in ('in_dist', 'answer', 'frame', 'vocab', 'variant'))
    k = -int(0.4 * n5 / 100 / 5) - 1                                                            # about -0.4 pooled-5 points on every seed
    alt = {s: (k if s % 2 else 0) for s in A.CONFIRM}                                          # a spread across seeds: mark 1 is the CI rule
    r = A.confirm(with_t1(d_correct=alt))
    m1 = next(x for k, x in r['marks'].items() if k.startswith('1 parity'))
    v1 = m1['value']
    assert abs(v1['mean'] - sum(v1['per_seed'].values()) / 6) < 1e-9
    assert m1['ok'] == (v1['mean'] >= -1 and v1['ci'][0] >= -2 and sum(x >= -1 for x in v1['per_seed'].values()) >= 5)
    two_low = {s: (-int(1.5 * n5 / 100 / 5) - 1 if s in (200, 201) else 0) for s in A.CONFIRM}            # two seeds 1.5 below: 1c fails
    assert not next(x for k, x in A.confirm(with_t1(d_correct=two_low))['marks'].items() if k.startswith('1 parity'))['ok']
    big = -int(2.5 * n5 / 100 / 5) - 1
    assert A.confirm(with_t1(d_correct=big))['verdict'] == 'PROVED WRONG'
    assert A.confirm(with_t1(tool_off=5.0))['verdict'].startswith('NOT SHOWN')
    assert A.confirm(with_t1(swap={s: (98.0 if s == 203 else 100.0) for s in A.CONFIRM}))['verdict'].startswith('NOT SHOWN')
    assert A.confirm(with_t1(loops0={s: (5.5 if s == 201 else 0.0) for s in A.CONFIRM}))['verdict'].startswith('NOT SHOWN')
    print('ok judge')


def test_queue40():
    """Queue 40 = T1 on seeds 200 and 201 with q33's B2 flags, only the model switched (B2: ledger copy=True; T1: tool)."""
    from custom_io.local_runner import parse_queue
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    q33 = {r[0]: r[2] for r in parse_queue(os.path.join(here, 'queue_local', '33-pc-confirm-b2.txt'))}
    q40 = parse_queue(os.path.join(here, 'queue_local', '40-pc-t1-screen.txt'))
    assert [r[0] for r in q40] == ['T1_s200', 'T1_s201']
    for name, _, args, mem in q40:
        assert args[-1] == '--save-preds'                                       # per-row dev predictions (no-hardcoding plan, section 2)
        args = args[:-1]
        b2 = q33[name.replace('T1', 'B2')]
        swap = lambda xs, model, cfg: [model if x in ('ledger', 'tool') else cfg if x.startswith('{') else x for x in xs]
        assert swap(args, 'M', 'C') == swap(b2, 'M', 'C'), (args, b2)
        assert args[args.index('--model') + 1] == 'tool' and json.loads(args[args.index('--cfg') + 1]) == {}
    print('ok queue40')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
