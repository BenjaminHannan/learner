"""L12 (domain/far/MARKS-L12-2026-10-12.md): join_last_draft's pick argument, the widened-ring pick, the census-l12 report."""
import hashlib
import random

from domain import mode
from domain.far import joinlast
from domain.far import learn_probe as L
from domain.tests.test_l10_joinlast import CONS, KINDS, ctx_for, run
from domain.tools import sheet

L10_RUN11_SHA = '75979ff6e6bd2c83fe1700f26e8b53710a82694f5b7114468b3fe1f803bd24a6'   # sha256 of run(11, 300) with pick=None; re-pinned after the A25 merge (word_edit draws once per vary; was d9cf97ae7f20... before)


def test_pick_none_is_l10():
    out, _ = run(11, 300)
    got = hashlib.sha256(repr([(i and (i['prompt'], i['kind'], i['value']), w) for i, w in out]).encode()).hexdigest()
    assert got == L10_RUN11_SHA


def test_pick_is_used():
    helps = sheet.help()
    calls, ctx, rng = [], ctx_for(), random.Random(3)
    prompt = 'A: 4 7 2 5 9 1 | B: 3 5 1 8 2 6 ; =SUM(A1:A6)'

    def pick(r):
        calls.append(r)
        return prompt, 'SUM'
    kept = 0
    for _ in range(200):
        item, why = joinlast.join_last_draft(sheet, helps, KINDS, rng, ctx, pick=pick)
        if item:
            kept += 1
            assert item['kind'] == 'SUM' and item['ring'] == 'joinlast'
            ctx['seen'].add(item['prompt'])
    assert len(calls) == 200 and all(c is rng for c in calls) and kept > 0


def test_l12_pick_and_census_keys():
    ctx = ctx_for()
    pick, wst = L.l12_pick(sheet, sheet.help(), ctx, dict(CONS, widen_ring_max=60), 'x-widen')
    rng = random.Random(1)
    kinds = [pick(rng)[1] for _ in range(2 * len(L.SP.SCORED))]
    assert kinds == list(L.SP.SCORED) * 2 and pick.last_ring in (1, 2, 3)
    cen = L.Census12()
    for _ in range(120):
        item, why = joinlast.join_last_draft(sheet, sheet.help(), KINDS, rng, ctx, pick=pick)
        cen.add(item, why, pick.last_ring)
    r = cen.report()
    assert r['attempts'] == 120 and 'two_or_more_far' in r['share'] and 'grid_rows' in r['share']
    assert abs(sum(r['ring_attempts'].values()) - 1) < 1e-9
    assert sum(r['ring_kept_counts'].values()) == r['kept']
    cen.print()
    assert L.far_factors('A: 1 2 3 4 5 6 | B: 1 ; =SUM(A1:A6)') >= 2
