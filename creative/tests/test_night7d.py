"""python3 -m pytest creative/tests/test_night7d.py   (CPU, instant): marks, proved-wrong and pick logic of Test VL on fake numbers."""
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
