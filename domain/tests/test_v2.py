"""Tests for DM-S v2 (addendum A10): the wider practice maker (mode.vary, edits a to d) and the DM4 decontamination.

Seeded rng throughout, so each test is deterministic. Run: python3 -m domain.tests.test_v2
"""
import json
import os
import random
import re
from collections import Counter

from domain import audit, mode
from domain.tools import rpn as rpn_tool
from domain.tools import sheet as sheet_tool

HERE = os.path.dirname(os.path.abspath(__file__))
CONST = json.load(open(os.path.join(HERE, '..', 'constants.json')))
SHEET_EX = 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'
CELL_EX = 'A: 4 7 2 | B: 3 5 1 ; =A1+B2*2'
RPN_EX = 'rpn: 3 4 + 2 *'
CHARS = set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz :|;=()+-*/,<>"[]._')
NUM = re.compile(r'[0-9]+')
LETTER_TOKEN = re.compile(r'(?<![A-Za-z])([A-Z])(?=\d)')


def test_a_lmax_is_the_longest_help_run_plus_one():
    # addendum A10 (a): the longest digit run over ALL help prompts of the domain, plus digit_len_extra
    fake = [{'prompt': 'x 12345'}, {'prompt': 'y 1'}]
    assert mode.lmax_of(fake, 1) == 6
    assert mode.lmax_of(sheet_tool.help(), 1) == 2   # sheet help digits are one digit: 1 + 1
    assert mode.lmax_of(rpn_tool.help(), 1) == 3     # rpn help has 56 and 17: 2 + 1


def test_a_every_digit_run_gets_a_length_in_range_no_leading_zero():
    n_runs = len(NUM.findall(SHEET_EX))
    lengths = Counter()
    for seed in range(300):
        text, runs = mode.relength(SHEET_EX, random.Random(seed), 2)
        assert runs == n_runs and len(NUM.findall(text)) == n_runs
        for t in NUM.findall(text):
            assert 1 <= len(t) <= 2, t
            assert len(t) == 1 or t[0] != '0', t
            lengths[len(t)] += 1
    assert set(lengths) == {1, 2}, lengths   # both lengths occur


def test_a_zero_leading_digit_only_as_one_digit_zero():
    seen_zero = False
    for seed in range(2000):
        text, _ = mode.relength('rpn: 56 7 /', random.Random(seed), 3)
        for t in NUM.findall(text):
            assert t == '0' or t[0] != '0', text
            seen_zero = seen_zero or t == '0'
    assert seen_zero


def test_b_run_insert_or_delete_one_number_never_below_one():
    base = SHEET_EX.split(' ')
    kinds = Counter()
    for seed in range(300):
        out, c = mode.run_edit(SHEET_EX, random.Random(seed), 2, 1.0)
        assert c['runs_seen'] == 2 and c['run_insert'] + c['run_delete'] == 2, c
        kinds.update(c)
        toks = out.split(' ')
        assert len(toks) - len(base) == c['run_insert'] - c['run_delete']
        # everything that is not a number is untouched and in order
        assert [t for t in base if not NUM.fullmatch(t)] == [t for t in toks if not NUM.fullmatch(t)]
        # each run keeps at least one number: at least two numbers overall (one per run)
        assert sum(1 for t in toks if NUM.fullmatch(t)) >= 2
        for t in toks:
            if NUM.fullmatch(t):
                assert 1 <= len(t) <= 2 and (len(t) == 1 or t[0] != '0')
    assert kinds['run_insert'] > 0 and kinds['run_delete'] > 0, kinds


def test_b_insert_puts_one_new_number_at_a_position_in_the_run():
    run_text = 'x 3 4 +'
    orig = run_text.split(' ')
    found = False
    for seed in range(200):
        out, c = mode.run_edit(run_text, random.Random(seed), 2, 1.0)
        if c['run_insert'] == 1:
            toks = out.split(' ')
            assert any(toks[:i] + toks[i + 1:] == orig for i in range(len(toks))), toks
            found = True
            break
    assert found


def test_b_p_zero_changes_nothing():
    out, c = mode.run_edit(SHEET_EX, random.Random(1), 2, 0.0)
    assert out == SHEET_EX and c['run_insert'] == 0 and c['run_delete'] == 0 and c['runs_seen'] == 2


def test_c_rename_touches_only_letter_digit_tokens():
    # the SUM example has one letter-digit letter (A), so this example has two: A1 and B2 (letters A and B)
    labels_in = re.findall(r'[A-Z]:', CELL_EX)
    renamed = 0
    for seed in range(300):
        out, c = mode.letter_edit(CELL_EX, random.Random(seed), 1.0)
        assert re.findall(r'[A-Z]:', out) == labels_in   # labels such as A: stay
        assert len(out) == len(CELL_EX)
        changed = [i for i, (a, b) in enumerate(zip(CELL_EX, out)) if a != b]
        if not changed:
            continue
        renamed += 1
        token_letters = {m.start(1) for m in LETTER_TOKEN.finditer(CELL_EX)}
        assert set(changed) <= token_letters, changed        # only letter-digit tokens change
        letters_out = set(LETTER_TOKEN.findall(out))
        assert len(letters_out) == 1, letters_out            # every token with X is now Y
    assert renamed > 0


def test_c_no_rename_without_a_second_letter():
    out, c = mode.letter_edit('rpn: 3 4 +', random.Random(3), 1.0)
    assert out == 'rpn: 3 4 +' and c == Counter(letter_no_pair=1)
    out, c = mode.letter_edit('A: 4 | x: 2 ; =SUM(A1:A1)', random.Random(3), 1.0)
    assert c.get('letter_rename', 0) == 0 and c.get('letter_no_pair', 0) == 1 and out == 'A: 4 | x: 2 ; =SUM(A1:A1)'


def test_c_a12_a_letter_standing_alone_can_be_the_new_name():
    # addendum A12: the SUM help example has one token letter (A) and the label B; the rename may now use B
    seen = Counter()
    for seed in range(200):
        out, c = mode.letter_edit(SHEET_EX, random.Random(seed), 1.0)
        assert out.startswith('A: 4 7 2 | B: 3 5 1 ; ')         # labels and grid stay
        seen[out.split(';')[1].strip()] += 1
        assert c == Counter(letter_rename=1)
    assert set(seen) == {'=SUM(B1:B3)'}


def test_d_symbol_swap_uses_only_symbols_of_the_draft():
    in_syms = {ch for ch in SHEET_EX if not (ch.isalnum() or ch == ' ')}
    swaps = 0
    for seed in range(300):
        out, c = mode.symbol_edit(SHEET_EX, random.Random(seed), 1.0)
        assert c['symbol_swap'] == 1 and len(out) == len(SHEET_EX)
        diffs = [(a, b) for a, b in zip(SHEET_EX, out) if a != b]
        assert len(diffs) == 1                                 # one occurrence only
        a, b = diffs[0]
        assert mode.is_symbol(a) and mode.is_symbol(b) and b != a and b in in_syms, (a, b)
        swaps += 1
    assert swaps == 300


def test_d_no_swap_without_two_symbols_and_p_zero_changes_nothing():
    out, c = mode.symbol_edit('x 1 2', random.Random(0), 1.0)
    assert out == 'x 1 2' and c == Counter(symbol_no_pair=1)
    out, c = mode.symbol_edit(SHEET_EX, random.Random(0), 0.0)
    assert out == SHEET_EX and not c


def test_vary_applies_a_to_d_in_order_and_is_deterministic():
    a = mode.vary(SHEET_EX, random.Random(42), 2, 0.5)
    b = mode.vary(SHEET_EX, random.Random(42), 2, 0.5)
    assert a == b
    text, c = mode.vary(SHEET_EX, random.Random(7), 2, 0.0)
    assert c['digit_runs'] == len(NUM.findall(SHEET_EX)) and not any(c[e] for e in mode.EDITS)


def test_vary_chains_the_edits_so_logged_counts_match_the_text():
    # regression: each edit must start from the text the edit before it left. Every logged insert or delete must show
    # in the output: the number count moves by exactly inserts minus deletes, and the rename shows as one letter left.
    for example in (SHEET_EX, CELL_EX):
        base_nums = len(NUM.findall(example))
        for seed in range(300):
            out, c = mode.vary(example, random.Random(seed), 2, 1.0)
            assert len(NUM.findall(out)) == base_nums + c['run_insert'] - c['run_delete'], (out, dict(c))
            if c['letter_rename']:
                assert len(set(LETTER_TOKEN.findall(out))) == 1, out
    inserted = deleted = renamed = 0
    for seed in range(300):
        _, c = mode.vary(CELL_EX, random.Random(seed), 2, 1.0)
        inserted += c['run_insert']
        deleted += c['run_delete']
        renamed += c['letter_rename']
    assert inserted and deleted and renamed


def test_draft_logs_edit_counts_and_keeps_the_tool_check():
    ctx = dict(vchars=CHARS, cons=CONST, seen=set(), quiz_set=set(), lmax=mode.lmax_of(sheet_tool.help(), 1))
    edits, kept = Counter(), 0
    for s in range(400):
        item, why = mode.draft(sheet_tool, SHEET_EX, 'SUM', random.Random(s), ctx, edits=edits)
        if item is None:
            assert why in {'tool_?', 'no_steps', 'tool_mismatch', 'caps_calls', 'caps_operand', 'caps_entry', 'dup', 'vocab',
                           'caps_answer', 'caps_numbers', 'caps_prompt', 'tool_exception', 'tool_negative', 'bad_op'}, why
            continue
        kept += 1
        assert item['steps'] and set(item['edits']) <= set(mode.EDITS)
        assert sheet_tool.evaluate(item['prompt'])['value'] == item['value']
    assert edits['digit_runs'] == 400 * len(NUM.findall(SHEET_EX))
    assert kept > 0


def test_decontam_counts_panel_rows_that_are_training_prompts():
    panel_rows = [dict(id='a', prompt='rpn: 3 4 +', kind='a b +', split='near'),
                  dict(id='b', prompt='rpn: 9 4 -', kind='a b -', split='near'),
                  dict(id='c', prompt='rpn: 1 2 * 3 +', kind='a b c * +', split='far')]
    dec = audit.decontam(panel_rows, {'rpn: 3 4 +', 'rpn: 1 2 * 3 +', 'other'})
    assert dec['n'] == 3 and dec['dropped'] == 2 and dec['ids'] == ['a', 'c']
    assert dec['by_kind'] == {'a b +': 1, 'a b c * +': 1} and dec['by_split'] == {'near': 1, 'far': 1}
    assert dec['frac'] == round(2 / 3, 6)


def test_v2_audit_fails_only_above_two_percent_of_the_tool_panel():
    panel_rows = [dict(id=str(i), prompt=f'rpn: {i} 1 +', kind='a b +', split='near', domain='rpn') for i in range(100)]
    panel_map = {r['prompt']: f"rpn.v2.jsonl:{r['id']}" for r in panel_rows}
    clean = dict(id='own1', source='own', kind='a b +', prompt='rpn: 500 1 +', steps=['500 + 1 = 501'])

    def rows_with(k):
        # k training rows are copies of panel prompts (their steps are fine, so only the decontamination can fail the audit)
        return [dict(id=f'r{i}', source='tool', kind='a b +', prompt=f'rpn: {i} 1 +', steps=['x']) for i in range(k)] + [clean]

    at_bar = audit.audit_rows(rows_with(2), panel_map, panel_rows, '.v2')
    assert at_bar['decontam']['dropped'] == 2 and at_bar['decontam']['frac'] == 0.02 and at_bar['ok']
    assert [o['id'] for o in at_bar['panel_overlap']] == ['r0', 'r1']   # listed, not fatal under v2
    over = audit.audit_rows(rows_with(3), panel_map, panel_rows, '.v2')
    assert over['decontam']['dropped'] == 3 and not over['ok']
    # a zero-step row still fails a v2 audit (A5 holds for practice rows)
    bad = audit.audit_rows(rows_with(0) + [dict(id='z', source='tool', kind='a b +', prompt='rpn: 7 1 +', steps=[])],
                           panel_map, panel_rows, '.v2')
    assert bad['zero_steps'] == ['z'] and not bad['ok']


def test_panel_suffix_names_the_version():
    assert audit.panel_suffix('/x/sheet.v2.jsonl') == '.v2' and audit.panel_suffix('rpn.v2.jsonl') == '.v2'
    assert audit.panel_suffix('/x/sheet.jsonl') == '' and audit.panel_suffix('rpn.jsonl') == ''
    for bad in ('sheet.v3.jsonl', 'other.jsonl', 'sheet.v2.json'):
        try:
            audit.panel_suffix(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
        print('ok', t.__name__, flush=True)
    print(f'{len(tests)} tests passed', flush=True)
