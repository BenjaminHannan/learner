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
