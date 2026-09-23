"""Checks for scripts/fable_confirmation_panels.py.  Plain script; no pytest.

Run:
    python3.12 -B tests/test_fable_confirmation_panels.py

Everything here is pure data work at a small n; no checkpoint is loaded and no model is
run on any confirmation panel.  Two tests assert that directly, by replacing the model
classes with objects that raise if anyone constructs them.

If the real 512-unit suite has been generated under
artifacts/fable-confirmation-panels-20260920/, the last group re-verifies its manifest
hashes and its audit verdict.  Those tests skip cleanly when it is absent.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher_v3 as V3                                            # noqa: E402
import astra_canonical_operator as A                                        # noqa: E402
import astra_canonical_operator_panels as P                                 # noqa: E402
import fable_confirmation_panels as F                                       # noqa: E402

torch = F.torch
REAL = F.DEFAULT_OUT

PASSED = 0
FAILED = []
SKIPPED = []
TEMP = []


def check(name, function):
    global PASSED
    try:
        detail = function()
    except _Skip as skip:
        SKIPPED.append((name, str(skip)))
        print(f'skip  {name}: {skip}', flush=True)
        return
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


class _Skip(Exception):
    pass


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'confirm-{name}-')) / 'out'
    TEMP.append(folder.parent)
    return folder


class _Forbidden:
    """Anything that constructs this raises: used to prove no model was built."""

    def __init__(self, *args, **kwargs):
        raise AssertionError('a model was constructed during a model-free step')


def without_models(function):
    saved = (A.CanonicalOperator, V3.FrozenOperator, V3.make_operator)
    A.CanonicalOperator = _Forbidden
    V3.FrozenOperator = _Forbidden
    V3.make_operator = _Forbidden
    try:
        return function()
    finally:
        A.CanonicalOperator, V3.FrozenOperator, V3.make_operator = saved


# --------------------------------------------------------------------------- generators


def test_operator_cell_reproduces_the_registered_generator():
    import premonition_pair_suite as PS
    A.data.bootstrap()
    checked = []
    for name in ('c1_own_one_hop', 'c3_own_heldout_two_hop', 'c4_changed_link',
                 'c6_irrelevant_edit'):
        seed = 202609202000 + PS.CELLS[name]['cell']
        mine = F.operator_cell(name, 8, P.NAMESPACE, seed)
        theirs = P.generate(name, n=8, namespace=P.NAMESPACE)
        assert P.signatures(mine) == P.signatures(theirs), name
        assert mine['rejections'] == theirs['rejections'], name
        checked.append(name)
    return f'{len(checked)} cells byte-identical to astra_canonical_operator_panels.generate'


def test_dispatcher_unit_reproduces_v3():
    for cell in ('k1-prac', 'k5-held', 'k8-held', 'pair-link', 'pair-irrelevant'):
        for index in range(4):
            assert F.dispatcher_unit(cell, index, V3.PANEL_NAMESPACE) == \
                V3.make_unit(cell, index), (cell, index)
    return '20 units identical to fable_dispatcher_v3.make_unit'


def test_new_namespace_draws_different_worlds():
    same = 0
    for cell in ('k1-prac', 'k5-held', 'pair-link'):
        for index in range(8):
            mine = F.dispatcher_unit(cell, index, F.DISPATCH_NAMESPACE)
            same += int(mine['a']['memory'] == V3.make_unit(cell, index)['a']['memory'])
    assert same == 0, f'{same} confirmation units repeat a development world'
    return '24 units, none repeating the development draw'


def test_generated_units_pass_the_v3_audit():
    n, audited = 8, 0
    for cell in V3.CELL_ORDER:
        for index in range(n):
            unit = F.dispatcher_unit(cell, index, F.DISPATCH_NAMESPACE)
            problems = V3.audit_unit(unit)
            assert not problems, (cell, index, problems)
            audited += 1
    return f'{audited} units pass audit_unit (both interpreters, paired-edit semantics)'


def test_three_hop_cell_shape():
    panel = F.three_hop_cell(8, F.OPERATOR_NAMESPACE, F.OPERATOR_SEED_BASE + 14)
    questions = [q for chunk in panel['chunks'] for x, _t in chunk['sides'].values()
                 for q in x.questions.tolist()]
    assert len(questions) == 8
    for q in questions:
        q = [t for t in q if t]
        assert len(q) == 6 and q[2] == F.LINK and q[3] == F.LINK, q
    return '8 units, two LINK tokens, targets checked by truth_paths'


def test_thresholds_match_the_draft():
    assert {k: v['cutoff'] for k, v in F.OPERATOR_CELLS.items()} == dict(
        c1=487, c2=487, c3=461, c4=461, c5=461, c6=461,
        **{'p12-1': 487, 'p12-2': 487, 'p12-3': 461, 's3': 461})
    assert len(F.OPERATOR_CELLS) == 10
    assert F.DISPATCH_CUTOFF == 464 and len(V3.CELL_ORDER) == 25
    assert F.CONFIRM_N == 512
    assert round(464 / 512, 6) == round(58 / 64, 6), 'the acceptance fraction must be kept'
    return '10 operator cells, 25 dispatcher cells, 464/512 == 58/64'


def test_namespaces_are_new():
    assert F.OPERATOR_NAMESPACE == 'astra-confirm-operator-v2-20260920'
    assert F.DISPATCH_NAMESPACE == 'astra-confirm-dispatch-v2-20260920'
    assert F.DISPATCH_NAMESPACE != V3.PANEL_NAMESPACE != F.OPERATOR_NAMESPACE
    assert F.OPERATOR_NAMESPACE != P.NAMESPACE
    return 'both namespaces distinct from every registered one'


# --------------------------------------------------------------------------- signatures


def test_fast_signature_equals_the_registered_one():
    checked = 0
    for cell in ('k1-prac', 'k3-held', 'pair-value'):
        unit = F.dispatcher_unit(cell, 0, F.DISPATCH_NAMESPACE)
        for _name, rows, question in F.unit_sides(unit):
            assert F.signature_from_facts(F.fact_tuples(rows), question) == \
                A.visible_signature(rows, question)
            checked += 1
    return f'{checked} sides match astra_canonical_operator.visible_signature'


def test_both_twins_are_indexed():
    unit = F.dispatcher_unit('pair-link', 0, F.DISPATCH_NAMESPACE)
    sides = F.unit_sides(unit)
    assert [name for name, _r, _q in sides] == ['a', 'b']
    sigs = F.dispatcher_unit_signatures(unit, canonical=False)
    assert len({s['full'] for s in sigs}) == 2, 'the twins must hash differently'
    single = F.dispatcher_unit_signatures(F.dispatcher_unit('k1-prac', 0,
                                                            F.DISPATCH_NAMESPACE), False)
    assert len(single) == 1
    return 'pair -> 2 sides, single -> 1'


def test_canonical_expansion_covers_sixteen_entities_by_four_ops():
    assert len(F.CANONICAL_QUESTIONS) == 64
    entities = {q[1] for q in F.CANONICAL_QUESTIONS}
    ops = {q[2] for q in F.CANONICAL_QUESTIONS}
    assert entities == set(range(A.ENTITY_MIN, A.ENTITY_MAX))
    assert ops == {8, 9, 10, A.LINK}
    unit = F.dispatcher_unit('p6-k1-prac', 0, F.DISPATCH_NAMESPACE)
    sig = F.dispatcher_unit_signatures(unit, canonical=True)[0]
    assert len(sig['canonical']) == 64
    # the six-person world has only six people, so most of the 64 calls are "unexpected"
    people = {row[1] for row in unit['a']['memory']
              if len(row) >= 4 and A.ENTITY_MIN <= row[1] < A.ENTITY_MAX}
    assert len(people) == 6, people
    assert sig['world'] and sig['tensor']
    return '64 canonical sub-queries per side, world-only hash present'


def test_reduced_and_full_signatures_differ_under_a_curriculum():
    """A shrunk story must not be represented by its parent world's hash."""
    records = list(F.replay_records('grow-blind', 0, 1, 2, verbose=False))
    assert records, 'no records replayed'
    differing = 0
    for seen, parent, question in records:
        if len(seen) != len(parent):
            assert F.signature_from_facts(F.fact_tuples(seen), question) != \
                F.signature_from_facts(F.fact_tuples(parent), question)
            differing += 1
    assert differing, 'the curriculum did not reduce any story in these updates'
    return f'{differing}/{len(records)} records present a reduced story'


# --------------------------------------------------------------------------- replay


def test_grow_blind_replay_matches_the_registered_builder():
    import fable_operator_startup as S
    A.data.bootstrap()
    updates = 4
    S.configure_variant('grow-blind', seed=0, **S.registered_params('grow-blind'))
    rng = random.Random(1101)
    reference, reference_sigs = [], set()
    for step in range(updates):
        S.STATE['step'] = step
        batch = S.training_batch_blind(rng, 16, frozenset())
        for inputs in (batch.canonical, batch.monolithic):
            for rows, question in F._packed_records(inputs):
                reference.append(question)
                reference_sigs.add(F.signature_from_facts(F.fact_tuples(rows), question))
    mine, mine_sigs = [], set()
    for seen, _parent, question in F.replay_records('grow-blind', 0, updates, 16, False):
        mine.append(question)
        mine_sigs.add(F.signature_from_facts(F.fact_tuples(seen), question))
    assert sorted(mine) == sorted(reference), (len(mine), len(reference))
    assert mine_sigs == reference_sigs
    return f'{len(mine)} records and {len(mine_sigs)} presented signatures agree'


def test_v3_replay_matches_the_v3_overlap_check():
    """v3's own training-time `forbidden` test hashes exactly what the replay indexes."""
    rng = random.Random(f'{V3.TRAIN_NAMESPACE}:0')
    inputs, questions, owners, _answers, _meta = V3.training_visits(
        rng, 4, V3.TRAIN_PEOPLE, V3.TRAIN_HOPS, frozenset())
    memory = inputs.memory.tolist()
    expected = set()
    for question, owner, eligible in zip(questions, owners, inputs.eligible.tolist()):
        rows = [r for r, ok in zip(memory[owner], eligible) if ok and any(r)]
        expected.add(A.visible_signature(rows, question))
    mine = {F.signature_from_facts(F.fact_tuples(seen), q)
            for seen, _p, q in F.replay_records('v3-dispatcher', 0, 1, 4, verbose=False)}
    assert mine == expected, (len(mine), len(expected))
    return f'{len(mine)} signatures identical to v3\'s own forbidden-set construction'


def test_replay_runs_no_model():
    def body():
        detail, presented, parent, tensors = F.replay_stream('grow-blind', 0, 2, 4, False)
        assert detail['model_computation'] is False
        assert presented and parent and tensors
        return detail['records']
    records = without_models(body)
    return f'{records} records indexed with no model constructed'


def test_partial_index_is_labelled():
    folder = scratch('replay')
    folder.mkdir(parents=True)

    class Args:
        builder = 'v3-dispatcher'
        seed = 0
        updates = 2
        visits = 4
        full_updates = 6000
        out = str(folder / 'index.json')

    detail = F.replay(Args)
    assert detail['partial'] is True and detail['full_updates'] == 6000
    payload = json.loads(Path(Args.out).read_text())
    assert payload['signatures'] and payload['provenance']
    return 'a short replay is marked partial'


# --------------------------------------------------------------------------- suite build + audit


def _build_small(n=4):
    folder = scratch('suite')

    class Args:
        out = str(folder)
        suite = 'both'

    Args.n = n
    without_models(lambda: F.generate(Args))
    return folder


def test_generate_and_audit_are_clean():
    folder = _build_small()

    class Args:
        out = str(folder)
        no_canonical = False

    report = without_models(lambda: F.audit(Args))
    assert report['all_clear'] is True, report['audit_failures']
    assert report['within_suite_duplicate_full_signatures'] == 0
    assert report['canonical_subquery_signatures'] == report['sides'] * 64
    assert all(row['checked'] for row in report['sources']), \
        [r['name'] for r in report['sources'] if not r['checked']]
    assert all(row['disjointness'] == 'clean' for row in report['sources'])
    return (f'{report["sides"]} sides, {report["canonical_subquery_signatures"]} canonical, '
            f'{len(report["sources"])} development sources clean')


def test_manifest_records_no_model_audit():
    folder = _build_small()
    top = json.loads((folder / 'manifest.json').read_text())
    assert top['model_free'] is True and top['scored_by_any_checkpoint'] is False
    assert top['filtered_by_model_correctness'] is False
    for suite in ('operator', 'dispatcher'):
        manifest = json.loads((folder / suite / 'manifest.json').read_text())
        assert manifest['operator_audit'] is None
        assert manifest['filtered_by_model_correctness'] is False
        assert manifest['namespace'] in (F.OPERATOR_NAMESPACE, F.DISPATCH_NAMESPACE)
    assert len(top['files']) == 39, top['files']
    for name, expected in top['files'].items():
        assert F.sha(folder / name) == expected, name
    return f'{len(top["files"])} files hashed, no operator audit recorded'


def test_generation_is_deterministic():
    one, two = _build_small(3), _build_small(3)
    a = json.loads((one / 'manifest.json').read_text())['files']
    b = json.loads((two / 'manifest.json').read_text())['files']
    assert sorted(a) == sorted(b)
    differing = [k for k in a if a[k] != b[k] and not k.endswith('manifest.json')]
    assert not differing, differing
    return f'{len(a) - 2} panel and exclusion files reproduce bit-for-bit'


def test_check_index_finds_a_planted_overlap():
    folder = _build_small()

    class AuditArgs:
        out = str(folder)
        no_canonical = False

    report = without_models(lambda: F.audit(AuditArgs))
    stolen = json.loads(Path(report['exclusion_path']).read_text())[:3]
    planted = folder / 'planted.json'
    with planted.open('x') as handle:
        json.dump(dict(builder='planted', seed=0, updates=1, partial=True,
                       signatures=stolen), handle)
    planted_paths = [str(planted)]

    class Args:
        out = str(folder)
        index = planted_paths
        name = 'planted-overlap.json'

    result = F.check_index(Args)
    assert result['clean'] is False and result['overlap'] == 3, result
    return f'{result["overlap"]} planted collisions detected'


def test_missing_development_source_is_an_audit_failure():
    folder = _build_small()
    saved = F.development_sources

    def broken():
        rows = saved()
        rows.append(dict(name='pretend-missing', kind='exclusion-json',
                         path='/nowhere/forbidden-semantics.json', exists=False))
        return rows

    F.development_sources = broken

    class Args:
        out = str(folder)
        no_canonical = True

    try:
        report = without_models(lambda: F.audit(Args))
    finally:
        F.development_sources = saved
    assert report['all_clear'] is False
    assert any('pretend-missing' in f for f in report['audit_failures'])
    entry = next(r for r in report['sources'] if r['name'] == 'pretend-missing')
    assert entry['disjointness'] == 'UNVERIFIED'
    return 'an unreadable source is reported as UNVERIFIED, not skipped'


# --------------------------------------------------------------------------- the real suite


def _require_real():
    if not (REAL / 'manifest.json').exists():
        raise _Skip('the 512-unit suite has not been generated')


def test_real_suite_counts():
    _require_real()
    top = json.loads((REAL / 'manifest.json').read_text())
    assert top['n'] == 512 and sorted(top['suites']) == ['dispatcher', 'operator']
    operator = json.loads((REAL / 'operator/manifest.json').read_text())
    dispatcher = json.loads((REAL / 'dispatcher/manifest.json').read_text())
    assert len(operator['cells']) == 10 and len(dispatcher['cells']) == 25
    sides = sum(row['n'] * row['sides'] for row in operator['cells'].values())
    assert all(row['n'] == 512 for row in operator['cells'].values())
    assert all(row['n'] == 512 for row in dispatcher['cells'].values())
    assert operator['operator_audit'] is None and dispatcher['operator_audit'] is None
    return f'10 + 25 cells at 512 units; operator suite {sides} sides'


def test_real_suite_hashes():
    _require_real()
    top = json.loads((REAL / 'manifest.json').read_text())
    for name, expected in top['files'].items():
        assert F.sha(REAL / name) == expected, name
    return f'{len(top["files"])} files match the frozen manifest'


def test_real_audit_is_clean():
    _require_real()
    path = REAL / 'audit/audit.json'
    if not path.exists():
        raise _Skip('the audit has not been run')
    report = json.loads(path.read_text())
    assert report['all_clear'] is True, report['audit_failures']
    assert report['sides'] == 20992, report['sides']
    assert report['canonical_subquery_signatures'] == 20992 * 64
    assert F.sha(report['exclusion_path']) == report['exclusion_sha256']
    assert F.sha(report['canonical_path']) == report['canonical_sha256']
    assert all(r['checked'] and r['disjointness'] == 'clean' for r in report['sources'])
    return (f'{report["sides"]} sides, union {report["exclusion_union_count"]}, '
            f'{len(report["sources"])} sources clean')


def main():
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for name, function in tests:
        check(name[5:].replace('_', ' '), function)
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    print(f'\n{PASSED} passed, {len(FAILED)} failed, {len(SKIPPED)} skipped', flush=True)
    if FAILED:
        for name, detail in FAILED:
            print(f'  {name}: {detail}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
