"""python3 -m custom_io.tests.test_talker_report   (CPU, about a minute; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=2)
The talker's reporting lines (talker_report.py: R1 operand exact-match on written call lines, R2 the copyable / other split and its CLI, R3 the scrambled-thoughts table and the TK-1
reading) and the answer-in-thoughts probe (talker_probe.py: R4, TK-2a / TK-2b), on tiny b3g2 models built as test_b3g2 builds them (make(), rows(), batch_of, StubEG) with a SCRIPTED
call writer (test_b3g2.Script) so the written lines are known, on hand-made `runs`, and on a hand-made RESULT.json. Nothing here trains the model; the probe's own fit is checked on a
synthetic state whose answer is linearly readable (and must NOT be read when the answer is not in the state)."""
import json, os, tempfile
import torch
import torch.nn as nn
from custom_io import talker_probe as P, talker_report as R
from custom_io.data import ByteVocab
from custom_io.models import progtext
from custom_io.tests.test_b3 import batch_of, rows
from custom_io.tests.test_b3g2 import V, Script, make

EXTRA = [
    dict(id='n2', family='list_stats', prompt='List: 4 7 10. Second largest plus 1?', answer='8', steps=['second_largest of [4, 7, 10]', '7 + 1 = 8']),
    dict(id='m1', family='arith_bare', prompt='38 + ? = 58 State the result only.', answer='20', steps=['38 + 20 = 58']),
    dict(id='o1', family='chain_ops', prompt='5 + 5', answer='10', steps=['5 + 5 = 10'])]


def withacc(rs):
    return [dict(r, accepted=[r['answer']], level=1) for r in rs]


def gold_texts(r):
    return [progtext.text(c) for c in R.gold_calls(r)]


def test_copyable_rule():
    t = R._token_in
    assert t('12', 'has 12 apples') and t('12', '12') and t('-5', 'x is -5.') and t('sune3', 'Echo: sune3 Give')
    assert not t('12', 'has 123 apples') and not t('12', 'a112') and not t('12', 'pi is 3.12') and not t('12', 'it is 12.5 now') and not t('12', '1,200') and not t('', 'x')
    assert t('12', 'sum 12. Then') and t('12', 'ends with 12.')                    # a sentence's full stop is not a decimal point
    rs = withacc(rows(8) + EXTRA)
    cp = {r['id']: R.is_copyable(r) for r in rs}
    assert cp['t1'] and cp['t0'] and cp['t2'], cp          # copy_word: in the prompt; chain_ops / chain_story2: the answer is the last call's reply
    assert cp['n2'] and cp['o1'], cp                       # the last reply is the answer; '10' is a whole token only in the reply here
    assert not cp['m1'], cp                                # 38 + ? = 58: the answer 20 is in neither the prompt nor the last reply (58)
    assert R.last_reply(rs[0]) == rs[0]['answer'] and R.last_reply(rs[1]) == ''
    print('ok copyable: a whole token in the prompt or in the last gold reply; %d of %d toy rows copyable, hidden-operand row is not' % (sum(cp.values()), len(cp)))


def test_collision_and_r3():
    rs = [dict(id=f'a{i}', family='A', answer=('1' if i < 5 else str(i))) for i in range(10)] + [dict(id=f'b{i}', family='B', answer=str(i)) for i in range(10)] + [dict(id='c0', family='C', answer='9')]
    c = R.collision(rs)
    assert abs(c['A']['baseline'] - 100 * 20 / 90) < 1e-9 and c['B']['baseline'] == 0 and c['C']['baseline'] == 0 and c['A']['n'] == 10
    fa = lambda ok, n: {'correct': ok, 'n': n}
    def result(shuf):
        return dict(final_eval=dict(in_dist=dict(by_family=dict(A=fa(8, 10), B=fa(6, 10)))),
            lesions=dict(shuffle_state=dict(in_dist=dict(by_family=dict(A=fa(shuf[0], 10), B=fa(shuf[1], 10)))),
                                               zero_state=dict(in_dist=dict(by_family=dict(A=fa(1, 10), B=fa(0, 10))))))
    t = R.scrambled_table(result((2, 1)), rs[:20])
    assert t['families']['A'] == dict(n=10, full=80.0, shuffle_state=20.0, zero_state=10.0, collision=c['A']['baseline']), t['families']['A']
    p = t['pooled']
    assert p['n'] == 20 and p['full'] == 70.0 and p['shuffle_state'] == 15.0 and p['zero_state'] == 5.0 and abs(p['collision'] - 100 * 20 / 90 / 2) < 1e-9, p
    k = R.tk1(t)
    assert k['reading'] == 'PASS' and k['passes'] and not k['proved_wrong'], k                          # 15 <= 11.1 + 5, 15 < 35
    k = R.tk1(R.scrambled_table(result((8, 4)), rs[:20]))
    assert k['reading'] == 'PROVED WRONG' and k['shuffle_state'] == 60.0, k                             # 60 >= 35
    k = R.tk1(R.scrambled_table(result((3, 3)), rs[:20]))
    assert k['reading'] == 'NOT SHOWN', k                                                               # 30 > 16.1 but 30 < 35
    assert R.tk1(R.scrambled_table(result((2, 1)), None))['reading'].startswith('n/a')
    assert R.scrambled_table(result((2, 1)), rs[:20], 'all')['pooled']['full'] == 70.0 and R.format_table(t).count('\n') >= 4
    print('ok R3: per-family collision baseline, scrambled table from a RESULT.json, TK-1 reads PASS / PROVED WRONG / NOT SHOWN / n/a')


def test_r1_scripted():
    m = make(5)
    m.eval()
    rs = withacc(rows(8))
    g = {r['id']: gold_texts(r) for r in rs}
    assert [len(g[r['id']]) for r in rs] == [1, 0, 2, 2, 1, 0, 2, 2], g
    bad_b = g['t2'][1].rsplit(' ', 1)[0] + ' 999999'
    texts = [[g['t0'][0]],                                      # exact
             [],                                                # copy_word: no gold call, writes nothing
             [g['t2'][0], bad_b],                               # call 1 exact; call 2 right name, wrong 2nd operand
             ['note a thought', g['t3'][0]],                    # a note is left out of the written calc lines; call 2 is missing
             ['mul 1 2', 'add 1 1'],                            # gold is `add a b`: name wrong; one EXTRA written line
             [],
             [g['t6'][0], g['t6'][1]],                          # both exact
             ['add 1 1', 'foo 3 4']]                            # wrong operands, then an unknown tool name
    m.cap = 3                                                   # rounds 0, 1, 2; every row stops after round 2 (the stop head is replaced), so Script sees all 8 rows each time
    m.p_stop = lambda z: torch.zeros(z.shape[0])
    Script(m, texts)
    b = batch_of(rs, V)
    with torch.no_grad():
        o = m.run(b)
    assert [[r[1] for r in x] for x in o['records']] == texts, o['records']
    order = sorted(range(len(rs)), key=lambda i: len(rs[i]['prompt']))        # free_runs batches the rows length-sorted, so the script follows that order
    Script(m, [texts[i] for i in order])
    runs = R.free_runs(m, rs, batch_size=8)
    assert set(runs) == {r['id'] for r in rs} and all(isinstance(v['answer'], str) for v in runs.values())
    c = R.call_lines(m, rs, runs=runs, per_row=True)
    # rows with gold calls: t0 t2 t3 t4 t6 t7 (6 rows, 10 gold calls)
    assert c['rows'] == 6 and c['n_gold_calls'] == 10, c['pooled']
    assert c['per_row']['t0'] == [[True, True, True]] and c['per_row']['t2'] == [[True, True, True], [True, False, False]], c['per_row']
    assert c['per_row']['t3'] == [[True, True, True], [False, False, False]] and c['per_row']['t4'] == [[False, False, False]]
    assert c['per_row']['t6'] == [[True] * 3] * 2 and c['per_row']['t7'] == [[False, False, False], [False, False, False]], c['per_row']['t7']
    # t7 is a chain_ops `a + b * 2` row: gold 1 is `mul b 2`, the first written line `add 1 1` has the wrong name; its second gold call `add a 2b` meets `foo 3 4`
    names = sum(x[0] for v in c['per_row'].values() for x in v)
    ops = sum(x[1] for v in c['per_row'].values() for x in v)
    lines = sum(x[2] for v in c['per_row'].values() for x in v)
    assert (c['name'], c['operands'], c['line']) == (names, ops, lines) == (6, 5, 5), (names, ops, lines)
    assert c['n_written_calc_lines'] == 1 + 2 + 1 + 2 + 2 + 2 and c['extra_written'] == 1, c['pooled']      # t4 wrote two lines for one gold call; the note is not counted
    assert abs(c['line_pct'] - 50.0) < 1e-9
    fam = c['by_family']
    assert set(fam) == {'chain_ops', 'chain_story2'} and fam['chain_story2']['n_gold_calls'] == 4 and fam['chain_ops']['n_gold_calls'] == 6, {f: v['n_gold_calls'] for f, v in fam.items()}
    assert sum(v['line'] for v in fam.values()) == c['line'] and sum(v['extra_written'] for v in fam.values()) == 1
    # a model with no gold rows in the file -> zeros, not a crash
    z = R.call_lines(m, [rs[1], rs[5]], runs=runs)
    assert z['rows'] == 0 and z['n_gold_calls'] == 0 and z['line_pct'] == 0 and z['by_family'] == {}
    json.dumps(c)
    # R2 with the same runs: operands per class, answers from the real (untrained) writer are only counted
    cs = R.copyable_split(m, rs, runs=runs, lines=c)
    cp = [R.is_copyable(r) for r in rs]
    assert cs['n'] == 8 and cs['copyable']['n'] == sum(cp) and cs['other']['n'] == 8 - sum(cp)
    ocalls = cs['copyable']['operands']['n_gold_calls'] + cs['other']['operands']['n_gold_calls']
    assert ocalls == 10 and cs['copyable']['operands']['operands'] + cs['other']['operands']['operands'] == c['operands']
    ev = R.talker_evals(m, rs, batch_size=8)
    assert set(ev) == {'call_lines', 'copyable'} and 'per_row' not in ev['call_lines'] and json.dumps(ev)
    print('ok R1: scripted lines -> name %d / operands %d / line %d of %d gold calls, %d extra written, notes left out, per family adds up; talker_evals is one pass' % (c['name'], c['operands'], c['line'], c['n_gold_calls'], c['extra_written']))


def test_r2_split():
    rs = withacc(rows(8) + EXTRA)
    cp = {r['id']: R.is_copyable(r) for r in rs}
    preds = {r['id']: r['answer'] for r in rs}
    preds['t0'], preds['m1'] = 'wrong', 'wrong'                     # one copyable miss, the only 'other' row missed
    s = R.copyable_split(None, rs, preds=preds)
    assert s['n'] == 11 and s['correct'] == 9 and s['other']['n'] == 1 and s['other']['exact'] == 0.0
    assert s['copyable']['n'] == 10 and s['copyable']['correct'] == 9 and abs(s['copyable']['exact'] - 90.0) < 1e-9 and abs(s['gap'] - (0.0 - 90.0)) < 1e-9
    assert s['copyable']['operands'] is None
    byf = s['copyable']['by_family']
    assert sum(v['n'] for v in byf.values()) == 10 and sum(v['correct'] for v in byf.values()) == 9 and set(s['other']['by_family']) == {'arith_bare'}
    # normalised scoring: case and spaces do not matter (evalx.is_hit)
    preds['t1'] = '  ' + rs[1]['answer'].upper()
    assert R.copyable_split(None, rs, preds=preds)['correct'] == 9
    # the gap between two arms
    p2 = {r['id']: r['answer'] for r in rs}
    s2 = R.copyable_split(None, rs, preds=p2)
    g = R.arm_gap(s2, s)
    assert abs(g['copyable'] - 10.0) < 1e-9 and abs(g['other'] - 100.0) < 1e-9 and abs(g['all'] - 100 * 2 / 11) < 1e-9 and g['operands_copyable'] is None, g
    # a plain arm: no run / state_of / talk, final answers by generate
    class Plain(nn.Module):
        vocab = ByteVocab()

        def __init__(self):
            super().__init__()
            self.w = nn.Linear(1, 1)

        def generate(self, batch, lesion=None):
            return [r['answer'] for r in batch['rows']]
    pl = R.copyable_split(Plain(), rs)
    assert pl['exact'] == 100.0 and pl['copyable']['operands'] is None
    assert 'copyable' in R.format_split('x', s)
    print('ok R2: copyable / other split pooled and per family, gap %+.1f, two-arm gap, a plain arm (answers only)' % s['gap'])


def test_r2_cli():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'dev'))
        rs = withacc(rows(12))
        with open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w') as f:
            f.write('\n'.join(json.dumps(r) for r in rs))
        res = os.path.join(d, 'RESULT.json')
        json.dump(dict(final_eval=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 5, 'n': 6}, copy_word={'correct': 3, 'n': 3}, chain_story2={'correct': 3, 'n': 3}))),
                       lesions=dict(shuffle_state=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 0, 'n': 6}, copy_word={'correct': 0, 'n': 3}, chain_story2={'correct': 0, 'n': 3}))),
                                    zero_state=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 0, 'n': 6}, copy_word={'correct': 1, 'n': 3}, chain_story2={'correct': 0, 'n': 3}))))), open(res, 'w'))
        out = os.path.join(d, 'out.json')
        rec = R.main(['--result', res, '--data', d, '--json', out])
        assert rec[res]['tk1']['reading'] == 'PASS' and json.load(open(out))[res]['table']['pooled']['n'] == 12, rec[res]['tk1']
        # two arms through --run (load_model patched to hand over tiny stub-Gemma models), the gap between them
        import custom_io.models as M
        arms = {'armA': make(0), 'armB': make(1)}
        real = M.load_model
        M.load_model = lambda path, device='cpu': arms[os.path.basename(os.path.dirname(path))]
        try:
            rec = R.main(['--run', os.path.join(d, 'armA'), os.path.join(d, 'armB'), '--data', d, '--splits', 'in_dist', '--max', '12', '--gap', '0', '1', '--batch', '4', '--json', out])
        finally:
            M.load_model = real
        ra, rb = (rec[os.path.join(d, a)] for a in ('armA', 'armB'))
        assert ra['copyable_split']['n'] == 12 == rb['copyable_split']['n'] and ra['call_lines']['rows'] == rb['call_lines']['rows'] > 0
        gp = rec['gap']
        assert abs(gp['all'] - (ra['copyable_split']['exact'] - rb['copyable_split']['exact'])) < 1e-9 and json.load(open(out))['gap']['a'].endswith('armA')
    print('ok CLI: --result prints R3 + TK-1; --run evaluates two checkpoints on the same rows and prints the gap')


def test_probe_fit():
    assert P.target_of('12') == [49, 50] + [256] * 6 and P.target_of('123456789') == list(b'12345678') and P.bucket_of('1') == '1-2' and P.bucket_of('abc') == '3-4'
    assert [P.bucket_of('x' * n) for n in (2, 3, 4, 5, 8, 9, 20)] == ['1-2', '3-4', '3-4', '5-8', '5-8', '9+', '9+']
    g = torch.Generator().manual_seed(0)
    ans = ['7', '42', '1000', 'sune', '314159', '1234567', '-5', 'yes']
    N, Fd = 400, 40
    cls = torch.randint(len(ans), (N,), generator=g)
    proto = torch.randn(len(ans), Fd, generator=g)
    Z = proto[cls] * 2 + 0.3 * torch.randn(N, Fd, generator=g)
    A = [ans[c] for c in cls.tolist()]
    probe, info = P.fit_probe(Z[:300], A[:300])
    assert info['n_heldout'] == 30 and info['n_fit'] == 270 and info['wd'] in (1e-3, 1e-1), info
    assert float(probe.read(Z[300:], A[300:]).float().mean()) >= 0.95
    assert float(probe.read(Z[300:].roll(1, 0), A[300:]).float().mean()) < 0.5
    # no answer in the state: the probe must not read held-out rows
    Zn = torch.randn(N, Fd, generator=g)
    pn, _ = P.fit_probe(Zn[:300], A[:300])
    assert float(pn.read(Zn[300:], A[300:]).float().mean()) < 0.4
    # a byte the fit rows never showed is a miss, not a crash
    assert not bool(probe.read(Z[300:301], ['zzz'])[0])
    print('ok probe fit: reads %.0f%% of held-out rows when the answer is linearly in the state, %.0f%% when it is not; held-out %d of 300, wd %g' %
          (100 * float(probe.read(Z[300:], A[300:]).float().mean()), 100 * float(pn.read(Zn[300:], A[300:]).float().mean()), info['n_heldout'], info['wd']))


def test_probe_readings():
    g = torch.Generator().manual_seed(1)
    ans = ['7', '42', '1000', 'sune', '314159', '123456789012', '-5', 'yes']
    fam = ['A', 'B']
    def make_rows(n):
        return [dict(id=f'r{i}', family=fam[i % 2], answer=ans[i % len(ans)], accepted=[ans[i % len(ans)]]) for i in range(n)]
    proto = torch.randn(len(ans), 40, generator=g)
    cl = lambda n: torch.arange(n) % len(ans)
    tr_rows, dv_rows = make_rows(400), make_rows(160)
    tr = proto[cl(400)] * 2 + 0.3 * torch.randn(400, 40, generator=g)
    dv = proto[cl(160)] * 2 + 0.3 * torch.randn(160, 40, generator=g)
    probe, _ = P.fit_probe(tr, [r['answer'] for r in tr_rows])
    hit = (torch.arange(160) % 5) != 0                                            # the talker is wrong on every 5th row (32), right on 128
    rep = P.read_dev(probe, dict(Z=dv, hit=hit), dv_rows)
    assert rep['n'] == 160 and rep['right_n'] == 128 and rep['wrong_n'] == 32 and rep['right_read'] >= 95 and rep['wrong_read'] >= 95, rep
    # family A holds answers[0,2,4,6], B the odd ones: the roll inside the family hands over another answer
    assert rep['control'] < 40 and rep['collision'] > 0
    assert rep['tk2a']['reading'] == 'PASS' and rep['tk2b']['reading'] == 'talker failed' and rep['tk2b']['K'] == rep['wrong_read'], (rep['tk2a'], rep['tk2b'])
    assert set(rep['by_family']) == {'A', 'B'} and set(rep['by_length']) == {'1-2', '3-4', '5-8', '9+'}
    assert rep['by_length']['9+']['n'] == 20 and rep['by_length']['5-8']['n'] == 20 and rep['by_length']['1-2']['n'] == 60 and sum(c['n'] for c in rep['by_length'].values()) == 160
    assert sum(c['wrong_n'] for c in rep['by_family'].values()) == 32 and rep['by_family']['A']['collision'] > 0
    # the decision rule: K at most 20 -> 'not in the thoughts'; between -> 'between'; a weak probe -> TK-2a FAIL and TK-2b VOID
    for K, want in ((10.0, 'not in the thoughts'), (35.0, 'between'), (50.0, 'talker failed'), (20.0, 'not in the thoughts')):
        assert P.tk2b(dict(rep, wrong_read=K))['reading'] == want, K
    assert P.tk2b(dict(rep, wrong_read=None))['reading'].startswith('n/a')
    weak = dict(rep, right_read=79.9)
    weak['tk2a'] = P.tk2a(weak)
    assert weak['tk2a']['reading'] == 'FAIL' and P.tk2b(weak)['reading'] == 'VOID'
    leaky = dict(rep, control=rep['collision'] + 5.1)
    assert P.tk2a(leaky)['reading'] == 'FAIL' and P.tk2a(dict(rep, control=rep['collision'] + 5.0))['reading'] == 'PASS'
    # random states: nothing is readable -> FAIL, void
    rp, _ = P.fit_probe(torch.randn(400, 40, generator=g), [r['answer'] for r in tr_rows])
    bad = P.read_dev(rp, dict(Z=torch.randn(160, 40, generator=g), hit=hit), dv_rows)
    assert bad['tk2a']['reading'] == 'FAIL' and bad['tk2b']['reading'] == 'VOID', (bad['tk2a'], bad['tk2b'])
    assert P.format_report(dict(rep, n_train=400, fit={})).count('\n') >= 8
    print('ok readings: TK-2a pass / fail at 80 and baseline + 5, TK-2b routes K (>= 50, <= 20, between) and is VOID when TK-2a fails; K per family and by length')


def test_probe_on_model():
    m = make(7)
    m.eval()
    tr_rows, dv_rows = withacc(rows(40)), withacc(rows(16)[::-1])
    # collect: the flattened Z the talker read, the talker's own final lines
    srt = sorted(dv_rows, key=lambda r: len(r['prompt']))
    c = P.collect(m, srt, batch_size=len(srt))
    b = batch_of(srt, V)
    with torch.no_grad():
        o = m.run(b)
        st = m.state_of(o)
        ans = m.talk(st, b)
    assert c['ans'] == ans and torch.equal(c['Z'], st[0].float().flatten(1)) and c['Z'].shape == (16, st[0].shape[1] * st[0].shape[2]), c['Z'].shape
    assert c['hit'].tolist() == [a.strip().lower() == r['answer'].lower() for a, r in zip(ans, srt)]
    rep = P.probe_report(m, tr_rows, dv_rows, batch_size=8)
    assert rep['n'] == 16 and rep['n_train'] == 40 and rep['fit']['n_heldout'] == 4 and rep['right_n'] + rep['wrong_n'] == 16
    assert rep['tk2a']['reading'] in ('PASS', 'FAIL', 'n/a') and rep['tk2b']['reading'] and json.dumps(rep)
    assert abs(rep['talker_exact'] - 100 * rep['right_n'] / 16) < 1e-9
    P.format_report(rep)
    print('ok probe on a tiny b3g2: collect = state_of(run)[0] flattened (%d numbers per row), report runs end to end (TK-2a %s)' % (c['Z'].shape[1], rep['tk2a']['reading']))


if __name__ == '__main__':
    torch.set_num_threads(2)
    for name in [k for k in sorted(globals()) if k.startswith('test_')]:
        globals()[name]()
    print('ALL OK')
