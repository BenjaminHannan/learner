"""Tests for dopamine.p1_sessions. Run: /tmp/claude-0/v/bin/python -m dopamine.tests.test_p1_sessions"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dopamine import p1_sessions as P   # noqa: E402
from domain.tools import sheet           # noqa: E402


def test_builder_valid():
    rng = random.Random(1)
    seen = set()
    for _ in range(600):
        n = rng.choice([3, 4])
        grid = {c: [rng.randint(1, 99) for _ in range(n)] for c in 'AB'}
        focus = P.random_focus(rng, n)
        assert 2 <= focus[2] - focus[1] + 1 <= 4 and focus[2] <= n
        for k in P.KINDS:
            pa = P.prompt_for(k, focus, grid)
            if pa is None:
                continue
            seen.add(k)
            assert pa[1] != '?' and sheet.evaluate(pa[0])['value'] == pa[1]
            assert len(sheet.evaluate(pa[0])['steps']) <= 7
    assert seen == set(P.KINDS), seen
    # hand check
    g = {'A': [4, 7, 2], 'B': [3, 5, 1]}
    assert P.prompt_for('SUM', ('A', 1, 3), g)[1] == '13'
    assert P.prompt_for('COUNTIF', ('A', 1, 2), g) == ('A: 4 7 2 | B: 3 5 1 ; =COUNTIF(A1:A2,">5")', '1')
    assert P.prompt_for('IF', ('A', 1, 2), g)[0].endswith('=IF(A1>B1,A2,B2)')
    assert P.prompt_for('IF', ('A', 1, 2), g)[1] == '7'


def test_habit_on_menu_and_deterministic():
    habit_hits = 0
    for i in range(300):
        s = P.make_session(P.TRAIN_SEED, i)
        assert s['L'] in (2, 3, 4) and len(s['requests']) == s['L']
        for t in range(s['L'] - 1):
            prev, nxt = s['requests'][t], s['requests'][t + 1]
            if nxt[0] == P.HABIT[prev[0]] and nxt[1] == prev[1]:
                habit_hits += 1
                assert nxt[2] in [m[1] for m in s['menus'][t]]
        assert P.make_session(P.TRAIN_SEED, i) == s
    assert habit_hits > 100, habit_hits
    assert [x[3] for x in P.all_sessions(smoke=True)][:3] == [P.make_session(P.TRAIN_SEED, j) for j in range(3)]
    assert P.all_sessions(True) == P.all_sessions(True)


def test_effort_accounting():
    assert P.reward(True, True) == 1 and P.reward(False, True) == -0.25 and P.reward(False, False) == -0.25
    assert P.reward(True, False) == -1
    L = 3
    assert L - 0 == 3                                        # NONE
    assert L - P.reward(True, True) == 2                     # one wanted+right
    assert L - (P.reward(True, True) + P.reward(False, True)) == 2.25
    assert L - P.reward(True, False) == 4                    # misled


def test_toy_sim():
    import numpy as np
    # 2 days x 1 session, 1 sealed; every round has 2 candidates: candidate 0 wanted & right when present
    rows = {}
    Z = toy_cache(np)
    arms, stats, L = P.simulate(Z)
    assert np.allclose(arms['NONE'], L)
    assert arms['ORACLE'].mean() < L.mean()


def toy_cache(np):
    rng = np.random.RandomState(0)
    prompts = [f'p{i}' for i in range(40)]
    F = rng.randn(40, 6).astype(np.float32)
    correct = np.ones(40, np.int8)
    sess_day, sess_split, sess_L = [], [], []
    rs, ri, rc, rn, ptr, cp, ck, cw = [], [], [], [], [0], [], [], []
    for s in range(14):
        split, day = (1, 0) if s >= 12 else (0, 1 + s // 2)
        sess_day.append(day), sess_split.append(split), sess_L.append(2)
        for t in range(2):
            rs.append(s), ri.append(t), rc.append(s), rn.append(-1)
            for j in range(2):
                cp.append(20 + (s * 2 + t + j) % 20), ck.append(j), cw.append(int(j == 0 and t == 0))
            ptr.append(len(cp))
    return dict(prompts=np.array(prompts), feats=F, correct=correct, sess_day=np.array(sess_day), sess_split=np.array(sess_split),
                sess_L=np.array(sess_L), round_sess=np.array(rs), round_idx=np.array(ri), round_cur=np.array(rc),
                round_next=np.array(rn), cand_ptr=np.array(ptr), cand_pid=np.array(cp), cand_kind=np.array(ck),
                cand_wanted=np.array(cw, np.int8), seed=np.array(0), ckpt=np.array('x'))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
