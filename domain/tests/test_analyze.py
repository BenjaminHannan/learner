"""Unit tests for domain/analyze.py: the Spearman correlation (ties included), and the DM1, DM2 and DM5 rules.

Run: python3 -m domain.tests.test_analyze   (or: pytest domain/tests/test_analyze.py)
The expected values were worked out by hand from the definitions in the design (sec. 5, addenda A8).
"""
import math

from domain.analyze import dm1_rule, dm2_rule, dm5_rule, ranks, scored_kinds, spearman


def close(a, b, tol=1e-9):
    assert a is not None and abs(a - b) <= tol, (a, b)


def test_spearman_perfect_and_reversed():
    close(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
    close(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)


def test_spearman_known_value_with_a_tie():
    # x = 1..5, y = 5, 6, 7, 8, 7. y ranks 1, 2, 3.5, 5, 3.5. Pearson of the ranks: 8 / sqrt(10 * 9.5) = 8 / sqrt(95).
    close(spearman([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]), 8 / math.sqrt(95))


def test_spearman_tie_in_x():
    # x ranks 1.5, 1.5, 3; y ranks 1, 2, 3. Pearson: 1.5 / sqrt(1.5 * 2) = sqrt(3) / 2.
    close(spearman([1, 1, 2], [1, 2, 3]), math.sqrt(3) / 2)


def test_ranks_average_ties():
    assert ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]
    assert ranks([5, 5, 5]) == [2.0, 2.0, 2.0]
    assert ranks([3, 1, 2]) == [3.0, 1.0, 2.0]


def test_spearman_undefined_cases():
    assert spearman([1], [2]) is None
    assert spearman([1, 1, 1], [1, 2, 3]) is None  # no variance in x


def test_dm5_pass_when_last_night_is_the_best():
    r = dm5_rule([10, 20, 25, 26])
    assert r['verdict'] == 'PASS' and r['stop_night'] == 3 and r['rise_last_night'] == 1.0 and r['nights_past_best'] == 0


def test_dm5_edges_three_below_best_and_rise_exactly_three_pass():
    assert dm5_rule([10, 20, 25, 22])['verdict'] == 'PASS'   # score(N) = best - 3 is allowed, rise -3 is allowed
    assert dm5_rule([0, 8, 11])['verdict'] == 'PASS'         # rise exactly 3 is allowed


def test_dm5_fail_more_than_three_below_best():
    assert dm5_rule([10, 20, 25, 21.9])['verdict'] == 'FAIL'  # 21.9 < 25 - 3, though the rise is only -3.1


def test_dm5_fail_rise_between_three_and_five():
    r = dm5_rule([10, 20, 24])  # rise 4: not proved wrong (needs > 5), but not a pass
    assert r['verdict'] == 'FAIL' and r['rise_at_most_3'] is False
    assert dm5_rule([0, 5.0])['verdict'] == 'FAIL'           # rise exactly 5 is not > 5


def test_dm5_proved_wrong_above_five():
    assert dm5_rule([10, 30, 36])['verdict'] == 'PROVED WRONG'  # rise 6


def test_dm5_needs_a_night():
    try:
        dm5_rule([10])
    except AssertionError:
        return
    raise AssertionError('dm5_rule should refuse a curve with no night after the parent')


def test_dm1_bars():
    assert dm1_rule(30)['verdict'] == 'PASS'
    assert dm1_rule(29.99)['verdict'] == 'FAIL'
    assert dm1_rule(10)['verdict'] == 'FAIL'
    assert dm1_rule(9.99)['verdict'] == 'PROVED WRONG'


def test_dm2_one_seed_never_proves_wrong():
    r = dm2_rule(1.0)
    assert r['verdict'] == 'FAIL' and 'one seed only' in r['note']
    assert dm2_rule(10)['verdict'] == 'PASS'
    assert dm2_rule(9.99)['verdict'] == 'FAIL' and dm2_rule(9.99)['note'] == ''


def test_dm5_proved_wrong_four_nights_past_best_with_dm3_failing():
    flat = [10, 30, 31, 30.5, 30.2, 30.1]        # best at night 2; stop at night 5 = 3 nights past the best: not yet
    r = dm5_rule(flat, dm3_not_pass=True)
    assert r['nights_past_best'] == 3 and r['verdict'] == 'PASS'
    long = [10, 30, 29, 28, 27, 26.5]            # best night 1, stop night 5: 4 nights past the best
    r = dm5_rule(long, dm3_not_pass=True)
    assert r['nights_past_best'] == 4 and r['verdict'] == 'PROVED WRONG'
    assert dm5_rule(long, dm3_not_pass=False)['verdict'] != 'PROVED WRONG'   # DM3 passing: the clause does not apply


def test_scored_kinds_follow_the_deviation_ops():
    class FakeTool:
        """help() and evaluate() shaped like domain/tools/sheet.py: evaluate gives (op, a, b, result) steps."""
        WORK = {'p': [('add', 1, 2, 3)], 'q': [('mod', 5, 2, 1)], 'r': [('cmp', 3, 2, 1), ('mul', 1, 4, 4)]}

        def help(self):
            return [{'kind': k, 'prompt': k} for k in self.WORK]

        def evaluate(self, prompt):
            return {'value': '0', 'steps': self.WORK[prompt]}
    events = [{'event': 'deviation', 'no_row_form_ops': ['cmp', 'mod']}]
    kinds, scored, unscored, ops, source = scored_kinds(FakeTool(), events)
    assert kinds == ['p', 'q', 'r'] and scored == ['p'] and sorted(unscored) == ['q', 'r']
    assert unscored['r']['no_row_form'] == ['cmp'] and ops == ['cmp', 'mod']
    # without a deviation event the fallback is the mode's NO_ROW_FORM list, which is the same here
    assert scored_kinds(FakeTool(), [])[1] == ['p']


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
        print('ok', t.__name__, flush=True)
    print(f'{len(tests)} tests passed', flush=True)
