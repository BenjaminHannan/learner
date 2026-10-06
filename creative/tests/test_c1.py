"""python3 -m creative.tests.test_c1   (CPU, about a minute; needs no data: everything is generated, B2 is a tiny random Ledger(copy=True))
Checks the C1 machinery: puzzles and seals, both checkers on planted bad programs and a fuzz, forced-replay targets, the sampler (greedy equals
Ledger.run, branching, dedup), the scoreboard and DEV gate, the arms, and the sleep plumbing."""
import copy, json, os, random, tempfile
import torch
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import arms, checkers, programs as P, puzzles, sampler, scoreboard, sleep
from creative.programs import ADD, DIV, MUL, SUB, R0, Try

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
VOCAB = CharVocab.build([])
NUMS = [3, 5, 7, 22]                     # given 3 5 7, target 22 = 3 x 5 + 7 (slots 0 1 2 | target slot 3)


def model(seed=0):
    torch.manual_seed(seed)
    return Ledger(VOCAB, copy=True, **SMALL)


_SP = {}


def splits():
    if not _SP:
        _SP.update(puzzles.build_splits())
    return _SP


def test_solver_and_floors():
    for nums, T in (([3, 5, 7], 22), ([7, 12, 25], 38 if 38 in puzzles.valid_targets([7, 12, 25]) else 30)):
        sols = puzzles.solutions(nums, T)
        assert sols or T not in puzzles.valid_targets(nums)
    sols = puzzles.solutions([3, 5, 7], 22)
    assert sols
    for t in sols:
        assert checkers.verdict(NUMS, 3, t)[0] == 'accept'
        vals, valid = P.run(NUMS, t)
        assert vals[t.ans] == 22
    assert puzzles.reachable_from_pair([3, 5, 7], 15) and not puzzles.reachable_from_pair([3, 5, 7], 22)
    f = puzzles.rules_only_floor([3, 5, 7], 22)
    assert 0 < f < 0.5, f
    u = puzzles.uniform_floor([3, 5, 7], 22, 4000)
    assert 0 <= u < f, (u, f)
    print(f'  rules-only floor {f:.3f}, uniform floor {u:.4f} on 3 5 7 -> 22')
    print('ok solver_and_floors')


def test_warmup_sets():
    sp = splits()
    used = {tuple(sorted(r['nums'])) for k in puzzles.SPLITS for r in sp[k]}
    w3 = puzzles.warmup3_rows(300, 0)
    assert len({r['id'] for r, _ in w3}) == 300 and not any(tuple(sorted(r['nums'])) in used for r, _ in w3)
    assert all(checkers.verdict(r['nums'] + [r['target']], 3, t)[0] == 'accept' for r, t in w3)
    w2 = puzzles.warmup_rows(100, 0, per_pair=3)
    assert all(checkers.verdict(r['nums'] + [r['target']], 2, t)[0] == 'accept' for r, t in w2)
    print('ok warmup_sets')


def test_splits_sealed():
    sp = splits()
    assert {k: len(v) for k, v in sp.items()} == dict(practice=1024, dev=128, t1=256, t1b=256, x=128)
    seen = {}
    for k in ('practice', 'dev', 't1', 't1b'):
        for r in sp[k]:
            assert seen.setdefault(tuple(sorted(r['nums'])), k) == k, 'number set crossed splits'
            assert r['target'] not in r['nums'] and r['target'] not in P.CONSTS and 1 <= r['target'] <= puzzles.T_MAX
            assert not any(n in P.CONSTS for n in r['nums']) and all(3 <= n <= 40 and n != 10 for n in r['nums'])
            assert not puzzles.reachable_from_pair(r['nums'], r['target'])
            assert len(r['prompt']) < 208 and [int(x) for x in __import__('re').findall(r'\d+', r['prompt'])] == r['nums'] + [r['target']]
            if k != 'practice':
                tw = r['twin']
                assert tw['nums'] == r['nums'] and tw['target'] != r['target'] and puzzles.solutions(tw['nums'], tw['target'])
    assert all(len(r['nums']) == 4 for r in sp['x'])
    assert len({r['prompt'].split('Use')[1] for k in sp for r in sp[k]}) == 1, 'instruction line must be identical'
    with tempfile.TemporaryDirectory() as d:
        man = puzzles.write_splits(d)
        assert puzzles.load_split(d, 't1') == [json.loads(json.dumps(r, sort_keys=True)) for r in sp['t1']]
        p = os.path.join(d, 't1.jsonl')
        open(p, 'a').write('{}\n')
        try:
            puzzles.load_split(d, 't1')
            raise AssertionError('tampered split loaded')
        except AssertionError as e:
            assert 'sealed hash' in str(e)
    print('  mean solutions per puzzle:', {k: round(sum(r['n_solutions'] for r in v) / len(v), 2) for k, v in sp.items()})
    print('ok splits_sealed')


def T_(steps, ans):
    return Try.make(steps, ans)


GOOD = T_([(MUL, 0, 1), (ADD, R0, 2)], R0 + 1)
BAD = {                                       # every kind of bad program: must be rejected (value-blind where the rule breaks, whatever the value)
    'number twice': T_([(MUL, 0, 1), (ADD, R0, 0)], R0 + 1),
    'missing number': T_([(ADD, 0, 1)], R0),
    'constant used': T_([(MUL, 0, 1), (ADD, R0, 18)], R0 + 1),
    'target slot used': T_([(ADD, 3, 0)], R0),
    'inexact division': T_([(DIV, 2, 0), (ADD, R0, 1)], R0 + 1),
    'MOD op': T_([(5, 0, 1), (ADD, R0, 2)], R0 + 1),
    'MIN op': T_([(6, 0, 1), (ADD, R0, 2)], R0 + 1),
    'MAX op': T_([(7, 0, 1), (ADD, R0, 2)], R0 + 1),
    'CMP op': T_([(8, 0, 1), (ADD, R0, 2)], R0 + 1),
    'answer on a prompt number': T_([(MUL, 0, 1), (ADD, R0, 2)], 2),
    'answer on the target slot': T_([(MUL, 0, 1), (ADD, R0, 2)], 3),
    'answer on a constant': T_([(MUL, 0, 1), (ADD, R0, 2)], 17),
    'answer on an unwritten step': T_([(MUL, 0, 1), (ADD, R0, 2)], R0 + 5),
    'answer outside the workspace': T_([(MUL, 0, 1), (ADD, R0, 2)], 40),
    'answer on a NOOP step': T_([(MUL, 0, 1), (0, 0, 0), (ADD, R0, 2)], R0 + 1),
    'forward reference': T_([(ADD, R0 + 1, 2), (MUL, 0, 1)], R0),
    'self reference': T_([(ADD, R0, 2)], R0),
    'result reused (dag)': T_([(ADD, 0, 1), (ADD, R0, R0), (ADD, R0 + 1, 2)], R0 + 2),
    'reads an unwritten result': T_([(MUL, 0, 1), (ADD, R0 + 4, 2)], R0 + 1),
    'same slot as both operands': T_([(MUL, 1, 1), (ADD, R0, 2)], R0 + 1),
    'number slot beyond the numbers': T_([(MUL, 0, 1), (ADD, R0, 9)], R0 + 1),
    'noop in the tree': T_([(MUL, 0, 1), (0, R0, 2)], R0 + 1),
    'operand out of range': T_([(MUL, 0, 99), (ADD, R0, 2)], R0 + 1),
}
WRONG_VALUE = T_([(ADD, 0, 1), (ADD, R0, 2)], R0 + 1)            # follows every rule, makes 15


def test_checkers_planted():
    assert checkers.verdict(NUMS, 3, GOOD) == ('accept', 'ok')
    junk = T_([(MUL, 0, 1), (SUB, 0, 2), (ADD, R0, 2)], R0 + 2)   # a step off the tree is ignored
    assert checkers.verdict(NUMS, 3, junk)[0] == 'accept'
    for name, t in BAD.items():
        for cv in (True, False):
            v = checkers.verdict(NUMS, 3, t, check_value=cv)
            assert v[0] == 'reject', (name, cv, v)
            assert not checkers.rules_a(NUMS, 3, t, cv)[0] and not checkers.rules_b(NUMS, 3, t, cv)[0], (name, cv)
    assert checkers.verdict(NUMS, 3, WRONG_VALUE, check_value=True)[0] == 'reject'
    assert checkers.verdict(NUMS, 3, WRONG_VALUE, check_value=False)[0] == 'accept'      # the value-blind rule check R / H select on
    # a crash is unresolved, never a hit
    assert checkers.verdict(NUMS, 3, Try((1,) * 7, (0,) * 7, (1,) * 7, None))[0] == 'unresolved'     # an answer that is not a slot: crash, never a hit
    print(f'  {len(BAD)} planted bad programs rejected by both checkers, value-aware and value-blind')
    print('ok checkers_planted')


def test_checkers_fuzz():
    """Two independently written checkers must never disagree on random tries; the torch replay must reproduce every python run."""
    rng = random.Random(0)
    n_acc = n_rules = 0
    for _ in range(6000):
        valid = [0, 1, 2, 3, 16, 17, 18, 19]
        steps = []
        for s in range(rng.randint(1, 7)):
            op = rng.choice([0, 1, 2, 3, 4, 4, 5, 6, 7, 8])
            steps.append((op, rng.choice(valid), rng.choice(valid)))
            valid.append(R0 + s)
        t = Try.make(steps, rng.choice(valid))
        for cv in (True, False):
            ra, rb = checkers.rules_a(NUMS, 3, t, cv)[0], checkers.rules_b(NUMS, 3, t, cv)[0]
            assert ra == rb, (steps, t.ans, cv, ra, rb)
        assert checkers.replay_agrees(NUMS, t), (steps, t.ans)
        n_acc += checkers.verdict(NUMS, 3, t)[0] == 'accept'
        n_rules += checkers.verdict(NUMS, 3, t, check_value=False)[0] == 'accept'
    for _ in range(4000):              # random trees over the three numbers, mutated: plenty of accepts and near misses
        order = [0, 1, 2]
        rng.shuffle(order)
        o1, o2 = rng.choice([1, 2, 3, 4]), rng.choice([1, 2, 3, 4])
        steps = [(o1, order[0], order[1]), (o2, R0, order[2]) if rng.random() < .5 else (o2, order[2], R0)]
        if rng.random() < .3:
            k = rng.randrange(2)
            steps[k] = (steps[k][0], rng.choice([0, 1, 2, 3, 16, 19, R0]), steps[k][2])
        t = T_(steps, R0 + 1)
        for cv in (True, False):
            assert checkers.rules_a(NUMS, 3, t, cv)[0] == checkers.rules_b(NUMS, 3, t, cv)[0], (steps, cv)
        n_acc += checkers.verdict(NUMS, 3, t)[0] == 'accept'
        n_rules += checkers.verdict(NUMS, 3, t, check_value=False)[0] == 'accept'
    assert n_rules > 1000 and n_acc > 0
    # exhaustive well-formed 2-step programs: every accepted one makes 22
    for o1 in (1, 2, 3, 4):
        for a in range(3):
            for b in range(3):
                for o2 in (1, 2, 3, 4):
                    for x, y in ((R0, 0), (R0, 1), (R0, 2), (0, R0), (1, R0), (2, R0)):
                        t = T_([(o1, a, b), (o2, x, y)], R0 + 1)
                        if checkers.verdict(NUMS, 3, t)[0] == 'accept':
                            assert P.run(NUMS, t)[0][R0 + 1] == 22
    print(f'  fuzz 10000: no disagreement, torch replay always agrees ({n_acc} accepted, {n_rules} rule-following)')
    print('ok checkers_fuzz')


def test_forced_replay_targets():
    """Targets come from logged slot ids: Ledger.run(gold=...) replays the registered program and lands on the answer slot."""
    m = model().eval()
    rows = []
    for k, r in enumerate(splits()['practice'][:12]):
        t = puzzles.solutions(r['nums'], r['target'])[0]
        rows.append(arms.record(r, t, 'PC', k))
    b = sampler.make_batch(rows, VOCAB, 'cpu')
    g = m.gold(b['rows'], 'cpu')
    with torch.no_grad():
        o = m.run(b, gold=g)
    for i, r in enumerate(rows):
        k = int(g['ans'][i].nonzero()[0])
        assert int(o['vals'][i, k]) == r['target'] and bool(o['valid'][i, k]), (r['id'], int(o['vals'][i, k]), r['target'])
        assert int(g['mode'][i]) == 0
    loss, aux = m.loss(b)
    assert torch.isfinite(loss)
    # the training form is the cone first, then NOOP, ids renumbered
    junk = T_([(SUB, 0, 2), (MUL, 0, 1), (ADD, R0 + 1, 2)], R0 + 2)
    steps, ans = P.train_form(junk)
    assert steps == [(MUL, 0, 1), (ADD, R0, 2)] and ans == R0 + 1
    print('ok forced_replay_targets')


def test_sampler():
    m = model()
    rows = splits()['dev'][:6]
    batch = sampler.make_batch(rows, VOCAB, 'cpu')
    with torch.no_grad():
        o = m.eval().run(batch)
        g = sampler.sample_run(m, batch, greedy=True)
    assert torch.equal(g['ops'], o['prog'][0]) and torch.equal(g['a'], o['prog'][1]) and torch.equal(g['b'], o['prog'][2])
    assert torch.equal(g['ans'], o['lans'].argmax(-1)) and torch.equal(g['vals'], o['vals']) and torch.equal(g['valid'], o['valid'])
    print('  greedy sampler = Ledger.run (program, answer pointer, values)')
    cands = sampler.first_step_candidates(m, rows, VOCAB, 'cpu', k=8)
    for c in cands:
        assert len(c) == 8 and len(set((o_, min(a, b), max(a, b)) if o_ in P.COMM else (o_, a, b) for o_, a, b in c)) == 8 and all(o_ > 0 for o_, _, _ in c)
    tries, raw = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=32, temperature=1.5, seed=1)
    for tr, r in zip(tries, raw):
        assert 1 <= len(tr) <= 32 and r >= len(tr)
        assert len({P.raw_key(x.t) for x in tr}) == len(tr), 'duplicates kept'
        assert {x.branch for x in tr} - {-1} <= set(range(8))
    # branches: the forced first step of every branch really is that step
    first = [tr[0].t for tr in tries]
    for i, tr in enumerate(tries):
        for rec in tr:
            if rec.branch >= 0:
                op, a, b = cands[i][rec.branch]
                assert (rec.t.ops[0], rec.t.a[0], rec.t.b[0]) == (op, a, b)
    z = sampler.sample_run(m, batch, greedy=True, loops=0)
    assert int(z['ops'].abs().sum()) == 0 and torch.equal(z['vals'][:, R0:], torch.zeros_like(z['vals'][:, R0:]))
    l0, _ = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=8, temperature=1.0, seed=1, loops=0)
    assert all(len(t) >= 1 and all(x.t.ops == (0,) * 7 for x in t) for t in l0)
    t2, _ = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=32, temperature=1.5, seed=1)
    assert [[P.raw_key(x.t) for x in tr] for tr in tries] == [[P.raw_key(x.t) for x in tr] for tr in t2], 'same seed must give the same tries'
    print(f'  sampler on {len(rows)} puzzles: kept {[len(t) for t in tries]} of raw {raw}')
    print('ok sampler')


def test_scoreboard_and_gate():
    m = model()
    rows = splits()['dev'][:8]
    tries, raw = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=16, temperature=1.5, seed=2)
    gr = sampler.greedy_tries(m, rows, VOCAB, 'cpu')
    s = scoreboard.score_puzzles(rows, tries, raw, gr)
    for k in ('luck', 'reach4', 'reach32', 'distinct', 'stop_luck', 'aim', 'first_try', 'unresolved', 'dup_drop_rate'):
        assert k in s, k
    assert s['unresolved'] == 0 and 0 <= s['reach4'] <= s['reach32'] <= 1
    assert abs(scoreboard.reach_at(2, 32, 4) - (1 - 30 * 29 * 28 * 27 / (32 * 31 * 30 * 29))) < 1e-9
    # inject known tries: all solver programs accepted, twin tries counted as twin hits only
    inj = [[sampler.TryRec(t) for t in puzzles.solutions(r['nums'], r['target'])[:3]] for r in rows]
    si = scoreboard.score_puzzles(rows, inj)
    assert si['luck'] == 1.0 and si['reach32'] == 1.0 and si['twin_luck'] == 0.0 and si['aim'] == 1.0
    tw = [[sampler.TryRec(t) for t in puzzles.solutions(r['nums'], r['twin']['target'])[:3]] for r in rows]
    st = scoreboard.score_puzzles(rows, tw)
    assert st['luck'] == 0.0 and st['twin_luck'] == 1.0 and st['aim'] == -1.0
    prac = splits()['practice'][:8]
    ptr, _ = sampler.sample_tries(m, prac, VOCAB, 'cpu', n_tries=8, temperature=1.5, seed=3)
    nb, _ = sampler.sample_tries(m, rows, VOCAB, 'cpu', n_tries=16, temperature=1.5, seed=2, branch=0)
    g = scoreboard.dev_gate(rows, tries, raw, nb, (prac, ptr))
    assert g['verdict'].startswith('stop') and not g['signal_ok'] and 'nobranch_distinct_rules' in g and g['practice_solved'] == 0
    assert 'reach32' in g and 'distinct' in g                                          # reported, not gated
    # a passing gate: solver tries on every practice puzzle give signal; 4+ distinct rule-following programs per puzzle give sameness
    prac_inj = [[sampler.TryRec(t) for t in puzzles.solutions(r['nums'], r['target'])[:1]] for r in splits()['practice'][:120]]
    ok_rf = lambda r: [x for x in sampler.rule_follower_tries([r], 60, 1)[0] if scoreboard.judge_try(r, x, rules_only=True) == 'accept'][:12]
    many = [[sampler.TryRec(t) for t in puzzles.solutions(r['nums'], r['target'])[:1]] + ok_rf(r) for r in rows]
    gp = scoreboard.dev_gate(rows, many, None, None, (splits()['practice'][:120], prac_inj))
    assert gp['signal_ok'] and gp['sameness_ok'] and gp['verdict'] == 'pass' and gp['practice_solved'] == 120, gp
    assert scoreboard.dev_gate(rows, many, None, None, (splits()['practice'][:99], prac_inj[:99]))['verdict'].startswith('stop: signal')
    assert gp['aim_ok'] and gp['hit_given_rules'] >= scoreboard.AIM_MIN and 'rules_share' in gp
    # aim gate: rule-following tries that never hit fail it however many practice puzzles are solved; a low rules share alone never fails the gate
    miss = [[x for x in sampler.rule_follower_tries([r], 60, 1)[0] if scoreboard.judge_try(r, x, rules_only=True) == 'accept'
             and scoreboard.judge_try(r, x) != 'accept'][:12] for r in rows]
    gm = scoreboard.dev_gate(rows, miss, None, None, (splits()['practice'][:120], prac_inj))
    assert not gm['aim_ok'] and 'aim' in gm['verdict'] and gm['signal_ok'], gm
    thin = [t[:6] + [sampler.TryRec(Try((1,) * 7, (0,) * 7, (1,) * 7, 0)) for _ in range(60)] if i % 2 else t for i, t in enumerate(many)]
    gt = scoreboard.dev_gate(rows, thin, None, None, (splits()['practice'][:120], prac_inj))
    assert gt['rules_share'] < 0.5 and not gt.get('verdict', '').startswith('stop: signal'), gt
    # the value-blind rule follower reproduces the exact rules-only floor, and the aim check reports own / twin / rules
    rf = sampler.rule_follower_tries(splits()['dev'][:64], 32, 0)
    sr = scoreboard.score_puzzles(splits()['dev'][:64], rf)
    fl = sum(puzzles.rules_only_floor(r['nums'], r['target']) for r in splits()['dev'][:64]) / 64
    assert abs(sr['luck'] - fl) < 0.01 and sr['unresolved'] == 0, (sr['luck'], fl)
    aim = scoreboard.aim_check(m, rows, VOCAB, 'cpu', n_tries=8)
    assert set(aim) >= {'own', 'twin', 'rules', 'own_minus_rules_luck', 'own_minus_twin_luck'} and aim['rules']['luck'] >= 0
    les = scoreboard.lesions(m, rows, VOCAB, 'cpu', n_tries=8)
    assert set(les) == {'luck', 'donor_luck', 'rules_floor', 'donor_ok', 'loops0_luck'} and les['loops0_luck'] == 0 and les['donor_ok']
    print('  random B2 on 8 dev puzzles:', {k: round(v, 4) for k, v in s.items() if isinstance(v, float)})
    print('  gate:', g['verdict'], '| rule follower luck', round(sr['luck'], 4), 'vs exact floor', round(fl, 4))
    print('ok scoreboard_and_gate')


def test_arms():
    rng = random.Random(0)
    rows = splits()['practice'][:30]
    sol = lambda r, k: [sampler.TryRec(t) for t in puzzles.solutions(r['nums'], r['target'])[:k]]
    junk = lambda r: [sampler.TryRec(T_([(MUL, 0, 1), (ADD, R0, 2)], R0 + 1)), sampler.TryRec(T_([(ADD, 0, 1), (SUB, R0, 2)], R0 + 1)),
                      sampler.TryRec(T_([(SUB, 0, 1), (MUL, R0, 2)], R0 + 1)), sampler.TryRec(T_([(MUL, 2, 1), (SUB, R0, 0)], R0 + 1))]
    tries = [sol(r, 5) + junk(r) for r in rows]
    pool = [junk(r) + sol(r, 2) for r in rows]
    a = arms.build_arms(rows, tries, pool, seed=3)
    assert a['N'] == [] and a['W'] and len(a['W']) == sum(a['counts'].values()) and max(a['counts'].values()) <= 2
    for r in a['W']:
        assert checkers.verdict(r['nums'] + [r['target']], len(r['nums']), arms.record_try(r))[0] == 'accept'
    assert len(a['R']) == len(a['H']) == len(a['Hw']) <= len(a['W']) and len(a['PC']) == len(a['W'])
    for r_, h, hw in zip(a['R'], a['H'], a['Hw']):
        assert [arms.record_try(x) for x in (h, hw)] == [arms.record_try(r_)] * 2          # same tries, only the label differs
        made = P.pp._CACHE[r_['id']]['prog'][-1][3]
        assert h['target'] == made and hw['target'] != made and r_['source'] == h['source'] == hw['source']
        assert r_['target'] == next(x for x in rows if x['id'] == r_['source'])['target']
        assert r_['prompt'].split('Target')[0] == h['prompt'].split('Target')[0]
        assert checkers.verdict(h['nums'] + [h['target']], len(h['nums']), arms.record_try(h))[0] == 'accept'      # hindsight label is true
        assert checkers.verdict(hw['nums'] + [hw['target']], len(hw['nums']), arms.record_try(hw))[0] == 'reject'  # wrong label is false
    d = a['diag']
    assert 0 <= d['placebo_accepted_share'] <= 1 and d['n_R'] == len(a['R'])
    # R never reads the value: a pool in which every rule-following try misses the target still fills R to W's counts
    allmiss = [[sampler.TryRec(T_([(ADD, 0, 1), (ADD, R0, 2)], R0 + 1)), sampler.TryRec(T_([(SUB, 1, 0), (ADD, R0, 2)], R0 + 1))] for r in rows]
    a2 = arms.build_arms(rows, tries, allmiss, seed=3)
    assert a2['diag']['placebo_accepted_share'] < 0.25 and len(a2['R']) == len(a2['W']) and not a2['diag']['short']
    # placebo-too-close verdict: a pool of only accepted tries makes R mostly accepted tries
    assert arms.build_arms(rows, tries, [sol(r, 3) for r in rows], seed=3)['diag']['placebo_too_close']
    print(f"  W {len(a['W'])} (cap 2 per puzzle), R/H/H' {len(a['R'])}, PC {len(a['PC'])}; placebo accepted share {d['placebo_accepted_share']:.2f}")
    print('ok arms')


def test_sleep_plumbing():
    rng = random.Random(1)
    rows = splits()['practice'][:16]
    recs = [arms.record(r, puzzles.solutions(r['nums'], r['target'])[0], 'PC', 0) for r in rows]
    cfg = sleep.SleepCfg(updates=8, batch=8, lr=1e-3, warmup=2, max_visits=4)
    assert sleep.sleep(model(), [], [], VOCAB, cfg)['updates'] == 0                       # arm N
    try:
        sleep.sleep(model(), recs[:2], [], VOCAB, sleep.SleepCfg(updates=8, batch=8))
        raise AssertionError('visit cap not enforced')
    except ValueError as e:
        assert 'visits' in str(e)
    replay = [dict(id=f'rp{i}', prompt=f'What is {10 + i} + {i}?', answer=str(10 + 2 * i), accepted=[str(10 + 2 * i)], family='arith_bare', level=1,
                   stage=1, variant='', steps=[f'{10 + i} + {i} = {10 + 2 * i}']) for i in range(1, 12)]
    m = model()
    out = sleep.sleep(m, recs, replay, VOCAB, cfg)
    assert out['updates'] == 8 and max(out['visits'].values()) <= 4 and sum(out['visits'].values()) == 8 * 4
    assert max(out['visits'].values()) - min(out['visits'].get(r['id'], 0) for r in recs) <= 1, 'visits must be balanced'
    # resume from a checkpoint, then sleep: saved weights come back, and sleeping changes them
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'parent', 'checkpoint.pt')
        m0 = model(5)
        sleep.save_parent(m0, 'ledger', dict(copy=True, **SMALL), VOCAB, path, step=123)
        m1, v1, meta = sleep.load_parent(path)
        assert meta['step'] == 123 and all(torch.equal(a, b) for a, b in zip(m0.state_dict().values(), m1.state_dict().values()))
        before = [p.detach().clone() for p in m1.parameters()]
        sleep.sleep(m1, recs, replay, v1, cfg)
        assert any(not torch.equal(a, b) for a, b in zip(before, m1.parameters()))
    # the forced targets are learnable: loss on the records falls over a short sleep (tiny model, overfit)
    m = model(2)
    cfg2 = sleep.SleepCfg(updates=120, batch=16, lr=2e-3, warmup=5, max_visits=1000)
    out = sleep.sleep(m, recs, [], VOCAB, cfg2)
    first, last = sum(out['loss'][:10]) / 10, sum(out['loss'][-10:]) / 10
    assert last < first * 0.5, (first, last)
    print(f'  overfit loss {first:.2f} -> {last:.2f} over 120 updates')
    print('ok sleep_plumbing')


def _parent(luck, aim, reach4, stop, first, skills, donor=0.0, floor=0.02):
    return dict(luck=luck, aim=aim, reach4=reach4, stop_luck=stop, first_try=first, skills=skills, donor_luck=donor, rules_floor=floor,
                reach32=reach4, unresolved=0.0)


def test_marks_and_verdicts():
    from creative import marks
    rng = random.Random(0)
    j = lambda x: x + rng.uniform(-0.01, 0.01)
    def parents(w_gain, w_aim, first_gain, skills_drop=0.0, pc=0.3):
        out = []
        for _ in range(6):
            out.append(dict(N=_parent(j(.05), j(0), j(.2), j(.03), j(.10), .70), R=_parent(j(.06), j(0), j(.2), j(.03), j(.10), .70),
                            W=_parent(j(.05 + w_gain), j(w_aim), j(.2 + w_gain), j(.03 + w_gain), j(.10 + first_gain), .70 - skills_drop),
                            H=_parent(j(.1), j(.05), j(.3), j(.1), j(.1), .7), Hw=_parent(j(.05), j(0), j(.2), j(.03), j(.1), .7),
                            PC=_parent(j(.05 + pc), j(.1), j(.5), j(.2), j(.3), .7)))
        return out
    v, m = marks.c1_verdict(parents(.25, .2, .12), dict(gate_pass=True))
    assert v == 'PASS with first answers' and m['F1'], (v, m['_diffs'])
    assert marks.c1_verdict(parents(.25, .2, .0), dict(gate_pass=True))[0] == 'PASS, search only'
    assert marks.c1_verdict(parents(.25, .0, .0), dict(gate_pass=True))[0] == 'rules only'
    assert marks.c1_verdict(parents(.25, .2, .12, skills_drop=.05), dict(gate_pass=True))[0] == 'gain with harm'
    assert marks.c1_verdict(parents(.25, .2, .12), dict(gate_pass=False))[0] == 'gate stop'
    assert marks.c1_verdict(parents(.25, .2, .12), dict(gate_pass=True, placebo_too_close=True))[0] == 'placebo too close'
    assert marks.c1_verdict(parents(.25, .2, .12), dict(checkers_disagree=True))[0] == 'void'
    bad = parents(.25, .2, .12)
    for p in bad:
        p['W']['donor_luck'] = .5
    assert marks.c1_verdict(bad, dict(gate_pass=True))[0] == 'void'                       # donor lesion fails
    assert marks.c1_verdict(parents(.0, .0, .0), dict(gate_pass=True))[0] == 'proved wrong'
    flat = parents(.25, .2, .12)                                   # +3 points on a high base is under 1.6x: L1 must fail
    for p in flat:
        p['N']['luck'], p['W']['luck'], p['R']['luck'] = .20, .23, .20
    assert not marks.c1_marks(flat)['L1']
    assert marks.pc_gate(3.5, 1.7) and not marks.pc_gate(2.5, 2.0) and not marks.pc_gate(4.0, 1.4)
    c2 = [dict(N=dict(first_try=.10, reach4=.3, skills=.7), R=dict(first_try=.10, reach4=.3, skills=.7), W=dict(first_try=.30 + rng.uniform(-.01, .01), reach4=.4, skills=.69)) for _ in range(6)]
    assert marks.c2b_verdict(c2)[0] == 'PASS'
    c2[0]['W']['skills'] = .60
    assert marks.c2b_verdict(c2)[0] == 'not shown'
    print('ok marks_and_verdicts')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
