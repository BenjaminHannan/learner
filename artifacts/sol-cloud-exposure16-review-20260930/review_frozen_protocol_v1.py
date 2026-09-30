#!/usr/bin/env python3
"""Independent stdlib-only review; mocks never authorize or launch a fit.

All outputs and numeric fixtures here are nontraining review evidence.
"""
from __future__ import annotations
import argparse
import ast
import builtins
from collections import Counter
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(name, value):
    with (OWN / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--driver-version', required=True)
    parser.add_argument('--receipt-suffix', default='v1')
    args = parser.parse_args()
    revision = ROOT / 'artifacts/sol-cloud-exposure16-20260930' / args.revision
    script = ROOT / ('scripts/sol_cloud_exposure16_' + args.driver_version + '.py')
    seal_path = revision / 'SEAL.json'
    seal = read(seal_path)
    plan = read(revision / 'PLAN.json')
    budget = read(revision / 'BUDGET.json')
    marks = read(revision / 'PASSMARKS.json')
    old = read(OWN / 'HISTORICAL-BASIS-v1.json')['sources']
    tiny = old['TINY-V12-PLAN.json']['metadata']
    historical_ids = old['ANSWER-V11-DIAGNOSTIC-PLAN.json']['metadata']['TRAIN_diagnostic_ids']
    checks = {}
    mismatches = [p for p, digest in seal['files'].items() if sha(ROOT / p) != digest]
    checks['all_62_sealed_files_match'] = len(seal['files']) == 62 and not mismatches
    checks['historical_ID_order_and_warm_tuples_exact'] = (plan['TRAIN_ids'] == historical_ids
        and plan['TRAIN_ids'][:4] == tiny['TRAIN_ids'] and plan['warmstart']['tuples'] == tiny['tuples'])
    checks['hyperparameters_match_V12_connected'] = all(plan[k] == tiny[old_k] for k, old_k in
        [('batch', 'batch'), ('lr', 'connected_lr'), ('weight_decay', 'weight_decay'), ('clip_norm', 'clip_norm')])
    checks['single_connected_arm_800_by_2'] = (plan['arms'] == ['connected'] and plan['seeds'] == [0, 1]
        and plan['updates_per_seed'] == 800 and plan['visits_per_row'] == 50 and plan['rounds'] == 4)
    schedules = {}
    for seed in (0, 1):
        entry = plan['schedules'][str(seed)]
        schedule = read(ROOT / entry['path'])
        rng = random.Random(2026093016 + seed)
        expected = []
        for _ in range(50):
            block = plan['TRAIN_ids'].copy()
            rng.shuffle(block)
            expected.extend(block)
        schedules[str(seed)] = {'updates': len(schedule), 'unique_rows': len(set(schedule)),
            'visits_per_row': sorted(set(Counter(schedule).values())), 'deterministic_schedule_matches': schedule == expected,
            'each_full_pass_permutation': all(set(schedule[i:i + 16]) == set(plan['TRAIN_ids']) for i in range(0, 800, 16)),
            'sha256': sha(ROOT / entry['path'])}
    checks['schedules_exact_50_visits_each'] = all(v['updates'] == 800 and v['unique_rows'] == 16
        and v['visits_per_row'] == [50] and v['deterministic_schedule_matches'] and v['each_full_pass_permutation']
        for v in schedules.values())
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT)]
    from sol_cloud_trainonly_v1 import load_packet, canonical_sha
    opened = []
    original_open = Path.open
    def observed_open(path, *a, **kw):
        opened.append(str(path.resolve()))
        return original_open(path, *a, **kw)
    source = plan['source']
    with patch.object(Path, 'open', observed_open):
        packet = load_packet(ROOT / source['packet']['path'], source['packet']['sha256'],
                             ROOT / source['manifest']['path'], source['manifest']['sha256'])
    admitted = {str((ROOT / source[k]['path']).resolve()) for k in ('packet', 'manifest')}
    checks['admission_reads_only_safe_packet_and_manifest'] = set(opened) == admitted
    byid = {r['id']: r for r in packet}
    references = read(ROOT / plan['references']['path'])
    refs_ok = references['model_authored_text_included'] is False and len(references['rows']) == 16
    for ref in references['rows']:
        row = byid[ref['id']]
        refs_ok = refs_ok and all(ref[k] == row[rk] for k, rk in
            [('human_question', 'question'), ('human_context', 'context'), ('human_answer_target', 'target_text'),
             ('field_sha256', 'field_sha256'), ('official_answer_offsets', 'official_answer_offsets'),
             ('source_hash', 'source_hash'), ('source_ref', 'source_ref'), ('source_provenance', 'provenance')])
        refs_ok = refs_ok and ref['packet_row_canonical_sha256'] == canonical_sha(row)
        refs_ok = refs_ok and ref['expected_identity_by_control'] == {'actual': row['id'], 'no_notebook': row['id'],
            'latent_swap_same_context': plan['latent_swap_donor_id'][row['id']]}
        for answer in row['official_answer_offsets']:
            start = answer['answer_start']
            refs_ok = refs_ok and row['context'][start:start + len(answer['text'])] == answer['text']
    checks['all_16_references_and_human_offsets_match_packet'] = refs_ok
    checks['swap_donors_involutive_other_rows_same_context'] = all(donor != identity
        and plan['latent_swap_donor_id'][donor] == identity
        and byid[identity]['context_sha256'] == byid[donor]['context_sha256']
        for identity, donor in plan['latent_swap_donor_id'].items())
    old_seal = read(ROOT / 'artifacts/sol-translator-20260929/TINY-V12-SEAL.json')
    runtime_paths = [p for p in seal['files'] if p.startswith('scripts/')
                     and not p.startswith('scripts/sol_cloud_exposure16_') and p != source['loader']['path']]
    checks['historical_runtime_hashes_unchanged'] = all(seal['files'][p] == old_seal['files'][p] for p in runtime_paths)
    checks['templates_held_outside_live_queues'] = all((revision / ('HELD-queue-exposure16-s%d.md' % seed)).read_text().startswith('STATUS: HELD')
        and 'handoff/queue' not in str(revision) and 'handoff/pcqueue' not in str(revision) for seed in (0, 1))
    checks['TRAIN_only_no_activation_or_holdout_claims'] = all(marks[k] is False for k in
        ('scientific_promotion', 'activation', 'grammar_qualified', 'live_user_day')) and all(marks[k] == 0 for k in ('holdouts', 'DEV100', 'stop88'))
    ast.parse(script.read_text())
    checks['driver_AST_valid'] = True
    retained = 2 * (budget['checkpoint_serialized_cap_bytes_per_seed'] + budget['raw_JSON_cap_bytes_per_seed'] + budget['binary_frame_cap_bytes_per_seed'])
    peak = retained + budget['checkpoint_serialized_cap_bytes_per_seed']
    checks['hard_resource_arithmetic_correct'] = (retained == budget['two_seed_retained_output_bound_bytes']
        and peak == budget['two_seed_output_atomic_bound_bytes'] and peak + budget['package_delivery_cap_bytes'] == budget['combined_output_atomic_plus_delivery_bound_bytes']
        and peak + budget['package_delivery_cap_bytes'] <= 384 * 1024 ** 2
        and budget['operating_run_output_cap_bytes'] + budget['package_delivery_cap_bytes'] <= 384 * 1024 ** 2
        and budget['startup_free_bytes'] == budget['retained_free_bytes'] + 384 * 1024 ** 2
        and budget['retained_free_bytes'] == 1024 ** 3 and budget['per_seed']['child_seconds'] == 570 and budget['per_seed']['outer_seconds'] == 600)
    v1_seal = ROOT / 'artifacts/sol-cloud-exposure16-20260930/SEAL.json'
    checks['v1_seal_and_all_v1_files_preserved'] = sha(v1_seal) == '55c7f578cd0d8a89d055f0858133d4533ac533fcc52bcbf73aeaf5238d8a60ae' and all(
        sha(ROOT / p) == digest for p, digest in read(v1_seal)['files'].items())
    spec = importlib.util.spec_from_file_location('independent_exposure_driver', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = []
    original_import = builtins.__import__
    attempted_torch = []
    def guarded_import(name, *a, **kw):
        if name == 'torch' or name.startswith('torch.'):
            attempted_torch.append(name)
            raise AssertionError('review must not import Torch')
        return original_import(name, *a, **kw)
    base_args = SimpleNamespace(seed=0, release=OWN / 'IN_MEMORY_ONLY_RELEASE', release_sha256='mock',
                                inventory=OWN / 'IN_MEMORY_ONLY_INVENTORY', inventory_sha256='mock')
    with patch.dict(os.environ, {}, clear=True), patch.object(builtins, '__import__', guarded_import):
        try:
            module.run(base_args)
            raise AssertionError('missing watcher gate admitted run')
        except RuntimeError as error:
            assert 'watcher queue' in str(error)
            tests.append({'name': 'missing_JOB_TREE_run_rejects_before_Torch', 'passed': True})
    seal_hash = sha(seal_path)
    release = {'authorized_by': 'Derek', 'fit_released': True, 'seal_sha256': seal_hash,
        'bridge_priority_satisfied': True, 'independent_review': {'path': 'MOCK-REVIEW', 'sha256': 'mock'}}
    review = {'release_readiness': True, 'seal_sha256': seal_hash}
    inventory = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'gpu_inventory_verified': True,
        'project_gpu_processes': [], 'other_watcher_running_claims': [], 'V11_source_checkpoint_closure_verified': True,
        'checkpoint_serialization_bound_verified': True, 'delivery_package_and_tree_bytes': 8 * 1024 ** 2}
    original_read_pin, original_sha = module.read_pin, module.sha
    warm_pins = {binding[k + '_path']: binding[k + '_sha256'] for binding in plan['warmstart']['tuples'].values()
                 for k in ('parent', 'reader', 'adapter')}
    def fixture_gate(name, seed=0, changes=None, free=None, wrong_warm=False, positive=False):
        local_release, local_review, local_inventory = copy.deepcopy(release), copy.deepcopy(review), copy.deepcopy(inventory)
        if changes:
            target, key, value = changes
            {'release': local_release, 'review': local_review, 'inventory': local_inventory}[target][key] = value
        def fake_pin(path, digest):
            if str(path) == str(base_args.release): return local_release
            if str(path) == 'MOCK-REVIEW': return local_review
            if str(path) == str(base_args.inventory): return local_inventory
            return original_read_pin(path, digest)
        def fake_sha(path):
            if str(path) in warm_pins: return '0' * 64 if wrong_warm else warm_pins[str(path)]
            return original_sha(path)
        fixture_args = copy.copy(base_args)
        fixture_args.seed = seed
        with patch.dict(os.environ, {'JOB': 'NONTRAINING-MOCK-REVIEW', 'TREE': str(ROOT)}), \
             patch.object(module, 'read_pin', fake_pin), patch.object(module, 'sha', fake_sha), \
             patch.object(module.shutil, 'disk_usage', return_value=SimpleNamespace(free=free if free is not None else budget['startup_free_bytes'])), \
             patch.object(builtins, '__import__', guarded_import):
            try:
                result = module.gates(fixture_args)
            except (RuntimeError, ValueError) as error:
                if positive: raise
                tests.append({'name': name, 'passed': True, 'rejection': str(error)})
            else:
                if not positive: raise AssertionError(name + ' unexpectedly admitted')
                assert len(result[2]) == 16 and len(result[3]) == 800
                tests.append({'name': name, 'passed': True, 'rows': 16, 'scheduled_updates': 800, 'mock_only': True})
    for seed in (0, 1): fixture_gate('mock_positive_seed%d' % seed, seed=seed, positive=True)
    cases = [
        ('bridge_unresolved', ('release', 'bridge_priority_satisfied', False)),
        ('no_parent_release', ('release', 'fit_released', False)),
        ('wrong_release_seal', ('release', 'seal_sha256', '0' * 64)),
        ('independent_review_not_approved', ('review', 'release_readiness', False)),
        ('wrong_review_seal', ('review', 'seal_sha256', '0' * 64)),
        ('stale_inventory', ('inventory', 'observed_utc', (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=121)).isoformat())),
        ('future_inventory', ('inventory', 'observed_utc', (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)).isoformat())),
        ('GPU_inventory_unverified', ('inventory', 'gpu_inventory_verified', False)),
        ('project_GPU_process_present', ('inventory', 'project_gpu_processes', ['NONTRAINING-FIXTURE'])),
        ('other_watcher_claim_present', ('inventory', 'other_watcher_running_claims', ['NONTRAINING-FIXTURE'])),
        ('checkpoint_closure_unverified', ('inventory', 'V11_source_checkpoint_closure_verified', False)),
        ('serialization_bound_unverified', ('inventory', 'checkpoint_serialization_bound_verified', False)),
        ('delivery_over_cap', ('inventory', 'delivery_package_and_tree_bytes', 8 * 1024 ** 2 + 1)),
        ('delivery_missing', ('inventory', 'delivery_package_and_tree_bytes', None)),
        ('delivery_boolean_rejected', ('inventory', 'delivery_package_and_tree_bytes', True))]
    for name, changes in cases: fixture_gate(name, changes=changes)
    fixture_gate('startup_free_one_byte_short', free=budget['startup_free_bytes'] - 1)
    fixture_gate('wrong_physical_warm_checkpoint_pin', wrong_warm=True)
    checks['metadata_gate_fixtures_all_pass'] = all(t['passed'] for t in tests)
    checks['Torch_never_imported_and_run_output_absent'] = not attempted_torch and not (revision / 'runs').exists()
    supervisor_tests = []
    for platform, waits in [('posix_normal', [0]), ('nt_timeout', ['timeout', 0]), ('posix_timeout', ['timeout', 'timeout', 0])]:
        calls, queue = [], list(waits)
        class MockProcess:
            pid = 424242
            def wait(self, timeout):
                calls.append(['wait', timeout])
                result = queue.pop(0)
                if result == 'timeout': raise subprocess.TimeoutExpired('NONTRAINING-MOCK', timeout)
                return result
        def fake_popen(command, **options):
            calls.append(['Popen_mock', '--worker' in command, 'start_new_session' in options, options.get('creationflags')])
            return MockProcess()
        def fake_run(command, **options):
            calls.append(['taskkill_mock', command, options])
            return SimpleNamespace(returncode=0)
        fake_os = SimpleNamespace(name='nt' if platform.startswith('nt') else 'posix', environ={}, getpid=lambda: 313131,
                                  killpg=lambda pid, sig: calls.append(['killpg_mock', pid, int(sig)]))
        fake_subprocess = SimpleNamespace(Popen=fake_popen, TimeoutExpired=subprocess.TimeoutExpired,
                                         CREATE_NEW_PROCESS_GROUP=512, run=fake_run)
        with patch.object(module, 'os', fake_os), patch.object(module, 'subprocess', fake_subprocess), \
             patch.object(module.sys, 'argv', ['REVIEW-NONTRAINING', '--seed', '0']):
            result = module.supervise(base_args)
        expected = 0 if platform == 'posix_normal' else 124
        assert result == expected and calls[1] == ['wait', 570]
        if platform == 'nt_timeout':
            assert calls[2] == ['taskkill_mock', ['taskkill', '/PID', '424242', '/T', '/F'], {'check': True, 'timeout': 10}]
            assert calls[3] == ['wait', 10]
        if platform == 'posix_timeout':
            assert calls[2][0:2] == ['killpg_mock', 424242] and calls[3] == ['wait', 3]
            assert calls[4][0:2] == ['killpg_mock', 424242] and calls[5] == ['wait', 10]
        supervisor_tests.append({'name': platform, 'passed': True, 'mock_calls': calls, 'actual_processes_launched': 0, 'actual_processes_killed': 0})
    checks['owned_supervisor_mock_control_flow_pass'] = len(supervisor_tests) == 3
    suffix = args.revision + '-' + args.receipt_suffix
    common = {'seal_sha256': seal_hash, 'driver_sha256': sha(script), 'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'models_loaded': 0, 'optimizer_updates': 0, 'GPU_calls': 0, 'actual_processes_launched': 0,
        'raw_official_corpus_opened': False, 'reserved_content_opened': False, 'all_generated_artifacts_are_nontraining': True}
    audit = {**common, 'schema': 'sol.cloud.exposure16.independent.metadata-audit.v2', 'checks': checks,
        'check_count': len(checks), 'passed_count': sum(checks.values()), 'all_passed': all(checks.values()),
        'mismatched_sealed_files': mismatches, 'sealed_file_count': len(seal['files']), 'admission_opened_only': sorted(set(opened)),
        'historical_runtime_file_count': len(runtime_paths), 'schedules': schedules,
        'resource_peak_bytes': peak, 'resource_peak_plus_delivery_bytes': peak + budget['package_delivery_cap_bytes'],
        'real_bridge_inventory_and_preflight_not_exercised': True}
    gates = {**common, 'schema': 'sol.cloud.exposure16.independent.mock-gate-tests.v1', 'gate_tests': tests,
        'gate_test_count': len(tests), 'all_gate_tests_passed': all(t['passed'] for t in tests),
        'supervisor_tests': supervisor_tests, 'supervisor_test_count': len(supervisor_tests),
        'mock_release_and_mock_physical_pins_only': True, 'no_real_release_or_inventory_created': True,
        'Windows_target_runtime_timeout_verified': False}
    save('METADATA-AUDIT-' + suffix + '.json', audit)
    save('GATE-TESTS-' + suffix + '.json', gates)
    print(json.dumps({'revision': args.revision, 'metadata_checks': len(checks), 'metadata_passed': sum(checks.values()),
        'gate_tests': len(tests), 'supervisor_mock_tests': len(supervisor_tests), 'models_loaded': 0, 'optimizer_updates': 0}))


if __name__ == '__main__':
    main()
