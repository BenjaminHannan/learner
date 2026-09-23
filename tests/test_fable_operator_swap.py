"""Checks for scripts/fable_operator_swap.py.  Plain script; no pytest.

Run:
    python3.12 -B tests/test_fable_operator_swap.py
    FABLE_SWAP_FULL=1 python3.12 -B tests/test_fable_operator_swap.py

The replication check re-scores the REGISTERED v3 development panels with the ORIGINAL
operator and compares against the registered scores.  That is a re-score of already-seen
development data, not a confirmation read.  By default it covers three cells so the file
stays fast; FABLE_SWAP_FULL=1 runs all 25 (about 40 s).

No checkpoint is ever scored on a confirmation panel here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402
import fable_operator_swap as S                                             # noqa: E402

torch = V3.torch
PANELS = S.DEFAULT_PANELS
SEED0 = S.dispatcher_dir(0)
ORIGINAL = S.ORIGINAL_OPERATOR
GROW_BLIND0 = S.operator_path(0)
SMALL_CELLS = ('k1-prac', 'k5-held', 'pair-irrelevant')
FULL = bool(os.environ.get('FABLE_SWAP_FULL'))

PASSED = 0
FAILED = []
TEMP = []


def check(name, function):
    global PASSED
    try:
        detail = function()
    except Exception as exc:                                    # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'swap-{name}-')) / 'out'
    TEMP.append(folder.parent)
    return folder


def small_units(cell='k5-held', n=6):
    units = []
    for index in range(n):
        unit = V3.make_unit(cell, index)
        unit.pop('rejections', None)
        units.append(unit)
    return units


# --------------------------------------------------------------------------- the stale-diagnostic fix


def test_panels_carry_the_stale_field():
    """The premise: the registered panels really do carry the ORIGINAL operator's hits."""
    _manifest, panels, _forbidden = V3.load_panels(PANELS)
    with_hits = [c for c, p in panels.items() if p.get('operator_chain_hits')]
    assert len(with_hits) == len(V3.CELL_ORDER), with_hits
    manifest = json.loads((Path(PANELS) / 'manifest.json').read_text())
    assert manifest['operator']['sha256'] == S.sha(ORIGINAL), 'panels were built elsewhere'
    return f'{len(with_hits)} cells, panel operator {manifest["operator"]["sha256"][:12]}'


def test_strip_removes_every_stale_field():
    _manifest, panels, _forbidden, dropped = S.load_panels_without_stale_diagnostics(PANELS)
    assert dropped == len(V3.CELL_ORDER), dropped
    for cell, panel in panels.items():
        assert 'operator_chain_hits' not in panel, cell
    return f'{dropped} panel fields dropped'


def test_manifest_operator_audit_dropped():
    manifest, _panels, _forbidden, _dropped = S.load_panels_without_stale_diagnostics(PANELS)
    assert 'operator_audit' not in manifest
    raw = json.loads((Path(PANELS) / 'manifest.json').read_text())
    assert 'operator_audit' in raw, 'the raw manifest should still have it'
    return 'manifest audit hidden from the scorer'


def test_stale_hits_cannot_steer_execution():
    """Native answers are byte-identical with the stale field supplied and withheld."""
    units = small_units()
    operator = V3.make_operator(str(GROW_BLIND0))
    saved = torch.load(SEED0 / 'dispatcher.pt', map_location='cpu', weights_only=False)
    model = V3.Dispatcher(width=saved['width'], absolute_positions=saved['absolute_positions'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    panel = json.loads((Path(PANELS) / 'k5-held.json').read_text())
    stale = {'a': panel['operator_chain_hits']['a'][:len(units)]}
    with_stale = V3.score_side(model, operator, units, 'a', 16, chain_hits=stale)
    without = V3.score_side(model, operator, units, 'a', 16, chain_hits=None)
    keys = ('answer', 'correct', 'status', 'calls', 'transcript', 'pointers', 'strict_path')
    assert [[r[k] for k in keys] for r in with_stale] == [[r[k] for k in keys] for r in without]
    # the stale field only ever reached the DIAGNOSTIC column, which is why the v3 bug
    # mis-attributed rather than corrupted; here it is present in one and absent in the other
    assert all(r['operator_chain_hits'] is not None for r in with_stale)
    assert all(r['operator_chain_hits'] is None for r in without)
    return 'identical native predictions'


def test_operator_calls_match_v3_hits():
    units = small_units()
    operator = V3.make_operator(str(GROW_BLIND0))
    mine = S.hits_of(S.operator_calls(operator, units, 'a'))
    theirs = V3.operator_on_chains(operator, units, 'a')
    assert mine == theirs, (mine, theirs)
    return f'{sum(len(h) for h in mine)} stages agree with V3.operator_on_chains'


def test_oracle_calls_are_all_hits():
    units = small_units()
    calls = S.operator_calls(V3.OracleOperator(), units, 'a')
    assert all(stage['hit'] and stage['predicted'] == stage['target']
               for unit in calls for stage in unit)
    return 'oracle answers every stage'


def test_recomputed_audit_reproduces_the_manifest_for_the_same_operator():
    """With the ORIGINAL operator the recomputation must equal the frozen panel audit."""
    manifest, panels, _forbidden = V3.load_panels(PANELS)
    operator = V3.make_operator(str(ORIGINAL))
    checked = []
    for cell in ('k1-prac', 'pair-value'):
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if V3.CELLS[cell]['kind'] == 'pair' else [])
        mine = S.chain_audit({s: S.operator_calls(operator, units, s) for s in sides})
        theirs = manifest['operator_audit'][cell]
        assert mine == theirs, (cell, mine, theirs)
        checked.append(cell)
    return f'{", ".join(checked)} reproduce the manifest exactly'


def test_recomputed_audit_uses_the_loaded_operator_not_the_manifest():
    """The stored audit must equal the replacement operator's own answers."""
    folder = scratch('audit')
    summary = S.score_pairing(SEED0, str(GROW_BLIND0), PANELS, folder, label='t',
                              cells={'k5-held'}, verbose=False)
    stored = summary['cells']['k5-held']['replacement_operator_on_true_chains']
    _manifest, panels, _forbidden = V3.load_panels(PANELS)
    operator = V3.make_operator(str(GROW_BLIND0))
    expected = S.chain_audit({'a': S.operator_calls(operator, panels['k5-held']['units'], 'a')})
    assert stored == expected, (stored, expected)
    frozen = json.loads((Path(PANELS) / 'manifest.json').read_text())['operator_audit']['k5-held']
    written = json.loads((folder / 'operator_chain_audit.json').read_text())
    assert written['operator_sha256'] == S.sha(GROW_BLIND0)
    assert written['copied_from_panels'] is False
    return (f'recomputed {stored["stages_correct"]}/{stored["stages"]}, '
            f'stale manifest said {frozen["stages_correct"]}/{frozen["stages"]}')


def test_panel_directory_is_not_written():
    before = {p.name: S.sha(p) for p in sorted(Path(PANELS).iterdir())}
    S.score_pairing(SEED0, str(GROW_BLIND0), PANELS, scratch('readonly'), label='t',
                    cells={'k1-prac'}, verbose=False)
    after = {p.name: S.sha(p) for p in sorted(Path(PANELS).iterdir())}
    assert before == after, 'the registered panel directory changed'
    return f'{len(before)} panel files unchanged'


# --------------------------------------------------------------------------- marks and failures


def test_cell_marks():
    assert S.cell_marks(dict(answers=58, strict=58, unit_pass=58)) == \
        dict(answers=True, strict=True, unit_pass=True)
    assert S.cell_marks(dict(answers=57, strict=64, unit_pass=64))['answers'] is False
    assert S.cell_marks(dict(answers=64, strict=57, unit_pass=64))['strict'] is False
    assert S.cell_marks(dict(answers=64, strict=64, unit_pass=57))['unit_pass'] is False
    assert S.CELL_MARK == 58, 'the ORIGINAL registered mark, not the observed 59'
    return 'mark 58/64 on answers, strict and unit_pass'


def test_failing_units_reports_transcripts_errors_and_the_oracle():
    def row(index, correct, strict, answer, transcript):
        return dict(index=index, correct=correct, strict_path=strict, answer=answer,
                    target=7, status='answered', calls=2, transcript=transcript,
                    pointers=[], truth_chain=[[52, 11, 53], [53, 10, 7]])
    scored = {S.REGISTERED_OPERATOR_LABEL: {'a': [row(0, 1, 1, 7, [[52, 11, 53]]),
                                                  row(1, 0, 0, 5, [[52, 11, 99]])]},
              S.CONTROL_OPERATOR_LABEL: {'a': [row(0, 1, 1, 7, [[52, 11, 53]]),
                                               row(1, 1, 1, 7, [[52, 11, 53]])]}}
    calls = {'a': [[dict(entity=52, operation=11, target=53, predicted=53, hit=1)],
                   [dict(entity=52, operation=11, target=53, predicted=99, hit=0)]]}
    found = S.failing_units(scored, V3.CELLS['k2-held'], calls)
    assert [f['index'] for f in found] == [1]
    assert found[0]['operator_calls_wrong'] == 1 and found[0]['operator_calls_total'] == 1
    assert found[0]['operator_call_errors']['a'][0]['predicted'] == 99
    assert found[0]['native']['a']['transcript'] == [[52, 11, 99]]
    assert found[0]['oracle_control']['a']['correct'] == 1
    return 'failing unit carries native, oracle and per-call error'


def test_invariant_pair_failure_is_caught():
    """A pair whose twins are both 'correct' but disagree still fails an invariant cell."""
    def row(answer):
        return dict(index=0, correct=1, strict_path=1, answer=answer, target=answer,
                    status='answered', calls=1, transcript=[], pointers=[], truth_chain=[])
    scored = {S.REGISTERED_OPERATOR_LABEL: {'a': [row(7)], 'b': [row(8)]},
              S.CONTROL_OPERATOR_LABEL: {'a': [row(7)], 'b': [row(7)]}}
    calls = {'a': [[]], 'b': [[]]}
    assert V3.CELLS['pair-irrelevant']['invariant'] is True
    found = S.failing_units(scored, V3.CELLS['pair-irrelevant'], calls)
    assert len(found) == 1 and found[0]['twins_identical'] == 0
    assert not S.failing_units(scored, V3.CELLS['pair-link'], calls), \
        'a non-invariant cell must not require identical twins'
    return 'twin invariance enforced only where registered'


# --------------------------------------------------------------------------- manifest


def test_freeze_and_verify():
    folder = scratch('freeze')

    class Args:
        out = str(folder)
        panels = str(PANELS)
        dispatcher_root = str(S.DEFAULT_DISPATCHER_ROOT)
        operator_root = str(S.DEFAULT_OPERATOR_ROOT)
        seeds = '0,1,2'
        mark = S.CELL_MARK
        eval_cap = S.EVAL_CAP

    manifest = S.freeze(Args)
    assert sorted(manifest['pairs']) == ['0', '1', '2']
    for key, row in manifest['pairs'].items():
        assert row['dispatcher_seed'] == row['operator_seed'] == int(key), 'no substitution'
        assert row['operator_sha256'] == S.sha(S.operator_path(int(key)))
        assert 'grow-blind' in row['operator_checkpoint']
        assert 'rl-cost01' in row['dispatcher_run']
    assert manifest['seed_substitution_allowed'] is False
    assert manifest['registered_mark'] == 58 and manifest['eval_cap'] == 16
    _loaded, problems = S.verify_manifest(folder)
    assert problems == [], problems
    return f'6 checkpoints frozen, {len(manifest["panel_files"])} panel hashes'


def test_freeze_refuses_to_repeat():
    folder = scratch('refreeze')

    class Args:
        out = str(folder)
        panels = str(PANELS)
        dispatcher_root = str(S.DEFAULT_DISPATCHER_ROOT)
        operator_root = str(S.DEFAULT_OPERATOR_ROOT)
        seeds = '0'
        mark = S.CELL_MARK
        eval_cap = S.EVAL_CAP

    S.freeze(Args)
    try:
        S.freeze(Args)
    except FileExistsError:
        return 'a second freeze into the same folder is refused'
    raise AssertionError('freeze overwrote an existing manifest')


def test_verify_manifest_catches_a_changed_checkpoint():
    folder = scratch('tamper')

    class Args:
        out = str(folder)
        panels = str(PANELS)
        dispatcher_root = str(S.DEFAULT_DISPATCHER_ROOT)
        operator_root = str(S.DEFAULT_OPERATOR_ROOT)
        seeds = '0'
        mark = S.CELL_MARK
        eval_cap = S.EVAL_CAP

    S.freeze(Args)
    path = folder / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['pairs']['0']['operator_sha256'] = '0' * 64
    path.write_text(json.dumps(manifest))
    _loaded, problems = S.verify_manifest(folder)
    assert any('operator checkpoint changed' in p for p in problems), problems
    return problems[0]


# --------------------------------------------------------------------------- replication


def test_replication_reproduces_the_registered_v3_scores():
    """The additive scorer + the ORIGINAL operator == the registered v3 numbers."""
    folder = scratch('replicate')
    cells = None if FULL else set(SMALL_CELLS)
    summary = S.score_pairing(SEED0, str(ORIGINAL), PANELS, folder, label='replication',
                              cells=cells, verbose=False)
    registered = json.loads((SEED0 / 'score/scores.json').read_text())
    differences = {}
    for cell, row in summary['cells'].items():
        theirs = registered['cells'][cell]['trained_operator']
        mine = row[S.REGISTERED_OPERATOR_LABEL]
        diff = {k: [theirs[k], mine[k]] for k in
                ('answers', 'strict', 'loose', 'unit_pass', 'over_cap', 'invalid')
                if theirs[k] != mine[k]}
        if diff:
            differences[cell] = diff
    assert differences == {}, differences
    oracle = {cell: row[S.CONTROL_OPERATOR_LABEL]['answers']
              for cell, row in summary['cells'].items()}
    assert oracle, 'the oracle control must also be scored'
    return f'{len(summary["cells"])} cells identical to the registered scores'


def test_pairing_pass_needs_every_cell():
    """A partial run can never report a pass."""
    folder = scratch('partial')
    summary = S.score_pairing(SEED0, str(ORIGINAL), PANELS, folder, label='t',
                              cells={'k1-prac'}, verbose=False)
    assert summary['complete'] is False and summary['pairing_pass'] is False
    assert summary['cells']['k1-prac']['cell_pass'] is True
    return 'one cell passes, the pairing does not'


def test_outputs_are_complete():
    folder = scratch('outputs')
    S.score_pairing(SEED0, str(GROW_BLIND0), PANELS, folder, label='t',
                    cells={'k1-prac'}, verbose=False)
    names = sorted(p.name for p in folder.iterdir())
    assert names == ['failures.json', 'operator_chain_audit.json', 'scores.json',
                     'transcripts.json'], names
    summary = json.loads((folder / 'scores.json').read_text())
    for key in ('dispatcher_fingerprint_before', 'dispatcher_fingerprint_after',
                'operator_fingerprint_before', 'operator_fingerprint_after',
                'panel_manifest_sha256', 'panel_files', 'dispatcher_checkpoint_sha256'):
        assert summary.get(key), key
    assert summary['dispatcher_fingerprint_before'] == summary['dispatcher_fingerprint_after']
    assert summary['operator_fingerprint_before'] == summary['operator_fingerprint_after']
    transcripts = json.loads((folder / 'transcripts.json').read_text())
    assert set(transcripts['k1-prac']) == {S.REGISTERED_OPERATOR_LABEL,
                                           S.CONTROL_OPERATOR_LABEL}
    return ', '.join(names)


def test_eval_cap_and_policy_unchanged():
    assert S.EVAL_CAP == V3.EVAL_CAP == 16
    assert S.CELL_MARK == V3.CELL_MARK
    source = Path(S.__file__).read_text()
    for banned in ('def rollout', 'def candidate_features', 'class Dispatcher'):
        assert banned not in source, f'{banned} must be v3\'s, not copied here'
    return 'executor, features and model all imported from v3'


def main():
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for name, function in tests:
        check(name[5:].replace('_', ' '), function)
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    print(f'\n{PASSED} passed, {len(FAILED)} failed', flush=True)
    if FAILED:
        for name, detail in FAILED:
            print(f'  {name}: {detail}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
