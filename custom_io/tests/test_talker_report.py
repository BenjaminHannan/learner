"""python3 -m custom_io.tests.test_talker_report   (CPU, about a minute; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=2)
The talker's reporting lines (talker_report.py: R1 operand exact-match on written call lines, R2 the copyable / other split and its CLI, R3 the scrambled-thoughts table and the TK-1
reading) and the answer-in-thoughts probe (talker_probe.py: R4, TK-2a / TK-2b), on tiny b3g2 models built as test_b3g2 builds them (make(), rows(), batch_of, StubEG) with a SCRIPTED
call writer (test_b3g2.Script) so the written lines are known, on hand-made `runs`, and on a hand-made RESULT.json. Nothing here trains the model; the probe's own fit is checked on a
synthetic state whose answer is linearly readable (and must NOT be read when the answer is not in the state)."""
import json, os, tempfile
import torch
import torch.nn as nn
from custom_io.evalx import subsample
from custom_io import talker_probe as P, talker_report as R
from custom_io.data import ByteVocab, DEV_SPLITS
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
    assert abs(c['A']['baseline'] - 100 * 20 / 90) < 1e-9 and c['B']['baseline'] == 0 and c['C']['baseline'] is None and c['A']['n'] == 10
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
    assert k['reading'] == 'UNCLEAR' and not k['passes'] and not k['proved_wrong'], k                  # 30 > 16.1 but 30 < 35: neither clause holds
    both = dict(split='in_dist', families={}, pooled=dict(n=20, full=10.0, shuffle_state=6.0, zero_state=0.0, collision=c['A']['baseline'] / 2 + c['B']['baseline'] / 2))
    k = R.tk1(both)
    assert k['reading'] == 'UNCLEAR' and k['passes'] and k['proved_wrong'], k                           # 6 <= 11.1 + 5 AND 6 >= 5: both clauses hold, neither reading is earned
    assert R.tk1(dict(both, pooled=dict(both['pooled'], collision=None, shuffle_state=2.0)))['reading'].startswith('n/a')
    assert R.tk1(R.scrambled_table(result((2, 1)), None))['reading'].startswith('n/a')
    assert R.scrambled_table(result((2, 1)), rs[:20], 'all')['pooled']['full'] == 70.0 and R.format_table(t).count('\n') >= 4
    print('ok R3: per-family collision baseline, scrambled table from a RESULT.json, TK-1 reads PASS / PROVED WRONG / UNCLEAR (neither clause, or both) / n/a')


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
    m.cap = 4                                                   # rounds 0..3; the learned stop runs quiet_last (9a5203b21b: no call at the last round, round 3), so calls are asked at rounds 1 and 2 only; every row stops after round 3 (the stop head is replaced), so Script sees all 8 rows each time
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
    assert z['rows'] == 0 and z['n_gold_calls'] == 0 and z['line_pct'] is None and z['name_pct'] is None and z['operands_pct'] is None and z['by_family'] == {}
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
    # F6: an empty group has no rate: exact None (not 0.0), no gap, printed n/a
    cps = [r for r in rs if cp[r['id']]]
    e = R.copyable_split(None, cps, preds={r['id']: r['answer'] for r in cps})
    assert e['other']['n'] == 0 and e['other']['exact'] is None and e['gap'] is None and e['copyable']['exact'] == 100.0, e
    ne = R.copyable_split(None, [], preds={})
    assert ne['n'] == 0 and ne['exact'] is None and ne['copyable']['exact'] is None and ne['gap'] is None
    assert 'n/a' in R.format_split('e', e) and 'None' not in R.format_split('e', e) and 'n/a' in R.format_split('ne', ne)
    ge = R.arm_gap(e, e)
    assert ge['other'] is None and ge['copyable'] == 0.0 and ge['all'] == 0.0, ge
    assert R.arm_gap(e, s)['other'] is None
    z = R.call_lines(None, rs, runs={})
    assert z['name_pct'] is None and 'n/a' in R.format_calls(z) and 'None' not in R.format_calls(z)
    print('ok R2: copyable / other split pooled and per family, gap %+.1f, two-arm gap, a plain arm (answers only)' % s['gap'])


def test_r2_third_split():
    """F2: inside copyable, in_question (answer in the prompt) and only_in_reply (in the last gold reply, not in the prompt); copyable / other keep their meaning. Counted independently with re."""
    import re
    rs = withacc(rows(8) + EXTRA)
    preds = {r['id']: r['answer'] for r in rs}
    preds['t0'], preds['m1'], preds['o1'] = 'wrong', 'wrong', 'wrong'
    s = R.copyable_split(None, rs, preds=preds)
    inq = lambda r: re.search(r'(?<![A-Za-z0-9])' + re.escape(r['answer']) + r'(?![A-Za-z0-9])', r['prompt']) is not None
    exp = {'in_question': [r for r in rs if R.is_copyable(r) and inq(r)], 'only_in_reply': [r for r in rs if R.is_copyable(r) and not inq(r)], 'other': [r for r in rs if not R.is_copyable(r)]}
    exp['copyable'] = exp['in_question'] + exp['only_in_reply']
    assert len(exp['in_question']) > 0 and len(exp['only_in_reply']) > 0 and len(exp['other']) == 1, {k: len(v) for k, v in exp.items()}
    for k, g in exp.items():
        part = s[k] if k in ('copyable', 'other') else s['copyable'][k]
        ok = sum(preds[r['id']] == r['answer'] for r in g)
        assert part['n'] == len(g) and part['correct'] == ok and abs(part['exact'] - 100 * ok / len(g)) < 1e-9, (k, part['n'], len(g))
        fams = {}
        for r in g:
            c = fams.setdefault(r['family'], [0, 0])
            c[0] += preds[r['id']] == r['answer']
            c[1] += 1
        assert {f: (v['correct'], v['n']) for f, v in part['by_family'].items()} == {f: tuple(v) for f, v in fams.items()}, k
    assert s['copyable']['n'] == s['copyable']['in_question']['n'] + s['copyable']['only_in_reply']['n'] and s['other']['n'] == 1 and s['n'] == len(rs)
    txt = R.format_split('x', s)
    assert 'in_question' in txt and 'only_in_reply' in txt and 'None' not in txt
    # operand exact-match rides along: an empty third group is n/a, not an error
    cps = [r for r in rs if inq(r)]
    e = R.copyable_split(None, cps, preds={r['id']: r['answer'] for r in cps})
    assert e['copyable']['only_in_reply']['n'] == 0 and e['copyable']['only_in_reply']['exact'] is None and 'None' not in R.format_split('e', e)
    print('ok R2: in_question %d / only_in_reply %d inside copyable %d, other %d; counts, accuracies and per-family n match an independent count' % (len(exp['in_question']), len(exp['only_in_reply']), len(exp['copyable']), len(exp['other'])))


def test_r2_cli():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'dev'))
        rs = withacc(rows(12))
        for sp in DEV_SPLITS:           # every split file holds the same rows (ids de-duplicated): 'all' pools them
            with open(os.path.join(d, 'dev', sp + '.jsonl'), 'w') as f:
                f.write('\n'.join(json.dumps(r) for r in rs))
        res = os.path.join(d, 'RESULT.json')
        json.dump(dict(final_eval=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 5, 'n': 6}, copy_word={'correct': 3, 'n': 3}, chain_story2={'correct': 3, 'n': 3}))),
                       lesions=dict(shuffle_state=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 0, 'n': 6}, copy_word={'correct': 0, 'n': 3}, chain_story2={'correct': 0, 'n': 3}))),
                                    zero_state=dict(in_dist=dict(by_family=dict(chain_ops={'correct': 0, 'n': 6}, copy_word={'correct': 1, 'n': 3}, chain_story2={'correct': 0, 'n': 3}))))), open(res, 'w'))
        out = os.path.join(d, 'out.json')
        rec = R.main(['--result', res, '--data', d, '--json', out])
        assert rec[res]['tk1']['reading'] == 'PASS' and json.load(open(out))[res]['table']['pooled']['n'] == 12, rec[res]['tk1']
        # F4: the default reading is the pooled dev over all six splits, the in_dist reading sits beside it, labelled
        assert rec[res]['table']['split'] == 'all' and rec[res]['table_in_dist']['split'] == 'in_dist' and rec[res]['tk1_in_dist']['reading'] == 'PASS'
        # F5: the baseline rows are the rows the RESULT's accuracies came from: evalx.subsample at the config's eval_max
        r2 = os.path.join(d, 'RESULT2.json')
        json.dump(dict(json.load(open(res)), config=dict(eval_max=5)), open(r2, 'w'))
        rec5 = R.main(['--result', r2, '--data', d, '--split', 'in_dist'])
        assert abs(rec5[r2]['table']['pooled']['collision'] - R.scrambled_table(json.load(open(res)), subsample(rs, 5))['pooled']['collision']) < 1e-9
        assert 'table_in_dist' not in rec5[r2]
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


def test_probe_reads_what_the_writer_reads():
    """talk_rounds='all': the writer reads the memory (rounds 0..stop round, masked), so collect() flattens writer_view(state), zero-padded to the longest valid memory; the last round's Z alone
    (state[0]) is not what it reads, so changing it changes neither the features nor the answers. 'last' is the state's Z as before. Subsampling is bounded and says so."""
    m = make(7, talk_rounds='all')
    m.eval()
    srt = sorted(withacc(rows(16)[::-1]), key=lambda r: len(r['prompt']))
    ticks = [0]

    def p_stop(z):          # even rows want to stop after round 1, odd rows after round 2: memories of 2 and 3 rounds, so the zero padding is exercised (the call count is reset per run)
        ticks[0] += 1
        return torch.tensor([1.0 if ticks[0] >= 2 + j % 2 else 0.0 for j in range(z.shape[0])])
    real_run = m.run
    m.p_stop, m.run = p_stop, lambda *a, **k: (ticks.__setitem__(0, 0), real_run(*a, **k))[1]
    c = P.collect(m, srt, batch_size=16)
    b = batch_of(srt, V)
    with torch.no_grad():
        o = m.run(b)
    nz, d = 17, o['Z'].shape[2]
    longest = int(o['mem_mask'].sum(1).max()) // nz
    assert sorted(set((o['mem_mask'].sum(1) // nz).tolist())) == [2, 3] and longest == 3
    assert o['Z'].shape[1] == nz and c['Z'].shape == (16, longest * nz * d), (c['Z'].shape, longest, nz, d)
    assert c['idx'] == list(range(16)) and c['note'] is None
    v, mk = m.writer_view(m.state_of(o))
    for i in range(16):           # masked blocks are zero; the valid prefix is the memory
        k = int(mk[i].sum())
        assert torch.equal(c['Z'][i, :k * d], v[i, :k].float().flatten()) and not c['Z'][i, k * d:].any()
    orig = m.state_of
    m.state_of = lambda o: (o['Z'] + 5.0,) + orig(o)[1:]              # the last round's Z alone is perturbed; the memory is untouched
    c2 = P.collect(m, srt, batch_size=16)
    m.state_of = orig
    assert torch.equal(c['Z'], c2['Z']) and c['ans'] == c2['ans'], 'the probe read something the writer does not read'
    # bounded memory: too many floats -> rows subsampled evenly, said in the note
    small = P.collect(m, srt, batch_size=16, max_floats=c['Z'].shape[1] * 5)
    assert small['Z'].shape == (5, c['Z'].shape[1]) and len(small['idx']) == 5 and small['idx'][0] == 0 and small['idx'][-1] == 15 and 'subsampled to 5 of 16' in small['note'], small['note']
    assert torch.equal(small['Z'], c['Z'][small['idx']]) and small['ans'] == [c['ans'][i] for i in small['idx']]
    rep = P.probe_report(m, withacc(rows(40)), withacc(rows(16)[::-1]), batch_size=8)
    assert rep['n'] == 16 and rep['n_features'] > 0 and rep['subsampled'] == []
    del m.p_stop, m.run
    ml = make(7)
    ml.eval()
    cl = P.collect(ml, srt, batch_size=16)
    with torch.no_grad():
        ol = ml.run(b)
    assert torch.equal(cl['Z'], ol['Z'].float().flatten(1)), "'last' changed"
    print('ok probe reads the writer view: %d features = %d rounds x %d x %d under all, perturbing state[0] changes nothing, subsample bounded, last unchanged' % (c['Z'].shape[1], longest, nz, d))


def test_probe_report_shares_one_width():
    """talk_rounds='all': collect() pads to the longest memory of the rows it is given, so train and dev can differ; probe_report pads both to the max of the two (zero blocks), whichever is longer."""
    m = make(7, talk_rounds='all')
    m.eval()
    stop = [2]                  # every row wants to stop after round stop[0]-1: all memories have stop[0] rounds
    ticks = [0]

    def p_stop(z):
        ticks[0] += 1
        return torch.full((z.shape[0],), 1.0 if ticks[0] >= stop[0] else 0.0)
    real_run = m.run
    m.p_stop, m.run = p_stop, lambda *a, **k: (ticks.__setitem__(0, 0), real_run(*a, **k))[1]
    tr, dv = withacc(rows(16)[::-1]), withacc(rows(16))
    widths = {}
    for k in (2, 3):
        stop[0] = k
        widths[k] = P.collect(m, tr, batch_size=16)['Z'].shape[1]
    assert widths[3] == widths[2] * 3 // 2, widths
    orig = P.pack
    seen = []
    P.pack = lambda *a, **kw: (lambda r: (seen.append(r['Z'].shape[1]), r)[1])(orig(*a, **kw))
    try:
        for tk, dk in ((3, 2), (2, 3)):         # dev memory shorter than train's, then longer
            seen.clear()
            gets = iter((tk, dk))
            real_gather = P.gather
            P.gather = lambda *a, **kw: (stop.__setitem__(0, next(gets)), real_gather(*a, **kw))[1]
            try:
                rep = P.probe_report(m, tr, dv, batch_size=16)
            finally:
                P.gather = real_gather
            assert seen == [widths[3], widths[3]] and rep['n_features'] == widths[3] and rep['n'] == 16, (seen, tk, dk)
    finally:
        P.pack = orig
    print('ok probe_report: train and dev share one width (%d features) whether dev memories are shorter or longer' % widths[3])


def test_answer_unended_is_counted():
    """F11: talk() keeps writer.greedy's 'ended' flag: a row whose answer had no EOS within WCAP is counted in free_stats['answer_unended'] (every path that writes an answer greedily goes
    through talk: generate, free_runs, sample_traces); reported by g2_evals beside free_unended, not gated."""
    m = make(3)
    m.eval()
    b = batch_of(rows(6), V)
    with torch.no_grad():
        st = m.state_of(m.run(b))
    assert m.free_stats['answer_unended'] == 0
    real = m.writer.greedy

    class Cut:
        def __call__(self, Z, zm, Xc, cm, ci, mode, **k):
            outs, ended = real(Z, zm, Xc, cm, ci, mode, **k)
            ended = torch.ones_like(ended)
            ended[:2] = False                           # the first two rows never wrote EOS (an untrained writer never ends any: all rows are forced to ended but these)
            return outs, ended
    m.writer.greedy = Cut()
    try:
        with torch.no_grad():
            a1 = m.talk(st, b)
            assert m.free_stats['answer_unended'] == 2 and len(a1) == 6
            m.sample_traces(b, 0.0, torch.Generator().manual_seed(0))
            assert m.free_stats['answer_unended'] == 4, m.free_stats          # sample_traces writes its answers through talk too
            m.generate(b)
            assert m.free_stats['answer_unended'] == 6, m.free_stats
    finally:
        m.writer.greedy = real
    print('ok answer side: unended answers counted in free_stats[answer_unended] (talk, sample_traces, generate), not gated')


def test_g2_evals_survives_a_talker_failure():
    """F7: a failure inside the talker readout is recorded as out['talker_error'] (the traceback) and every other g2 readout is still returned (and so reaches RESULT.json)."""
    import contextlib
    m = make(3)
    m.eval()
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'dev'))
        rs = withacc(rows(8))
        from custom_io.data import DEV_SPLITS as DS
        for sp in DS:
            with open(os.path.join(d, 'dev', sp + '.jsonl'), 'w') as f:
                f.write('\n'.join(json.dumps(r) for r in rs))
        ctx = dict(data=d, big=None, device=torch.device('cpu'), batch_size=8, amp=contextlib.nullcontext)
        ok = m.g2_evals(ctx)
        assert 'talker' in ok and 'talker_error' not in ok and 'answer_unended' in ok
        real = R.talker_evals
        R.talker_evals = lambda *a, **k: 1 / 0
        try:
            bad = m.g2_evals(ctx)
        finally:
            R.talker_evals = real
        assert 'talker' not in bad and 'ZeroDivisionError' in bad['talker_error'] and 'Traceback' in bad['talker_error']
        assert bad['agreement']['n'] == ok['agreement']['n'] and bad['inverse']['hidden'] == ok['inverse']['hidden'] and json.dumps(bad) and m.training is False
        import sys
        m.train()        # a failing import must still record talker_error and put the model back in its previous (train) mode
        import custom_io
        saved = sys.modules.get('custom_io.talker_report')
        sys.modules['custom_io.talker_report'] = None
        del custom_io.talker_report          # `from custom_io import talker_report` would otherwise find the package attribute and never reach the import system
        try:
            imp = m.g2_evals(ctx)
        finally:
            sys.modules['custom_io.talker_report'] = saved
            custom_io.talker_report = saved
        assert 'talker' not in imp and 'ModuleNotFoundError' in imp.get('talker_error', repr(imp.keys())) and imp['agreement']['n'] == ok['agreement']['n'] and m.training is True, (imp.get('talker_error'), m.training)
        m.eval()
        # answer_unended is read after this eval's own talk passes: every answer forced unended -> the returned count is the eval's own
        orig = m.writer.greedy
        def all_unended(*a, **k):
            outs, ended = orig(*a, **k)
            return outs, torch.zeros_like(ended)
        m.writer.greedy = all_unended
        try:
            cut = m.g2_evals(ctx)
        finally:
            m.writer.greedy = orig
        assert cut['answer_unended'] > ok['answer_unended'] and cut['answer_unended'] == m.free_stats['answer_unended'], (cut['answer_unended'], ok['answer_unended'])
    print('ok g2_evals: a talker failure is recorded as talker_error, the other readouts are returned')


def test_caps_trained_checkpoint_reloads():
    """F8: a checkpoint trained under --caps (the PC run's) does not reload with a bare load_model (the reader's position table is sized by the caps); the tools' loader applies the caps
    first: the --caps path, else the caps the run directory records (RESULT.json config.caps, or the job's caps.json). Checked in FRESH subprocesses (caps.apply patches module globals)."""
    import subprocess, sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = dict(os.environ, PYTHONPATH=root, OMP_NUM_THREADS='1')
    save = """
import json, os, sys, torch
from custom_io.g8a import caps as C
from custom_io.tests.test_b3g2 import G2, V, make
d = sys.argv[1]
caps = dict(max_prompt=320, max_ans=8)                     # a bigger prompt cap than today's 208: reader.pos is [320, d], not [208, d]
json.dump(caps, open(os.path.join(d, 'caps.json'), 'w'))
C.apply(json.load(open(os.path.join(d, 'caps.json'))))
m = make(3)
os.makedirs(os.path.join(d, 'run'))
torch.save(dict(model=m.state_dict(), name='b3g2', cfg=G2, chars=V.chars, vocab='bytes', step=3), os.path.join(d, 'run', 'checkpoint.pt'))     # train.py's save
json.dump(dict(config=dict(caps=os.path.join(d, 'caps.json'), cfg=G2)), open(os.path.join(d, 'run', 'RESULT.json'), 'w'))
torch.save(m.state_dict(), os.path.join(d, 'sd.pt'))
"""
    load = """
import sys, torch
from custom_io import talker_report as R, talker_probe as P
from custom_io.models import load_model
d, mode = sys.argv[1], sys.argv[2]
run = d + '/run'
if mode == 'bare':
    try:
        load_model(run + '/checkpoint.pt')
    except RuntimeError as e:
        print('MISMATCH' if 'size mismatch' in str(e) else 'OTHER ' + str(e)[:200])
    else:
        print('LOADED')
else:
    m = R.load_checkpoint(run, 'cpu', None if mode == 'auto' else d + '/caps.json')
    sd = torch.load(d + '/sd.pt')
    print('SAME' if all(torch.equal(m.state_dict()[k], v) for k, v in sd.items()) else 'DIFFERENT')
"""
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run([sys.executable, '-c', save, d], cwd=root, env=env, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr[-3000:]
        run = lambda mode: subprocess.run([sys.executable, '-c', load, d, mode], cwd=root, env=env, capture_output=True, text=True)
        b = run('bare')
        assert b.stdout.strip().endswith('MISMATCH'), (b.stdout, b.stderr[-2000:])
        for mode in ('auto', 'explicit'):
            o = run(mode)
            assert o.returncode == 0 and o.stdout.strip().endswith('SAME') and 'caps applied' in o.stdout, (mode, o.stdout, o.stderr[-3000:])
        # where the caps are found from a run directory
        assert R.caps_of_run(os.path.join(d, 'run')) == os.path.join(d, 'caps.json') and R.caps_of_run(os.path.join(d, 'run', 'checkpoint.pt')) == os.path.join(d, 'caps.json')
        os.remove(os.path.join(d, 'run', 'RESULT.json'))
        assert R.caps_of_run(os.path.join(d, 'run')) == os.path.join(d, 'caps.json')                  # --local job: caps.json beside the arm dirs
        os.makedirs(os.path.join(d, 'w', 'tag-B3G2'))
        os.makedirs(os.path.join(d, 'w', 'tag-pool'))
        open(os.path.join(d, 'w', 'tag-pool', 'caps.json'), 'w').write('{}')
        assert R.caps_of_run(os.path.join(d, 'w', 'tag-B3G2')) == os.path.join(d, 'w', 'tag-pool', 'caps.json')     # the job's layout: <tag>-pool beside <tag>-<arm>
        json.dump(dict(config=dict(caps=None)), open(os.path.join(d, 'w', 'tag-B3G2', 'RESULT.json'), 'w'))
        assert R.caps_of_run(os.path.join(d, 'w', 'tag-B3G2')) is None                                   # a run that trained without caps gets none
    print('ok caps: a caps-trained b3g2 checkpoint fails a bare load_model, reloads through load_checkpoint (auto from RESULT.json / --caps) in a fresh process; caps found from the job layout')


def test_two_arms_in_one_process():
    """A caps-trained arm followed by a no-caps arm in ONE process: load_checkpoint resets the caps (caps.apply({})) when the arm has none, so the second arm loads against the defaults."""
    import subprocess, sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = dict(os.environ, PYTHONPATH=root, OMP_NUM_THREADS='1')
    save = """
import json, os, sys, torch
from custom_io.g8a import caps as C
from custom_io.tests.test_b3g2 import G2, V, make
d, arm = sys.argv[1], sys.argv[2]
if arm == 'capsarm':
    json.dump(dict(max_prompt=320, max_ans=8), open(os.path.join(d, 'caps.json'), 'w'))
    C.apply(json.load(open(os.path.join(d, 'caps.json'))))
m = make(3)
os.makedirs(os.path.join(d, arm))
torch.save(dict(model=m.state_dict(), name='b3g2', cfg=G2, chars=V.chars, vocab='bytes', step=3), os.path.join(d, arm, 'checkpoint.pt'))
json.dump(dict(config=dict(caps=os.path.join(d, 'caps.json') if arm == 'capsarm' else None, cfg=G2)), open(os.path.join(d, arm, 'RESULT.json'), 'w'))
torch.save(m.state_dict(), os.path.join(d, arm + '.pt'))
"""
    load = """
import sys, torch
from custom_io import talker_report as R, data
d = sys.argv[1]
for arm in ('capsarm', 'plain'):                       # the caps arm first, then the arm trained without caps, in this one process
    m = R.load_checkpoint(d + '/' + arm, 'cpu')
    sd = torch.load(d + '/' + arm + '.pt')
    print(arm, data.MAX_PROMPT, 'SAME' if all(torch.equal(m.state_dict()[k], v) for k, v in sd.items()) else 'DIFFERENT')
"""
    with tempfile.TemporaryDirectory() as d:
        for arm in ('capsarm', 'plain'):
            out = subprocess.run([sys.executable, '-c', save, d, arm], cwd=root, env=env, capture_output=True, text=True)
            assert out.returncode == 0, out.stderr[-3000:]
        o = subprocess.run([sys.executable, '-c', load, d], cwd=root, env=env, capture_output=True, text=True)
        lines = o.stdout.strip().splitlines()
        assert o.returncode == 0 and lines[-2].endswith('320 SAME') and lines[-1] == 'plain 208 SAME', (o.stdout, o.stderr[-3000:])
    print('ok two arms in one process: the no-caps arm after a caps arm loads against the default caps')


if __name__ == '__main__':
    torch.set_num_threads(2)
    for name in [k for k in sorted(globals()) if k.startswith('test_')]:
        globals()[name]()
    print('ALL OK')
