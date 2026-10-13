"""Run: /tmp/claude-0/v/bin/python -m dopamine.tests.test_g_transfer"""
import numpy as np

from dopamine.g_transfer import judge, kind_rate_pred


def mk(sq, d0):
    return {'SELFQUIZ8K': {'within_kind_auc': sq}, 'D0': {'within_kind_auc': d0}}


def test_marks():
    j = judge(mk(0.70, 0.543), 0.5428, 200)
    assert j['PASS'] and not j['PROVED WRONG']
    j = judge(mk(0.60, 0.543), 0.5428, 200)          # below 0.62 absolute
    assert not j['PASS'] and not j['PROVED WRONG']
    j = judge(mk(0.62, 0.575), 0.5428, 200)          # 0.62 but < d0 + .05 ... and baseline off by .032
    assert j['verdict'].startswith('NOT JUDGED') and j['PASS'] is None
    j = judge(mk(0.553, 0.543), 0.5428, 200)         # <= d0 + 0.01 (0.553)
    assert j['PROVED WRONG'] and not j['PASS']
    j = judge(mk(0.62, 0.57), 0.57, 200)             # exactly +0.05 and 0.62
    assert j['PASS']


def test_kind_rate():
    y, k = np.array([1, 1, 0, 0, 1]), np.array(['a', 'a', 'a', 'b', 'b'])
    v = kind_rate_pred(y, k, np.array(['a', 'b', 'c']))
    assert np.allclose(v, [2 / 3, 0.5, 0.6])


if __name__ == '__main__':
    test_marks(); test_kind_rate(); print('ok')
