"""python3 -m pytest creative/tests/test_night7d.py   (CPU, instant): marks, proved-wrong and pick logic of Test VL on fake numbers."""
import copy
from creative import night7d as N


def test_arm_marks():
    m = N.arm_marks(True, -1.9, 1.0, 5.0)
    assert m['passes'] and not m['proved_wrong']
    assert not N.arm_marks(True, -2.1, 1.0, 5.0)['passes']                  # first try too low
    assert not N.arm_marks(False, 0.0, 1.0, 5.0)['passes']                  # harm fails
    assert not N.arm_marks(True, 0, 4.0, 5.0)['proved_wrong']               # exactly 1.0 smaller: not wrong
    assert N.arm_marks(True, 0, 4.01, 5.0)['proved_wrong']


def _p(**arms):
    return {a: dict(passes=v[0], proved_wrong=v[1], drop=v[2]) for a, v in arms.items()}


def test_pick():
    both = {'s100': _p(V=(True, False, 2.0), L=(True, False, 1.0)), 's101': _p(V=(True, False, 2.0), L=(True, False, 1.5))}
    s, p = N.pick(both)
    assert s['V']['passes'] and s['L']['passes'] and p == 'L'
    neither = {'s100': _p(V=(False, True, 4.0), L=(False, False, 3.0)), 's101': _p(V=(False, True, 4.0), L=(False, True, 3.0))}
    s, p = N.pick(neither)
    assert p == 'L'                                                         # L is not proved wrong on every parent
    assert s['V']['proved_wrong'] and not s['L']['proved_wrong']
    assert N.pick({'s100': _p(V=(False, True, 4.0), L=(False, True, 3.0))})[1] is None
    mixed = {'s100': _p(V=(True, False, 2.0), L=(False, False, 1.0)), 's101': _p(V=(True, False, 2.0), L=(True, False, 1.0))}
    assert N.pick(mixed)[1] == 'V'                                          # L fails on one parent


def test_l2_marks_and_verdict():
    m = N.l2_marks(True, -1.9, 3.0)
    assert m['passes'] and not m['proved_wrong']
    assert not N.l2_marks(True, -2.1, 3.0)['passes']                       # multi-step first try too low
    assert not N.l2_marks(False, 5.0, 8.0)['passes']                       # harm fails
    assert N.l2_marks(True, -6.0, -0.1)['proved_wrong'] and not N.l2_marks(True, -6.0, 0.0)['proved_wrong']
    a, b = N.l2_marks(True, 0.0, 2.0), N.l2_marks(True, -8.0, -1.0)
    v = N.l2_verdict({'s100': a, 's101': b})
    assert not v['passes'] and not v['proved_wrong'] and 'passes' in v['disagree']
    v = N.l2_verdict({'s100': a, 's101': a})
    assert v['passes'] and not v['disagree'] and 'L64' in v['next']
    assert N.l2_verdict({'s100': b, 's101': b})['proved_wrong']


def test_l64_no_climb_rule():
    a = N.l2_marks(True, 0.0, 2.0, 1.0)                                    # exactly +1.0: not proved wrong by the no-climb rule
    assert a['proved_wrong_no_climb'] is False and N.l2_marks(True, 0.0, 2.0, 0.99)['proved_wrong_no_climb'] is True
    assert N.l2_marks(True, 0.0, 2.0)['proved_wrong_no_climb'] is None     # L2 itself: no comparison
    lo, hi = N.l2_marks(True, 0.0, 2.0, 0.5), N.l2_marks(True, 0.0, 2.0, 3.0)
    v = N.l2_verdict({'s100': lo, 's101': lo})
    assert v['proved_wrong_no_climb'] and v['proved_wrong'] and not v['proved_wrong_vs_W2']
    v = N.l2_verdict({'s100': lo, 's101': hi})                              # only one parent: not proved wrong
    assert not v['proved_wrong_no_climb'] and not v['proved_wrong'] and 'proved_wrong_no_climb' in v['disagree']
    v = N.l2_verdict({'s100': N.l2_marks(True, -6.0, -0.1, 3.0), 's101': N.l2_marks(True, -6.0, -0.1, 3.0)})   # rule 1 alone
    assert v['proved_wrong_vs_W2'] and v['proved_wrong'] and v['proved_wrong_no_climb'] is False
    assert N.l2_verdict({'s100': N.l2_marks(True, 0, 2), 's101': N.l2_marks(True, 0, 2)})['proved_wrong_no_climb'] is None


def test_sc_marks_and_verdict():
    m = N.sc_marks(True, -2.0, -3.0, 1.0, 3.0)
    assert m['passes'] and not m['proved_wrong']                            # boundaries inclusive; drop exactly 1.0 smaller is not wrong
    assert not N.sc_marks(True, -2.1, 0, 1.0, 3.0)['passes'] and not N.sc_marks(True, 0, -3.1, 1.0, 3.0)['passes'] and not N.sc_marks(False, 0, 0, 1.0, 3.0)['passes']
    assert N.sc_marks(True, 0, 0, 2.01, 3.0)['proved_wrong']
    w, g = N.sc_marks(True, 0, 0, 3.0, 3.0), N.sc_marks(True, 0, 0, 0.5, 3.0)
    assert N.sc_verdict({'a': w, 'b': w})['proved_wrong'] and not N.sc_verdict({'a': w, 'b': g})['proved_wrong'] and 'proved_wrong' in N.sc_verdict({'a': w, 'b': g})['disagree']
    assert N.sc_verdict({'a': g, 'b': g})['passes']


def test_sc_scorecard():
    n0, w1 = 100 / 256, 100 * 80 / 256                  # N' 1 of 256, W1 80 of 256 (s100): 0.9x needs 72.1 of 256
    m = N.sc_scorecard(100 * 73 / 256, w1, n0, True)
    assert m['passes'] and m['questions_short'] == 0 and not m['near_miss'] and not m['low']
    m = N.sc_scorecard(100 * 72 / 256, w1, n0, True)    # ratio 0.899: one question short = near miss, met
    assert m['questions_short'] == 1 and m['near_miss'] and m['mark2'] and m['passes'] and m['ratio'] < 0.9
    m = N.sc_scorecard(100 * 71 / 256, w1, n0, True)    # two short: fails
    assert m['questions_short'] == 2 and not m['mark2'] and not m['passes']
    assert not N.sc_scorecard(w1, w1, n0, False)['passes']
    assert N.sc_scorecard(15.0, 31.2, 0.4, True)['low'] and not N.sc_scorecard(16.0, 31.2, 0.4, True)['low']
    assert N.sc_scorecard(5.0, 0.4, 0.4, True)['low'] and not N.sc_scorecard(5.0, 0.4, 0.4, True)['passes']   # no W1 gain to compare with
    ok, low, harm = N.sc_scorecard(31.2, 31.2, 0.4, True), N.sc_scorecard(10.0, 31.2, 0.4, True), N.sc_scorecard(31.2, 31.2, 0.4, False)
    v = N.sc_scorecard_verdict
    assert v({'a': ok, 'b': ok})['passes'] and not v({'a': ok, 'b': ok})['proved_wrong']
    assert v({'a': ok, 'b': harm})['proved_wrong'] and not v({'a': ok, 'b': harm})['passes']      # harm on either parent
    assert not v({'a': ok, 'b': low})['proved_wrong'] and v({'a': low, 'b': low})['proved_wrong']  # low gain only on both

def test_sleep_sc_hook_off_is_sleep_and_row_losses():
    import os, pytest, torch
    from creative import sleep
    from custom_io.data import Dataset, collate, load_rows
    ck, tr = os.path.expanduser('~/c7d/s100/Nprime.pt'), os.path.expanduser('~/work/data/train.jsonl')
    if not (os.path.exists(ck) and os.path.exists(tr)):
        pytest.skip('no N-prime / train file')
    torch.set_num_threads(1)
    rows = load_rows(tr)[::4000][:48]
    recs, rep, ext = rows[:8], rows[8:40], rows[40:48]
    base, vocab, _ = sleep.load_parent(ck, 'cpu')
    cfg = sleep.SleepCfg(updates=3, batch=8, lr=1e-3, warmup=2, seed=3, max_visits=8)
    a, b = copy.deepcopy(base), copy.deepcopy(base)
    ra = sleep.sleep(a, recs, rep, vocab, cfg, 'cpu', replay_extra=ext)
    rb = N.sleep_sc(b, recs, rep, vocab, cfg, 'cpu', replay_extra=ext, select=False)
    assert ra['loss'] == rb['loss'] and ra['visits'] == rb['visits']
    assert all(torch.equal(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values())), 'hook off must reproduce sleep.sleep bit for bit'
    # the hook on changes only the skills slots: same records, and selection rounds fire
    c = copy.deepcopy(base)
    rc = N.sleep_sc(c, recs, rep, vocab, sleep.SleepCfg(updates=4, batch=8, lr=1e-3, warmup=2, seed=3, max_visits=8), 'cpu', replay_extra=ext, every=2, n_draw=16, n_pick=4)
    assert [r['step'] for r in rc['selection']] == [2] and len(rc['selection'][0]['families']) >= 1
    # per-row losses average to model.loss on the same batch
    base.eval()
    batch = collate([Dataset(rows[:8], vocab, strict=False)[i] for i in range(8)])
    o = base.loss(batch)
    assert abs(sum(N.row_losses(base, rows[:8], vocab)) / 8 - float((o[0] if isinstance(o, tuple) else o))) < 1e-4


def test_ap_marks_verdict_and_prefix():
    m = N.ap_marks(2.0, -2.0, True, 4.0)
    assert m['passes'] and not m['proved_wrong']                           # boundaries inclusive
    assert not N.ap_marks(1.9, 0, True, 4.0)['passes'] and not N.ap_marks(5, -2.1, True, 4.0)['passes'] and not N.ap_marks(5, 0, False, 4.0)['passes']
    assert N.ap_marks(0.0, 0, True, 0.99)['proved_wrong'] and not N.ap_marks(0.0, 0, True, 1.0)['proved_wrong']
    w, g = N.ap_marks(0, 0, True, 0.5), N.ap_marks(3, 0, True, 5.0)
    v = N.ap_verdict({'a': w, 'b': g})
    assert not v['passes'] and not v['proved_wrong'] and 'proved_wrong' in v['disagree'] and N.ap_verdict({'a': w, 'b': w})['proved_wrong'] and N.ap_verdict({'a': g, 'b': g})['passes']
    r = [{'id': 'W:x:0', 'prompt': 'p', 'answer': 'a'}, {'id': 'W:x:1', 'prompt': 'p', 'answer': 'b'}]
    c = N.prefixed_copies(r, 'n1|', register=False)
    assert [x['id'] for x in c] == ['n1|W:x:0', 'n1|W:x:1'] and r[0]['id'] == 'W:x:0' and c[0]['answer'] == 'a'


def test_ap_check_prefixed_targets():
    import os, pytest
    from custom_io.data import load_rows
    tr = os.path.expanduser('~/work/data/train.jsonl')
    if not os.path.exists(tr):
        pytest.skip('no train file')
    rows = load_rows(tr)[::5000][:20]
    from custom_io.models import progparse as pp
    for r in rows:                                                          # stand-in for fewshot._record's registration
        pp.row_targets(r)
    out = N.check_prefixed(rows, 'n2|')
    assert out['targets_equal'] and out['stale_entries'] == 0
    import pytest
    with pytest.raises(AssertionError):                                      # a second call finds the entries now there
        N.check_prefixed(rows, 'n2|')


def test_scl_scorecard_edges():
    n0, L = 100 / 256, 100 * 80 / 256                   # L gain ~ 78.9 questions-worth; 0.9x of it needs ~72.1 of 256 (as SC's W1)
    v, sc = N.sc_scorecard_verdict, N.sc_scorecard
    ok = sc(100 * 73 / 256, L, n0, True)
    near = sc(100 * 72 / 256, L, n0, True)              # one question short: met
    short2 = sc(100 * 71 / 256, L, n0, True)            # two short: fails
    harm = sc(L, L, n0, False)
    low = sc(10.0, L, n0, True)
    assert near['questions_short'] == 1 and near['mark2'] and near['passes'] and short2['questions_short'] == 2 and not short2['passes']
    assert v({'a': ok, 'b': near})['passes'] and not v({'a': ok, 'b': near})['proved_wrong']
    assert not v({'a': ok, 'b': short2})['passes'] and not v({'a': ok, 'b': short2})['proved_wrong']      # short, not low: neither
    assert v({'a': harm, 'b': ok})['proved_wrong'] and v({'a': ok, 'b': harm})['proved_wrong']            # harm on either parent
    assert v({'a': low, 'b': low})['proved_wrong'] and not v({'a': low, 'b': ok})['proved_wrong']         # low on both only
    assert N.SCL_LR == 1e-4 and N.SCL_VISITS == 32 and (N.SC_EVERY, N.SC_DRAW, N.SC_PICK) == (32, 1024, 256)


def test_scl_night_picking_off_is_vl_L_smoke():
    """_sc_night(select=False) at lr 1e-4 == sleep7d.sleep_on (VL's arm L call) bit for bit, on 8 real N-prime records (8 updates)."""
    import os, pytest, torch
    from creative import sleep, c2_stones, rules_real as R
    from creative.sleep7d import DATA, sleep_on, _limit
    ck, tr = os.path.expanduser('~/c7d/s100/Nprime.pt'), os.path.expanduser('~/work/data/train.jsonl')
    if not (os.path.exists(ck) and os.path.exists(tr) and os.path.isdir(os.path.expanduser('~/c7d/s1/s100'))):
        pytest.skip('no N-prime / train / S1 day')
    torch.set_num_threads(1)
    s3 = __import__('json').load(open(os.path.expanduser('~/c7d/s3/s100/s3.json')))
    base, vocab, _ = sleep.load_parent(ck, 'cpu')
    base.eval()
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), s3['args']['pool_limit']))
    recs, _ = N._w1_records(ck, 's100', os.path.expanduser('~/c7d/s1'), s3, pool, base, vocab, 'cpu')
    recs = recs[:8]
    replay = sleep.load_replay(tr, s3['args']['replay_n'], s3['seed'])[:64]
    warm = R.warm_records(R.load_split(DATA, 'warm'))
    a, ia = sleep_on(base, recs, vocab, replay, warm, 1e-4, 32, s3['seed'], 'cpu')
    b, ib = N._sc_night(base, recs, replay, warm, vocab, 1e-4, 32, s3['seed'], 'cpu', None, select=False)
    assert ia['updates'] == ib['updates'] == 8 and ia['last_loss'] == ib['last_loss']
    assert all(torch.equal(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values()))
