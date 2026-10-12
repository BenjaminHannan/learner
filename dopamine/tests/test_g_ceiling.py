"""Run: /tmp/claude-0/v/bin/python -m dopamine.tests.test_g_ceiling"""
import numpy as np

from dopamine.g_ceiling import (call_features, diag_features, nested_subsets, process_flags, stratified_folds)
from dopamine.d0_guess import within_kind_auc


def test_folds():
    kind = np.array(['a'] * 53 + ['b'] * 31 + ['c'] * 17)
    f = stratified_folds(kind)
    assert f.shape == kind.shape and set(f) == set(range(5))
    for k in 'abc':   # each kind spread evenly over folds
        c = np.bincount(f[kind == k], minlength=5)
        assert c.max() - c.min() <= 1, (k, c)
    assert (stratified_folds(kind) == f).all()
    # every row is held out exactly once
    held = np.zeros(len(kind), int)
    for i in range(5):
        held[f == i] += 1
    assert (held == 1).all()


def test_nested():
    s = nested_subsets(5000, sizes=(100, 400, 2000, 9000))
    assert set(s[100]) <= set(s[400]) <= set(s[2000]) <= set(s[9000])
    assert len(s[100]) == 100 and len(s[2000]) == 2000 and len(s[9000]) == 5000


def test_within_kind_auc():
    rs = np.random.RandomState(0)
    # kind a: score perfectly ranks (AUC 1); kind b: reversed (AUC 0); kind c: too few wrong (skipped)
    ya = np.array([1] * 20 + [0] * 20)
    yb = np.array([1] * 30 + [0] * 30)
    yc = np.array([1] * 40 + [0] * 5)
    y = np.concatenate([ya, yb, yc])
    v = np.concatenate([ya + 0.0, 1.0 - yb, rs.rand(45)])
    kind = np.array(['a'] * 40 + ['b'] * 60 + ['c'] * 45)
    wk, groups, rows = within_kind_auc(y, v, kind, np.zeros(len(y), int))
    assert groups == 2 and rows == 100
    assert abs(wk - (1.0 * 40 + 0.0 * 60) / 100) < 1e-12, wk


def test_process_flags():
    flags, nd = process_flags('12', ['12', '13', '12', '12'])
    assert flags == [1, 0, 1, 1] and nd == 2
    flags, nd = process_flags('5', ['5', '5', '5', '5'])
    assert flags == [1, 1, 1, 1] and nd == 1
    flags, nd = process_flags('1', ['2', '3', '4', '5'])
    assert flags == [0, 0, 0, 0] and nd == 5


def test_call_and_diag():
    assert call_features([(0, '+', '1', '2', '3'), (1, '*', '3', '4', '12')], '12') == (2, 1)
    assert call_features([(0, '+', '1', '2', '3')], '12') == (1, 0)
    assert call_features([], '12') == (0, 0)
    assert diag_features('A: 12 345 | =SUM(A1:A3)') == (4, 3)
    assert diag_features('no digits') == (0, 0)


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            print('ok', name)
