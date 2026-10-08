"""python3 -m pytest creative/tests/test_drift7d.py   (CPU, instant): the mark logic of the 2x2 drift check on fake drops."""
from creative import drift7d as D


def _d(a, b, c, e):
    return {'lr1e-3_reused': a, 'lr1e-3_fresh': b, 'lr1e-4_reused': c, 'lr1e-4_fresh': e}


def test_marks():
    m = D.marks(_d(5.6, 4.0, 0.2, 0.5))                     # drift: only lr 1e-3 hurts, fresh rows too
    assert m['drift_confirmed'] and not m['overfit_confirmed'] and not m['proved_wrong']
    m = D.marks(_d(5.6, 0.5, 0.2, 0.1))                     # overfit: only the reused rows hurt
    assert m['overfit_confirmed'] and not m['drift_confirmed'] and not m['proved_wrong']
    m = D.marks(_d(0.4, 0.8, 0.2, 0.1))                     # nothing separates the cells
    assert m['proved_wrong'] and not m['drift_confirmed'] and not m['overfit_confirmed']
    m = D.marks(_d(5.0, 5.0, 5.0, 5.5))                     # all hurt alike: neither named suspect, but the cells do not differ
    assert not m['drift_confirmed'] and not m['overfit_confirmed'] and m['proved_wrong']
    assert D.marks(_d(5.0, 3.0, 1.0, 1.0))['drift_confirmed']                  # boundaries are inclusive
    assert not D.marks(_d(5.0, 3.0, 1.01, 1.0))['drift_confirmed']
    assert D.marks(_d(3.0, 1.0, 0.0, 0.0))['overfit_confirmed']
