"""python3 -m custom_io.tests.test_tool_span   (CPU; the real-data checks need the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
T1S = T1 + span copy (models/tool.py cfg {"span_copy": true}; Amendment 3, PASS-MARKS.md addendum 22): size and shared init, the copy's own
stepping and bounds, the training labels, no look-ahead, every lesion and eval runs, and the mechanism: a small T1S trained on 1-3 digit numbers
copies 1-9 digit calculator results into the next call (and into the answer up to 6 digits; plain T1 copies nothing at 5+)."""
import json, os, random, time
import torch
from custom_io.tests import legacy_widths
legacy_widths.apply()      # T1SDR's 11 operand cells / 40-char entries, before CELLS / LE are imported by value
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
    assert {'write_copy', 'write_copy_u', 'op_acc', 'noexec', 'opswap', 'span_use'} <= set(ex) and set(ex['span_use']) == {'operand', 'answer', 'n_sides', 'n_rows'}
    wu, wc = ex['write_copy_u'], ex['write_copy']
    assert {'operand', 'operand_ambiguous', 'answer', 'answer_ambiguous', 'passes', 'counts'} <= set(wu) and 1 <= wu['passes'] <= 8
    if wu['passes'] == 1:       # pass 0 is write_copy's own draw: its events split into unambiguous + ambiguous
        n = lambda d: sum(v[0] for v in d.values())
        assert n(wu['counts']['operand']) + n(wu['counts']['operand_ambiguous']) == wc['op_n']
    print('ok extra_evals', ex['span_use'], 'write_copy_u passes', wu['passes'])


def test_span_idx():
    """Amendment 5's next change (cfg span_idx): one zero table on the span keys; every T1S weight starts the same, so outputs match T1S."""
    v = vocab()
    torch.manual_seed(0)
    m = Tool(v, span_copy=True, span_idx=True, **S_CFG)
    t1s = seeded(S_CFG, v=v)
    assert m.n_params() == T1S_PARAMS + (1 + N_RES) * 64 == 3311572 and abs(m.n_params() / 3.24e6 - 1) <= 0.03, m.n_params()
    s1, s2 = m.state_dict(), t1s.state_dict()
    assert set(s1) - set(s2) == {'e_s.weight'} and all(torch.equal(s1[k], s2[k]) for k in s2)
    m, t1s = seeded(SMALL, 5, v), seeded(SMALL, 5, v)
    torch.manual_seed(5)
    mi = Tool(v, span_copy=True, span_idx=True, **SMALL)
    mi.load_state_dict(dict(m.state_dict(), **{'e_s.weight': mi.e_s.weight.detach().clone()}))
    rows = train_rows(32, 6)
    b = batch_of(rows, v)
    mi.eval(); m.eval()
    with torch.no_grad():
        assert mi.generate(b) == m.generate(b)
        l1, _ = mi.loss(b); l0, _ = m.loss(b)
        assert torch.allclose(l1, l0), (l1, l0)
    mi.train()
    loss, _ = mi.loss(b)
    loss.backward()
    assert mi.e_s.weight.grad is not None and mi.e_s.weight.grad.abs().sum() > 0
    with torch.no_grad():       # the index is the string a char sits in: 0 = prompt, 1 + k = entry k
        mi.e_s.weight.copy_(torch.arange(1 + N_RES, dtype=torch.float)[:, None].expand(-1, mi.e_s.weight.shape[1]))
        T, le = 5, 4
        Xc = torch.zeros(1, T + N_RES * le, mi.d)
        ks = mi.span_keys(Xc, T, le) - mi.k_s(Xc)
        want = [0] * T + [1 + k for k in range(N_RES) for _ in range(le)]
        assert ks[0, :, 0].tolist() == want, ks[0, :, 0].tolist()
    print('ok span_idx', 3311572)


def test_span_end():
    """Amendment 7's change (cfg span_end): one zero table e_e[distance from the end of the char's string] on the span keys, on top of T1SI."""
    v = vocab()
    torch.manual_seed(0)
    m = Tool(v, span_copy=True, span_idx=True, span_end=True, **S_CFG)
    torch.manual_seed(0)
    t1si = Tool(v, span_copy=True, span_idx=True, **S_CFG)
    assert m.n_params() == 3311572 + LE * 64 == 3314132 and abs(m.n_params() / 3311572 - 1) <= 0.03, m.n_params()
    s1, s2 = m.state_dict(), t1si.state_dict()
    assert set(s1) - set(s2) == {'e_e.weight'} and all(torch.equal(s1[k], s2[k]) for k in s2)
    torch.manual_seed(7)
    mi = Tool(v, span_copy=True, span_idx=True, **SMALL)
    me = Tool(v, span_copy=True, span_idx=True, span_end=True, **SMALL)
    me.load_state_dict(dict(mi.state_dict(), **{'e_e.weight': me.e_e.weight.detach().clone()}))
    rows = train_rows(32, 8)
    b = batch_of(rows, v)
    mi.eval(); me.eval()
    with torch.no_grad():
        assert me.generate(b) == mi.generate(b)
        l1, _ = me.loss(b); l0, _ = mi.loss(b)
        assert torch.allclose(l1, l0), (l1, l0)
    me.train()
    loss, _ = me.loss(b)
    loss.backward()
    assert me.e_e.weight.grad is not None and me.e_e.weight.grad.abs().sum() > 0
    with torch.no_grad():       # d = distance from the end of the char's own string (prompt or entry k), from which chars exist
        me.e_s.weight.zero_()
        me.e_e.weight.copy_(torch.arange(LE, dtype=torch.float)[:, None].expand(-1, me.e_e.weight.shape[1]))
        ids, mask, T = text_ctx(v, 'ab 123', ['add 1 2 = 3', 'mul 30 4 = 120'], T=8, le=16)
        Xc = torch.zeros(1, ids.shape[1], me.d)
        d = (me.span_keys(Xc, T, 16, mask) - me.k_s(Xc))[0, :, 0]
        assert d[:6].tolist() == [5, 4, 3, 2, 1, 0], d[:8]                                   # prompt 'ab 123': '3' is its last char
        assert d[8:19].tolist() == list(range(10, -1, -1)) and d[24:38].tolist() == list(range(13, -1, -1)), d[8:40]
    print('ok span_end', 3314132)


def test_ans_drill():
    """Amendment 8's change (cfg ans_drill, T1SDR = T1SD + ans_drill 0.25): drawn-result drills in training only. No new weight (T1SD's size and
    init); off in eval and at 0; a drill's tape, operands, answer, mode and GEN targets follow the drawn strings (lengths 1-10, nothing cut);
    other rows keep their real targets; the share is p of the eligible rows; the draws touch no torch / python-global random state."""
    from custom_io.models import progparse as pp
    from custom_io.models.tool import DRILL_LEN, GEN_MAX, R0
    v = vocab()
    torch.manual_seed(0)
    m = Tool(v, span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, **S_CFG)
    torch.manual_seed(0)
    t1sd = Tool(v, span_copy=True, span_idx=True, span_end=True, **S_CFG)
    assert m.n_params() == t1sd.n_params() == 3314132
    s1, s2 = m.state_dict(), t1sd.state_dict()
    assert set(s1) == set(s2) and all(torch.equal(s1[k], s2[k]) for k in s2)
    rows = prog_rows(96, 2, 7) + train_rows(96, 8)
    nat = t1sd.gold(rows, 'cpu')
    m.eval()
    assert m.train_golds(rows) == [m.row_gold(r) + (r['answer'], False) for r in rows] and m.drill_stats['eligible'] == 0, 'a drill in eval'
    torch.manual_seed(11)
    m1 = Tool(v, span_copy=True, span_idx=True, span_end=True, ans_drill=1.0, **SMALL)
    m1.train()
    ts, ps = torch.get_rng_state(), random.getstate()
    golds = m1.train_golds(rows)
    assert torch.equal(ts, torch.get_rng_state()) and ps == random.getstate(), 'the drills drew from a shared random stream'
    g = m1.gold(rows, 'cpu', golds)
    b = batch_of(rows, v)
    with torch.no_grad():
        o = m1.run(b, gold=g)
    T, le, K = b['prompt_ids'].shape[1], o['le'], o['K']
    Ma, Mb, Mn, _ = m1.span_gold(rows, T, le, K, golds)
    n_dr, lens = 0, set()
    for i, r in enumerate(rows):
        ops, opd, tape, md, wd, ans, dr = golds[i]
        if not m1.drill_slots(r):
            assert not dr and golds[i][:5] == m1.row_gold(r) and ans == r['answer'], r['id']
            assert torch.equal(g['gen'][i], nat['gen'][i]) and torch.equal(g['ca'][i], nat['ca'][i]) and g['mode'][i] == nat['mode'][i]
            continue
        if not dr:                      # p = 1: only an entry that would not fit in LE chars keeps the real targets
            assert m1.drill_gold(r, random.Random(0)) is not None
            continue
        n_dr += 1
        t = pp.row_targets(r)
        d = [x.split(' = ')[1] for x in tape[:len(ops)]]
        lens |= {len(x) for x in d}
        assert all(DRILL_LEN[0] <= len(x) <= DRILL_LEN[1] and x.isdigit() and (len(x) == 1 or x[0] != '0') for x in d), d
        assert all(len(x) <= LE for x in tape) and md == 0 and wd == () and ans == d[max(m1.drill_slots(r))]
        for s_, (o_, ca, cb, _) in enumerate(t['prog']):
            for slot, got in ((ca[0], opd[s_][0]), (cb[0], opd[s_][1])):
                if slot >= R0:
                    assert got == d[slot - R0], (r['id'], got, d)
                else:
                    assert got == m1.row_gold(r)[1][s_][0 if slot == ca[0] else 1], r['id']
            assert tape[s_] == f"{o_ and pp.OPS[o_].lower()} {opd[s_][0]} {opd[s_][1]} = {d[s_]}"
            for side, x in ((g['ca'], opd[s_][0]), (g['cb'], opd[s_][1])):       # cell targets: the whole string, reversed, then EOS
                c = [k for k in side[i, s_].tolist() if k >= 0]
                assert v.decode(c[:-1])[::-1] == x, (x, c)
        gen = [k for k in g['gen'][i].tolist() if k >= 0]
        assert (v.decode(gen[:-1])[::-1] == ans) if len(ans) <= GEN_MAX else not gen, (ans, gen)
        assert Mn[i].any() and g['mode'][i] == 0
        ids = torch.cat([b['prompt_ids'], o['tape'][1]], 1)[i, :T + K * le]
        for p_ in Mn[i].nonzero()[0]:
            q, txt = int(p_), ''
            while q >= 0 and v.itos[int(ids[q])].isdigit():
                txt, q = v.itos[int(ids[q])] + txt, q - 1
            assert txt == ans and (int(p_) + 1 == len(ids) or not v.itos[int(ids[int(p_) + 1])].isdigit()), (txt, ans)
    assert n_dr >= 40 and lens == set(range(1, 11)), (n_dr, lens)
    # p = 0.25: about a quarter of the eligible rows, over many draws
    m.train(); m.drill_stats.update(rows=0, eligible=0, drilled=0, too_long=0)
    for _ in range(20):
        m.train_golds(rows)
    st = m.drill_stats
    share = (st['drilled'] + st['too_long']) / st['eligible']
    assert st['eligible'] > 1000 and abs(share - 0.25) < 0.04 and st['too_long'] <= 0.02 * st['eligible'], st
    # the loss trains on them, and ans_drill 0 is T1SD exactly
    loss, aux = m1.loss(b)
    loss.backward()
    assert torch.isfinite(loss) and aux['drill_share'] > 0.3 and m1.q_s.weight.grad.abs().sum() > 0
    m0 = Tool(v, span_copy=True, span_idx=True, span_end=True, **SMALL)
    m0.load_state_dict(m1.state_dict()); m0.train()
    m1.ans_drill = 0.0
    torch.manual_seed(3); l1, _ = m1.loss(b)
    torch.manual_seed(3); l0, _ = m0.loss(b)
    assert torch.allclose(l1, l0) and 'drill_share' not in _
    print(f'ok ans_drill ({n_dr} drilled rows, share {share:.3f} at p 0.25, too long {st["too_long"]})')


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


def test_queue70():
    """Queue 70 (T1SDR) = queue 60's T1SD lines with only the name and the cfg changed; the box jobs run the same lines, re-score the
    T1SDR checkpoints at n >= 1000 and export them; nothing else differs from queue 60's box jobs but the pin and the export pace."""
    from custom_io.local_runner import parse_queue
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    q60 = {r[0]: r[2] for r in parse_queue(os.path.join(here, 'queue_local', '60-pc-t1sd-screen.txt'))}
    q70 = parse_queue(os.path.join(here, 'queue_local', '70-pc-t1sdr-screen.txt'))
    assert [r[0] for r in q70] == ['T1SDR_s200', 'T1SDR_s201']
    for name, _, args, mem in q70:
        s = name[-3:]
        old = q60[f'T1SD_s{s}']
        i = args.index('--cfg')
        assert json.loads(args[i + 1]) == {'span_copy': True, 'span_idx': True, 'span_end': True, 'ans_drill': 0.25}
        assert args[:i + 1] + args[i + 2:] == old[:i + 1] + old[i + 2:], (args, old)
        q, oq = ('t1r1', 't1d1') if s == '200' else ('t1r2', 't1d2')
        rd = lambda d, f: open(os.path.join(here, 'queue', d, f)).read()
        box = rd(q, f'70-t1sdr-s{s}.sh')
        assert f"run {name} " + ' '.join(a if not a.startswith('{') else f"'{a}'" for a in args) in box, name
        pin = [x for x in box.splitlines() if x.startswith('SHA=')]
        assert len(pin) == 1 and len(pin[0]) == 44 and pin[0] in rd(q, f'71-wc-t1sdr-s{s}.sh'), pin
        wc, ck = rd(q, f'71-wc-t1sdr-s{s}.sh'), rd(q, f'72-ck-t1sdr-s{s}.sh')
        assert f'--ck $J/w/70-t1sdr-s{s}/T1SDR_s{s}/checkpoint.pt' in wc and '--min-n 1000 --max-passes 12' in wc
        assert f'queue/{q}/CKGO' in ck and f'GLOB="$J/w/70-t1sdr-s{s}/*/checkpoint.pt"' in ck and 'PACE=200' in ck
        strip = lambda t: [x for x in t.splitlines() if not x.startswith('#') and not x.startswith('SHA=')]
        assert [x.replace('T1SDR_s', 'T1SD_s').replace(', "ans_drill": 0.25', '') for x in strip(box)] == strip(rd(oq, f'60-t1sd-s{s}.sh'))
    print('ok queue70')


def fake_wc(name, cfg, n_params, exact=100.0, n=250, cell=None, min_n=200, cells=()):
    """A WC.json (rescore_wc) with every unambiguous cell at `exact` (cell = (side, L, exact, n) overrides one; cells: several)."""
    u = {side: {str(L): dict(n=n, exact=exact) for L in range(1, 10)} for side in ('operand', 'answer')}
    u.update(operand_ambiguous={}, answer_ambiguous={}, passes=1, min_n=min_n)
    for c in ([cell] if cell else []) + list(cells):
        u[c[0]][str(c[1])] = dict(exact=c[2], n=c[3])
    return dict(write_copy_u=u, name=name, cfg=cfg, n_params=n_params, step=24000)


def test_judge():
    """analyze_t1s reads the sealed R1-R4 and Amendment 4 as written, on fake T1S runs built from q40's T1 results."""
    import copy
    from custom_io import analyze_t1s as J
    from custom_io.analyze import load
    runs, _ = load(['custom_io/results/33-pc-confirm-b2', 'custom_io/results/40-vast-t1'])
    for s in J.SEEDS:
        r = copy.deepcopy(runs[('T1', s)])
        r['config'] = dict(r['config'], cfg={'span_copy': True})
        r['n_params'] = T1S_PARAMS
        r['extra']['noexec']['program_families'] = 1.0
        r['extra']['op_acc']['free_run']['call'] = 99.0
        runs[('T1S', s)] = r

    def verdict(cell=None, t1=99.0, **kw):
        wcs = {}
        for s in J.SEEDS:
            wcs[('T1S', s)] = fake_wc('tool', {'span_copy': True}, T1S_PARAMS, cell=cell if s == 201 else None, **kw)
            wcs[('T1', s)] = fake_wc('tool', {}, T1_PARAMS, exact=t1)
        return J.screen(runs, wcs)
    v = verdict()
    assert v['verdict'].startswith('PASS'), (v['verdict'], {k: x['ok'] for k, x in v['marks'].items()})
    assert verdict(cell=('operand', 7, 89.0, 250))['verdict'].startswith('PROVED WRONG')
    assert verdict(cell=('answer', 7, 89.0, 250))['verdict'].startswith('NOT SHOWN: answer selection')     # Amendment 5: read by path
    assert verdict(cell=('operand', 5, 95.0, 250))['verdict'].startswith('NOT SHOWN')
    assert verdict(cell=('operand', 2, 95.0, 250))['verdict'].startswith('NOT SHOWN')         # a 1-3 cell 90-99: not shown, not proved wrong
    assert verdict(cell=('operand', 6, 50.0, 150))['verdict'].startswith('NOT JUDGED on R1')   # short cell: cannot fail by itself
    assert verdict(t1=100.0, exact=99.5)['verdict'].startswith('NOT SHOWN')                    # R3: a 1-3 cell below T1's re-scored value
    assert J.screen(runs, {})['verdict'] == 'NOT JUDGED'
    # --arm T1SI (Amendment 5's next change): T1SI's runs and WC.json judged in T1S's slot, a T1S run must not stand in for it
    spec, keep = J.NEXT['T1SI'], dict(J.ARMS)
    try:
        J.ARMS['T1S'] = spec
        ri = {(a, s): r for (a, s), r in runs.items() if a != 'T1S'}
        for s in J.SEEDS:
            r = copy.deepcopy(runs[('T1S', s)])
            r['config'] = dict(r['config'], cfg=spec[1]); r['n_params'] = spec[2]
            ri[('T1SI', s)] = r
        wi = {('T1', s): fake_wc('tool', {}, T1_PARAMS, exact=99.0) for s in J.SEEDS}
        wi.update({('T1SI', s): fake_wc('tool', spec[1], spec[2]) for s in J.SEEDS})
        assert J.screen(J.as_t1s(ri, 'T1SI'), J.as_t1s(wi, 'T1SI'))['verdict'].startswith('PASS')
        assert J.screen(J.as_t1s(runs, 'T1SI'), J.as_t1s(wi, 'T1SI'))['verdict'] == 'NOT JUDGED'     # T1S's own run: wrong cfg/size
    finally:
        J.ARMS.clear(); J.ARMS.update(keep)
    # --arm T1SD: Amendment 7 + Clarification 7a (screen7)
    spec = J.NEXT['T1SD']
    try:
        J.ARMS['T1S'] = spec
        rd = {(a, s): r for (a, s), r in runs.items() if a != 'T1S'}
        for s in J.SEEDS:
            r = copy.deepcopy(runs[('T1S', s)])
            r['config'] = dict(r['config'], cfg=spec[1]); r['n_params'] = spec[2]
            rd[('T1S', s)] = r

        def v7(cells=(), t1=98.0, n=1100, min_n=1000):
            wd = {('T1', s): fake_wc('tool', {}, T1_PARAMS, exact=t1) for s in J.SEEDS}
            wd.update({('T1S', s): fake_wc('tool', spec[1], spec[2], n=n, min_n=min_n, cells=cells if s == 201 else ()) for s in J.SEEDS})
            return J.screen7(rd, wd)['verdict']
        assert v7().startswith('PASS'), v7()
        assert v7(cells=[('operand', 7, 97.5, 1100)]).startswith('PASS')              # 7a: mean >= 99 and worst >= 97
        assert v7(cells=[('operand', 7, 96.9, 1100)]).startswith('NOT SHOWN')          # a cell below 97
        assert v7(cells=[('operand', L, 98.0, 1100) for L in (4, 5, 6, 7, 8, 9)]).startswith('NOT SHOWN')   # mean 98.7 < 99
        assert v7(cells=[('answer', 5, 89.0, 1100)]).startswith('PROVED WRONG: a 4-9')  # answers count for proved wrong now
        assert v7(cells=[('operand', 8, 88.0, 1100)]).startswith('PROVED WRONG on the same s201')
        assert v7(cells=[('operand', 2, 98.9, 1100)]).startswith('NOT SHOWN')          # R3: a 1-3 cell below 99
        assert v7(t1=100.0, cells=[('answer', 1, 99.0, 1100)]).startswith('PASS')       # R3: exactly 1.0 below T1's re-score is allowed
        assert v7(cells=[('operand', 3, 99.5, 900)]).startswith('NOT JUDGED on R1/R3')  # n < 1000
        assert v7(min_n=200) == 'NOT JUDGED'                                           # scored with the old n
        # --arm T1SDR: Amendment 8 (screen8): screen7's R1-R4 + S2, R5 natural number-answer exact vs T1SD, the hair rule
        J.ARMS['T1SD'] = spec
        s8 = J.NEXT['T1SDR']
        J.ARMS['T1S'] = s8
        r8 = {k: r for k, r in rd.items() if k[0] != 'T1S'}
        for s in J.SEEDS:
            r = copy.deepcopy(rd[('T1S', s)])
            r['config'] = dict(r['config'], cfg=s8[1])
            r8[('T1S', s)], r8[('T1SD', s)] = r, rd[('T1S', s)]
        rows = {f'n{i}': dict(id=f'n{i}', answer=str(i), accepted=[str(i)]) for i in range(400)}
        rows.update({f't{i}': dict(id=f't{i}', answer='cat', accepted=['cat']) for i in range(100)})

        def v8(cells=(), wrong=0, wrong_text=0, ref=None, n=1100):
            wd = {('T1', s): fake_wc('tool', {}, T1_PARAMS, exact=98.0) for s in J.SEEDS}
            wd.update({('T1S', s): fake_wc('tool', s8[1], s8[2], n=n, min_n=1000, cells=cells if s == 201 else ()) for s in J.SEEDS})
            pr = {}
            for s in J.SEEDS:
                pr[('T1SD', s)] = {i: r['answer'] for i, r in rows.items()}
                pr[('T1S', s)] = {i: ('x' if (i.startswith('n') and int(i[1:]) < (wrong if s == 201 else 0)) or
                                      (i.startswith('t') and int(i[1:]) < wrong_text) else r['answer']) for i, r in rows.items()}
            if ref is not None:
                pr[('T1SD', 201)] = ref
            return J.screen8(r8, wd, pr, rows)
        assert v8()['verdict'].startswith('PASS'), v8()['verdict']
        assert v8(wrong=4)['verdict'].startswith('PASS')                                # 4 of 400 number rows: -1.0, allowed
        assert v8(wrong=5)['verdict'].startswith('NOT SHOWN on R5 alone')               # -1.25 on seed 201, every other mark passes (8a)
        assert v8(wrong=5, cells=[('answer', 8, 96.5, 1100)])['verdict'].startswith('NOT SHOWN (failing: R1, R5)')   # R5 and R1
        assert v8(wrong_text=30)['verdict'].startswith('PASS')                          # text answers are not R5's rows
        assert v8(cells=[('answer', L, 98.0, 1100) for L in (6, 7, 8, 9)])['verdict'].startswith('PASS')               # mean 99.11
        assert v8(cells=[('answer', L, 98.0, 1100) for L in (5, 6, 7, 8, 9)])['verdict'].startswith('NOT SHOWN by a hair')  # mean 98.89
        assert v8(cells=[('answer', L, 97.5, 1100) for L in (5, 6, 7, 8, 9)])['verdict'].startswith('NOT SHOWN by a hair')  # mean 98.6
        assert v8(cells=[('answer', L, 97.0, 1100) for L in range(1, 10)])['verdict'].startswith('NOT SHOWN (failing: ')   # mean 97 < 98.5
        assert v8(cells=[('answer', 8, 96.5, 1100)])['verdict'].startswith('NOT SHOWN (failing: ')       # a cell below 97: not a hair
        assert v8(cells=[('answer', 5, 98.0, 1100)] * 1 + [('answer', L, 97.5, 1100) for L in (6, 7, 8, 9)], wrong=5)['verdict'].startswith(
            'NOT SHOWN (failing: R1, R5)')                                                      # R5 fails too: not a hair
        assert v8(cells=[('operand', 8, 88.0, 1100)])['verdict'].startswith('PROVED WRONG: a 4-9')    # any cell < 90 (no s201 special case)
        assert v8(cells=[('operand', 3, 99.5, 900)])['verdict'].startswith('NOT JUDGED on R1/R3')
        assert v8(ref={})['verdict'] == 'NOT JUDGED'                                    # T1SD's predictions missing
        r8b = dict(r8); del r8b[('T1SD', 200)]
        assert J.screen8(r8b, {}, {}, rows)['verdict'] == 'NOT JUDGED'
    finally:
        J.ARMS.clear(); J.ARMS.update(keep)
    print('ok judge')


if __name__ == '__main__':
    import sys
    want = sys.argv[1:]
    for name, fn in list(globals().items()):
        if name.startswith('test_') and (not want or name in want):
            fn()
