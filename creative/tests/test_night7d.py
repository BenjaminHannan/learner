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
