from domain.far import report
from domain.tools import sheet


def test_shape_and_label():
    assert report.shape_of('rpn: 50 53 +') == 'rpn: # # +'
    assert report.ckpt_label('/x/runs/sheet-s200-v7/night_4/checkpoint.pt') == 'sheet-s200-v7/night_4'


def test_scored_and_trainable():
    assert report.scored('sheet', 'SUM') and not report.scored('sheet', 'MOD')
    assert report.scored('rpn', 'a b +') and not report.scored('rpn', 'a b %')
    assert not report.is_trainable(sheet, 'A: 1 2 | B: 3 4 ; =MOD(A2,B1)')
    assert report.is_trainable(sheet, 'A: 1 2 | B: 3 4 ; =SUM(A1:A2)')


def test_coverage_sheet_and_rpn():
    c = report.coverage('sheet', [(1, 'A: 1 2 | B: 3 4 ; =SUM(A1:A2)'),
                                  (2, 'A: 1 2 3 4 5 | B: 3 4 ; =SUM(A1:A5)+B1')])
    assert c['pooled']['grid_ge5']['n'] == 1 and c['ring2']['two_kinds']['n'] == 1
    assert c['ring1']['range_ge5']['n'] == 0
    r = report.coverage('rpn', [(1, 'rpn: 1 2 +'), (1, 'rpn: 1 2 + 3 + 4 + 5 +')])
    assert r['pooled']['ops_ge4']['n'] == 1 and r['pooled']['ops_hist'] == {'1': 1, '4': 1}


def test_acc():
    assert report.acc([{'id': 'a'}, {'id': 'b'}], {'a': 1, 'b': 0}) == dict(n=2, hits=1, pct=50.0)
