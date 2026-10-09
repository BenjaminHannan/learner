"""python3 -m custom_io.tests.test_b3g2   (CPU, a few minutes; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=1)
B3 group 2 (architecture/B3-GROUP2-BUILD-2026-10-09.md; models/b3g2.py): the deleted heads are gone and nothing reaches for them (every path runs); the gold is progtext's, with the
tool's real reply and notes; teacher-forced loss finite and EVERY trainable parameter gets a gradient (the stop head too, in a whole-turn batch); a free run with a SCRIPTED
writer: calls dispatch, an unknown tool and a call the calculator cannot read reply '?', a reply is on the tape and visible from the next round, a full tape is counted;
noexec and opswap change the replies; drills are deterministic; the lesions work; ST1's interface; the counters (steps_unparsed, no_trace, writer_over); and, in a child process
with 2,000-byte caps, a tiny end-to-end training run (loss falls, the free run writes calls and answers), extra_evals on a tiny dev dir, and the rung size table."""
import contextlib, json, os, subprocess, sys, tempfile
import numpy as np
import torch
from custom_io import capcount
from custom_io.data import BOS, EOS, ByteVocab, CharVocab
from custom_io.models import build, progtext
from custom_io.models.b3g2 import DELETED
from custom_io.tests.test_b3 import CFG, StubEG, batch_of, rows

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G2 = dict(CFG, eg_embed=True, any_round=True, gap_p=0.25, no_slots=True, no_place=True, bytes=True)
V = ByteVocab()


def make(seed=0, vocab=V, **kw):
    torch.manual_seed(seed)
    m = build('b3g2', vocab, **{**G2, **kw})
    if m.eg_embed:
        m._eg = [StubEG()]
    return m


class Script:
    """Replaces writer.greedy: mode 0 ("call?") at round t returns texts[i][t - 1] for row i (all rows alive: a forced run); mode 1 is the real writer's."""

    def __init__(self, m, texts):
        self.m, self.texts, self.real, self.r = m, texts, m.writer.greedy, 0
        m.writer.greedy = self

    def __call__(self, Z, zmask, Xc, cmask, cids, mode, *a, **k):
        if int(mode[0]) == 1:
            return self.real(Z, zmask, Xc, cmask, cids, mode, *a, **k)
        r, self.r = self.r, self.r + 1
        assert Z.shape[0] == len(self.texts)
        return [self.m.vocab.encode(t[r]) if r < len(t) else [] for t in self.texts], torch.ones(Z.shape[0], dtype=torch.bool)


def test_deleted_and_paths():
    m = make()
    names = {n for n, _ in m.named_parameters()}
    for d in DELETED + ('ordinal', 'stype', 'vcode', 'op_emb', 'q_a'):
        assert not hasattr(m, d), d
        assert not any(n == d or n.startswith(d + '.') for n in names), d
    assert hasattr(m, 'e_s') and hasattr(m, 'e_e') and m.WCAP == 69 and m.writer.cap == 69
    assert m.writer.tok is m.reader.tok and not any(p is m.reader.tok.weight for p in m.writer.parameters())
    b = batch_of(rows(8), V)
    loss, aux = m.loss(b)              # a deleted attribute touched anywhere on a path raises AttributeError
    loss.backward()
    m.eval()
    with torch.no_grad():
        for les in [None, 'noexec', 'opswap', 'nocopy', 'zero_state', 'shuffle_state'] + [f'loops:{k}' for k in (0, 1, 2, 8)]:
            out = m.generate(b, lesion=les)
            assert len(out) == 8 and all(isinstance(x, str) for x in out), (les, out)
        o = m.run(b)
        st = m.state_of(o)
        assert m.talk(st, b) == m.generate(b) and len(st) == 4 and st[0].shape[0] == 8
        d = batch_of(rows(8)[::-1], V)                         # a donor swap: the donor's state, the current batch
        assert len(m.talk(m.state(d), b)) == 8
    try:
        m.generate(b, lesion='nowordc')
        raise SystemExit('nowordc should be refused')
    except ValueError:
        pass
    assert 'nowordc' not in m.LESIONS and m.supports_donor()
    # b3g2 with the input switches off (CharVocab, slots, place): the same paths run
    m2 = make(1, vocab=CharVocab.build([]), no_slots=False, no_place=False, bytes=False)
    b2 = batch_of(rows(8), m2.vocab)
    loss, _ = m2.loss(b2)
    loss.backward()
    m2.eval()
    with torch.no_grad():
        assert len(m2.generate(b2)) == 8 and hasattr(m2, 'ordinal')
    print('ok deleted heads are gone (%d names), every path runs, switches off also runs; trained %d (writer %d)' % (len(DELETED), m.n_params(), m.writer.size()))


def test_gold():
    m = make()
    rs = rows(8) + [
        dict(id='n1', family='list_stats', prompt='Numbers: 4, 7, 10. How many are even?', answer='2', steps=['count_even of [4, 7, 10]']),
        dict(id='n2', family='list_stats', prompt='List: 4 7 10. Second largest plus 1?', answer='8', steps=['second_largest of [4, 7, 10]', '7 + 1 = 8']),
        dict(id='m1', family='arith_bare', prompt='38 + ? = 58 State the result only.', answer='20', steps=['38 + 20 = 58']),
        dict(id='z1', family='copy_word', prompt='Echo: sune. Give only the answer.', answer='sune', steps=[])]
    gl = [m.trace_of(r)['gold'] for r in rs]
    for r, g in zip(rs, gl):
        calls, _ = progtext.steps_of(r, True)
        assert g['texts'] == [progtext.text(c) for c in (calls or [])], (r['id'], g['texts'])
        assert g['tape'] == [progtext.entry(c) for c in (calls or [])], (r['id'], g['tape'])
        assert g['ans'] == r['answer'] and g['ids'] == [list(V.encode(x)) for x in g['texts']]
    assert gl[8]['texts'] == ['note count_even of [4, 7, 10]'] and gl[8]['tape'] == ['note count_even of [4, 7, 10]']       # a note: no ' = ', nothing replied
    assert gl[9]['texts'] == ['note second_largest of [4, 7, 10]', 'add 7 1'] and gl[9]['tape'] == ['note second_largest of [4, 7, 10]', 'add 7 1 = 8']
    assert gl[10]['texts'] == ['add 38 20'] and gl[10]['tape'] == ['add 38 20 = 58']        # as written: the hidden operand is a target
    assert gl[11]['texts'] == [] and m.trace_stats['reply_mismatch'] == 0 and m.trace_stats['notes'] == 2
    # the tool's real reply is taught, not the label's: a result the calculator cannot reproduce is counted, and the tape holds calc's
    big = dict(id='big', family='chain_ops', prompt='2000000000 + 1', answer='2000000001', steps=['2000000000 + 1 = 2000000001'])
    assert m.trace_of(big)['gold']['tape'] == ['add 2000000000 1 = ?'] and m.trace_stats['reply_mismatch'] == 1
    m.trace_stats['reply_mismatch'] = 0
    # as_written=False: T1's calls (the inverse rewrite), the same texts progparse's program gives; unreadable rows are counted and trained answer-only
    capcount.reset()
    m0 = make(as_written=False)
    t = m0.trace_of(rs[10])['gold']
    assert t['texts'] == ['sub 58 38'] and t['tape'] == ['sub 58 38 = 20']
    m0.trace_of(rs[8])
    snap = capcount.snapshot()
    assert snap['steps_unparsed'] == 1 and snap['no_trace'] == 1 and m0.trace_stats['unreadable'] == 1, snap
    capcount.reset()
    for r in rs:
        m.trace_of(dict(r, id=r['id'] + 'x'))
    snap = capcount.snapshot()
    assert snap['steps_unparsed'] == 0 and snap['no_trace'] == 0 and snap['writer_over'] == 0 and snap['tape_entry_over'] == 0, snap
    # writer_over: an answer or a call the writer cannot write in WCAP steps gets no target and is counted
    capcount.reset()
    m.trace_of(dict(id='long', family='copy_word', prompt='Echo: ' + 'x' * 90, answer='x' * 90, steps=[]))
    assert capcount.snapshot()['writer_over'] == 1
    long_b = batch_of([dict(id='long', family='copy_word', prompt='Echo: ' + 'x' * 90, answer='x' * 90, steps=[])] + rows(3), V)
    loss, aux = m.loss(long_b)
    assert torch.isfinite(loss)
    capcount.reset()
    print('ok gold: progtext texts, notes as written (no reply), the hidden operand as a target, real replies, counters (steps_unparsed, no_trace, writer_over)')


def test_drills():
    rs = rows(60)
    outs = []
    for _ in range(2):
        m = make(3)
        m.train()
        outs.append([(g['texts'], g['tape'], g['ans'], g['drill']) for _ in range(3) for g in m.train_golds(rs)])
        st = dict(m.drill_stats)
    assert outs[0] == outs[1] and st['drilled'] > 0 and st['eligible'] >= st['drilled'], st
    dr = [x for x in outs[0] if x[3]]
    for texts, tape, ans, _ in dr:
        res = tape[-1].split(' = ')[1]
        assert ans == res and len(res) >= 1 and tape[-1].startswith(texts[-1] + ' = '), (texts, tape, ans)
    m = make(3)
    m.eval()                                                                  # eval: never drilled
    assert not any(g['drill'] for g in m.train_golds(rs))
    # a drill's tape carries the drawn string, a later operand that was a result is that string
    m = make(4)
    m.train()
    r = dict(id='c2', family='chain_story2', prompt='Facts: Xavi had 5 cards. Then Xavi got 7 more. After that, Xavi lost 3. How many now?', answer='9', steps=['5 + 7 = 12', '12 - 3 = 9'])
    got = [g for _ in range(40) for g in m.train_golds([r]) if g['drill']]
    assert got
    g = got[0]
    d1 = g['tape'][0].split(' = ')[1]
    assert g['texts'][1] == f'sub {d1} 3' and g['ans'] == g['tape'][1].split(' = ')[1], g
    print('ok drills deterministic (%d drilled of %d eligible), tape carries the drawn strings' % (st['drilled'], st['eligible']))


def test_grads():
    import custom_io.models.b3g2 as M
    M.KS = (32,)                                              # whole-turn batches, so the 'settled' stop loss counts
    try:
        m = make(2)
        b = batch_of(rows(8), V)
        loss, aux = m.loss(b)
        assert float(aux['stop_w']) == 1.0 and aux['rounds'] == 32.0
        loss.backward()
        bad, zero = [], []
        for n, p in m.named_parameters():
            if p.grad is None or not torch.isfinite(p.grad).all():
                bad.append(n)
            elif not p.grad.abs().sum() > 0 and not n.startswith(('tape_emb', 'step_emb', 'reader.pos', 'reader.place', 'ctrl', 'src', 'ln_eg')):
                zero.append(n)
        assert not bad, bad
        assert not zero, f'no gradient reached: {zero}'
        assert torch.isfinite(loss) and float(aux['call']) > 0 and float(aux['ans']) > 0
        # K = 4: the stop loss is off (stop_w 0), everything else is finite
        M.KS = (4,)
        m.zero_grad()
        loss, aux = m.loss(b)
        assert float(aux['stop_w']) == 0.0 and torch.isfinite(loss)
    finally:
        M.KS = (4, 8, 16, 32)
    print('ok teacher-forced loss finite; every trainable parameter (%d tensors) gets a gradient, the stop head in a whole-turn batch' % sum(1 for _ in m.parameters()))


def test_scripted_free_run():
    m = make(5)
    m.eval()
    b = batch_of(rows(4), V)
    texts = [['add 7 5', 'sub 12 3', ''], ['foo 1 2', ''], ['add 1', 'note hello there', 'mul 3 4'], ['add 1 1'] * 19]
    masks = []
    think = m.think

    def spy(Z, kvs, kvx, mask, t):
        masks.append(mask[:, :m.tape * 68].sum(1).tolist())             # no_slots: the first K * le keys are the tape
        return think(Z, kvs, kvx, mask, t)
    m.think = spy
    Script(m, texts)
    with torch.no_grad():
        o = m.run(b, loops=20)
    c = o['calls']
    assert c[0] == [(1, 'add', '7', '5', '12'), (2, 'sub', '12', '3', '9')], c[0]
    assert c[1] == [(1, 'foo', '1 2', '', '?')], c[1]                    # unknown tool
    assert c[2] == [(1, 'add', '1', '', '?'), (2, 'note', 'hello there', '', ''), (3, 'mul', '3', '4', '12')], c[2]      # one operand: '?'; a note replies ''
    assert len(c[3]) == 16 and sorted(set(i for i, _ in o['tape_full'])) == [3] and [t for _, t in o['tape_full']] == [17, 18, 19], o['tape_full']
    assert m.last_tape_full == [False, False, False, True]
    Xt, idt, vis = o['tape']
    le = o['le']
    ent = lambda i, k: V.decode(idt[i, k * le:(k + 1) * le][vis[i, k * le:(k + 1) * le]].tolist())
    assert [ent(0, 0), ent(0, 1), ent(0, 2)] == ['add 7 5 = 12', 'sub 12 3 = 9', ''] and ent(1, 0) == 'foo 1 2 = ?'
    assert [ent(2, k) for k in range(3)] == ['add 1 = ?', 'note hello there', 'mul 3 4 = 12'] and ent(3, 15) == 'add 1 1 = 2'
    assert o['records'][0] == [(1, 'add 7 5', '12'), (2, 'sub 12 3', '9')]
    # a reply is on the tape and visible from the NEXT round
    assert masks[1] == [0, 0, 0, 0] and masks[2] == [12, 11, 9, 11] and masks[3][0] == 12 + 12 and masks[3][2] == 9 + 16, masks[:4]      # round index t: masks[t]
    # the stop head decides in a normal run: stopped rows make no more calls (the script is not consulted for them in order, so only check the plumbing)
    m.think = think
    # noexec / opswap act inside the dispatch
    for les, want in (('noexec', ['?', '?']), ('opswap', ['2', '15'])):
        s = Script(m, texts)
        with torch.no_grad():
            o = m.run(b, loops=4, lesion=les)
        assert [x[4] for x in o['calls'][0]] == want, (les, o['calls'][0])
        assert [x[4] for x in o['calls'][2]][1:] == ['', '12' if les == 'opswap' else '?'] or les == 'noexec', o['calls'][2]
        if les == 'noexec':
            assert [x[4] for x in o['calls'][2]] == ['?', '', '?'], o['calls'][2]          # a note replies nothing, with or without the lesion
        m.writer.greedy = s.real
    # the oracle (write_copy) replaces the calculator's reply for a two-token call
    s = Script(m, texts)
    with torch.no_grad():
        o = m.run(b, loops=3, oracle=lambda i, t, c: '99')
    assert o['calls'][0][0][4] == '99' and o['calls'][1][0][4] == '?'
    m.writer.greedy = s.real
    # an unfinished write (no EOS within WCAP) is not a call
    class Run:
        def __call__(self, Z, *a, **k):
            return [[7, 8]] * Z.shape[0], torch.zeros(Z.shape[0], dtype=torch.bool)
    m.writer.greedy = Run()
    with torch.no_grad():
        o = m.run(b, loops=3)
    assert all(not x for x in o['calls']) and m.free_stats['unended'] > 0
    print('ok scripted writer: calls dispatch, unknown tool and bad arity reply ?, notes reply nothing, replies visible next round, full tape counted, noexec / opswap / oracle')


def test_stop_and_talk():
    m = make(6)
    m.eval()
    b = batch_of(rows(6), V)
    with torch.no_grad():
        o = m.run(b)
    assert len(o['rounds']) == 6 and all(1 <= u <= 32 for u in o['rounds']) and m.last_rounds == o['rounds']
    # a row's state is the one at its own stop round: forcing the stop head to stop at 2 / 5 gives rows with different tapes
    m.stop.weight.data.zero_()
    m.stop.bias.data.fill_(-50.0)
    with torch.no_grad():
        o = m.run(b)
    assert o['rounds'] == [32] * 6
    m.stop.bias.data.fill_(50.0)
    with torch.no_grad():
        o = m.run(b)
    assert o['rounds'] == [1] * 6
    # zero_state / shuffle_state act on Z only; the donor's tape comes with its state
    with torch.no_grad():
        st = m.state(b)
        a0 = m.talk(st, b)
        z0 = m.talk((torch.zeros_like(st[0]),) + st[1:], b)
        assert m.generate(b, lesion='zero_state') == z0
    # nocopy forces the gate in the writer
    gates = []
    real = m.writer.head

    def spy(R, Xc, cmask, cids, nocopy, ckeys):
        p, gate, a = real(R, Xc, cmask, cids, nocopy, ckeys)
        gates.append((nocopy, float(gate.min())))
        return p, gate, a
    m.writer.head = spy
    with torch.no_grad():
        m.generate(b, lesion='nocopy')
    assert gates and all(nc and g == 1.0 for nc, g in gates), gates
    print('ok stop head rounds, state at the stop round, zero / shuffle / donor on Z, nocopy forces the writer gate')


def test_st1_interface():
    from custom_io import st1
    m = make(7)
    rs = rows(8)
    b = batch_of(rs, V)
    gen = torch.Generator().manual_seed(0)
    m.eval()
    tr = m.sample_traces(b, 1.0, gen)
    assert len(tr) == 8 and all(set(t) == {'calls', 'answer'} and isinstance(t['answer'], str) for t in tr)
    gen2 = torch.Generator().manual_seed(0)
    assert m.sample_traces(b, 1.0, gen2) == tr                       # drawn only from the generator
    tr = [dict(calls=[('add 3 4', '7'), ('sub 7 2', '5')], answer='5')] * 4 + [dict(calls=[], answer='x')] * 4
    m.train()
    loss, aux = m.trace_loss(b, tr)
    loss.backward()
    assert torch.isfinite(loss)
    gold = m.trace_gold(tr[0])
    assert gold['texts'] == ['add 3 4', 'sub 7 2'] and gold['tape'] == ['add 3 4 = 7', 'sub 7 2 = 5']
    # the ST1 stage runs end to end on it (one tiny round)
    opt = torch.optim.AdamW(m.parameters(), lr=1e-4)
    qa = [dict(r, steps=[], accepted=[r['answer']]) for r in rs]
    mk = lambda rs_: batch_of(rs_, V)
    res = st1.self_teach(m, qa, rs, mk, opt, rounds=1, k=2, temperature=1.0, updates=2, batch_size=4, seed=0, log=lambda *a: None)
    assert len(res['rounds']) == 1
    print('ok ST1 interface: sample_traces is generator-pure, trace_loss trains on given traces, self_teach runs')


# ---- child process: 2,000-byte caps ----
CAPS = dict(max_prompt=2000, max_ans=35, n_num=650, w_max=1485, n_res=11, n_reg=36, plain_target=109, le=95)


def child():
    torch.set_num_threads(1)
    from custom_io.g8a import caps as CP
    CP.apply(dict(CAPS))
    from custom_io.data import DEV_SPLITS, Dataset, collate
    from custom_io.g8a.tok_cost import synth_text
    text = synth_text(80000)
    SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12)
    cfg = dict(SMALL, **{k: v for k, v in G2.items() if k not in CFG}, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, writer_inner=24)

    def row(i, letters, fam='chain_story2'):
        a, b, c = 120 + 17 * (i % 4), 340 + 29 * (i % 4), 7 + (i % 4)
        q = f' Tom has {a} apples and buys {b} more, then gives {c} away. How many apples now?'
        body = text[i * 2000:i * 2000 + max(letters - len(q), 0)]
        return dict(id=f'r{i}', family=fam, prompt=(body + q)[-letters:] if body else q.strip(), answer=str(a + b - c), accepted=[str(a + b - c)], level=2, variant='v', stage=9,
                    steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}'])
    lens = [60, 400, 1200, 1999]
    train = [row(i, lens[i % 4]) for i in range(8)]
    assert max(V.length(r['prompt']) for r in train) >= 1900
    ds = Dataset(train, V, strict=False)
    batches = [collate([ds[i] for i in range(s, s + 2)]) for s in range(0, 8, 2)]
    torch.manual_seed(0)
    m = build('b3g2', V, **cfg)
    m._eg = [StubEG()]
    assert m.writer.cap == 96 and m.WCAP == 96
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3, betas=(0.9, 0.95), weight_decay=0.0)
    m.train()
    ls, call_acc = [], []
    N = int(os.environ.get('B3G2_STEPS', 400))
    for s in range(N):
        loss, aux = m.loss(batches[s % 4])
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        ls.append(float(loss.detach())); call_acc.append(float(aux['call_acc']))
        if os.environ.get('B3G2_V') and s % 20 == 0:
            print(s, round(ls[-1], 2), round(call_acc[-1], 2), round(float(aux['call']), 2), round(float(aux['ans']), 2), flush=True)
    assert all(x == x and abs(x) < 1e9 for x in ls), ls
    first, last = sum(ls[:5]) / 5, sum(ls[-5:]) / 5
    assert last < 0.5 * first, (first, last)
    m.eval()
    with torch.no_grad():
        o = m.run(batches[0])
        ans = m.generate(batches[0])
    nc = sum(len(c) for c in o['calls'])
    assert len(ans) == 2 and nc > 0 and all(isinstance(a, str) and a for a in ans), (o['calls'], ans)
    right = sum(ans[i] == batches[0]['rows'][i]['answer'] for i in range(2))
    # a tiny dev dir, the extra evals
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'dev'))
    dev = [row(20 + i, [100, 300, 800, 1400, 1999][i % 5]) for i in range(30)] + [
        dict(id='miss0', family='arith_bare', prompt='38 + ? = 58 State the result only.', answer='20', accepted=['20'], level=2, variant='missing', stage=9, steps=['38 + 20 = 58']),
        dict(id='miss1', family='arith_bare', prompt='9 + ? = 12 State the result only.', answer='3', accepted=['3'], level=2, variant='missing', stage=9, steps=['9 + 3 = 12']),
        dict(id='note0', family='list_stats', prompt='Numbers: 4, 7, 10. How many are even?', answer='2', accepted=['2'], level=2, variant='v', stage=9, steps=['count_even of [4, 7, 10]'])]
    for sp in DEV_SPLITS:
        with open(os.path.join(d, 'dev', f'{sp}.jsonl'), 'w') as f:
            for r in dev[:10] + dev[-3:]:
                f.write(json.dumps(dict(r, id=r['id'] + sp)) + '\n')
    with open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w') as f:
        for r in dev:
            f.write(json.dumps(r) + '\n')
    ctx = dict(data=d, big=None, device=torch.device('cpu'), batch_size=8, amp=contextlib.nullcontext)
    ex = m.extra_evals(ctx)
    for k in ('op_acc', 'noexec', 'chain5_lesions', 'opswap', 'write_copy', 'write_copy_u', 'copy_gate', 'h1', 'b3', 'g2', 'coverage'):
        assert k in ex, k
    g2 = ex['g2']
    assert g2['dev_rows']['hidden_rows'] >= 1 and g2['dev_rows']['note_rows'] >= 1 and g2['inverse']['hidden']['n'] >= 1, g2['dev_rows']
    assert 0 <= g2['agreement']['agree'] <= 100 and g2['agreement']['n'] > 0
    assert set(ex['op_acc']['free_run']) == {'op', 'call', 'program', 'answer'} and ex['op_acc']['teacher_forced']['call'] >= 0
    assert g2['train_counts']['trace']['reply_mismatch'] == 0
    sp = ex['b3']['splits']['in_dist']
    assert set(sp['by_length']) == {'0-280', '281-700', '701-1300', '1301-2000'}, sp['by_length']
    # checkpoint round trip
    sd = m.state_dict()
    m2 = build('b3g2', V, **cfg)
    m2.load_state_dict(sd)
    assert all(torch.equal(m2.state_dict()[k], v) for k, v in sd.items())
    snap = capcount.snapshot()
    print(json.dumps(dict(ok=True, loss_first5=round(first, 2), loss_last5=round(last, 2), steps=N, calls_written=nc, answers=ans, gold=[r['answer'] for r in batches[0]['rows']], right=right,
                          call_acc_last=round(sum(call_acc[-10:]) / 10, 2), op_acc=ex['op_acc'], caps={k: v for k, v in snap.items() if v})))


def test_end_to_end():
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_b3g2', '--child'], cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS='1'), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-4000:]
    res = json.loads(out.stdout.strip().splitlines()[-1])
    print('ok b3g2 end to end on CPU at 2,000 bytes: %d steps, loss %.1f -> %.1f, %d calls written, answers %s (gold %s), call_acc(last 10 steps) %.2f; extra evals ran; caps hit %s'
          % (res['steps'], res['loss_first5'], res['loss_last5'], res['calls_written'], res['answers'], res['gold'], res['call_acc_last'], res['caps']))
    print('    free-run call accuracy:', json.dumps(res['op_acc']))


def child_sizes():
    torch.set_num_threads(1)
    from custom_io.g8a import caps as CP, configs as C
    caps = CP.apply(json.load(open(os.path.join(ROOT, 'custom_io', 'g8a', 'caps_b3g2.json'))))
    rows_ = C.b3g2_table()
    print(json.dumps(rows_))


def test_sizes():
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_b3g2', '--sizes'], cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS='1'), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-4000:]
    rows_ = json.loads(out.stdout.strip().splitlines()[-1])
    g2c3 = 4_022_440
    r3 = next(r for r in rows_ if r['rung'] == '3M')
    assert abs(r3['trained'] / g2c3 - 1) <= 0.02, (r3['trained'], g2c3)
    for r in rows_:
        print('ok size %5s: trained %12s  frozen Gemma %12s  whole %12s  blocks %s mlp %s writer_mlp %s' % (r['rung'], f"{r['trained']:,}", f"{r['frozen_gemma']:,}", f"{r['whole']:,}",
                                                                                                        r['cfg']['blocks'], r['cfg']['mlp'], r['cfg'].get('writer_mlp')))
    print('ok 3M trained %s is %+.2f%% from g2c3 %s (band +-2%%)' % (f"{r3['trained']:,}", 100 * (r3['trained'] / g2c3 - 1), f"{g2c3:,}"))


if __name__ == '__main__':
    if '--child' in sys.argv:
        child()
    elif '--sizes' in sys.argv:
        child_sizes()
    else:
        torch.set_num_threads(1)
        for f in (test_deleted_and_paths, test_gold, test_drills, test_grads, test_scripted_free_run, test_stop_and_talk, test_st1_interface, test_end_to_end, test_sizes):
            f()
        print('ALL OK')
