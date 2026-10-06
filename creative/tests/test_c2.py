"""python3 -m creative.tests.test_c2   (CPU, under a minute; synthetic few-example questions, tiny random B2)
C2a checker: planted bad programs, two executors, no answer key anywhere in the verdict; C2b arms; forced-replay targets; sleep on the records."""
import random
import torch
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import fewshot as F, sampler, sleep
from creative.programs import ADD, DIV, MUL, R0, SUB, Try

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
VOCAB = CharVocab.build([])
Q = 4                                           # "14->44; 26->80. Now 35->?" : x_q is slot 4
C1, C2_, C10 = 16, 17, 18                       # constants 1 2 10
T_ = lambda steps, ans: Try.make(steps, ans)


def model(seed=0):
    torch.manual_seed(seed)
    return Ledger(VOCAB, copy=True, **SMALL)


def row_for(f, xs, rid='t0'):
    ex = '; '.join(f'{x}->{f(x)}' for x in xs[:-1])
    return dict(id=rid, prompt=f'{ex}. Now {xs[-1]}->?', answer=str(f(xs[-1])), accepted=[str(f(xs[-1]))], family='fewshot_number_rule', level=7,
                stage=9, variant='', steps=[])


def test_checker_planted():
    r = row_for(lambda x: 2 * x + 1, [14, 20, 35])               # 14->29; 20->41. Now 35->?   answer 71
    p = F.parse(r['prompt'])
    assert p['q_slot'] == 4 and p['xs'] == [14, 20] and p['ys'] == [29, 41] and p['q'] == 35
    good = T_([(MUL, Q, C2_), (ADD, R0, C1)], R0 + 1)
    assert F.verdict(p, good) == ('accept', 'ok', 71)
    assert F.outputs_py(p, good) == F.outputs_torch(p, good) == [29, 41, 71]
    bad = {
        'fits one example only': T_([(ADD, Q, C10)], R0),                                    # 14+10 != 29
        'wrong rule': T_([(MUL, Q, C2_)], R0),
        'constant answer': T_([(MUL, C2_, C2_), (ADD, R0, C10)], R0 + 1),                    # never reads x
        'points at an example output': T_([(ADD, 1, C1)], R0),                               # slot 1 = y_1
        'points at another input': T_([(ADD, 2, Q)], R0),                                    # slot 2 = x_2
        'answer on a prompt slot': T_([(MUL, Q, C2_), (ADD, R0, C1)], 3),
        'answer on a constant': T_([(MUL, Q, C2_), (ADD, R0, C1)], C1),
        'answer on unwritten': T_([(MUL, Q, C2_), (ADD, R0, C1)], R0 + 3),
        'noop in the tree': T_([(MUL, Q, C2_), (0, R0, C1)], R0 + 1),
        'forward reference': T_([(ADD, R0 + 1, C1), (MUL, Q, C2_)], R0),
        'inexact division': T_([(DIV, Q, C10), (ADD, R0, C1)], R0 + 1),
    }
    for name, t in bad.items():
        v = F.verdict(p, t)
        assert v[0] == 'reject', (name, v)
    # a cheat that fits by reading the examples' own numbers: y_1 - x_1 = 15 is a constant the program "finds" in the prompt
    cheat = T_([(SUB, 1, 0), (ADD, Q, R0)], R0 + 1)
    assert F.verdict(p, cheat)[0] == 'reject'
    # value-blind view (what R / H select on): wrong rule runs on every row, structure-broken ones do not
    assert F.verdict(p, bad['wrong rule'], rules_only=True)[0] == 'accept'
    assert F.verdict(p, bad['constant answer'], rules_only=True)[0] == 'reject'
    assert F.verdict(p, bad['points at an example output'], rules_only=True)[0] == 'reject'
    assert F.verdict(p, Try((1,) * 7, (0,) * 7, (1,) * 7, None))[0] == 'unresolved'
    print(f'  {len(bad) + 1} planted bad programs rejected; the verdict function takes no answer key')
    print('ok checker_planted')


def test_executors_agree_fuzz():
    rng = random.Random(0)
    r = row_for(lambda x: x * x, [13, 17, 23, 29])
    p = F.parse(r['prompt'])
    n_acc, q = 0, p['q_slot']
    for _ in range(3000):
        valid = [q, C1, C2_, C10]
        steps = []
        for s in range(rng.randint(1, 5)):
            steps.append((rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 4]), rng.choice(valid + [0, 1, 2, 3]), rng.choice(valid)))
            valid.append(R0 + s)
        t = T_(steps, rng.choice(valid))
        a, b = F.outputs_py(p, t), F.outputs_torch(p, t)
        if F.structure(p, t)[0]:
            assert a == b, (steps, t.ans, a, b)
        n_acc += F.verdict(p, t)[0] == 'accept'
    sq = T_([(MUL, q, q)], R0)
    assert F.verdict(p, sq) == ('accept', 'ok', 29 * 29)
    print(f'  fuzz 3000: the two executors never disagree on a structure-ok try ({n_acc} accepted)')
    print('ok executors_agree_fuzz')


def test_sampler_never_sees_the_key():
    rows = F.make_rows(F.HELD_OUT, 6, seed=3)
    blank = [dict(r, answer='', accepted=[''], steps=[]) for r in rows]
    m = model()
    a, _ = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=16, temperature=1.5, seed=4)
    b, _ = sampler.sample_tries(m, blank, VOCAB, 'cpu', n_tries=16, temperature=1.5, seed=4)
    assert [[x.t for x in t] for t in a] == [[x.t for x in t] for t in b]
    s = F.score_fewshot(rows, a)
    assert s['unresolved'] == 0 and 0 <= s['reach4'] <= s['reach32'] <= 1
    print(f"  tries identical with the answer key blanked; random B2: luck {s['luck']:.3f}, distinct {s['distinct']:.1f}")
    print('ok sampler_never_sees_the_key')


def make_pool():
    """Hand-built tries on three questions: right rules, a wrong rule that runs, a broken structure."""
    fs = [lambda x: 2 * x + 1, lambda x: x * x, lambda x: (x + 1) * 2]
    rows = [row_for(f, [14, 20, 35 + i], rid=f'q{i}') for i, f in enumerate(fs)]
    prog = [
        [T_([(MUL, Q, C2_), (ADD, R0, C1)], R0 + 1), T_([(ADD, Q, C1), (MUL, R0, C2_)], R0 + 1)],     # 2x+1 (and a different one that does not fit)
        [T_([(MUL, Q, Q)], R0), T_([(MUL, Q, Q), (ADD, R0, C1)], R0 + 1)],
        [T_([(ADD, Q, C1), (MUL, R0, C2_)], R0 + 1), T_([(MUL, Q, C2_), (ADD, R0, C1)], R0 + 1), T_([(MUL, Q, C2_)], R0)],
    ]
    return rows, prog


def test_arms_and_records():
    rows, prog = make_pool()
    tries = [[sampler.TryRec(t) for t in ts] for ts in prog]
    wrong = [[sampler.TryRec(T_([(ADD, Q, C10)], R0)), sampler.TryRec(T_([(MUL, Q, C2_)], R0)), sampler.TryRec(T_([(SUB, Q, C1), (MUL, R0, C2_)], R0 + 1)),
              sampler.TryRec(T_([(MUL, C2_, C2_)], R0))] for _ in rows]
    for pool in (wrong, tries):        # R comes from a separate pool; tries that already fit are never R
        a = F.build_arms(rows, tries, pool, seed=1)
        assert a['N'] == [] and len(a['W']) == sum(a['counts'].values()) and max(a['counts'].values()) <= 2
        for w in a['W']:
            assert F.verdict(F.parse(w['prompt']), F.record_try(w))[0] == 'accept'
        for r_ in a['R']:
            assert F.verdict(F.parse(r_['prompt']), F.record_try(r_))[0] == 'reject'
        assert len(a['R']) == len(a['H']) <= len(a['W'])
        for r_, h in zip(a['R'], a['H']):
            assert F.record_try(r_) == F.record_try(h) and r_['source'] == h['source']
            assert F.verdict(F.parse(h['prompt']), F.record_try(h))[0] == 'accept', 'hindsight relabel must make the examples fit'
            assert h['prompt'] != r_['prompt'] and F.parse(h['prompt'])['xs'] == F.parse(r_['prompt'])['xs']
        assert a['diag']['hindsight_fits'] == 1.0
    a = F.build_arms(rows, tries, wrong, seed=1)
    assert len(a['R']) > 0 and not a['diag']['short'] or a['diag']['short']
    # the key is never read: corrupt every answer key, the records (answered by the try's own output) do not change
    rows_bad = [dict(r, answer='999', accepted=['999']) for r in rows]
    a2 = F.build_arms(rows_bad, tries, wrong, seed=1)
    assert [x['answer'] for x in a['W']] == [x['answer'] for x in a2['W']]
    # forced replay: B2's gold targets run to the record's own answer
    m = model().eval()
    recs = a['W'] + a['H']
    b = sampler.make_batch(recs, VOCAB, 'cpu')
    g = m.gold(b['rows'], 'cpu')
    with torch.no_grad():
        o = m.run(b, gold=g)
    for i, r in enumerate(recs):
        k = int(g['ans'][i].nonzero()[0])
        assert int(o['vals'][i, k]) == int(r['answer']) and bool(o['valid'][i, k]), (r['id'], int(o['vals'][i, k]), r['answer'])
    # sleeping on the records works (plumbing shared with C1)
    out = sleep.sleep(model(2), a['W'], [], VOCAB, sleep.SleepCfg(updates=2, batch=6, lr=1e-3, warmup=1, max_visits=4))
    assert out['updates'] == 2
    mech = F.mechanism_report(rows, [[sampler.TryRec(F.record_try(w)) for w in a['W'] if w['source'] == r['id']] for r in rows])
    assert mech['passes'] and mech['agreement'] == 1.0
    print(f"  W {len(a['W'])}, R {len(a['R'])}, H {len(a['H'])}; hindsight relabels all fit; mechanism agreement {mech['agreement']}")
    print('ok arms_and_records')


def test_labelled_sets_and_synthetic():
    held = F.make_rows(F.HELD_OUT, 400, seed=9)
    sets = F.labelled_sets(held, seed=1)
    assert [len(sets[k]) for k in (0, 8, 32, 128)] == [0, 8, 32, 128]
    ids = {k: {r['id'] for r in v} for k, v in sets.items()}
    assert ids[8] <= ids[32] <= ids[128]
    kinds = {r['kind'] for r in held}
    assert kinds == set(F.HELD_OUT) and not kinds & set(F.PRACTISED)
    # every synthetic question is solvable by the true rule through the real checker: spot-check that parse works on all
    assert all(F.parse(r['prompt']) for r in held)
    print(f'  kind seal {F.KIND_SEAL[:12]}…; 400 synthetic held-out questions parse')
    print('ok labelled_sets_and_synthetic')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
