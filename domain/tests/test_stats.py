"""Tests for domain/tools/stats.py.

Run: python3 -m domain.tests.test_stats   (or: pytest domain/tests/test_stats.py)
The expected answers and step ops below were worked out by hand, not taken from the tool.
"""
import unittest

from domain.tools import stats

# The ops of each help example's steps, in order, worked out by hand.
HELP_OPS = {
    'product': ['mul', 'mul'],                                       # 6 * 3 * 4
    'half the sum': ['add', 'add', 'div'],                           # 12 + 4 + 8, then / 2
    'largest plus smallest': ['max', 'max', 'min', 'min', 'add'],    # 84 + 7
    'largest times smallest': ['max', 'max', 'min', 'min', 'mul'],   # 9 * 4
    'twice the largest': ['max', 'max', 'max', 'mul'],               # 84 * 2
    'twice the smallest': ['min', 'min', 'mul'],                     # 6 * 2
    'sum minus largest': ['add', 'add', 'max', 'max', 'sub'],        # 47 - 30
}


class HelpExamples(unittest.TestCase):
    def test_help_lists_the_seven_kinds_in_order(self):
        self.assertEqual([h['kind'] for h in stats.help()], list(HELP_OPS))
        for h in stats.help():
            self.assertEqual(set(h), {'kind', 'prompt', 'answer'})

    def test_every_help_example_gives_its_answer(self):
        for kind, prompt, answer in stats.HELP:
            with self.subTest(kind=kind):
                self.assertEqual(stats.evaluate(prompt)['value'], answer)

    def test_every_help_example_has_the_listed_ops(self):
        for kind, prompt, _ in stats.HELP:
            with self.subTest(kind=kind):
                ops = [step[0] for step in stats.evaluate(prompt)['steps']]
                self.assertEqual(ops, HELP_OPS[kind])


class Rejects(unittest.TestCase):
    def test_half_the_sum_of_an_odd_sum_is_question_mark(self):
        # 1 + 2 = 3 is odd, so the / 2 step is not exact
        self.assertEqual(stats.evaluate('Numbers: 1, 2. What is half the sum of the numbers?')['value'], '?')

    def test_bad_prompts_give_question_mark(self):
        cases = {
            'wrong question': 'Numbers: 6, 3, 4. What is the sum of the numbers?',
            'missing period': 'Numbers: 6, 3, 4 What is the product of the numbers?',
            'one number only': 'Numbers: 6. What is the product of the numbers?',
            'no space after the colon': 'Numbers? 1, 2. What is the product of the numbers?',
            'ten-digit number': 'Numbers: 1234567890, 2. What is the product of the numbers?',
        }
        for name, prompt in cases.items():
            with self.subTest(name):
                self.assertEqual(stats.evaluate(prompt)['value'], '?')

    def test_not_a_string_gives_question_mark(self):
        self.assertEqual(stats.evaluate(None), {'value': '?', 'steps': []})


if __name__ == '__main__':
    unittest.main()
