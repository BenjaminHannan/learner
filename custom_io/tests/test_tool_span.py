"""python3 -m custom_io.tests.test_tool_span   (CPU; the real-data checks need the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
T1S = T1 + span copy (models/tool.py cfg {"span_copy": true}; Amendment 3, PASS-MARKS.md addendum 22): size and shared init, the copy's own
stepping and bounds, the training labels, no look-ahead, every lesion and eval runs, and the mechanism: a small T1S trained on 1-3 digit numbers
copies 1-9 digit calculator results into the next call (and into the answer up to 6 digits; plain T1 copies nothing at 5+)."""
import json, os, random, time
import torch
from custom_io.data import Dataset, collate
from custom_io.evalx import donor_eval, evaluate
from custom_io.models.tool import LE, N_RES, Tool, rand_digits
from custom_io.tests.test_ledger import S_CFG, SMALL, batch_of, train_rows, vocab
from custom_io.tests.test_tool import MECH_CFG, T1_PARAMS, prog_rows, tool_rows
from custom_io.train import lesion_names

T1S_PARAMS = 3311060
NEW = ('q_s', 'k_s', 'g_s', 'stop_s')


def seeded(cfg, seed=0, v=None, span=True):
    torch.manual_seed(seed)
    return Tool(v or vocab(), span_copy=span, **cfg)


def test_size_and_init():
    v = vocab()
    m, t1 = seeded(S_CFG, v=v), seeded(S_CFG, v=v, span=False)
    assert m.n_params() == T1S_PARAMS and t1.n_params() == T1_PARAMS and abs(T1S_PARAMS / 3.24e6 - 1) <= 0.03, m.n_params()
    s1, s2 = m.state_dict(), t1.state_dict()
    assert {k.split('.')[0] for k in s1 if k not in s2} == set(NEW) and all(k in s1 for k in s2)
    assert all(torch.equal(s1[k], s2[k]) for k in s2), 'a weight shared with T1 starts differently'
    print('ok size_and_init', m.n_params())


def text_ctx(v, prompt, entries, T=None, le=LE):
    """ids [1, N] and mask for a prompt (padded to T) then len(entries) <= 7 entries of le chars (the free-run layout)."""
    T = T or len(prompt)
    ids = torch.zeros(1, T + N_RES * le, dtype=torch.long)
    for off, s in [(0, prompt)] + [(T + k * le, e) for k, e in enumerate(entries)]:
        ids[0, off:off + len(s)] = torch.tensor(v.encode(s))
    return ids, ids != 0, T


def test_span_read():
    """The copy steps left from the picked char, ends where the stop head says, at a string's edge or at padding, and reads in text order."""
    v = vocab()
    m = seeded(SMALL, v=v)
    m.stop_logit = lambda c, tape: torch.tensor([0.0 if (v.itos[int(x)] in '0123456789' or (v.itos[int(x)] == '-' and bool(t))) else 1.0 for x, t in
                                                 zip(c, tape)]) - 0.5
    prompt = 'It had -45 cats and 1203 dogs'
    ents = ['add 12 5 = 17', 'sub 3 8 = -5', 'mul 123456789 2 = 246913578']
    ids, mask, T = text_ctx(v, prompt, ents)
    want = {prompt.index('45') + 1: '45', prompt.index('1203') + 3: '1203', prompt.index('cats') + 3: 'cats'[-1],
            T + ents[0].index('17') + 1: '17', T + LE + len(ents[1]) - 1: '-5', T + 2 * LE + len(ents[2]) - 1: '246913578',
            T + 2 * LE + ents[2].index('123456789') + 8: '123456789'}
    for p, w in want.items():
        lg = torch.full((1, ids.shape[1]), -1e9)
        lg[0, p] = 0.0
        got = m.span_read(lg, ids, mask, T, LE)[0]
        assert got == w, (p, got, w)
    # a number at the very start of an entry stops at the entry's edge, not in the previous entry's padding or the prompt
    ids2, mask2, T2 = text_ctx(v, 'x 7', ['99 = 3'])
    lg = torch.full((1, ids2.shape[1]), -1e9)
    lg[0, T2 + 1] = 0.0
    assert m.span_read(lg, ids2, mask2, T2, LE)[0] == '99'
    print('ok span_read')


def test_labels():
    """Every marked position is the units digit of a number token spelling the gold string, visible at that call; NUM rows whose answer is
    in the context get mode 0 and keep their GEN targets; the stop samples say go on for digits and stop before the token."""
    v = vocab()
    m = seeded(SMALL, 1, v)
    rows = prog_rows(64, 2, 7) + train_rows(64, 8)
    b = batch_of(rows, v)
    g = m.gold(rows, 'cpu')
    with torch.no_grad():
        o = m.run(b, gold=g)
    T, le, K = b['prompt_ids'].shape[1], o['le'], o['K']
    Ma, Mb, Mn, (cs, ts, ys) = m.span_gold(rows, T, le, K)
    ids = torch.cat([b['prompt_ids'], o['tape'][1]], 1)[:, :T + K * le]
    seg = m.seg_of(T, le, ids.shape[1], 'cpu')
    num = lambda c: c.isdigit() or c == '-'
    n = 0
    for i, r in enumerate(rows):
        ops, opd, tape, md, _ = m.row_gold(r)
        checks = [(Ma[i, k], sa, k) for k, (sa, sb) in enumerate(opd)] + [(Mb[i, k], sb, k) for k, (sa, sb) in enumerate(opd)]
        if md == 0:
            checks.append((Mn[i], r['answer'], len(ops)))
            assert Mn[i].any() and (g['gen'][i] >= 0).any(), r['id']
        for M, want, k in checks:
            for p in M.nonzero()[0]:
                lo, s, q = int(seg[p]), '', int(p)
                while q >= lo and num(v.itos[int(ids[i, q])]) and not (q < T and v.itos[int(ids[i, q])] == '-'):
                    s, q = v.itos[int(ids[i, q])] + s, q - 1
                assert s == want, (r['id'], s, want)
                assert p < T or (p - T) // le < k, ('look-ahead', r['id'], int(p), k)
                n += 1
    assert n > 200 and 0 in set(g['mode'].tolist()) and {1, 2} <= set(g['mode'].tolist()), n
    by = {}
    for c, t, y in zip(cs, ts, ys):
        by.setdefault((v.itos[c], t), set()).add(y)
    assert all(by[(d, t)] == {0.0} for d, t in by if d.isdigit()) and by.get(('-', True), {0.0}) == {0.0} and by.get(('-', False), {1.0}) == {1.0}
    assert by[(' ', False)] == {1.0} and by[(' ', True)] == {1.0}
    print(f'ok labels ({n} occurrences, {len(cs)} stop samples)')


def test_no_lookahead():
    v = vocab()
    m = seeded(SMALL, 2, v).eval()
    rows = prog_rows(16, 3)
    b = batch_of(rows, v)
    with torch.no_grad():
        g = m.gold(rows, 'cpu')
        o1 = m.run(b, gold=g)
        bump = lambda e: e.split(' = ')[0] + ' = ' + ''.join(str((int(c) + 1) % 10) if c.isdigit() else c for c in e.split(' = ')[1])
        o2 = m.run(b, gold=dict(g, tape=[[e if k != 1 else bump(e) for k, e in enumerate(tp)] for tp in g['tape']]))
    for s in (0, 1):
        for k in ('la', 'lb', 'ga', 'gb'):
            assert torch.equal(o1['steps'][s][2][k], o2['steps'][s][2][k]), (s, k)
    assert not torch.equal(o1['steps'][2][2]['la'], o2['steps'][2][2]['la'])
    print('ok no_lookahead')


def test_runs_and_lesions():
    v = vocab()
    m = seeded(SMALL, 3, v)
    rows = train_rows(48, 5)
    loss, aux = m.loss(batch_of(rows, v))
    assert torch.isfinite(loss) and {'span_call', 'span_ans', 'stop', 'span_share'} <= set(aux), aux
    loss.backward()
    assert all(p.grad is not None for p in m.parameters()), [k for k, p in m.named_parameters() if p.grad is None]
    m.eval()
    b = batch_of(rows, v)
    for les in [None] + lesion_names(m) + ['ctl27']:
        out = m.generate(b, les)
        assert len(out) == len(rows) and all(isinstance(x, str) for x in out), les
    from custom_io.data import DEFAULT_DATA, load_rows
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    res = donor_eval(m, random.Random(0).sample(dev, 64), 32)
    assert res['n'] > 0
    print('ok runs_and_lesions')


def test_extra_evals():
    import contextlib, tempfile
    from custom_io.data import DEFAULT_DATA, load_rows
    v = vocab()
    m = seeded(SMALL, 4, v).eval()
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    with open(tmp + '/dev/in_dist.jsonl', 'w') as f:
        for r in random.Random(1).sample(dev, 200):
            f.write(json.dumps(r) + '\n')
    ex = m.extra_evals(dict(data=tmp, big=None, device=torch.device('cpu'), batch_size=64, amp=contextlib.nullcontext))
    json.dumps(ex)
    assert {'write_copy', 'op_acc', 'noexec', 'opswap', 'span_use'} <= set(ex) and set(ex['span_use']) == {'operand', 'answer', 'n_sides', 'n_rows'}
    print('ok extra_evals', ex['span_use'])


# ---- the mechanism: trained on 1-3 digit numbers, copying 1-9 digit results ------------------------------------------------------
MECH_STEPS = 1500


def mech_copy(m, rows):
    """write_copy in miniature: every calculator result becomes a random 1-9 digit string; -> {length: dict(op=[n, ok], ans=[n, ok])}."""
    by, ds = {}, Dataset(rows, m.vocab, strict=False)
    with torch.no_grad():
        for s in range(0, len(rows), 100):
            rs = rows[s:s + 100]
            b = collate([ds[i] for i in range(s, s + len(rs))])
            o = m.run(b, oracle=lambda i, t, c, _rs=rs: rand_digits(random.Random(f"{_rs[i]['id']}|{t}"), 1, 9))
            ans = m.talk(m.state_of(o), b)
            for i, r in enumerate(rs):
                calls = o['calls'][i]
                if not calls:
                    continue
                if r['family'] == 'syn_chain' and len(calls) >= 2:
                    d = by.setdefault(len(calls[0][4]), dict(op=[0, 0], ans=[0, 0]))
                    d['op'][0] += 1; d['op'][1] += calls[1][2] == calls[0][4]
                d = by.setdefault(len(calls[-1][4]), dict(op=[0, 0], ans=[0, 0]))
                d['ans'][0] += 1; d['ans'][1] += ans[i] == calls[-1][4]
    return by


def test_mechanism_span():
    v = vocab()
    torch.manual_seed(0)
    m = Tool(v, span_copy=True, **MECH_CFG)
    rows = tool_rows(20000, 'tr', 0, 1, 3)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=0.0)
    ds, rng, t0 = Dataset(rows, v), random.Random(0), time.time()
    for step in range(MECH_STEPS):
        loss, aux = m.loss(collate([ds[i] for i in rng.sample(range(len(rows)), 64)]))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
    m.eval()
    seen = {r['prompt'] for r in rows}
    test = [r for r in tool_rows(600, 'te', 1, 1, 3) if r['prompt'] not in seen]
    res, off = evaluate(m, test, 100), evaluate(m, test, 100, lesion='noexec')
    by = mech_copy(m, test)
    pc = lambda x: 100 * x[1] / max(x[0], 1)
    table = {L: (round(pc(d['op']), 1), round(pc(d['ans']), 1)) for L, d in sorted(by.items())}
    print(f"  {time.time() - t0:.0f}s: held-out exact {res['exact']:.1f}, tool off {off['exact']:.1f}, copy by length (operand, answer) {table}")
    assert res['exact'] >= 90 and off['exact'] <= 5, (res['exact'], off['exact'])
    assert set(by) == set(range(1, 10)) and all(pc(d['op']) >= 95 for d in by.values()), table
    # answers: shown length-general to 6 digits here; at 7-9 this small model's answer pointer sometimes picks the FIRST result when both
    # results are long (73-89% at 1500 steps; named as a risk for the real re-screen, judged there by R1), so only 1-6 are asserted
    assert all(pc(by[L]['ans']) >= 95 for L in range(1, 7)), table
    print('ok mechanism_span')


def test_queue50():
    """Queue 50 = queue 40's T1 lines with only the name and the cfg changed; the box jobs run the same lines."""
    from custom_io.local_runner import parse_queue
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    q40 = {r[0]: r[2] for r in parse_queue(os.path.join(here, 'queue_local', '40-pc-t1-screen.txt'))}
    q50 = parse_queue(os.path.join(here, 'queue_local', '50-pc-t1s-screen.txt'))
    assert [r[0] for r in q50] == ['T1S_s200', 'T1S_s201']
    for name, _, args, mem in q50:
        t1 = q40[name.replace('T1S', 'T1')]
        i = args.index('--cfg')
        assert json.loads(args[i + 1]) == {'span_copy': True} and args[:i + 1] + args[i + 2:] == t1[:i + 1] + t1[i + 2:], (args, t1)
        box = open(os.path.join(here, 'queue', 't1a' if name.endswith('200') else 't1b', f"50-t1s-s{name[-3:]}.sh")).read()
        assert f"run {name} " + ' '.join(a if not a.startswith('{') else f"'{a}'" for a in args) in box, name
    print('ok queue50')


if __name__ == '__main__':
    import sys
    want = sys.argv[1:]
    for name, fn in list(globals().items()):
        if name.startswith('test_') and (not want or name in want):
            fn()
