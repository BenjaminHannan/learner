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
    assert all('found_length' in r['dream'] for r in a) and all(r['dream']['found_length'] <= r['dream']['length'] for r in b)
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


# ---------------- round 3: depth-balanced Occam dreams ----------------
def test_found_length_quotas_exact_and_programs_have_that_length(tmp_path):
    rows = D.dream_rows_c2(16, 1, max_steps=5, check_real=False, night=11, occam=True, found_lengths=(1, 2, 3, 4))
    assert [sum(r['dream']['found_length'] == L for r in rows) for L in (1, 2, 3, 4)] == [4] * 4
    assert all(len(cone(Try.make(r['dream']['steps'], r['dream']['ans']))) == r['dream']['found_length'] <= r['dream']['length'] for r in rows)
    again = D.dream_rows_c2(16, 1, max_steps=5, check_real=False, night=11, occam=True, found_lengths=(1, 2, 3, 4))
    assert [(r['id'], r['prompt']) for r in rows] == [(r['id'], r['prompt']) for r in again]
    with pytest.raises(AssertionError):
        D.dream_rows_c2(4, 1, check_real=False, found_lengths=(1, 2))              # needs occam
    a = D.dream_rows_par(24, 3, (), night=917, max_steps=5, strict=True, shards=3, workers=2, cache_dir=str(tmp_path), occam=True, found_lengths=(1, 2, 3, 4))
    assert [sum(r['dream']['found_length'] == L for r in a) for L in (1, 2, 3, 4)] == [6] * 4
    assert not any(D.is_held_out_form(Try.make(r['dream']['steps'], r['dream']['ans']), Q) for r in a)
    D.dream_rows_par(24, 3, (), night=917, max_steps=5, strict=True, shards=3, workers=1, cache_dir=str(tmp_path), occam=True)       # drawn-length dealing: its own cache entry
    assert len(list(tmp_path.glob('*.pkl'))) == 2 and any('_f1234_' in p.name for p in tmp_path.glob('*.pkl'))
    c = D.dream_rows_par(24, 3, (), night=917, max_steps=5, strict=True, shards=3, workers=1, cache_dir=str(tmp_path), occam=True, found_lengths=(1, 2, 3, 4))
    assert [(r['id'], r['prompt']) for r in a] == [(r['id'], r['prompt']) for r in c]


def test_round3_arm_and_verdict():
    k = MS.arm_kwargs('occam_deep', MS.SIZES)
    o = k['school']
    assert (o['n'], o['visits'], o['lr'], o['strict'], o['occam'], o['shards'], tuple(o['found_lengths'])) == (40000, 4, 1e-3, True, True, 128, (1, 2, 3, 4))
    assert k['dream2'] == 1000 and k['dream2_occam'] and k['dream2_strict'] and MS.ROUND3_ARMS == ('base', 'occam_deep')
    assert CS.school_plan(o) == [(917, 5, 40000)] and CS.school_plan(dict(o, found_lengths=None)) == [(915, 5, 40000)]
    A = lambda h, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm)
    v = MS.verdict_round3(dict(base=A(0.02), occam_deep=A(0.30)), dict(occam_deep=1.0), dict(hard=0.20))
    assert v['pass'] and v['depth_helps'] and not v['proved_wrong'] and v['mechanism_learned']['occam_deep']
    v = MS.verdict_round3(dict(base=A(0.02), occam_deep=A(0.30)), None, dict(hard=0.27))
    assert v['pass'] and v['depth_helps'] is False
    v = MS.verdict_round3(dict(base=A(0.02), occam_deep=A(0.04)))
    assert v['proved_wrong'] and not v['pass'] and v['depth_helps'] is None and any('n/a' in l for l in v['lines'])
    assert not MS.verdict_round3(dict(base=A(0.02), occam_deep=A(0.15)))['pass']


def test_round4_nights_default_unchanged_and_four_nights(tmp_path):
    sig = inspect.signature(CS.run_creative).parameters
    assert sig['nights'].default == 2 and sig['eval_each_night'].default is False
    assert MS.arm_kwargs('base', MS.SIZES) == {} and MS.arm_kwargs('base', MS.SIZES, round_=4) == dict(eval_each_night=True)
    assert MS.arm_kwargs('nights4', MS.SIZES, round_=4) == dict(nights=4, eval_each_night=True)
    ck, sk = _tiny_workdir(tmp_path)
    info = CS.run_creative(str(tmp_path / 'n4'), ck, sk, None, device='cpu', seed=0, pool_limit=6, dev_limit=4, n1=2, n2=2, T=1.0, updates_cap=2, nights=4, eval_each_night=True)
    ns = info.get('night_scores', {})
    for k in sorted(ns):
        assert (tmp_path / 'n4' / f'W{k}.pt').exists() and 'hard' in ns[k]
    assert (tmp_path / 'n4' / 'W4.pt').exists() == (len(ns) == 4) or info.get('stop')


def test_round4_verdict():
    v = MS.verdict_round4(dict(base=dict(hard=0.11, easy=0.9, harm=0.0), nights4=dict(hard=0.20, easy=0.88, harm=0.01)), dict(nights4={'1': .01, '4': .2}))
    assert v['pass'] and not v['proved_wrong'] and any('CURVE' in l for l in v['lines'])
    v = MS.verdict_round4(dict(base=dict(hard=0.11, easy=0.9, harm=0.0), nights4=dict(hard=0.12, easy=0.9, harm=0.0)))
    assert not v['pass'] and v['proved_wrong']


def _hs_pool():
    from creative.sampler import TryRec
    rows = [dict(id=f'q{i}', prompt='3 -> 7; 5 -> 11. Now 4 -> ?', nums=[3, 7, 5, 11, 4]) for i in range(5)]          # no 'kind'
    one = TryRec(Try.make([(1, 4, 4)], R0))                                    # x+x: runs, does not fit (7 != 6)
    two = TryRec(Try.make([(1, 4, 4), (1, R0, 4)], R0 + 1))                    # 3x: runs, 2 steps
    return rows, [[one, two] for _ in rows]


def test_hindsight_records_reads_no_kind_skips_counts_and_caps():
    from creative.c2b import hindsight_records
    rows, tries = _hs_pool()
    recs, info = hindsight_records(rows, tries, {'q0': 1}, 0, 3, cap=100)
    assert recs and all(not r['id'].startswith('HS3:q0') and r['id'].startswith('HS3:') and 'kind' not in r for r in recs)
    assert info['records'] == len(recs) and info['by_kind'] == {} and info['questions'] == 4
    assert all(r['prompt'] != rows[0]['prompt'] for r in recs)               # example outputs rewritten
    assert 0 < info['multi_step_share'] <= 1
    capped, ci = hindsight_records(rows, tries, {}, 0, 3, cap=3)
    assert len(capped) == 3 == ci['records']
    assert hindsight_records(rows, tries, {}, 0, 3, cap=3)[0] == capped      # seeded
    r2, i2 = hindsight_records([dict(r, kind='affine') for r in rows], tries, {}, 0, 3, cap=100)
    assert i2['by_kind'] == dict(affine=len(r2))


def test_round6_arm_flags_and_verdict():
    sig = inspect.signature(CS.run_creative).parameters
    assert sig['hindsight'].default is False and sig['op_entropy'].default is False
    assert MS.arm_kwargs('hind4', MS.SIZES, round_=6) == dict(nights=4, eval_each_night=True, hindsight=True, op_entropy=True) and 'hind4' in MS.ARMS
    A = lambda h, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm)
    base = A(0.10)
    v = MS.verdict_round6(dict(base=base, nights4=A(0.15), hind4=A(0.20)))
    assert v['pass'] and not v['proved_wrong']
    assert not MS.verdict_round6(dict(base=base, nights4=A(0.15), hind4=A(0.20, e=0.80)))['pass']
    assert not MS.verdict_round6(dict(base=base, nights4=A(0.15), hind4=A(0.20, hm=0.03)))['pass']
    v = MS.verdict_round6(dict(base=base, nights4=A(0.15), hind4=A(0.16)))
    assert v['proved_wrong'] and not v['pass']
    v = MS.verdict_round6(dict(base=base, nights4=A(0.15), hind4=A(0.18)))
    assert not v['pass'] and not v['proved_wrong'] and any('BETWEEN' in l for l in v['lines'])


def test_round5_verdict():
    A = lambda h: dict(hard=h, easy=0.9, harm=0.0)
    assert MS.verdict_round5(dict(base=A(0.10), nights4=A(0.18), nights8=A(0.23)))['pass']
    v = MS.verdict_round5(dict(base=A(0.10), nights4=A(0.18), nights8=A(0.19)))
    assert v['plateau'] and not v['pass']


def test_round6_end_to_end_tiny(tmp_path):
    ck, sk = _tiny_workdir(tmp_path)
    info = CS.run_creative(str(tmp_path / 'h'), ck, sk, None, device='cpu', seed=0, pool_limit=6, dev_limit=4, n1=2, n2=2, T=1.0, updates_cap=2, nights=2, eval_each_night=True, hindsight=True, op_entropy=True)
    assert info.get('stop') or ('Nprime' in info['op_entropy'] and 'W1' in info['op_entropy'] and all(v >= 0 for v in info['op_entropy'].values()))
    assert 'hindsight' in info and MS.op_entropy(ck, R.load_split(D.DATA, 'pool')[:6], 'cpu') >= 0       # tiny model finds no W records (cap 0), so check the entropy function directly


def _prog_rec(rid, steps, ans, q=6):
    from creative import fewshot as F
    prompt = 'Examples: 3 -> 0; 4 -> 0; 5 -> 0. Now 6 -> ?'
    F.register_targets(rid, F.parse(prompt)['nums'], steps, ans)
    return dict(id=rid, prompt=prompt)


def test_composition_chain_and_rows():
    from creative import dream2 as D
    from creative.programs import Try, run
    C1, C2_, ADD_, MUL_ = R0 - 4, R0 - 3, 1, 3                # constants 1 2 10 100 sit at R0-4..R0-1
    p1 = ([(ADD_, 'x', C1), (ADD_, R0, C2_)], R0 + 1)         # x + 1 + 2 = x + 3
    p2 = ([(MUL_, 'x', C2_)], R0)                              # x * 2
    t = D.chain(p1, p2, 6)
    for x in (3, 7, 12, 29):
        vals, valid = run([0] * 6 + [x], t)
        assert valid[t.ans] and vals[t.ans] == (x + 3) * 2
    assert D.chain(([(ADD_, 'x', C1)] * 4, R0 + 3), ([(ADD_, 'x', C1)] * 4, R0 + 3), 6) is None          # 8 steps > 7
    warm = [_prog_rec('t:w1', [(ADD_, 6, C1), (ADD_, R0, C2_)], R0 + 1), _prog_rec('t:w2', [(MUL_, 6, C2_)], R0)]
    wr = [_prog_rec(f't:W{i}', [(ADD_, 6, C1)], R0) for i in range(4)]
    recs, info = D.composition_rows(warm, wr, 0, 1, check_real=False)
    assert info['cap'] == 2 and len(recs) == info['count'] == 2 == sum(info['by_length'].values()) and info['warm_only'] + info['with_w'] == 2
    assert D.composition_rows(warm, wr, 0, 1, check_real=False, requested=1)[1]['count'] == 1
    assert D.composition_rows(warm, wr, 0, 1, check_real=False)[0] == recs and D.composition_rows(warm, wr, 1, 1, check_real=False)[0] != recs   # seeded
    for r in recs:
        d = r['dream']
        assert 'kind' not in r and all(0 <= y <= 999 for y in d['ys']) and 0 <= int(r['answer']) <= 999 and len(d['xs']) == 3
        tt = Try.make(d['steps'], d['ans'])
        for x, y in zip(d['xs'] + [d['q']], d['ys'] + [int(r['answer'])]):
            vals, valid = run([0] * 6 + [x], tt)
            assert valid[tt.ans] and vals[tt.ans] == y
    big, binfo = D.composition_rows(warm, wr[:1], 0, 1, check_real=False)
    assert big == [] and binfo['cap'] == 0


def test_round7_arm_flags_and_verdict():
    assert inspect.signature(CS.run_creative).parameters['composition'].default is False
    assert MS.arm_kwargs('comp4', MS.SIZES, round_=7) == dict(nights=4, eval_each_night=True, composition=True, op_entropy=True) and 'comp4' in MS.ARMS
    A = lambda h, aff=0.06, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm, affine=aff, sq_plus=0.02)
    base, n4 = A(0.10), A(0.15)
    v = MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.20)))
    assert v['pass'] and not v['proved_wrong'] and any('sq_plus' in l for l in v['lines'])
    assert not MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.20, aff=0.04)))['pass']
    assert not MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.20, e=0.80)))['pass']
    assert not MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.20, hm=0.03)))['pass']
    v = MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.16)))
    assert v['proved_wrong'] and not v['pass']
    v = MS.verdict_round7(dict(base=base, nights4=n4, comp4=A(0.18)))
    assert not v['pass'] and not v['proved_wrong'] and any('BETWEEN' in l for l in v['lines'])


def _py(code, consts=None):
    import os
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if k != 'PREMO_CONSTS'}
    if consts:
        env['PREMO_CONSTS'] = consts
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, cwd=str(__import__('pathlib').Path(__file__).resolve().parents[2]))
    return r


def test_round8_env_switch_changes_consts_everywhere_and_default_is_unchanged():
    code = ("import json; from custom_io.models import progparse as pp; from creative import programs as P, dream2 as D, checkers as C, fewshot as F, puzzles as Z; "
            "print(json.dumps([pp.CONSTS, P.CONSTS, list(D.CONST_VALUES), pp.R0, P.R0, len(C.CONST_SLOTS)]))")
    d = json.loads(_py(code).stdout)
    assert d[0] == d[1] == d[2] == [1, 2, 10, 100] and d[3] == d[4] == 20 and d[5] == 4
    n = json.loads(_py(code, '1,2,10,3').stdout)
    assert n[0] == n[1] == n[2] == [1, 2, 10, 3] and n[3] == n[4] == 20 and n[5] == 4          # same slot count: shapes unchanged
    assert json.loads(_py(code, '').stdout) == d
    assert _py(code, '1,2,10').returncode != 0 and _py(code, '1,2,10,10').returncode != 0 and _py(code, '1,2,x,3').returncode != 0
    # a program that needs 100 loses it; rows that lose their program under the swap are the ones lost_by_swap names
    code2 = ("from custom_io.models import progparse as pp; "
             "r = {'id': 'percent_rate-T1-2', 'family': 'percent_rate', 'prompt': 'What is 20% of 340?', 'answer': '68', 'steps': ['340 * 20 / 100'], 'meta': {'base': 340, 'p': 20}, 'variant': 'percent'}; "
             "print(pp.lost_by_swap(r), pp.CONSTS)")
    assert _py(code2).stdout.startswith('False [1, 2, 10, 100]')            # default set: nothing is lost
    assert _py(code2, '1,2,10,5').stdout.startswith('True [1, 2, 10, 5]')   # "x * p / 100" needs the constant 100: the row is skipped from replay, not trained program-less


def test_round8_resume_refuses_a_mixed_constant_set(tmp_path):
    ck, sk = _tiny_workdir(tmp_path)
    out = tmp_path / 'm'
    out.mkdir()
    json.dump(dict(ckpt=ck, seed=0, stages=['warmup'], seconds={}, g1=False, phases={}, consts=[1, 2, 10, 5]), open(out / 'train.json', 'w'))
    with pytest.raises(RuntimeError, match='constants'):
        CS.run_creative(str(out), ck, sk, None, device='cpu', seed=0, pool_limit=6, dev_limit=4, n1=2, n2=2, T=1.0, updates_cap=2)


def test_round8_arms_dirs_env_and_verdict():
    assert MS.arm_kwargs('const_base', MS.SIZES, round_=8) == MS.arm_kwargs('base', MS.SIZES, round_=8) == dict(eval_each_night=True)
    assert MS.arm_kwargs('const_nights4', MS.SIZES, round_=8) == MS.arm_kwargs('nights4', MS.SIZES, round_=8)
    assert MS.arm_consts('const_nights4') == '1,2,10,3' and MS.arm_consts('nights4') is None and MS.arm_consts('const_base', '1,2,10,5') == '1,2,10,5'
    assert MS.group_dir('/o', 0, None) == '/o/s0' and MS.group_dir('/o', 1, '1,2,10,5') == '/o/s1/const5'
    import os
    old = os.environ.get('PREMO_CONSTS')
    os.environ['PREMO_CONSTS'] = '1,2,10,7'
    try:
        assert 'PREMO_CONSTS' not in MS.sub_env(None) and MS.sub_env('1,2,10,3')['PREMO_CONSTS'] == '1,2,10,3'
    finally:
        os.environ.pop('PREMO_CONSTS') if old is None else os.environ.__setitem__('PREMO_CONSTS', old)
    A = lambda h, aff=0.06, e=0.9, hm=0.0: dict(hard=h, easy=e, harm=hm, affine=aff)
    cb, n4 = A(0.10), A(0.169)
    v = MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.21), nights4=n4))
    assert v['pass'] and not v['proved_wrong']
    assert not MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.21, aff=0.04), nights4=n4))['pass']       # affine < 5
    assert not MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.21, e=0.80), nights4=n4))['pass']           # Easy more than 5 below const_base
    assert not MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.21, hm=0.03), nights4=n4))['pass']          # harm > 2
    assert not MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.208), nights4=n4))['pass'] or True
    assert not MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.208), nights4=n4))['pass']                  # +3.9 < +4
    v = MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.175, aff=0.01)), ref=dict(hard=0.169))            # nights4 from the flag; +0.6, affine 1%
    assert v['proved_wrong'] and not v['pass']
    v = MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.175, aff=0.02), nights4=n4))                        # affine 2% > 1: not proved wrong
    assert not v['proved_wrong'] and not v['pass'] and any('BETWEEN' in l for l in v['lines'])
    v = MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.25, aff=0.0), nights4=n4))                          # big Hard gain but affine 0: no pass, not proved wrong
    assert not v['pass'] and not v['proved_wrong']
    with pytest.raises(ValueError):
        MS.verdict_round8(dict(const_base=cb, const_nights4=A(0.2)))
