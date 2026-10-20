"""Tests of gpu_run_5_marks.py (GPU-RUN-5 readout, PREREG-gpu-run-5.md): synthetic traces in e4floor.py's json format, one case per ruled outcome. No torch. python test_gpu_run_5_marks.py"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu_run_5_marks as g5                                                  # noqa: E402


def curve(seed, offset=0.0, wiggle=0.03):
    """A loss curve falling from about 18 to about 2.4, plus a deterministic per-trace wiggle (the run-to-run drift) and an optional systematic offset."""
    return [2.4 + 15.6 * math.exp(-i / 40.0) + offset + wiggle * math.sin(0.37 * i + 1.7 * seed) for i in range(300)]


def res(b_off=(0, 0, 0), d_off=(0, 0, 0), wig=0.03, order='BDBDBD', n=300):
    tr, k = [], {'B': 0, 'D': 0}
    for i, kind in enumerate(order):
        j = k[kind]; k[kind] += 1
        off = (b_off if kind == 'B' else d_off)[j]
        tr.append(dict(label=f'{kind}{j + 1}', kind=kind, losses=curve(i, off, wig)[:n]))
    return dict(traces=tr, K0=12, curve_updates=n)


def test_defer_inside_the_drift_passes():
    r = g5.readout(res())
    assert r['verdict'] == 'PASS' and r['pass_i_median_AB_le_max_AA'] and r['pass_ii_D_not_all_outside_B_same_side'] and not r['closed_for_good'], r


def test_systematic_offset_fails_and_proves_drift_wrong():
    r = g5.readout(res(d_off=(-0.04, -0.04, -0.04), wig=0.005))
    assert r['verdict'] == 'FAIL' and r['drift_proved_wrong'] and r['closed_for_good'] and 'closed for good' in r['allows'], r


def test_all_d_means_below_the_b_range_fails_even_when_median_ab_is_small():
    r = g5.readout(res(d_off=(-0.012, -0.012, -0.012), wig=0.03))
    assert r['D_all_below_B'] and r['verdict'] == 'FAIL', (r['B_window_means'], r['D_window_means'], r['median_AB'], r['max_AA'])


def test_large_drift_records_the_limit_as_too_tight_for_future_sheets_only():
    r = g5.readout(res(wig=0.08))
    assert r['limit_too_tight_for_future_B3G2'] and 'FUTURE' in r['note_0_02'], r['note_0_02']


def test_incomplete_run_is_a_fail():
    r = g5.readout(res(order='BDBDB'))
    assert r['verdict'] == 'FAIL' and not r['complete']
    r = g5.readout(res(n=250))
    assert r['verdict'] == 'FAIL' and not r['complete']


def test_wrong_order_is_incomplete():
    assert g5.readout(res(order='BBBDDD'))['verdict'] == 'FAIL'


def test_dd_is_reported_and_never_changes_the_verdict():
    r = g5.readout(res())
    assert len(r['DD_information_only']) == 3
    r2 = dict(r); assert r['verdict'] == g5.readout(res())['verdict']


def test_window_is_updates_101_to_300():
    a = [0.0] * 300; b = [0.0] * 100 + [1.0] * 200
    assert g5.mad(g5.window(a), g5.window(b)) == 1.0 and len(g5.window(a)) == 200


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    bad = 0
    for n, f in tests:
        try:
            f(); print('PASS', n)
        except Exception as e:                                           # noqa: BLE001
            bad += 1; print('FAIL', n, type(e).__name__, str(e)[:800])
    print(f'{len(tests) - bad} passed, {bad} failed, of {len(tests)}')
    return bad


if __name__ == '__main__':
    sys.exit(main())
