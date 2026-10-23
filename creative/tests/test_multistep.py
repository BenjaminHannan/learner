"""python3 -m pytest creative/tests/test_multistep.py   (CPU, a few minutes; tiny random B2)
Dream school (strict filter, lengths to 5, ids), run_creative's school path, the multistep driver's verdict. Never opens creative/data/c2/test.jsonl."""
import inspect
import json

import pytest
import torch

from creative import dream2 as D, multistep as MS, rules_real as R
from creative.programs import R0, Try
from creative.tests.test_dream2 import _tiny_workdir
from v1 import creative_sleep as CS

Q = 2 * D.K_EX
C10 = D.CONST_SLOTS[D.CONST_VALUES.index(10)]


def test_strict_filter_recognises_held_out_forms():
    affine = Try.make([(1, Q, Q), (1, R0, Q), (1, R0 + 1, C10)], R0 + 2)     # x+x, +x, +10 = 3x + 10 = affine(3, 10)
    sq = Try.make([(3, Q, Q)], R0)
    ld = Try.make([(5, Q, C10)], R0)
    dbl = Try.make([(1, Q, C10), (3, R0, D.CONST_SLOTS[1])], R0 + 1)         # (x+10)*2 is not double_add (B in 3..9)
    near = Try.make([(1, Q, Q), (1, R0, Q), (1, R0 + 1, D.CONST_SLOTS[1])], R0 + 2)   # 3x + 2: B=2 is outside affine's PARAMS
    assert D.is_held_out_form(affine, Q) and D.is_held_out_form(sq, Q) and D.is_held_out_form(ld, Q)
    assert not D.is_held_out_form(dbl, Q) and not D.is_held_out_form(near, Q)


def test_strict_removes_held_out_forms_from_a_draw():
    loose = D.dream_rows_c2(1500, 0, max_steps=1, check_real=False, night=5)
    assert D.kind_overlap(loose)['any_held_out_same_function'] > 0                  # square / last_digit do appear among 1-step dreams
    st = {}
    tight = D.dream_rows_c2(300, 0, max_steps=1, check_real=False, night=5, strict=True, stats=st)
    assert D.kind_overlap(tight)['any_held_out_same_function'] == 0 and st[1]['strict_rejected'] > 0


def test_default_is_bit_identical_and_lengths_to_5_balanced():
    a, b = D.dream_rows_c2(40, 3), D.dream_rows_c2(40, 3, strict=False)
    assert [(r['id'], r['prompt']) for r in a] == [(r['id'], r['prompt']) for r in b]
    st = {}
    rows = D.dream_rows_c2(50, 1, max_steps=5, check_real=False, stats=st, night=9)
    assert [sum(r['dream']['length'] == L for r in rows) for L in range(1, 6)] == [10] * 5
    assert all(len(__import__('creative.programs', fromlist=['cone']).cone(Try.make(r['dream']['steps'], r['dream']['ans']))) == r['dream']['length'] for r in rows)
    assert all(st[L]['accepted'] == 10 and st[L]['draws'] >= 10 for L in range(1, 6))


def test_ids_unique_across_phases_nights_and_shards():
    sets = [D.dream_rows_par(20, 0, (), night=n, max_steps=m, shards=2, workers=2) for n, m in ((900, 5), (910, 5), (921, 2), (922, 3), (923, 5))]
    sets += [D.dream_rows_c2(20, 0, night=n, max_steps=5) for n in (1, 2)]
    ids = [r['id'] for s in sets for r in s]
    assert len(ids) == len(set(ids)) == 140
    from custom_io.models import progparse as pp
    assert all(i in pp._CACHE for i in ids)
    assert [sum(r['dream']['length'] == L for r in sets[0]) for L in range(1, 6)] == [4] * 5


def test_par_cache_roundtrip(tmp_path):
    a = D.dream_rows_par(20, 4, (), night=900, max_steps=5, shards=2, workers=1, cache_dir=str(tmp_path))
    from custom_io.models import progparse as pp
    for r in a:
        pp._CACHE.pop(r['id'], None)
    b = D.dream_rows_par(20, 4, (), night=900, max_steps=5, shards=2, workers=1, cache_dir=str(tmp_path))
    assert [(r['id'], r['prompt']) for r in a] == [(r['id'], r['prompt']) for r in b] and all(r['id'] in pp._CACHE for r in b)


def test_school_off_path_and_school_on_end_to_end(tmp_path):
    sig = inspect.signature(CS.run_creative).parameters
    assert sig['school'].default is None and sig['dream2'].default == 0 and sig['dream2_strict'].default is False
    ck, sk = _tiny_workdir(tmp_path)
    common = dict(device='cpu', seed=0, pool_limit=6, dev_limit=4, n1=2, n2=2, T=1.0, updates_cap=2)
    off = CS.run_creative(str(tmp_path / 'off'), ck, sk, None, **common)
    assert 'school' not in off and 'school' not in off['stages'] and not (tmp_path / 'off' / 'school.pt').exists()
    on = CS.run_creative(str(tmp_path / 'on'), ck, sk, None, school=dict(n=96, max_steps=5, strict=True, curriculum=True, visits=2, lr=3e-4), dream2=10, dream2_max_steps=5, dream2_strict=True, **common)
    assert 'school' in on['stages'] and (tmp_path / 'on' / 'school.pt').exists() and len(on['school']['phases']) == 3
    assert [p['max_steps'] for p in on['school']['phases']] == [2, 3, 5] and sum(p['n'] for p in on['school']['phases']) == 96
    assert json.load(open(tmp_path / 'on' / 'train.json'))['school']['phases'][0]['final_loss'] is not None
    assert (tmp_path / 'on' / 'W2.pt').exists() or on.get('stop')


def test_oracle_records_use_pool_reference_programs():
    pool = [r for r in R.load_split(D.DATA, 'pool') if r['kind'] in ('square', 'last_digit')][:4]
    recs, skipped = CS.oracle_records(pool)
    assert skipped == 0 and len(recs) == 4 and all(r['id'].startswith('OR:') and r['answer'] == p['answer'] for r, p in zip(recs, pool))
    with pytest.raises(AssertionError):
        CS.oracle_records([dict(pool[0], kind='add')])


def test_sealed_test_split_is_refused():
    with pytest.raises(PermissionError):
        CS.dev_report('nowhere.pt', split='test')


def test_verdict_on_synthetic_numbers():
    A = lambda h, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm)
    v = MS.verdict(dict(base=A(0.02), dream2=A(0.02), school5=A(0.30), school5_strict=A(0.25), school5_curr=A(0.40), oracle=A(0.9)))
    assert v['pass'] and v['not_leakage'] and v['curriculum_helps'] and not v['proved_wrong']
    assert any('oracle' in l and 'REPORT ONLY' in l for l in v['lines'])
    v = MS.verdict(dict(base=A(0.02), school5=A(0.30), school5_strict=A(0.10), school5_curr=A(0.32)))
    assert v['pass'] and v['not_leakage'] is False and v['curriculum_helps'] is False
    v = MS.verdict(dict(base=A(0.02), school5=A(0.14), school5_strict=A(0.13), school5_curr=A(0.05)))
    assert not v['pass'] and not v['proved_wrong']                                   # 14% < 15%
    assert MS.verdict(dict(base=A(0.02), school5=A(0.04), school5_strict=A(0.05), school5_curr=A(0.03)))['proved_wrong']
    assert not MS.verdict(dict(base=A(0.02, 0.9), school5=A(0.30, 0.80)))['pass']      # Easy fell 10 points
    assert not MS.verdict(dict(base=A(0.02), school5=A(0.30, 0.9, 0.03)))['pass']      # skills harm 3 points
    assert not MS.verdict(dict(base=A(0.02), school5=A(0.30, 0.9, 0.0), oracle=A(0.9)))['proved_wrong']
    assert MS.verdict(dict(base=A(0.02), oracle=A(0.9), school5=A(0.0)))['proved_wrong']


def test_arms_follow_the_prereg_table():
    k = {a: MS.arm_kwargs(a, MS.SIZES) for a in MS.ARMS}
    assert k['base'] == {} and k['dream2'] == dict(dream2=1000, dream2_max_steps=2)
    s5 = k['school5']['school']
    assert (s5['n'], s5['max_steps'], s5['visits'], s5['lr'], s5['strict'], s5['curriculum']) == (40000, 5, 2, 3e-4, False, False) and k['school5']['dream2'] == 1000
    assert k['school5_strict']['school']['strict'] and k['school5_strict']['dream2_strict'] and k['school5_curr']['school']['curriculum']
    assert CS.school_plan(k['school5_curr']['school']) == [(921, 2, 13333), (922, 3, 13333), (923, 5, 13334)]
    assert k['oracle']['school']['updates'] == 2500 and 'dream2' not in k['oracle'] and 'oracle' in MS.REPORT_ONLY


# ---------------- round 2: Occam dreams ----------------
from creative import fewshot as F
from creative.programs import cone, run, train_form


def test_occam_relabel_fits_row_and_is_not_longer():
    st = {}
    rows = D.dream_rows_c2(30, 2, max_steps=5, check_real=False, night=7, occam=True, stats=st)
    assert len(rows) == 30
    for r in rows:
        d = r['dream']
        t = Try.make(d['steps'], d['ans'])
        p = F.parse(r['prompt'])
        assert F.verdict(p, t)[0] == 'accept' and r['answer'] == str(F.verdict(p, t)[2])      # the forced program reproduces every example and the query
        assert d['found_length'] == len(cone(t)) <= d['length']
        outs = [run([0] * Q + [x], t)[0][t.ans] for x in d['xs'] + [d['q']]]
        assert outs == d['ys'] + [int(r['answer'])]
    assert sum(v['occam_dropped'] for v in st.values()) >= 0 and sum(v[f'found_{k}'] for v in st.values() for k in range(1, 6)) == 30


def test_occam_deterministic_and_default_off_unchanged():
    a = D.dream_rows_c2(12, 5, max_steps=5, check_real=False, night=8, occam=True)
    b = D.dream_rows_c2(12, 5, max_steps=5, check_real=False, night=8, occam=True)
    assert [(r['id'], r['prompt'], r['dream']['steps']) for r in a] == [(r['id'], r['prompt'], r['dream']['steps']) for r in b]
    assert inspect.signature(D.dream_rows_c2).parameters['occam'].default is False and inspect.signature(D.dream_rows_par).parameters['occam'].default is False
    assert inspect.signature(CS.add_dreams).parameters['occam'].default is False and inspect.signature(CS.run_creative).parameters['dream2_occam'].default is False
    x, y = D.dream_rows_c2(20, 3), D.dream_rows_c2(20, 3, occam=False)
    assert [(r['id'], r['prompt'], r['dream']['steps']) for r in x] == [(r['id'], r['prompt'], r['dream']['steps']) for r in y]


def test_occam_strict_still_applied_and_par_cache_key(tmp_path):
    rows = D.dream_rows_c2(150, 0, max_steps=1, check_real=False, night=5, occam=True, strict=True)
    assert D.kind_overlap(rows)['any_held_out_same_function'] == 0
    assert not any(D.is_held_out_form(Try.make(r['dream']['steps'], r['dream']['ans']), Q) for r in rows)
    a = D.dream_rows_par(20, 4, (), night=905, max_steps=5, shards=4, workers=2, cache_dir=str(tmp_path), occam=True)
    b = D.dream_rows_par(20, 4, (), night=905, max_steps=5, shards=4, workers=1, cache_dir=str(tmp_path))           # same args but occam off: must not hit the occam cache
    assert len(list(tmp_path.glob('*.pkl'))) == 2 and any('occam' in p.name for p in tmp_path.glob('*.pkl'))
    assert all('found_length' in r['dream'] for r in a) and not any('found_length' in r['dream'] for r in b)
    c = D.dream_rows_par(20, 4, (), night=905, max_steps=5, shards=4, workers=1, cache_dir=str(tmp_path), occam=True)
    assert [(r['id'], r['prompt']) for r in a] == [(r['id'], r['prompt']) for r in c]
    assert sorted(r['dream']['length'] for r in a) == sorted([1, 2, 3, 4, 5] * 4)


def test_round2_arms_and_verdict():
    k = {a: MS.arm_kwargs(a, MS.SIZES) for a in MS.ROUND2_ARMS}
    o = k['occam5']['school']
    assert (o['n'], o['max_steps'], o['visits'], o['lr'], o['strict'], o['occam'], o['shards']) == (40000, 5, 4, 1e-3, False, True, 128)
    assert k['occam5']['dream2'] == 1000 and k['occam5']['dream2_occam'] and not k['occam5'].get('dream2_strict')
    assert k['occam5_strict']['school']['strict'] and k['occam5_strict']['dream2_strict'] and k['occam5_strict']['dream2_occam']
    assert k['base'] == {} and k['oracle'] == MS.arm_kwargs('oracle', MS.SIZES)
    assert MS.arm_kwargs('school5', MS.SIZES)['school']['lr'] == 3e-4 and 'occam' not in MS.arm_kwargs('school5', MS.SIZES)['school']      # round 1 unchanged
    assert CS.school_plan(o) != CS.school_plan(dict(o, occam=False)) and CS.school_plan(dict(o, occam=False)) == [(900, 5, 40000)]
    A = lambda h, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm)
    v = MS.verdict_round2(dict(base=A(0.02), occam5=A(0.30), occam5_strict=A(0.25), oracle=A(0.9)), dict(occam5=1.2, occam5_strict=1.5))
    assert v['pass'] and v['not_leakage'] and not v['proved_wrong'] and all(v['mechanism_learned'].values())
    v = MS.verdict_round2(dict(base=A(0.02), occam5=A(0.30), occam5_strict=A(0.15)), dict(occam5=1.2, occam5_strict=2.5))
    assert not v['pass'] and not v['mechanism_learned']['occam5_strict'] and any('DID NOT LEARN' in l for l in v['lines'])       # 15% < 20%
    v = MS.verdict_round2(dict(base=A(0.02), occam5=A(0.30), occam5_strict=A(0.10)))
    assert v['not_leakage'] is False
    v = MS.verdict_round2(dict(base=A(0.10), occam5=A(0.12), occam5_strict=A(0.13)))
    assert v['proved_wrong'] and not v['pass']
    assert not MS.verdict_round2(dict(base=A(0.02, 0.9), occam5_strict=A(0.30, 0.80)))['pass'] and not MS.verdict_round2(dict(base=A(0.02), occam5_strict=A(0.30, 0.9, 0.03)))['pass']
