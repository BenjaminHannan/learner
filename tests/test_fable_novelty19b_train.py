"""Checks for scripts/fable_novelty19b_train.py.  Plain script; no pytest.

Run:
    OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
        python3.12 -B tests/test_fable_novelty19b_train.py

Experiment 19b reuses the frozen experiment-19 trainer for everything that decides a
number, so these checks deliberately do NOT re-verify the frozen machinery -- chunked
resume bit-identity, the optimizer reset, operator freezing and the rest are checked by
`tests/test_fable_novelty19_train.py` against the same code.  What is checked here is
exactly what 19b adds:

  * the cap/STOP boundary Astra told us to verify on a disposable fixture, run for real;
  * that the work ledger cannot change the training path, by object identity;
  * that the training and data modules agree about what experiment this is;
  * that the five conditions are read over the right cells, by TWO independent
    derivations that must agree;
  * that each condition passes, fails and abstains where Astra's text says it should,
    including the H-loss boundary and the paired-unit contrast;
  * that a DEV-PASSED.json is written only on a full pass, and only in the shape the
    data module's own lockout accepts.

Fixtures use disposable seeds >= 999000 and synthetic score files.  The registered seeds
1900/1901/1902 are never trained here, no registered artifact is written, the real
development panels are never generated, and no `test.pt` is read.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_novelty19_train as TR                                          # noqa: E402
import fable_novelty19b_train as B                                          # noqa: E402
import fable_novelty19b_data as D                                           # noqa: E402

FIXTURE_SEED = 999411            # disposable; far from 1900/1901/1902
SPEC = HERE.parent / 'design' / 'v3' / '19-development-readout-and-next-step.md'

PASSED = 0
FAILED = []
SKIPPED = []
TEMP = []


class _Skip(Exception):
    pass


def check(name, function):
    global PASSED
    try:
        detail = function()
    except _Skip as skip:
        SKIPPED.append((name, str(skip)))
        print(f'skip  {name}: {skip}', flush=True)
        return
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'novelty19b-train-{name}-'))
    TEMP.append(folder)
    return folder


def fake_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


FAKE_FINGERPRINT = dict(novelty19_train=fake_sha('trainer-v1'),
                        novelty19b_train=fake_sha('19b-trainer-v1'),
                        novelty19b_data=fake_sha('19b-data-v1'),
                        torch='0.0.0+fixture')


# --------------------------------------------------------------- fixtures


def fake_panels(exp):
    """A real manifest file: the unlock record is checked against its bytes."""
    folder = Path(exp) / 'dev-panels'
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / 'manifest.json'
    if not manifest.exists():
        manifest.write_text(json.dumps(dict(kind='development', namespace=D.NS_DEV,
                                            experiment='19b', n=B.UNITS_PER_CELL)))
    return folder, TR.sha(manifest)


def fake_run_dir(exp, seed, phase, arm, *, ckpt_sha=None, complete=True):
    name = B.run_key(seed, phase, arm)
    folder = Path(exp) / 'runs' / name
    folder.mkdir(parents=True, exist_ok=True)
    updates = TR.AWAKE_UPDATES if phase == 'awake' else B.OFFLINE_UPDATES
    ckpt = folder / TR.checkpoint_name(updates)
    (folder / 'completion.json').write_text(json.dumps(dict(
        kind='novelty19-run', arch='D', seed=int(seed), phase=phase, arm=arm,
        complete=bool(complete), updates_done=updates, total_updates=updates,
        checkpoint=str(ckpt), checkpoint_sha256=ckpt_sha or fake_sha(name))))
    return ckpt


def cell_row(cell, answers, strict, *, n=B.UNITS_PER_CELL):
    spec = B.cell_specs()[cell]
    return dict(cell=cell, family=B.family_of(cell), n=n, answers=int(answers),
                strict=int(strict), loose=int(strict), mean_calls=float(spec['hops']),
                over_cap=0, invalid=0, answered=n, unit_pass=int(strict),
                hops=spec['hops'], people=spec['people'], kind=spec['kind'],
                terminal=spec['terminal'], fixed_terminal=spec['fixed_terminal'],
                failure_shapes=dict(calls_histogram={str(spec['hops']): n},
                                    first_wrong_call={}, stopped_early=0, stopped_late=0,
                                    over_cap=0, invalid_action=0,
                                    frozen_operator_wrong_on_true_chain=0),
                oracle_operator=dict(strict=int(strict)))


def flags_for(strict, *, n=B.UNITS_PER_CELL, offset=0, index=None):
    """Per-unit flags with `strict` successes, placed deterministically."""
    hits = {(i * 7 + offset) % n for i in range(int(strict))}
    while len(hits) < int(strict):
        hits.add(max(hits, default=-1) + 1)
    return dict(unit_index=list(index if index is not None else range(n)),
                answers=[1] * n, strict=[1 if i in hits else 0 for i in range(n)],
                calls=[1] * n)


def fake_score(exp, seed, phase, arm, *, counts=None, unit_flags=None, panels=None,
               panel_sha=None, extra=None, name=None, run=True, complete=True):
    folder = Path(exp) / 'scores'
    folder.mkdir(parents=True, exist_ok=True)
    if panels is None:
        panels, disk = fake_panels(exp)
        panel_sha = panel_sha or disk
    key = B.run_key(seed, phase, arm)
    registered = TR.AWAKE_UPDATES if phase == 'awake' else B.OFFLINE_UPDATES
    ckpt = (fake_run_dir(exp, seed, phase, arm, complete=complete) if run
            else Path(exp) / 'runs' / key / TR.checkpoint_name(registered))
    counts = counts or {}
    cells = {c: cell_row(c, *counts.get(c, (64, 64))) for c in B.cell_order()}
    payload = dict(kind='novelty19b-score', experiment='novelty19b', arch='D',
                   seed=int(seed), phase=phase, arm=arm,
                   updates_done=registered, total_updates=registered,
                   checkpoint=str(ckpt), checkpoint_sha256=fake_sha(key),
                   eval_cap=B.EVAL_CAP, registered_caps=True,
                   panels=str(Path(panels).resolve()), panel_manifest_sha256=panel_sha,
                   panel_kind='development', panel_namespace=D.NS_DEV,
                   source_fingerprint=dict(FAKE_FINGERPRINT),
                   n_per_cell=B.UNITS_PER_CELL, cell_order=list(B.cell_order()),
                   cells=cells,
                   unit_flags=unit_flags or {c: flags_for(cells[c]['strict'])
                                             for c in cells})
    payload.update(extra or {})
    (folder / f'{name or key}.json').write_text(json.dumps(payload))
    return payload


def fake_buffers(exp, *, zero_exposure=True):
    """One buffers folder per seed, holding both arms and ONE shared order file.

    Condition 5 reads the buffers' own audit for composite-r10 exposure and checks that
    the arms share a world-index order, so a fixture without them abstains rather than
    passes -- which is correct, and is why they are built here.
    """
    for seed in B.SEEDS:
        folder = Path(exp) / f'buffers-{seed}'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'manifest.json').write_text(json.dumps(dict(
            kind='buffers', experiment='19b', seed=int(seed), arms=list(B.ARMS),
            files={f'buffer-{a}.pt': fake_sha(f'{seed}-{a}') for a in B.ARMS})))
        (folder / 'offline-order.json').write_text(json.dumps(dict(
            seed=int(seed), updates=B.OFFLINE_UPDATES, order=[0, 1, 2])))
        (folder / 'audit.json').write_text(json.dumps(dict(
            kind='buffers', seed=int(seed),
            composite_r10_exposure=dict(zero_exposure=bool(zero_exposure), sources={}))))
    return exp


def passing_experiment(folder, *, treatment=None, control=None, awake=None, gap=20,
                       zero_exposure=True):
    """Six continuations and three anchors that satisfy every condition."""
    groups = B.groups()
    fake_buffers(folder, zero_exposure=zero_exposure)
    for seed in B.SEEDS:
        fake_score(folder, seed, 'awake', None, counts=dict(awake or {}))
        for arm in B.ARMS:
            counts = dict(control or {}) if arm == B.CONTROL_ARM else dict(treatment or {})
            flags = {}
            for cell in B.cell_order():
                strict = counts.get(cell, (64, 64))[1]
                # the control trails the treatment by `gap` on the contrast cells
                if arm == B.CONTROL_ARM and cell in groups['contrast']:
                    strict = max(0, strict - gap)
                    counts[cell] = (64, strict)
                flags[cell] = flags_for(strict)
            fake_score(folder, seed, 'offline', arm, counts=counts, unit_flags=flags)
    return folder


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# --------------------------------------------------------------- the cap / STOP boundary


def test_the_training_cap_and_stop_boundary_are_what_astra_registered():
    """Astra: cap 8, STOP sampled AFTER the 8th lookup, an exhausted episode fails."""
    verdict = B.cap_probe(Args(seed=999990, cell='k1-prac', units=4, out=None))
    assert verdict['train_cap'] == 8 and verdict['eval_cap'] == 16, verdict
    assert verdict['stop_sampled_after_the_last_lookup'], verdict
    assert verdict['cap_length_answer_terminates_normally'], verdict
    assert verdict['exhausted_episode_fails'], verdict
    assert verdict['override_needed'] is False, verdict
    text = SPEC.read_text()
    assert 'training cap eight/evaluation cap sixteen' in text, 'the spec sentence moved'
    assert 'a continuing episode exhausted at the cap fails' in text
    return (f'cap 8: STOP sampled at 8 steps; 8-call answer -> answered; '
            f'never-STOP -> over_cap; no override needed')


def test_the_registered_settings_match_the_frozen_trainer_and_the_specification():
    assert B.TRAIN_CAP is TR.D_TRAIN_CAP and B.EVAL_CAP is TR.D_EVAL_CAP
    assert B.OFFLINE_UPDATES == 2000, B.OFFLINE_UPDATES
    assert B.OFFLINE_CHUNK == TR.OFFLINE_CHUNK == 500
    assert B.EPISODES_PER_UPDATE == 16 * 4 * 16 == 1024, B.EPISODES_PER_UPDATE
    text = SPEC.read_text()
    assert 'exactly **2,000 updates**' in text, 'the 2,000-update sentence moved'
    assert '16 worlds × four questions, K=16' in text
    return 'cap 8/16, 2,000 updates, chunk 500, 16x4xK16 = 1,024 episodes/update'


# --------------------------------------------------------------- the work ledger


def test_the_work_ledger_cannot_change_the_training_path():
    """The row the frozen update built must reach the caller as the SAME OBJECT.

    The update fingerprint is chained from that row, so object identity is a stronger
    statement than equality: the ledger cannot have rewritten a field, because there is
    only one dict and the frozen code owns it.
    """
    folder = scratch('ledger')
    rows = [dict(update=i, mean_calls=2.0 + i, mean_reward=0.5, entropy=0.1,
                 invalid_fraction=0.0, over_cap_fraction=0.25) for i in range(3)]
    original = TR.dispatcher_update
    seen = []
    try:
        TR.dispatcher_update = lambda *a, **k: rows[len(seen)]
        with B.work_ledger(folder) as ledger:
            for _ in rows:
                seen.append(TR.dispatcher_update(None, None, None, None, None, None, 0, 0))
            summary = ledger.summary()
    finally:
        TR.dispatcher_update = original
    assert all(a is b for a, b in zip(seen, rows)), 'the ledger replaced the row object'
    assert TR.dispatcher_update is original, 'the frozen name was not restored'
    written = sorted(folder.glob('work-*.jsonl'))
    assert len(written) == 1, [p.name for p in written]
    entries = [json.loads(line) for line in written[0].read_text().splitlines()]
    assert len(entries) == 3 and entries[0]['active_calls'] == 2 * 1024, entries[0]
    assert summary['updates'] == 3 and summary['active_calls_total'] == sum(
        e['active_calls'] for e in entries)
    return f'3 updates recorded, rows returned by identity, {written[0].name}'


def test_work_counts_executed_lookups_not_updates():
    row = dict(update=7, mean_calls=6.5, mean_reward=0.2, entropy=0.3,
               invalid_fraction=0.125, over_cap_fraction=0.25)
    got = B.work_row(7, row)
    assert got['active_calls'] == round(6.5 * 1024), got
    assert abs(got['answered_fraction'] - 0.625) < 1e-9, got
    assert 'Record active calls and work' in SPEC.read_text()
    return 'mean_calls 6.5 x 1,024 episodes = 6,656 executed lookups; answered 62.5%'


# --------------------------------------------------------------- what experiment is this


def test_the_training_and_data_modules_agree_about_the_experiment():
    layout = B.check_layout_agrees()
    assert layout['cells'] == 38 and layout['arms'] == ['U5', 'U8']
    assert layout['seeds'] == [1900, 1901, 1902]
    return f'{len(layout["checked"])} constants compared with {layout["data_module"]}'


def test_a_data_module_that_disagrees_is_refused():
    stub = types.ModuleType('fake19b')
    stub.__file__ = D.__file__
    stub.CELLS, stub.CELL_ORDER = D.CELLS, D.CELL_ORDER
    stub.ARMS, stub.SEEDS = ('U5', 'U9'), D.SEEDS          # a different treatment arm
    stub.OFFLINE_UPDATES, stub.DEV_N = 2000, 64
    with B.use_data_module(stub):
        try:
            B.check_layout_agrees()
        except SystemExit as exc:
            assert 'U9' in str(exc) and 'not one experiment' in str(exc), str(exc)
            return 'a data module naming a different arm is refused by name'
    raise AssertionError('a disagreeing data module was accepted')


def test_the_five_conditions_are_read_over_the_cells_astra_named():
    groups = B.groups()
    expected = B.expected_group_sizes()
    for name, size in expected.items():
        assert len(groups[name]) == size, f'{name}: {len(groups[name])} != {size}'
    assert len(set(groups['all'])) == 38
    # 26 old N/P/F/H/E + nine long + three c=8 edit pairs, as Astra's arithmetic says
    families = {}
    for cell in groups['all']:
        families[B.family_of(cell)] = families.get(B.family_of(cell), 0) + 1
    assert families == dict(N=4, E=6, F=7, P=8, H=4, L=9), families
    practised, held = B.split_long_cells(groups)
    assert len(practised) == 6 and len(held) == 3
    assert set(held) == set(groups['contrast']), (held, groups['contrast'])
    assert 'There are **38 cells**' in SPEC.read_text()
    return (f'38 cells {families}; bounded 21, contrast 3, guards 6, F 7, H 4; '
            f'held-out ending = the three r10 long cells')


def test_published_and_derived_cell_groups_must_agree():
    """MARKS is authoritative, but a MARKS that contradicts the specs is a refusal."""
    stub = types.ModuleType('fake19b')
    stub.__file__ = D.__file__
    stub.CELLS, stub.CELL_ORDER = D.CELLS, D.CELL_ORDER
    marks = json.loads(json.dumps(D.MARKS))
    marks['treatment_effect']['cells'] = ['L-c6-r8-p16']     # a practised ending, not r10
    stub.MARKS = marks
    with B.use_data_module(stub):
        try:
            B.groups(stub)
        except SystemExit as exc:
            assert 'disagree' in str(exc) and 'contrast' in str(exc), str(exc)
            return 'a MARKS list that contradicts the cell specifications is refused'
    raise AssertionError('contradictory cell groups were accepted')


# --------------------------------------------------------------- the conditions


def test_bounded_competence_needs_both_metrics_in_every_cell():
    groups = B.groups()
    entry = dict(cells={c: cell_row(c, 64, 64) for c in groups['bounded']})
    assert B.condition_bounded(entry, groups['bounded'])['passed'] is True
    entry['cells']['N-c4-p6'] = cell_row('N-c4-p6', 64, 57)      # strict one short
    verdict = B.condition_bounded(entry, groups['bounded'])
    assert verdict['passed'] is False and verdict['failed_cells'] == ['N-c4-p6'], verdict
    entry['cells']['N-c4-p6'] = cell_row('N-c4-p6', 57, 64)      # answers one short
    assert B.condition_bounded(entry, groups['bounded'])['passed'] is False
    del entry['cells']['L-c8-r10-p16']
    absent = B.condition_bounded(entry, groups['bounded'])
    assert absent['passed'] is False and 'L-c8-r10-p16' in absent['absent_cells']
    return '58/64 in BOTH metrics; 57 fails in either; a missing cell abstains'


def test_the_treatment_effect_is_paired_on_identical_units():
    treatment = dict(unit_flags={'c': flags_for(40, offset=0)})
    control = dict(unit_flags={'c': flags_for(27, offset=0)})
    verdict = B.condition_contrast(treatment, control, ['c'])
    row = verdict['cells']['c']
    assert row['difference'] == 13 and verdict['passed'] is True, row
    assert row['wins'] - row['losses'] == 13, row
    assert row['wins'] + row['losses'] + row['ties'] == 64, row
    control12 = dict(unit_flags={'c': flags_for(28, offset=0)})
    assert B.condition_contrast(treatment, control12, ['c'])['passed'] is False
    mismatched = dict(unit_flags={'c': flags_for(27, index=list(range(100, 164)))})
    other = B.condition_contrast(treatment, mismatched, ['c'])['cells']['c']
    assert other['passed'] is None and 'different units' in other['reason'], other
    return 'difference 13 passes, 12 fails, wins/losses published, unit mismatch abstains'


def test_the_guards_count_strict_pair_units():
    groups = B.groups()
    entry = dict(cells={c: cell_row(c, 64, 58) for c in groups['guards']})
    assert B.condition_guards(entry, groups['guards'])['passed'] is True
    entry['cells']['E-c8-link'] = cell_row('E-c8-link', 64, 57)
    verdict = B.condition_guards(entry, groups['guards'])
    assert verdict['passed'] is False and verdict['failed_cells'] == ['E-c8-link']
    assert all(B.cell_specs()[c]['kind'] == 'pair' for c in groups['guards'])
    return 'six E pair cells (c=5 and c=8) at 58/64 strict pair units'


def test_retention_h_fails_on_a_loss_of_seven_even_when_the_mark_is_met():
    """Astra's stricter H guard: 58/64 is not enough if the awake anchor was 7 higher."""
    groups = B.groups()
    f_cells, h_cells = groups['retention_f'], groups['retention_h']
    entry = dict(cells={c: cell_row(c, 64, 61) for c in f_cells})
    entry['cells'].update({c: cell_row(c, 64, 64) for c in h_cells})
    anchor = dict(cells={c: cell_row(c, 64, 64) for c in h_cells})
    assert B.condition_retention(entry, anchor, f_cells, h_cells)['passed'] is True
    entry['cells']['H-c2-p6'] = cell_row('H-c2-p6', 64, 58)      # meets 58, lost 6
    assert B.condition_retention(entry, anchor, f_cells, h_cells)['passed'] is True
    anchor['cells']['H-c2-p6'] = cell_row('H-c2-p6', 64, 65)     # now the loss is 7
    verdict = B.condition_retention(entry, anchor, f_cells, h_cells)
    assert verdict['passed'] is False, verdict['cells']['H-c2-p6']
    assert verdict['cells']['H-c2-p6']['strict_loss'] == 7
    entry['cells']['F-c1-r8'] = cell_row('F-c1-r8', 64, 60)      # F needs 61, not 58
    assert B.condition_retention(entry, anchor, f_cells, h_cells)['cells']['F-c1-r8'][
        'passed'] is False
    return 'H: 58 met but a 7/64 loss from the anchor still fails; F needs 61'


def test_a_failing_seed_is_not_rescued_by_the_others():
    folder = passing_experiment(scratch('per-seed'))
    # seed 1902's treatment arm loses one strict trace in one bounded cell
    target = folder / 'scores' / f'{B.run_key(1902, "offline", "U8")}.json'
    payload = json.loads(target.read_text())
    payload['cells']['N-c5-p16'] = cell_row('N-c5-p16', 64, 57)
    target.write_text(json.dumps(payload))
    collected = B.collect_scores(folder)
    rule = B.development_rule(collected, folder)
    assert rule['per_seed'][1900]['passed'] is True
    assert rule['per_seed'][1901]['passed'] is True
    assert rule['per_seed'][1902]['passed'] is False
    assert rule['passed'] is False, 'two passing seeds rescued a failing one'
    assert 'No averaging rescues a failing cell or seed' in SPEC.read_text()
    return 'one cell, one seed, 57/64 -> the whole development rule is FAIL'


# --------------------------------------------------------------- merging and provenance


def test_every_endpoint_must_be_present():
    folder = scratch('endpoints')
    fake_score(folder, 1900, 'awake', None)
    collected = B.collect_scores(folder)
    assert len(collected['missing']) == 8, collected['missing']
    assert 'offline-D-s1900-U8' in collected['missing']
    rule = B.development_rule(collected, folder)
    assert rule['provenance']['parts']['every_endpoint']['passed'] is None
    assert rule['passed'] is None, 'an absent endpoint must abstain, not fail'
    return '9 endpoints required (3 anchors + 6 continuations); 8 missing -> undetermined'


def test_a_score_at_an_unregistered_cap_is_rejected():
    folder = scratch('cap')
    fake_score(folder, 1900, 'awake', None,
               extra=dict(eval_cap=8, registered_caps=False))
    collected = B.collect_scores(folder)
    assert not collected['runs'] and len(collected['rejected']) == 1
    assert 'eval cap 8' in collected['rejected'][0]['reason']
    return 'a score taken at cap 8 is refused, not merged'


def test_a_score_of_an_unfinished_run_is_rejected():
    folder = scratch('binding')
    fake_score(folder, 1900, 'awake', None, complete=False)
    collected = B.collect_scores(folder)
    assert not collected['runs'] and collected['rejected'], collected
    assert collected['rejected'][0]['reason'] == TR.WRONG_CKPT
    assert 'awake-D-s1900' in collected['rejected_runs']
    return 'completion.json says the run never finished -> "(wrong checkpoint)"'


def test_merged_runs_must_come_from_one_frozen_script_version():
    folder = passing_experiment(scratch('version'))
    target = folder / 'scores' / f'{B.run_key(1901, "offline", "U8")}.json'
    payload = json.loads(target.read_text())
    payload['source_fingerprint'] = dict(FAKE_FINGERPRINT,
                                         novelty19b_train=fake_sha('19b-trainer-v2'))
    target.write_text(json.dumps(payload))
    collected = B.collect_scores(folder)
    version = B.trainer_version(collected)
    assert version['passed'] is False and version['distinct'] == 2, version
    assert 'offline-D-s1901-U8' in version['offending_runs'], version
    try:
        B.report(Args(exp=folder, seed_list=B.SEEDS, out=None, overwrite=False))
    except SystemExit as exc:
        assert 'one frozen script version' in str(exc), str(exc)
        assert (folder / 'report.json').is_file(), 'the evidence was lost with the refusal'
        return 'two script versions among the merged runs -> refused, report still written'
    raise AssertionError('a mixed-version merge was reported as a result')


def test_the_arms_must_share_one_world_index_order():
    folder = scratch('order')
    for seed in B.SEEDS:
        buffers = folder / f'buffers-{seed}'
        buffers.mkdir(parents=True)
        (buffers / 'manifest.json').write_text(json.dumps(dict(seed=seed, arms=['U5', 'U8'])))
        (buffers / 'offline-order.json').write_text(json.dumps(dict(seed=seed, order=[1, 2])))
    shared = B.shared_order(folder, 1900)
    assert shared['passed'] is True and len(set(shared['per_arm'].values())) == 1
    return 'one buffers folder per seed: both arms read the same offline-order.json bytes'


# --------------------------------------------------------------- the verdict


def test_a_full_pass_writes_an_unlock_record_the_data_module_accepts():
    folder = passing_experiment(scratch('pass'))
    payload = B.report(Args(exp=folder, seed_list=B.SEEDS, out=None, overwrite=False))
    rule = payload['development_rule']
    assert rule['passed'] is True, [k for k, v in rule['per_seed'].items()
                                    if v['passed'] is not True]
    flag = folder / 'DEV-PASSED.json'
    assert flag.is_file(), 'a full pass wrote no unlock record'
    doc = json.loads(flag.read_text())
    assert doc['schema'] == D.DEV_PASSED_SCHEMA
    assert set(doc['awake_checkpoints']) == set(D.checkpoint_keys('awake'))
    assert set(doc['offline_checkpoints']) == set(D.checkpoint_keys('offline'))
    record = D.validate_dev_passed(folder)       # the real lockout, not a re-implementation
    assert record['awake_checkpoints'] == 3 and record['offline_checkpoints'] == 6
    assert payload['dev_passed_record']['sha256'] == TR.sha(flag)
    return (f'DEV-PASSED.json accepted by {D.__name__}.validate_dev_passed '
            f'(3 awake + 6 offline checkpoints, panel manifest bound by sha)')


def test_no_unlock_record_when_a_condition_fails():
    groups = B.groups()
    folder = passing_experiment(scratch('fail'),
                               treatment={groups['contrast'][0]: (64, 30)})
    try:
        payload = B.report(Args(exp=folder, seed_list=B.SEEDS, out=None, overwrite=False))
    except SystemExit as exc:                                   # pragma: no cover
        raise AssertionError(f'report refused instead of reporting a FAIL: {exc}') from None
    assert payload['development_rule']['passed'] is False
    assert not (folder / 'DEV-PASSED.json').exists(), 'a failing rule unlocked confirmation'
    assert (folder / 'report.json').is_file()
    return 'the treatment contrast fails -> report written, confirmation stays locked'


def test_confirmation_is_not_built_but_its_marks_are_recorded():
    marks = B.confirmation_marks()
    assert (marks['units'], marks['bounded'], marks['retention_f'], marks['gain'],
            marks['h_loss']) == (512, 464, 488, 104, 56), marks
    assert marks['bounded'] == B.BOUNDED_MARK * 8 and marks['gain'] == B.GAIN_MARK * 8
    assert 'Scale 58→464, 61→488, 13→104, and the H loss boundary 7→56' in SPEC.read_text()
    assert B.EXP2.name == 'fable-novelty19b-u8-20260920'
    return '58->464, 61->488, 13->104, 7->56 at 512 units; nothing built for confirmation'


def test_the_report_names_a_missing_run_rather_than_scoring_it_zero():
    folder = passing_experiment(scratch('missing'))
    (folder / 'scores' / f'{B.run_key(1901, "awake", None)}.json').unlink()
    payload = B.report(Args(exp=folder, seed_list=B.SEEDS, out=None, overwrite=False))
    assert 'awake-D-s1901' in payload['missing_runs']
    assert TR.MISSING in payload['text'], 'the absent anchor was not marked "(missing)"'
    rule = payload['development_rule']
    assert rule['per_seed'][1901]['parts']['retention']['passed'] is None
    assert rule['passed'] is None and not (folder / 'DEV-PASSED.json').exists()
    return 'an absent awake anchor prints "(missing)" and leaves the rule undetermined'


def test_astras_interpretive_cases_are_raised_when_they_apply():
    """Both readings Astra warns about, each on the outcome that produces it."""
    groups = B.groups()

    # (i) U5 is also competent and the gain mark is missed: the widening is unestablished
    near = passing_experiment(scratch('cases-u5'), gap=6)
    cases = B.report(Args(exp=near, seed_list=B.SEEDS, out=None,
                          overwrite=False))['development_rule']['interpretive_cases']
    assert cases['u5_also_competent']['holds'] is True, cases['u5_also_competent']
    assert cases['treatment_effect_all_seeds'] is False
    assert cases['extra_calls_are_not_a_pass']['holds'] is True

    # (ii) only the practised endings succeed: held-out-ending transfer has failed
    split = passing_experiment(scratch('cases-endings'),
                               treatment={c: (64, 30) for c in groups['contrast']})
    payload = B.report(Args(exp=split, seed_list=B.SEEDS, out=None, overwrite=False))
    other = payload['development_rule']['interpretive_cases']
    assert other['only_practised_endings_succeed']['holds'] is True, other[
        'only_practised_endings_succeed']
    assert set(other['only_practised_endings_succeed']['held_out_ending_cells']) == set(
        groups['contrast'])
    assert 'interpretive cases' in payload['text']
    assert 'Extra calls with wrong paths are not a pass' in SPEC.read_text()
    return ('U5-also-competent raised when the gain is +6, held-out-ending failure '
            'raised when only r8/r9 long cells pass; neither is ever a pass')


# --------------------------------------------------------------- runner


def main():
    print(f'novelty19b training checks   fixture seed {FIXTURE_SEED}   '
          f'registered seeds {B.SEEDS} are NOT trained here', flush=True)
    names = sorted(n for n in globals() if n.startswith('test_'))
    for name in names:
        check(name.replace('test_', '', 1), globals()[name])
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    print(f'\n{PASSED} passed, {len(FAILED)} failed, {len(SKIPPED)} skipped '
          f'out of {len(names)}', flush=True)
    for name, detail in FAILED:
        print(f'  FAIL {name}: {detail}', flush=True)
    for name, detail in SKIPPED:
        print(f'  skip {name}: {detail}', flush=True)
    if FAILED:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
