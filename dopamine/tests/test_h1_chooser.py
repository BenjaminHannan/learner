"""Tests for dopamine.h1_chooser. Run: /tmp/claude-0/v/bin/python -m dopamine.tests.test_h1_chooser"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dopamine import h1_chooser as H   # noqa: E402
from dopamine import p1_sessions as P  # noqa: E402


def test_sessions_same_as_p1_and_person_mix():
    for i in range(5):
        s, pt, th = H.make_h1_session(93006, i)
        assert s == P.make_session(93006, i) and pt in (0, 1) and len(th) == s['L']
        assert H.make_h1_session(93006, i) == (s, pt, th)
    pts, ths = [], []
    for i in range(600):
        _, pt, th = H.make_h1_session(93005, i)
        pts.append(pt), ths.extend(th)
    assert 0.44 < np.mean(pts) < 0.56 and 0.26 < np.mean(ths) < 0.34
    sm = H.all_h1_sessions(smoke=True)
    assert len(sm) == H.SMOKE_DAYS * H.SMOKE_PER_DAY + H.SMOKE_SEALED
    assert sm[0][3] == P.make_session(H.SMOKE_TRAIN_SEED, 0) and sm[-1][3] == P.make_session(H.SMOKE_SEALED_SEED, H.SMOKE_SEALED - 1)
    assert H.TRAIN_SEED == 93006 and H.SEALED_SEED == 93005 and (H.DAYS, H.PER_DAY, H.N_SEALED) == (20, 150, 400)


def toy_cache(days=3, per=6, sealed=24, d=8):
    rng = np.random.RandomState(0)
    n_sess = days * per + sealed
    F = rng.randn(2000, d).astype(np.float32)
    sess_day, sess_split, sess_L, ptype = [], [], [], []
    rs, ri, rc, rn, ptr, cp, ck, cw, thx = [], [], [], [], [0], [], [], [], []
    k = 0
    for s in range(n_sess):
        split, day = (1, 0) if s >= days * per else (0, 1 + s // per)
        sess_day.append(day), sess_split.append(split), sess_L.append(3), ptype.append(s % 2)
        for t in range(3):
            rs.append(s), ri.append(t), rc.append(k % 1000), rn.append(-1), thx.append(int(rng.rand() < 0.3))
            for j in range(3):
                cp.append(1000 + (k * 3 + j) % 1000), ck.append(j), cw.append(int(j == 0 and t < 2))
            ptr.append(len(cp))
            k += 1
    correct = (rng.rand(2000) < 0.5).astype(np.int8)
    return dict(prompts=np.array([f'p{i}' for i in range(2000)]), feats=F, correct=correct, sess_day=np.array(sess_day),
                sess_split=np.array(sess_split), sess_L=np.array(sess_L), sess_ptype=np.array(ptype), round_thanks=np.array(thx),
                round_sess=np.array(rs), round_idx=np.array(ri), round_cur=np.array(rc), round_next=np.array(rn),
                cand_ptr=np.array(ptr), cand_pid=np.array(cp), cand_kind=np.array(ck), cand_wanted=np.array(cw, np.int8),
                seed=np.array(0), ckpt=np.array('x'), smoke=np.array(True))


def test_rewards_and_effort():
    T = H.Tables(toy_cache())
    r = np.where(T.has & T.wt & T.rt)[0][0]          # wanted and right
    assert T.rew(np.array([1]), np.array([r]))[0] == 1.0
    assert abs(T.rew(np.array([2]), np.array([r]))[0] - (1.0 - 0.02)) < 1e-9
    assert T.rew(np.array([0]), np.array([r]))[0] == 0.0
    r = np.where(T.has & T.wt & ~T.rt)[0][0]         # wanted, model wrong: -1; tool right
    assert T.rew(np.array([1]), np.array([r]))[0] == -1.0 and abs(T.rew(np.array([2]), np.array([r]))[0] - 0.98) < 1e-9
    for ptype, cost in ((0, 0.25), (1, 1.0)):        # unwanted: person-dependent
        r = np.where(T.has & ~T.wt & (T.ptype == ptype))[0][0]
        assert T.rew(np.array([1]), np.array([r]))[0] == -cost and abs(T.rew(np.array([2]), np.array([r]))[0] + cost + 0.02) < 1e-9
    assert T.thanks_prev[T.ridx == 0].sum() == 0
    r = np.where(T.ridx == 1)[0][0]
    assert T.thanks_prev[r] == T.Z['round_thanks'][r - 1]


def test_run_all_toy():
    Z = toy_cache()
    res = H.run_all(Z, log=lambda *a: None)
    ea = res['mean_effort']['all']
    assert abs(ea['NONE'] - 3.0) < 1e-9 and ea['ORACLE'] < 3.0
    assert res['H1-3']['verdict'] in ('PASS', 'neither pass nor wrong', 'PROVED WRONG (on this seed)')
    # EAGER-TOOL by hand: sum over sealed rounds of tool reward of the top guess
    T = H.Tables(Z)
    sealed = np.where(Z['sess_split'] == 1)[0]
    rounds = np.where(T.round_day == 0)[0]
    eff = 3.0 - T.rew(np.full(len(rounds), 2), rounds).sum() / len(sealed)
    assert abs(eff - ea['EAGER-TOOL']) < 1e-9
    assert abs(res['mean_effort']['easygoing']['NONE'] - 3.0) < 1e-9
    assert 0 <= res['H1-4']['share_tool'] <= 1 or np.isnan(res['H1-4']['share_tool'])
    import tempfile
    d = tempfile.mkdtemp()
    H.write_outputs(res, d)
    assert os.path.exists(os.path.join(d, 'RESULT.json')) and os.path.exists(os.path.join(d, 'RESULT.md'))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
