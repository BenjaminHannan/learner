"""Checks for `scripts/fable_novelty19b_data.py` (experiment 19b, DATA side).

Everything here runs on DISPOSABLE fixtures: seed 999201, a two-update operator
history, a 48-world memory and 16-unit panels.  The registered seeds (1900/1901/1902),
the registered namespaces and the real panels are NEVER generated, and no artifact
under `artifacts/fable-novelty19-replay-20260920/` is written to -- the fixture builds
its own miniature experiment 19 and points 19b at that.

Run:  python3.12 -B tests/test_fable_novelty19b_data.py
"""

from __future__ import annotations

import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

import fable_dispatcher_v3 as V3                                            # noqa: E402
import fable_novelty19_data as N                                            # noqa: E402
import fable_novelty19b_data as M                                           # noqa: E402

A = N.A

FIXTURE_SEED = 999201           # disposable; well above B2.DEV_SEED_FLOOR
FIXTURE_NAMESPACE = 'astra-novelty19b-devfixture-999201'
FIXTURE_N = 16                  # one unit per answer value, so stratification is exact
FIXTURE_CELLS = ('N-c4-p6', 'E-c8-link', 'L-c6-r10-p16')

PASSED = 0
FAILED = []
TEMP = []
_CACHE = {}


def check(name, function):
    global PASSED
    try:
        detail = function()
    except (SystemExit, Exception) as exc:                      # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'novelty19b-{name}-'))
    TEMP.append(folder)
    return folder


def fixture():
    """A miniature experiment 19 plus the 19b artifacts built on top of it.

    `exp19/` is built with the FROZEN module exactly as the real one was (operator
    history, dev panels, awake stream, memory, R/G/U buffers), so the 19b side reads it
    through the same verified loaders it will use on the registered folders.
    """
    if 'fixture' in _CACHE:
        return _CACHE['fixture']
    root = scratch('fixture')
    exp19, exp2 = root / 'exp19', root / 'exp2'
    history = exp19 / 'operator-history'
    N.build_operator_history(history, updates=2, progress=False)
    N.build_dev_panels(exp19 / 'dev-panels', n=8, namespace=FIXTURE_NAMESPACE + '-old',
                       cells={k: N.DEV_CELLS[k] for k in ('N-c4-p6', 'F-c1-r8')},
                       operator_history=history, require_full_history=False,
                       progress=False)
    N.build_awake_stream(exp19 / f'awake-{FIXTURE_SEED}', FIXTURE_SEED, 12, chunk=4,
                         dev_panels=exp19 / 'dev-panels', progress=False)
    N.build_memory(exp19 / f'memory-{FIXTURE_SEED}', FIXTURE_SEED,
                   exp19 / f'awake-{FIXTURE_SEED}', worlds=48)
    N.build_buffers(exp19 / f'buffers-{FIXTURE_SEED}', FIXTURE_SEED,
                    exp19 / f'memory-{FIXTURE_SEED}', dev_panels=exp19 / 'dev-panels',
                    offline_updates=8, progress=False)
    buffers = M.build_buffers(exp2 / f'buffers-{FIXTURE_SEED}', FIXTURE_SEED,
                              exp19 / f'memory-{FIXTURE_SEED}',
                              dev_panels=exp19 / 'dev-panels', offline_updates=8,
                              compare_buffers=exp19 / f'buffers-{FIXTURE_SEED}',
                              progress=False)
    cells = {k: M.CELLS[k] for k in FIXTURE_CELLS}
    panels = M.build_dev_panels(exp2 / 'dev-panels', n=FIXTURE_N,
                                namespace=FIXTURE_NAMESPACE, cells=cells,
                                experiment=exp2, exp19=exp19, operator_history=history,
                                require_full_history=False,
                                exclusion_folders=exclusion_folders(root),
                                progress=False)
    _CACHE['fixture'] = dict(root=root, exp19=exp19, exp2=exp2, history=history,
                             cells=cells, buffers=buffers, panels=panels)
    return _CACHE['fixture']


def exclusion_folders(root):
    """The fixture's stand-in for the registered excluded-source set."""
    exp19, exp2 = Path(root) / 'exp19', Path(root) / 'exp2'
    return {'exp19_dev_panels': exp19 / 'dev-panels',
            f'exp19_stream_{FIXTURE_SEED}': exp19 / f'awake-{FIXTURE_SEED}',
            f'exp19_memory_{FIXTURE_SEED}': exp19 / f'memory-{FIXTURE_SEED}',
            f'exp19_buffers_{FIXTURE_SEED}': exp19 / f'buffers-{FIXTURE_SEED}',
            f'buffers_{FIXTURE_SEED}': exp2 / f'buffers-{FIXTURE_SEED}'}


def copied_fixture(name):
    """A writable copy of the whole fixture, for the tamper attacks."""
    root = scratch(name)
    shutil.copytree(fixture()['root'], root / 'copy')
    return root / 'copy'


# --------------------------------------------------------------------------- the laws


def test_arm_length_laws():
    """U5 draws c in 1..5, U8 in 1..8; r=10 only at c=1; both roughly uniform."""
    seen = {arm: {} for arm in M.ARMS}
    draws = 4000
    for arm in M.ARMS:
        for i in range(draws):
            names = M.uniform_string(random.Random(f'{M.NS_LENGTH}:0:{i}:0'), arm)
            calls = len(names)
            seen[arm][calls] = seen[arm].get(calls, 0) + 1
            assert names[-1] in ('8', '9', '10'), names
            assert names[:-1] == ['LINK'] * (calls - 1), names
            if names[-1] == '10':
                assert calls == 1, f'{arm} proposed a composite r=10: {names}'
    for arm, support in seen.items():
        assert sorted(support) == list(M.ARM_CALLS[arm]), (arm, sorted(support))
        share = draws / len(M.ARM_CALLS[arm])
        worst = max(abs(v - share) / share for v in support.values())
        assert worst < 0.15, f'{arm} length law is not uniform enough: {support}'
    long_share = sum(v for c, v in seen['U8'].items() if c >= 6) / draws
    return (f"U5 support {sorted(seen['U5'])}, U8 {sorted(seen['U8'])}, "
            f'U8 c>=6 share {long_share:.3f} (nominal 0.375)')


def test_u5_law_is_the_frozen_law():
    """U5 IS experiment 19's U law: same key, same draws, same string."""
    for i in range(500):
        key = f'{M.NS_LENGTH}:{FIXTURE_SEED}:{i}:0'
        assert M.uniform_string(random.Random(key), 'U5') == \
            N.uniform_string(random.Random(key)), key
    return '500 keys agree with N.uniform_string'


def test_the_binding_stream_is_arm_independent():
    """The binding key has no arm in it, so both arms bind the same start person."""
    people = list(range(52, 58))
    for i in range(200):
        key = f'{M.NS_BIND}:{FIXTURE_SEED}:{i}:3'
        first = random.Random(key).choice(people)
        assert all(random.Random(key).choice(people) == first for _ in M.ARMS)
    assert 'arm' not in M.STREAM_MAPPING['length']['key']
    assert M.STREAM_MAPPING['length']['arm_in_key'] is False
    assert M.STREAM_MAPPING['binding']['arm_in_key'] is False
    return f'mapping sha {M.STREAM_MAPPING_SHA256[:16]}'


# --------------------------------------------------------------------------- the cells


def test_cell_table_is_38_cells_in_six_families():
    assert len(M.CELLS) == 38, len(M.CELLS)
    assert M.FAMILY_SIZES == dict(N=4, E=6, F=7, P=8, H=4, L=9), M.FAMILY_SIZES
    assert M.family_sizes(M.CELLS) == M.FAMILY_SIZES
    inherited = {k: v for k, v in N.DEV_CELLS.items() if not k.startswith('L-')}
    assert len(inherited) == 26
    for name, cfg in inherited.items():
        assert M.CELLS[name] == cfg, f'{name} drifted from the frozen specification'
    new = sorted(set(M.CELLS) - set(N.DEV_CELLS))
    assert len(new) == 12, new
    assert sorted(c for c in new if c.startswith('L-')) == sorted(
        f'L-c{c}-r{r}-p16' for c in (6, 7, 8) for r in (8, 9, 10)), new
    assert sorted(c for c in new if c.startswith('E-')) == [
        'E-c8-irrelevant', 'E-c8-link', 'E-c8-value'], new
    assert [c for c in M.CELL_ORDER if c not in M.CELLS] == []
    return f'26 inherited + 12 new = {len(M.CELLS)}, families {M.FAMILY_SIZES}'


def test_every_cell_is_single_ending_and_all_distinct():
    """Ruling 5 everywhere; and 19b has no mixed-ending cell left to conceal an ending."""
    for name, cfg in M.CELLS.items():
        assert cfg['distinct'] is True, name
        assert cfg['fixed_terminal'] != 'balanced', f'{name} is still mixed-ending'
        assert int(cfg['fixed_terminal']) in (8, 9, 10), name
        if name.startswith('L-'):
            assert cfg['people'] == 16 and cfg['hops'] in (6, 7, 8), name
            assert int(cfg['fixed_terminal']) == int(name.split('-r')[1].split('-')[0])
        if name.startswith('E-c8'):
            assert cfg['kind'] == 'pair' and cfg['hops'] == 8, name
            assert int(cfg['fixed_terminal']) == N.HELDOUT_REL, name
            assert cfg['invariant'] == (cfg['edit'] == 'irrelevant'), name
    return 'all 38 cells single-ending, distinct-people'


def test_answer_and_ending_stratification_are_unchanged():
    """`target_answer` and ruling 6's blocked schedule come from the frozen module."""
    counts = {}
    for i in range(64):
        counts[N.target_answer(i)] = counts.get(N.target_answer(i), 0) + 1
    assert set(counts.values()) == {4} and len(counts) == 16, counts
    balance = N.mixed_ending_balance(64)
    assert set(balance.values()) == {2} and len(balance) == 32, balance
    assert all(len({int(M.CELLS[c]['fixed_terminal'])}) == 1 for c in M.CELLS)
    return '64 units: 4 per value; ruling 6 table still 2 per (value, ending)'


def test_marks_match_the_readout():
    marks = M.MARKS
    assert marks['bounded_competence']['dev'] == 58
    assert marks['bounded_competence']['confirm'] == 464
    assert marks['treatment_effect']['dev'] == 13
    assert marks['treatment_effect']['confirm'] == 104
    assert marks['guards']['dev'] == 58 and marks['guards']['confirm'] == 464
    assert marks['retention_f']['dev'] == 61 and marks['retention_f']['confirm'] == 488
    assert marks['retention_h']['dev'] == 58
    assert marks['retention_h']['max_loss_vs_awake_anchor'] == dict(dev=7, confirm=56)
    assert len(marks['bounded_competence']['cells']) == 4 + 8 + 9
    assert marks['treatment_effect']['cells'] == [f'L-c{c}-r10-p16' for c in (6, 7, 8)]
    assert len(marks['guards']['cells']) == 6
    assert len(marks['retention_f']['cells']) == 7
    assert len(marks['retention_h']['cells']) == 4
    for mark in marks.values():
        missing = [c for c in mark['cells'] if c not in M.CELLS]
        assert not missing, missing
    return '58->464, 61->488, 13->104, H loss 7->56'


def test_registered_cells_context_is_clean():
    before = dict(V3.CELLS)
    with M.registered_cells():
        assert 'L-c8-r10-p16' in V3.CELLS and 'E-c8-link' in V3.CELLS
    assert dict(V3.CELLS) == before, 'V3.CELLS was not restored'
    return f'{len(M.CELLS)} cells injected and removed'


def test_checkpoint_keys_and_layout():
    assert M.ARCHITECTURES == ('D',)
    assert M.checkpoint_keys('awake') == tuple(f'D-{s}' for s in M.SEEDS)
    assert M.checkpoint_keys('offline') == tuple(
        f'D-{a}-{s}' for a in M.ARMS for s in M.SEEDS)
    assert len(M.checkpoint_keys('offline')) == 6
    assert M.LAYOUT['buffers'] == 'buffers-{seed}'
    return '3 awake + 6 offline D checkpoints'


# --------------------------------------------------------------------------- buffers


def test_buffers_share_world_bytes_and_order():
    fix = fixture()
    loaded = {arm: M.load_buffer(fix['exp2'] / f'buffers-{FIXTURE_SEED}', arm)
              for arm in M.ARMS}
    first = loaded['U5']
    for arm, rec in loaded.items():
        assert rec['stories'] == first['stories'], arm
        assert [it['owner'] for it in rec['items']] == \
            [it['owner'] for it in first['items']], arm
    assert fix['buffers']['identical_world_bytes']['identical']
    return f"{len(first['stories'])} worlds, {len(first['items'])} questions per arm"


def test_u5_is_experiment_19s_u_buffer():
    """The answer to Astra's question, measured: item-identical, not byte-identical."""
    fix = fixture()
    report = fix['buffers']['u5_vs_experiment19_u']
    assert report['identical_items'] is True, report['first_differences']
    assert report['identical_world_rows'] is True
    assert report['item_view_sha256'] == report['other_item_view_sha256']
    assert report['byte_identical_file'] is False
    mine = N.sha(fix['exp2'] / f'buffers-{FIXTURE_SEED}' / 'buffer-U5.pt')
    theirs = N.sha(fix['exp19'] / f'buffers-{FIXTURE_SEED}' / 'buffer-U.pt')
    assert mine != theirs, 'the .pt files should differ in their recorded kind/profile'
    return f"{report['items']} items identical; files differ ({mine[:8]} vs {theirs[:8]})"


def test_u8_reaches_longer_chains_and_reports_them():
    fix = fixture()
    hist = {a: fix['buffers']['per_arm'][a]['length_histogram'] for a in M.ARMS}
    lengths = {a: sorted({int(k.split(',')[0][2:]) for k in hist[a]}) for a in hist}
    assert max(lengths['U5']) <= 5, lengths['U5']
    assert max(lengths['U8']) == 8, lengths['U8']
    assert all(k.split(',')[1] in ('r=8', 'r=9') or k.startswith('c=1,')
               for k in hist['U8']), hist['U8']
    return f"U5 {lengths['U5']}, U8 {lengths['U8']}"


def test_buffer_labels_and_zero_composite_r10():
    fix = fixture()
    for arm in M.ARMS:
        rec = M.load_buffer(fix['exp2'] / f'buffers-{FIXTURE_SEED}', arm)
        for it in rec['items']:
            names = N.op_names(it['question'][2:-1])
            assert not N.composite_r10(names), (arm, names)
            assert N.label_question(rec['stories'][it['owner']], it['question']) \
                == it['chain'], (arm, it['question'])
    assert fix['buffers']['composite_r10_exposure']['zero_exposure']
    return 'every label re-derived from the fixed interpreter; zero composite r=10'


def test_revisits_are_disclosed_not_filtered():
    """c=7/8 must revisit people in six-person worlds -- and the audit says so."""
    fix = fixture()
    report = fix['buffers']['per_arm']['U8']['revisits']
    long_rows = {k: v for k, v in report['per_length'].items()
                 if int(k[2:]) >= 7}
    assert long_rows, report
    assert all(v['with_revisits'] == v['units'] for v in long_rows.values()), long_rows
    assert fix['buffers']['per_arm']['U5']['revisits']['units'] > 0
    return f"U8: {report['with_revisits']}/{report['units']} chains revisit a person"


def test_offline_order_is_experiment_19s():
    fix = fixture()
    mine = json.loads((fix['exp2'] / f'buffers-{FIXTURE_SEED}'
                       / 'offline-order.json').read_text())
    theirs = json.loads((fix['exp19'] / f'buffers-{FIXTURE_SEED}'
                         / 'offline-order.json').read_text())
    assert mine['order'] == theirs['order']
    assert mine['order'] == M.offline_order(FIXTURE_SEED, updates=mine['updates'],
                                            visits=mine['visits'],
                                            worlds=mine['worlds'])
    return f"{mine['updates']} updates, order sha {mine['order_sha256'][:12]}"


def test_paired_streams_are_verified_on_the_built_buffers():
    fix = fixture()
    report = fix['buffers']['paired_streams']
    assert report['verified'] and report['start_mismatches'] == 0
    assert report['length_law_mismatches'] == 0
    assert report['shared_candidate_slots'] > 0
    assert fix['buffers']['stream_mapping_sha256'] == M.STREAM_MAPPING_SHA256
    return f"{report['shared_candidate_slots']} shared candidate slots, 0 mismatches"


def test_buffers_refuse_to_overwrite():
    fix = fixture()
    try:
        M.build_buffers(fix['exp2'] / f'buffers-{FIXTURE_SEED}', FIXTURE_SEED,
                        fix['exp19'] / f'memory-{FIXTURE_SEED}',
                        dev_panels=fix['exp19'] / 'dev-panels', offline_updates=8,
                        progress=False)
    except (SystemExit, Exception) as exc:                      # noqa: BLE001
        return f'refused: {type(exc).__name__}'
    raise AssertionError('a second build overwrote an existing buffer folder')


# --------------------------------------------------------------------------- panels


def test_panels_are_disjoint_from_every_excluded_source():
    """Fresh worlds AND fresh questions, against every source the readout names."""
    fix = fixture()
    _, _, questions = M.load_dev_panels(fix['exp2'] / 'dev-panels')
    worlds, primary = M.dev_panel_worlds(fix['exp2'] / 'dev-panels')
    assert primary <= worlds and primary, 'primary worlds were not published'
    sources = dict(exclusion_folders(fix['root']))
    sources['operator_history'] = fix['history']
    hits = {}
    for name, folder in sources.items():
        sets = N.artifact_exclusions(folder)
        hits[name] = (len(questions & sets['questions']), len(worlds & sets['worlds']))
    assert all(q == 0 and w == 0 for q, w in hits.values()), hits
    return f'{len(sources)} sources, 0 overlaps at both levels'


def test_panels_record_what_they_consumed():
    fix = fixture()
    manifest = json.loads((fix['exp2'] / 'dev-panels' / 'manifest.json').read_text())
    consumed = {row['name']: row for row in manifest['consumed_exclusions']}
    assert 'operator_history' in consumed
    for name, folder in exclusion_folders(fix['root']).items():
        assert name in consumed, name
        recorded = consumed[name]
        assert recorded['verified'] is True
        # the awake stream publishes through `index.json`, everything else through
        # `manifest.json`; the shared helper knows which
        _, published = N.published_exclusion_record(folder)
        assert recorded['questions_sha256'] == published['questions_sha256'], name
        assert recorded['worlds_sha256'] == published['worlds_sha256'], name
    assert manifest['attempt_limit'] == N.DEV_ATTEMPTS
    assert manifest['excluded_sources']['questions'] > 0
    return f'{len(consumed)} exclusion sources recorded with their shas'


def test_a_truncated_exclusion_file_is_refused_by_the_panel_build():
    """The auditor's R2-7 attack, at 19b's new source: a shortened buffer world file."""
    root = copied_fixture('truncate')
    path = root / 'exp2' / f'buffers-{FIXTURE_SEED}' / 'forbidden-worlds.json'
    value = json.loads(path.read_text())
    path.write_text(json.dumps(value[:5]))
    out = root / 'exp2' / 'attack-panels'
    try:
        M.build_dev_panels(out, n=FIXTURE_N, namespace=FIXTURE_NAMESPACE,
                           cells={'N-c4-p6': M.CELLS['N-c4-p6']},
                           experiment=root / 'exp2', exp19=root / 'exp19',
                           operator_history=root / 'exp19' / 'operator-history',
                           require_full_history=False,
                           exclusion_folders=exclusion_folders(root), progress=False)
    except SystemExit as exc:
        assert not out.exists(), 'a refused build left a panel folder behind'
        assert 'truncated' in str(exc) or 'entries' in str(exc), str(exc)
        return f'refused, folder absent: {str(exc)[:60]}...'
    raise AssertionError('a truncated exclusion file was accepted')


def test_a_tampered_exclusion_entry_is_refused_by_the_panel_build():
    root = copied_fixture('tamper')
    path = root / 'exp2' / f'buffers-{FIXTURE_SEED}' / 'forbidden-worlds.json'
    value = json.loads(path.read_text())
    value[0] = 'f' * 64
    path.write_text(json.dumps(sorted(set(value))))
    try:
        M.build_dev_panels(root / 'exp2' / 'attack-panels', n=FIXTURE_N,
                           namespace=FIXTURE_NAMESPACE,
                           cells={'N-c4-p6': M.CELLS['N-c4-p6']},
                           experiment=root / 'exp2', exp19=root / 'exp19',
                           operator_history=root / 'exp19' / 'operator-history',
                           require_full_history=False,
                           exclusion_folders=exclusion_folders(root), progress=False)
    except SystemExit as exc:
        assert 'tampered' in str(exc) or 'hashes to' in str(exc), str(exc)
        return f'refused: {str(exc)[:60]}...'
    raise AssertionError('a tampered exclusion entry was accepted')


def test_panels_refuse_to_overwrite():
    fix = fixture()
    try:
        M.build_dev_panels(fix['exp2'] / 'dev-panels', n=FIXTURE_N,
                           namespace=FIXTURE_NAMESPACE, cells=fix['cells'],
                           experiment=fix['exp2'], exp19=fix['exp19'],
                           operator_history=fix['history'], require_full_history=False,
                           exclusion_folders=exclusion_folders(fix['root']),
                           progress=False)
    except FileExistsError:
        return 'refused an existing panel folder'
    raise AssertionError('a second panel build overwrote the folder')


# --------------------------------------------------------------------------- the lock


def _dev_passed_doc(root, **override):
    panels = Path(root) / 'exp2' / 'dev-panels'
    doc = dict(schema=M.DEV_PASSED_SCHEMA, seeds=[FIXTURE_SEED],
               report_sha256='a' * 64,
               dev_panels=dict(path=str(panels),
                               manifest_sha256=N.sha(panels / 'manifest.json')),
               awake_checkpoints={k: 'b' * 64 for k in
                                  M.checkpoint_keys('awake', (FIXTURE_SEED,))},
               offline_checkpoints={k: 'c' * 64 for k in
                                    M.checkpoint_keys('offline', (FIXTURE_SEED,))})
    doc.update(override)
    return doc


def _confirmation_refuses(root, doc=None, out='confirm-panels'):
    flag = Path(root) / 'exp2' / 'DEV-PASSED.json'
    if doc is None:
        flag.unlink(missing_ok=True)
    else:
        flag.write_text(doc if isinstance(doc, str) else json.dumps(doc))
    folder = Path(root) / 'exp2' / out
    try:
        M.build_dev_panels(folder, n=FIXTURE_N, namespace=FIXTURE_NAMESPACE + '-confirm',
                           cells={'L-c6-r10-p16': M.CELLS['L-c6-r10-p16']},
                           confirmation=True, experiment=Path(root) / 'exp2',
                           exp19=Path(root) / 'exp19',
                           operator_history=Path(root) / 'exp19' / 'operator-history',
                           require_full_history=False, seeds=(FIXTURE_SEED,),
                           exclusion_folders=exclusion_folders(root), progress=False)
    except SystemExit as exc:
        assert not folder.exists(), 'a refused confirmation build left a folder'
        return str(exc)
    raise AssertionError('the confirmation lock opened')


def test_confirmation_is_locked_behind_a_19b_dev_passed():
    root = copied_fixture('lock')
    reasons = [_confirmation_refuses(root)]                      # no flag at all
    reasons.append(_confirmation_refuses(root, ''))              # empty
    reasons.append(_confirmation_refuses(root, 'not json'))      # malformed
    reasons.append(_confirmation_refuses(                        # experiment 19's schema
        root, _dev_passed_doc(root, schema=N.DEV_PASSED_SCHEMA)))
    doc = _dev_passed_doc(root)
    doc['offline_checkpoints'].pop('D-U8-999201')
    reasons.append(_confirmation_refuses(root, doc))             # missing a continuation
    doc = _dev_passed_doc(root)
    doc['offline_checkpoints']['D-G-999201'] = 'd' * 64
    reasons.append(_confirmation_refuses(root, doc))             # an experiment-19 arm
    doc = _dev_passed_doc(root)
    doc['dev_panels']['manifest_sha256'] = 'e' * 64
    reasons.append(_confirmation_refuses(root, doc))             # panels not the ones scored
    doc = _dev_passed_doc(root)
    doc['report_sha256'] = 'no'
    reasons.append(_confirmation_refuses(root, doc))
    assert len(reasons) == 8 and all(reasons)
    return f'{len(reasons)} malformed DEV-PASSED documents all refused'


def test_the_lock_opens_for_a_complete_dev_passed():
    """And the confirmation copy excludes the development panels it was unlocked by."""
    root = copied_fixture('unlock')
    flag = Path(root) / 'exp2' / 'DEV-PASSED.json'
    flag.write_text(json.dumps(_dev_passed_doc(root)))
    folders = exclusion_folders(root)
    folders['dev_panels_19b'] = Path(root) / 'exp2' / 'dev-panels'
    out = M.build_dev_panels(
        Path(root) / 'exp2' / 'confirm-panels', n=FIXTURE_N,
        namespace=FIXTURE_NAMESPACE + '-confirm',
        cells={'L-c6-r10-p16': M.CELLS['L-c6-r10-p16']}, confirmation=True,
        experiment=Path(root) / 'exp2', exp19=Path(root) / 'exp19',
        operator_history=Path(root) / 'exp19' / 'operator-history',
        require_full_history=False, seeds=(FIXTURE_SEED,),
        exclusion_folders=folders, progress=False)
    manifest = json.loads((Path(out['panels']) / 'manifest.json').read_text())
    assert manifest['kind'] == 'confirmation'
    assert manifest['dev_passed']['schema'] == M.DEV_PASSED_SCHEMA
    # the fixture registers ONE seed, so the roster is 1 awake + 2 offline
    assert manifest['dev_passed']['awake_checkpoints'] == 1
    assert manifest['dev_passed']['offline_checkpoints'] == 2
    assert 'dev_panels_19b' in manifest['excluded_sources']['folders']
    _, _, dev_questions = M.load_dev_panels(Path(root) / 'exp2' / 'dev-panels')
    _, _, confirm_questions = M.load_dev_panels(Path(out['panels']))
    assert not (dev_questions & confirm_questions), 'confirmation reused a dev question'
    return f"unlocked; {out['cells']} cell, dev/confirmation disjoint"


def test_confirmation_namespace_needs_the_flag_and_a_full_history():
    fix = fixture()
    for kwargs, expect in (
            (dict(namespace=M.NS_CONFIRM, confirmation=False), 'explicit'),
            (dict(namespace=M.NS_DEV, require_full_history=False), 'partial'),
            (dict(namespace=M.NS_CONFIRM, require_full_history=False), 'explicit')):
        folder = fix['exp2'] / f'never-{abs(hash(str(kwargs))) % 10 ** 6}'
        base = dict(n=FIXTURE_N, cells={'N-c4-p6': M.CELLS['N-c4-p6']},
                    experiment=fix['exp2'], exp19=fix['exp19'],
                    operator_history=fix['history'], require_full_history=False,
                    exclusion_folders=exclusion_folders(fix['root']), progress=False)
        base.update(kwargs)
        try:
            M.build_dev_panels(folder, **base)
        except SystemExit as exc:
            assert expect in str(exc), (kwargs, str(exc))
            assert not folder.exists()
            continue
        raise AssertionError(f'{kwargs} was accepted')
    return 'registered namespaces refuse a partial history; NS_CONFIRM needs the flag'


# --------------------------------------------------------------------------- audit


def _audit(root=None, **override):
    root = Path(root or fixture()['root'])
    kwargs = dict(buffers=root / 'exp2' / f'buffers-{FIXTURE_SEED}',
                  dev_panels=root / 'exp2' / 'dev-panels',
                  memory=root / 'exp19' / f'memory-{FIXTURE_SEED}',
                  experiment=root / 'exp2', exp19=root / 'exp19',
                  operator_history=root / 'exp19' / 'operator-history',
                  require_full_history=False, seeds=(FIXTURE_SEED,),
                  cells={k: M.CELLS[k] for k in FIXTURE_CELLS},
                  exclusion_folders=exclusion_folders(root))
    kwargs.update(override)
    return M.audit_everything(FIXTURE_SEED, **kwargs)


def test_audit_verdict():
    verdict = _CACHE.setdefault('verdict', _audit())
    assert verdict['passed'], verdict['failures']
    assert verdict['checks_run'] == verdict['checks_expected'] == \
        len(M.EXPECTED_AUDIT_CHECKS)
    assert not verdict['checks_absent']
    assert verdict['checks']['u5_matches_experiment_19_u']['passed']
    assert verdict['checks']['paired_stream_mapping']['passed']
    assert verdict['checks']['memory_bytes_identical_to_experiment_19']['passed']
    support = verdict['checks']['buffer_accepted_length_support']['detail']['support']
    assert max(support['U8']) == 8 and max(support['U5']) <= 5, support
    return (f"{verdict['checks_run']}/{verdict['checks_expected']} checks, "
            f"U5 {support['U5']}, U8 {support['U8']}")


def test_audit_reports_the_length_and_ending_histograms():
    verdict = _CACHE.setdefault('verdict', _audit())
    detail = verdict['checks']['buffer_accepted_length_support']['detail']
    hist = detail['length_ending_histogram']
    assert set(hist) == set(M.ARMS)
    assert all(k.startswith('c=') and ',r=' in k for arm in hist for k in hist[arm])
    census = verdict['checks']['dev_panel_census']['detail']
    assert census['families_match'] and census['all_single_ending']
    assert census['answer_stratified'] and census['answer_ending_balanced']
    assert not census['impure_cells']
    return (f"U8 keys {len(hist['U8'])}, census {census['cells']} cells, "
            f"families {census['families']}")


def test_audit_refuses_a_truncated_exclusion_file():
    root = copied_fixture('audit-truncate')
    path = root / 'exp2' / f'buffers-{FIXTURE_SEED}' / 'forbidden-worlds.json'
    path.write_text(json.dumps(json.loads(path.read_text())[:5]))
    verdict = _audit(root)
    assert not verdict['passed']
    assert verdict['failures'] == ['exclusion_files_match_their_manifests'], \
        verdict['failures']
    assert verdict.get('aborted'), 'the audit did not say why it stopped'
    assert 'expected_checks_absent' not in verdict['failures']
    offenders = list(verdict['checks']['exclusion_files_match_their_manifests']['detail'])
    return f'aborted on {offenders}'


def test_audit_refuses_a_missing_producer_manifest():
    root = copied_fixture('audit-nomanifest')
    (root / 'exp2' / f'buffers-{FIXTURE_SEED}' / 'manifest.json').unlink()
    verdict = _audit(root)
    assert not verdict['passed'] and verdict.get('aborted')
    return 'an exclusion file without its manifest is refused'


def test_an_absent_check_is_itself_a_failure():
    original = M.EXPECTED_AUDIT_CHECKS
    M.EXPECTED_AUDIT_CHECKS = original + ('a_check_nobody_runs',)
    try:
        verdict = _audit()
    finally:
        M.EXPECTED_AUDIT_CHECKS = original
    assert not verdict['passed']
    assert verdict['checks_absent'] == ['a_check_nobody_runs']
    assert 'expected_checks_absent' in verdict['failures']
    assert verdict['checks_expected'] == len(original) + 1
    return f'{verdict["checks_run"]}/{verdict["checks_expected"]} reported honestly'


def test_audit_notices_a_disagreeing_execution_profile():
    root = copied_fixture('audit-profile')
    path = root / 'exp2' / f'buffers-{FIXTURE_SEED}' / 'manifest.json'
    doc = json.loads(path.read_text())
    doc['execution_profile']['python'] = '3.0.0-not-this-one'
    path.write_text(json.dumps(doc))
    verdict = _audit(root)
    assert 'execution_profiles_agree' in verdict['failures'], verdict['failures']
    return 'one experiment, one execution profile'


def test_audit_needs_the_whole_panel_table():
    """Building fewer cells cannot satisfy the census: the roster names what it wants."""
    verdict = _audit(cells=M.CELLS)
    assert not verdict['passed']
    assert 'dev_panel_cell_count' in verdict['failures']
    detail = verdict['checks']['dev_panel_cell_count']['detail']
    assert detail == dict(cells=len(FIXTURE_CELLS), expected=38, registered=False) \
        or detail['expected'] == 38, detail
    return 'a 3-cell folder fails a 38-cell audit'


# --------------------------------------------------------------------------- contract


def test_registered_numbers_are_unchanged():
    assert M.SEEDS == (1900, 1901, 1902)
    assert M.ARMS == ('U5', 'U8')
    assert M.ARM_CALLS == dict(U5=(1, 2, 3, 4, 5), U8=(1, 2, 3, 4, 5, 6, 7, 8))
    assert M.CANDIDATES_PER_WORLD == 64
    assert M.BUFFER_QUESTIONS_PER_WORLD == 4
    assert M.MEMORY_WORLDS == 1024
    assert M.OFFLINE_UPDATES == 2000 and M.OFFLINE_VISITS == 16
    assert M.DEV_N == 64 and M.CONFIRM_N == 512
    assert M.DEV_ATTEMPTS == 10_000
    assert M.NS_LENGTH == N.NS_UNIFORM and M.NS_BIND == N.NS_BIND
    assert M.NS_ORDER == N.NS_ORDER
    assert M.ARCHITECTURES == ('D',)
    assert len(M.CELLS) == 38
    return '2 arms x 3 seeds, 2,000 updates, 38 cells, 64/512 units'


def test_the_frozen_module_was_not_touched():
    """19b imports experiment 19; it never edits it."""
    assert N.DEV_CELLS is not M.CELLS
    assert len(N.DEV_CELLS) == 32 and len(N.EXPECTED_AUDIT_CHECKS) == 37
    assert N.ARMS == ('R', 'G', 'U') and N.ARCHITECTURES == ('D', 'T')
    assert N.DEV_PASSED_SCHEMA == 'novelty19-dev-passed-v1'
    assert M.DEV_PASSED_SCHEMA == 'novelty19b-dev-passed-v1'
    before = dict(V3.CELLS)
    with M.registered_cells():
        pass
    assert dict(V3.CELLS) == before
    return f'frozen module sha {N.sha(N.__file__)[:12]}, 32 cells, 37 checks'


def test_trainer_api_surface():
    """Everything the training builder imports, with the shapes promised in the brief."""
    import inspect
    wanted = {
        'load_buffer': ('buffers', 'arm'),
        'offline_order': ('seed', 'updates', 'visits', 'worlds'),
        'load_dev_panels': ('panels', 'cells'),
        'dev_panel_worlds': ('panels',),
        'whole_cell': ('panel', 'units'),
        'registered_cells': ('cells',),
        'cell_table': ('cells',),
        'checkpoint_keys': ('stage', 'seeds'),
        'validate_dev_passed': ('experiment', 'panels_folder', 'seeds'),
        'census': ('manifest', 'cells'),
        'family_sizes': ('cells',),
        'execution_profile': (),
        'fingerprint': (),
    }
    for name, params in wanted.items():
        function = getattr(M, name)
        got = tuple(inspect.signature(function).parameters)
        assert got == params, f'{name}{got} != {name}{params}'
    for name in ('CELLS', 'CELL_ORDER', 'FAMILY_SIZES', 'MARKS', 'ARMS', 'ARM_CALLS',
                 'SEEDS', 'LAYOUT', 'STREAM_MAPPING', 'STREAM_MAPPING_SHA256',
                 'DEV_PASSED_SCHEMA', 'EXPECTED_AUDIT_CHECKS'):
        assert hasattr(M, name), name
    table = M.cell_table()
    assert len(table) == 38
    row = table['L-c8-r10-p16']
    assert row['family'] == 'L' and row['hops'] == 8 and row['people'] == 16
    assert row['ending'] == 10 and 'treatment_effect' in row['marks']
    assert 'bounded_competence' in row['marks']
    return f'{len(wanted)} functions and 12 constants exported'


def main():
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith('test_') and callable(value)]
    for name, function in tests:
        check(name, function)
    print(f'\n{PASSED}/{len(tests)} checks passed', flush=True)
    for name, error in FAILED:
        print(f'  FAILED {name}: {error}', flush=True)
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
