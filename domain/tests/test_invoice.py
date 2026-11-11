"""Tests for domain/tools/invoice.py.

Run: python3 -m domain.tests.test_invoice   (or: pytest domain/tests/test_invoice.py)
The expected values below were worked out by hand, not taken from the tool.
"""
import unittest

from domain.tools import BIG, invoice

# The calculator ops each help example runs, in order (3 rows each).
HELP_OPS = {
    'price sum': ['add', 'add'],                  # 12 + 10 + 7
    'two rows cost': ['mul', 'mul', 'add'],       # 3*9, 2*11, then add
    'largest qty': ['max', 'max'],                # 7, 4, 9
    'smallest price': ['min', 'min'],             # 6, 10, 4
    'cost difference': ['mul', 'mul', 'sub'],     # 6*9, 4*5, then sub
    'twice qty sum': ['add', 'add', 'mul'],       # 2+5+3, then times 2
}

ZIP = 'Row zipper: qty 6, price 12. Row hammer: qty 2, price 10. Row pocket: qty 4, price 7. '

# Each must give '?': a parse error, an unknown or repeated name, a bad question, a big number, or a negative step.
BAD = {
    'cost difference, row a costs less': 'Row anchor: qty 1, price 9. Row kettle: qty 4, price 5. Row bridge: qty 2, price 8. '
                                         'How much more is the cost of row anchor than row kettle?',   # 9 < 20
    'unknown row name': ZIP + 'What is the total cost of rows zipper and nail?',
    'same name twice in the rows': 'Row zipper: qty 6, price 12. Row zipper: qty 2, price 10. '
                                   'What is the total price over all rows?',
    'same name twice in the question': ZIP + 'What is the total cost of rows zipper and zipper?',
    'changed question word': ZIP + 'Which is the total price over all rows?',
    'symbol swapped': 'Row zipper; qty 6, price 12. Row hammer: qty 2, price 10. Row pocket: qty 4, price 7. '
                      'What is the total price over all rows?',
    'one row only': 'Row zipper: qty 6, price 12. What is the total price over all rows?',
    'number too large': f'Row zipper: qty {BIG}, price 12. Row hammer: qty 2, price 10. '
                        'What is the total price over all rows?',
    'missing full stop after a row': 'Row zipper: qty 6, price 12 Row hammer: qty 2, price 10. '
                                     'What is the total price over all rows?',
    'two spaces before the question': ZIP + ' What is the total price over all rows?',
    'trailing space': ZIP + 'What is the total price over all rows? ',
    'capital letter in a row name': ZIP.replace('zipper', 'Zipper') + 'What is the total price over all rows?',
}


class InvoiceTests(unittest.TestCase):
    def test_help_examples_give_their_answers_and_ops(self):
        helps = invoice.help()
        self.assertEqual([h['kind'] for h in helps], list(HELP_OPS))
        for h in helps:
            with self.subTest(kind=h['kind']):
                res = invoice.evaluate(h['prompt'])
                self.assertEqual(res['value'], h['answer'])
                self.assertEqual([s[0] for s in res['steps']], HELP_OPS[h['kind']])

    def test_steps_show_the_working(self):
        res = invoice.evaluate(invoice.help()[1]['prompt'])          # two rows cost: candle (3, 9) and mitten (2, 11)
        self.assertEqual(res['steps'], [('mul', '3', '9', '27'), ('mul', '2', '11', '22'), ('add', '27', '22', '49')])
        res = invoice.evaluate(invoice.help()[4]['prompt'])          # cost difference: anchor (6, 9) and kettle (4, 5)
        self.assertEqual(res['steps'], [('mul', '6', '9', '54'), ('mul', '4', '5', '20'), ('sub', '54', '20', '34')])

    def test_two_rows_cost_takes_the_first_named_row_as_a(self):
        # Rows d (7, 8) and a (1, 2) with the question naming d first: d's cost is computed first.
        p = ('Row a: qty 1, price 2. Row b: qty 3, price 4. Row c: qty 5, price 6. Row d: qty 7, price 8. '
             'What is the total cost of rows d and a?')
        res = invoice.evaluate(p)
        self.assertEqual(res['value'], '58')
        self.assertEqual(res['steps'], [('mul', '7', '8', '56'), ('mul', '1', '2', '2'), ('add', '56', '2', '58')])

    def test_four_rows_use_all_of_them_in_order(self):
        p = ('Row a: qty 1, price 2. Row b: qty 3, price 4. Row c: qty 5, price 6. Row d: qty 7, price 8. '
             'What is twice the total qty over all rows?')
        res = invoice.evaluate(p)
        self.assertEqual(res['value'], '32')                          # 1+3+5+7 = 16, times 2
        self.assertEqual([s[0] for s in res['steps']], ['add', 'add', 'add', 'mul'])

    def test_bad_prompts_give_question_mark(self):
        for label, p in BAD.items():
            with self.subTest(case=label):
                self.assertEqual(invoice.evaluate(p)['value'], '?')

    def test_non_string_gives_question_mark(self):
        self.assertEqual(invoice.evaluate(None), {'value': '?', 'steps': []})


if __name__ == '__main__':
    unittest.main()
