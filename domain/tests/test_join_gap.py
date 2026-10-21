from domain.far import join_gap as J

G = 'A: 4 7 2 | B: 3 5 1'


def test_split_plus_and_times():
    assert J.split_formula('SUM(A1:A3)+MAX(B1:B2)') == ('+', 'SUM(A1:A3)', 'MAX(B1:B2)', True)
    assert J.split_formula('(SUM(A1:A3))*(ABS(A1-B1))') == ('*', 'SUM(A1:A3)', 'ABS(A1-B1)', True)
    assert J.split_formula('(A1+B2*2)*(A1/B1)') == ('*', 'A1+B2*2', 'A1/B1', True)
    assert J.split_formula('A1/B1+MIN(A1:A2)') == ('+', 'A1/B1', 'MIN(A1:A2)', True)


def test_split_cell_arithmetic_atom_is_not_strict():
    assert J.split_formula('A1+B2*2+SUM(A1:A2)') == ('+', 'A1+B2*2', 'SUM(A1:A2)', False)
    assert J.split_formula('SUM(A1:A2)+A1+B2*2') == ('+', 'SUM(A1:A2)', 'A1+B2*2', False)


def test_split_refuses_unclean():
    assert J.split_formula('SUM(A1:A3)') is None
    assert J.split_formula('SUM(A1:A2)+MAX(A1:A2)+MIN(A1:A2)') is None
    assert J.split_formula('(A1+B1)*A2') is None   # K is a single bracketed piece but J has no pair
    assert J.split_formula('A1+B2*2') is None


def test_prompts():
    p = f'{G} ; =SUM(A1:A3)+MAX(B1:B2)'
    assert J.piece_prompt(p, 'MAX(B1:B2)') == f'{G} ; =MAX(B1:B2)'
    assert J.join_prompt(p, '+', '13', '5') == f'{G} ; =13+5'
    assert J.join_prompt(p, '*', '13', '5') == f'{G} ; =13*5'


def test_pair_type():
    assert J.pair_type('SUM(A1:A2)', 'MAX(B1:B2)') == 'range+range'
    assert J.pair_type('A1/B1', 'MAX(B1:B2)') == 'range+cell'
    assert J.pair_type('MAX(B1:B2)', 'ABS(A1-B1)') == 'range+cell'
    assert J.pair_type('A1/B1', 'A1+B2*2') == 'cell+cell'


def test_first_error():
    steps = [('add', '4', '7', '11'), ('add', '11', '2', '13'), ('max', '3', '5', '5'), ('add', '13', '5', '18')]
    ok = [('add', '7', '4', '11'), ('add', '2', '11', '13'), ('max', '5', '3', '5'), ('add', '5', '13', '18')]
    assert J.first_error(ok, steps, 2, 1) == 'answer'
    assert J.first_error([ok[0], ('add', '11', '3', '14')] + ok[2:], steps, 2, 1) == 'K'
    assert J.first_error(ok[:2] + [('min', '3', '5', '3'), ok[3]], steps, 2, 1) == 'J'
    assert J.first_error(ok[:3] + [('add', '13', '4', '17')], steps, 2, 1) == 'join'
    assert J.first_error(ok[:3], steps, 2, 1) == 'stopped/extra'
    assert J.first_error(ok + [ok[0]], steps, 2, 1) == 'stopped/extra'
    # sub is not commutative
    assert J.first_error([('sub', '3', '5', '2')], [('sub', '5', '3', '2')], 1, 0) == 'K'
