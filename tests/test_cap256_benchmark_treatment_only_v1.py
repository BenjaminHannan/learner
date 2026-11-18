"""CPU contract fixtures for the treatment-only fresh-process benchmark copies.

Stdlib only: no Torch, tensors, checkpoints, native processes, SSH or GPU. These
fixtures check software contracts (pins, AST scope, counters, windows, restore
comparison); they do not show that the native endpoint runs.
"""
import ast
import copy
from datetime import datetime, timedelta, timezone
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / 'scripts/cap256_launch'
B = ROOT / 'artifacts/cap256-launch/contextual-input-compare-v1/TRAIN-TEMPLATE-CURRICULUM-PREPARATION-v1/LOCAL-DISPOSABLE-ARITHMETIC-BENCHMARK-v1'
PLAN = B / 'TREATMENT-ONLY-FRESH-PROCESS-CPU-PREPARATION-v1/TREATMENT-ONLY-FRESH-PROCESS-IMPLEMENTATION-PLAN-v1.json'
STAGE = B / 'ACTUAL-EXECUTION-v8/STAGE-v1'

NEW = {'worker': 'benchmark_matched_template_curriculum_windows_treatment_only_v1',
       'driver': 'execute_matched_template_curriculum_benchmark_windows_treatment_only_v1',
       'transport': 'execute_bounded_disposable_arithmetic_benchmark_transport_treatment_only_v1',
       'relay': 'native_disposable_arithmetic_benchmark_relay_treatment_only_v1'}
OLD = {'worker': 'benchmark_matched_template_curriculum_windows_v4',
       'driver': 'execute_matched_template_curriculum_benchmark_windows_v1',
       'transport': 'execute_bounded_disposable_arithmetic_benchmark_transport_v1',
       'relay': 'native_disposable_arithmetic_benchmark_relay_v1'}
MAPPED = {'worker': {'execution_authority', 'cpu_preflight', 'run', 'qualification_window', 'run_endpoint', 'validate_budget'},
          'driver': {'validate_request', 'authority_check', 'validate_closed', 'verify_final_checkpoints',
                     'continuation_terminal', 'validate_failed', 'prepare_benchmark_queue_job', 'main'},
          'transport': {'bounded', 'execute', 'validate', 'verify_extract'},
          'relay': {'main', 'window'}}
ADDED = {'worker': {'_restore_identity', 'validate_prior_control_resume', 'compare_treatment_to_prior_control'},
         'driver': set(), 'transport': set(), 'relay': set()}


def module(name):
    spec = importlib.util.spec_from_file_location('_treatment_only_fixture_' + name, S / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


w = module(NEW['worker'])
d = module(NEW['driver'])
t = module(NEW['transport'])
n = module(NEW['relay'])
plan = json.loads(PLAN.read_text())
PRIOR = plan['initialization']['priorcontrol_RESUME']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def top_functions(path):
    return {x.name: ast.dump(x, include_attributes=False) for x in ast.parse(Path(path).read_text()).body
            if isinstance(x, (ast.FunctionDef, ast.ClassDef))}


def body_without_docstring(source):
    tree = ast.parse(source)
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) else tree.body
    return [ast.dump(x, include_attributes=False) for x in body]


def prior():
    return json.loads((ROOT / PRIOR['path']).read_text())


def treatment_fixture():
    value = copy.deepcopy(prior())
    value.update(schema=w.SCHEMA, curriculum_arm='treatment', endpoint_index=1)
    return value


class SourcePinsAndScope(unittest.TestCase):
    def test_plan_source_pins_match_disk_and_originals_unmodified(self):
        for pin in plan['source_pins'].values():
            path = ROOT / pin['path']
            self.assertEqual((sha(path), path.stat().st_size), (pin['sha256'], pin['bytes']), pin['path'])
        self.assertEqual(sha(ROOT / PRIOR['path']), PRIOR['sha256'])
        self.assertEqual((ROOT / PRIOR['path']).stat().st_size, PRIOR['bytes'])
        self.assertEqual(w.PRIOR_CONTROL_RESUME_SHA256, PRIOR['sha256'])
        self.assertEqual(w.PRIOR_RESTORED_FINGERPRINTS, plan['initialization']['prior_restored_fingerprints'])

    def test_every_unmapped_top_level_function_is_ast_identical(self):
        for key in NEW:
            with self.subTest(key=key):
                old, new = top_functions(S / (OLD[key] + '.py')), top_functions(S / (NEW[key] + '.py'))
                self.assertEqual(set(new), set(old) | ADDED[key])
                for name in set(old) - MAPPED[key]:
                    self.assertEqual(old[name], new[name], name)

    def test_worker_execution_authority_differs_only_in_approval_id(self):
        old = (S / (OLD['worker'] + '.py')).read_text().replace(
            '01a0f0d8-d903-7668-b40d-8cd0d96410c3', 'cmsg_01GSLCHTCnZxn7DhV19qcDvMPbYEV1BgsUFXSkJNiRu4J7')
        self.assertEqual(top_functions(S / (NEW['worker'] + '.py'))['execution_authority'],
                         {x.name: ast.dump(x, include_attributes=False) for x in ast.parse(old).body
                          if isinstance(x, ast.FunctionDef)}['execution_authority'])

    def test_worker_run_endpoint_differs_only_in_deadline_message(self):
        old = (S / (OLD['worker'] + '.py')).read_text().replace(
            "'absolute900second qualification/export deadline'", "'absolute600second qualification/export deadline'")
        self.assertEqual(top_functions(S / (NEW['worker'] + '.py'))['run_endpoint'],
                         {x.name: ast.dump(x, include_attributes=False) for x in ast.parse(old).body
                          if isinstance(x, ast.FunctionDef)}['run_endpoint'])

    def test_transport_and_relay_differ_only_by_900_to_600(self):
        for key in ('transport', 'relay'):
            with self.subTest(key=key):
                old = (S / (OLD[key] + '.py')).read_text().replace('900', '600')
                self.assertEqual(body_without_docstring(old), body_without_docstring((S / (NEW[key] + '.py')).read_text()))

    def test_worker_and_driver_anchor_unset_and_no_torch(self):
        self.assertNotIn('torch', sys.modules)
        self.assertIsNone(w.TRUSTED_EXECUTION_RELEASE_SHA256)
        self.assertIsNone(d.TRUSTED_EXECUTION_RELEASE_SHA256)
        with self.assertRaisesRegex(ValueError, 'UNSET'):
            w.execution_authority(STAGE, {}, S / (NEW['worker'] + '.py'))
        with self.assertRaisesRegex(ValueError, 'UNSET'):
            d.authority_check({}, {})

    def test_run_uses_literal_index1_loop_and_order_unchanged(self):
        self.assertEqual(w.ORDER[1], (0, 'treatment'))
        run = next(x for x in ast.parse((S / (NEW['worker'] + '.py')).read_text()).body if getattr(x, 'name', '') == 'run')
        loops = [x for x in ast.walk(run) if isinstance(x, ast.For)]
        literal = [x for x in loops if isinstance(x.iter, ast.Tuple) and [getattr(e, 'value', None) for e in x.iter.elts] == [1]]
        self.assertEqual(len(literal), 1)
        self.assertFalse(any(isinstance(x.iter, ast.Call) and getattr(x.iter.func, 'id', '') == 'range' for x in loops))


class WorkerContracts(unittest.TestCase):
    def budget(self):
        return {'worker_seconds': 400, 'new_output_bytes': 1792 * w.MIB, 'checkpoint_cap_bytes': 128 * w.MIB,
                'raw_cap_bytes_per_endpoint': 32 * w.MIB, 'cuda_peak_reserved_cap_bytes': 10 * 1024 ** 3,
                'retained_global_CUDA_free_bytes': 2 * 1024 ** 3, 'project_cap_bytes': 100000000000,
                'retained_free_bytes': 2 * 1024 ** 3, 'aggregate_spend_usd_cap': '0.00', 'receipt_reserve_bytes': 16 * w.MIB,
                'checkpoint_positions': [64], 'cache_seconds': 300, 'cache_cap_bytes': 512 * w.MIB}

    def test_budget_400_only_other_caps_unchanged(self):
        w.validate_budget(self.budget(), 64)
        for key, value in (('worker_seconds', 700), ('worker_seconds', 401), ('new_output_bytes', 2 * 1024 ** 3),
                           ('cuda_peak_reserved_cap_bytes', 12 * 1024 ** 3), ('cache_seconds', 301)):
            bad = self.budget(); bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                w.validate_budget(bad, 64)

    def test_window_exact_600_live(self):
        start = datetime.now(timezone.utc) - timedelta(seconds=1)
        def authority(seconds, begin=start):
            return {'qualification_window_utc': {'start': begin.isoformat(), 'deadline': (begin + timedelta(seconds=seconds)).isoformat()}}
        self.assertEqual(w.qualification_window(authority(600)), start + timedelta(seconds=600))
        for seconds in (599, 601, 900):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                w.qualification_window(authority(seconds))
        with self.assertRaises(ValueError):
            w.qualification_window(authority(600, start - timedelta(seconds=700)))

    def test_actual_prior_control_resume_validates_and_mutations_fail(self):
        w.validate_prior_control_resume(prior())
        mutations = [('curriculum_arm', 'treatment'), ('endpoint_index', 1), ('schema', w.SCHEMA), ('optimizer_reset', True),
                     ('source_update', 5184), ('module_buffers_sha256', '0' * 64), ('source_RNG_sha256', '0' * 64),
                     ('new_curriculum_visits', {'x': 1})]
        for key, value in mutations:
            bad = prior(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                w.validate_prior_control_resume(bad)
        bad = prior(); bad['source_checkpoint']['sha256'] = w.PRIOR_CONTROL_CHECKPOINT_SHA256
        with self.assertRaises(ValueError):
            w.validate_prior_control_resume(bad)

    def test_comparison_passes_only_on_actual_equality(self):
        result = w.compare_treatment_to_prior_control(treatment_fixture(), prior())
        self.assertIs(result['same_initial_state_as_prior_control'], True)
        self.assertEqual(result['prior_control_resume_sha256'], PRIOR['sha256'])
        for key in w.RESTORE_KEYS:
            bad = treatment_fixture()
            if isinstance(bad[key], dict):
                bad[key]['core'] = '0' * 64
            elif isinstance(bad[key], list):
                bad[key] = bad[key][::-1]
            else:
                bad[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                w.compare_treatment_to_prior_control(bad, prior())
        for mutate in (lambda v: v['source_checkpoint'].__setitem__('sha256', w.PRIOR_CONTROL_CHECKPOINT_SHA256),
                       lambda v: v['historical_visits'].__setitem__(next(iter(v['historical_visits'])), 159),
                       lambda v: v.update(curriculum_arm='control'), lambda v: v.update(endpoint_index=0),
                       lambda v: v.update(schema=w.PRIOR_CONTROL_SCHEMA), lambda v: v.update(optimizer_reset=True)):
            bad = treatment_fixture(); mutate(bad)
            with self.assertRaises(ValueError):
                w.compare_treatment_to_prior_control(bad, prior())
        # Arms swapped: the control record cannot stand in for the treatment.
        with self.assertRaises(ValueError):
            w.compare_treatment_to_prior_control(prior(), treatment_fixture())


class WorkerPreflightFixture(unittest.TestCase):
    """STAGE-v1 copy in a temp root. The 60 MB input copy is absent on the Mac,
    so the expected stop is the parents pin; every earlier check must pass."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'stage'
        shutil.copytree(STAGE, self.root)
        rel = 'scripts/cap256_launch/' + NEW['worker'] + '.py'
        shutil.copyfile(S / (NEW['worker'] + '.py'), self.root / rel)
        (self.root / PRIOR['path']).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / PRIOR['path'], self.root / PRIOR['path'])
        self.workerpath = self.root / rel
        cfg = json.loads((self.root / 'cfg/BENCHMARK-CONFIG-v1.json').read_text())
        cfg.update(schema=w.SCHEMA, endpoint_index=1, prior_control_resume=dict(PRIOR),
                   runner={'path': rel, 'sha256': sha(self.workerpath)},
                   runner_normalized_AST_sha256=w.normalized_source_sha256(self.workerpath.read_text()))
        cfg['budget']['worker_seconds'] = 400
        self.cfg = cfg

    def tearDown(self):
        self.tmp.cleanup()

    def preflight(self, cfg):
        start = datetime.now(timezone.utc) - timedelta(seconds=1)
        authority = {'qualification_window_utc': {'start': start.isoformat(), 'deadline': (start + timedelta(seconds=600)).isoformat()}}
        with patch.object(w, 'execution_authority', return_value=authority), \
                patch.object(w, 'benchmark_rows', side_effect=w.checked_benchmark_rows_unmarked):
            return w.cpu_preflight(self.root, cfg, self.workerpath)

    def test_all_checks_before_absent_input_copy_pass(self):
        seen = []
        real = w.pin
        def spy(root, record):
            seen.append(record['path'])
            return real(root, record)
        with patch.object(w, 'pin', side_effect=spy), self.assertRaisesRegex(ValueError, 'ordinary nonsymlink file required'):
            self.preflight(self.cfg)
        self.assertEqual(seen[-1], 'input-copy/original-seed0-global5120.pt')
        self.assertEqual(seen[-2], PRIOR['path'])

    def test_index0_missing_key_bad_prior_pin_or_0818_parent_refused_earlier(self):
        bad = copy.deepcopy(self.cfg); bad['endpoint_index'] = 0
        with self.assertRaisesRegex(ValueError, 'treatment-only physical endpoint1'):
            self.preflight(bad)
        bad = copy.deepcopy(self.cfg); bad.pop('prior_control_resume')
        with self.assertRaisesRegex(ValueError, 'treatment-only physical endpoint1'):
            self.preflight(bad)
        bad = copy.deepcopy(self.cfg); bad['prior_control_resume']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'prior control RESUME pin'):
            self.preflight(bad)
        bad = copy.deepcopy(self.cfg); bad['budget']['worker_seconds'] = 700
        with self.assertRaises(ValueError):
            self.preflight(bad)
        bad = copy.deepcopy(self.cfg); bad['parents'][0]['checkpoint']['sha256'] = w.PRIOR_CONTROL_CHECKPOINT_SHA256
        with self.assertRaisesRegex(ValueError, 'never an initializer'):
            self.preflight(bad)

    def test_tampered_prior_resume_bytes_refused(self):
        path = self.root / PRIOR['path']
        data = path.read_bytes(); path.write_bytes(data[:-1] + (b' ' if data[-1:] != b' ' else b'\n'))
        with self.assertRaisesRegex(ValueError, 'physical pin differs'):
            self.preflight(self.cfg)


class DriverContracts(unittest.TestCase):
    def request(self):
        pin = {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__))}
        value = {'schema': d.SCHEMA, 'execution_platform': 'Windows', 'TRAIN_only': True, 'EVAL_access_allowed': False,
                 'benchmark_checkpoint_promotion_allowed': False, 'endpoint_index': 1, 'execution_order': [[0, 'treatment']],
                 'optimizer_updates_allowed': 64, 'generation_calls_allowed': 16, 'model_calls_allowed': 144,
                 'job_id': 'benchmark-treatment', 'attempt_id': 'benchmark-treatment-a', 'batch_id': 'benchmark-treatment-a',
                 'root': 'C:/project/package', 'pc_project_root': 'C:/project', 'expected_base_exe': 'C:/Python/python.exe',
                 'gpu_policy': 'fixture-only-no-GPU',
                 'driver_budget': {'whole_job_seconds': 600, 'whole_output_bytes': 2 * 1024 ** 3, 'controller_reserve_bytes': 64 * d.MIB,
                                   'log_cap_bytes': d.MIB, 'closure_seconds': 180, 'ownership_handshake_seconds': 10},
                 'state_namespace': 'benchmark-controller-v1', 'terminal_path': 'BENCHMARK-TERMINAL-v1.json',
                 'worker_output_namespace': 'benchmark-output-v1',
                 **{k: copy.deepcopy(pin) for k in ('driver', 'runtime_adapter', 'queue_module', 'pc_guard', 'storage_module', 'worker_source',
                                                   'continuation_config', 'authority', 'python_exe', 'ownership_runtime', 'native_CPU_receipt')}}
        for name, value_sha in (('runtime_adapter', d.ADAPTER_SHA256), ('queue_module', d.QUEUE_SHA256), ('ownership_runtime', d.OWNERSHIP_SHA256)):
            value[name]['sha256'] = value_sha
        return value

    def test_request_exact_index1_64_16_144_and_600_180(self):
        d.validate_request(self.request())
        self.assertLessEqual(d.WORKER_SECONDS + d.CLOSURE_SECONDS, d.WHOLE_JOB_SECONDS)
        for key, value in (('endpoint_index', 0), ('execution_order', [[0, 'control'], [0, 'treatment']]), ('optimizer_updates_allowed', 128),
                           ('generation_calls_allowed', 32), ('model_calls_allowed', 288), ('model_calls_allowed', 144.0),
                           ('benchmark_checkpoint_promotion_allowed', True)):
            bad = self.request(); bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                d.validate_request(bad)
        for key, value in (('whole_job_seconds', 900), ('whole_job_seconds', 601), ('closure_seconds', 120)):
            bad = self.request(); bad['driver_budget'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.validate_request(bad)

    def closure(self):
        r = self.request()
        e = {'seed': 0, 'endpoint_index': 1, 'curriculum_arm': 'treatment', 'optimizer_updates': 64, 'teacherforced_calls': 64,
             'generate_calls': 16, 'core_forwards': 80, 'input_backbone_forwards': 1024, 'model_cursor': 64, 'last_durable_raw_cursor': 64,
             'historical_cursor': 5120, 'final_global_cursor': 5184, 'native_answers_scored': False,
             'benchmark_checkpoint_promotion_allowed': False, 'curriculum_visits': {'r%d' % i: 1 for i in range(64)},
             'historical_visits': {'old%d' % i: 160 for i in range(32)}}
        return {'schema': w.SCHEMA, 'closed': True, 'status': 'completed', 'config_sha256': r['continuation_config']['sha256'],
                'endpoint_index': 1, 'seed': 0, 'curriculum_arm': 'treatment', 'TRAIN_only': True, 'EVAL_accessed': False, 'fresh_calls': 0,
                'optimizer_updates': 64, 'generate_calls': 16, 'teacherforced_calls': 64, 'endpoint_teacherforced_calls': 0,
                'core_forwards': 80, 'input_backbone_forwards': 1024, 'model_calls': 144, 'model_cursor': 64, 'last_durable_raw_cursor': 64,
                'source_global_cursor': 5120, 'final_global_cursor': 5184, 'all_final_checkpoints_durable': True, 'LM_unchanged': True,
                'all_module_buffers_unchanged': True, 'halt_unchanged': True, 'source_Adam_loaded_exact': True,
                'source_RNG_restored_exact': True, 'durable_model_and_Adam_reload_equal': True,
                'benchmark_checkpoint_promotion_allowed': False, 'native_answers_scored': False, 'comparison_successor_authorized': False,
                'same_initial_state_as_prior_control': True, 'prior_control_counts_included': False,
                'prior_control_restore_comparison': w.compare_treatment_to_prior_control(treatment_fixture(), prior()), 'endpoints': [e]}

    def test_closed_one_treatment_endpoint_144(self):
        self.assertEqual(d.validate_closed(self.closure(), self.request()), 144)
        mutations = (lambda v: v.__setitem__('same_initial_state_as_prior_control', False),
                     lambda v: v.__setitem__('same_initial_state_restored_both_arms', True),
                     lambda v: v.__setitem__('model_calls', 288), lambda v: v.__setitem__('optimizer_updates', 128),
                     lambda v: v.__setitem__('endpoint_index', 0), lambda v: v.__setitem__('prior_control_counts_included', True),
                     lambda v: v['endpoints'].append(copy.deepcopy(v['endpoints'][0])),
                     lambda v: v['endpoints'][0].__setitem__('curriculum_arm', 'control'),
                     lambda v: v['endpoints'][0].__setitem__('generate_calls', 17),
                     lambda v: v['prior_control_restore_comparison'].__setitem__('prior_control_resume_sha256', '0' * 64),
                     lambda v: v.pop('prior_control_restore_comparison'))
        for i, mutate in enumerate(mutations):
            bad = self.closure(); mutate(bad)
            with self.subTest(i=i), self.assertRaises(ValueError):
                d.validate_closed(bad, self.request())

    def test_final_checkpoint_exactly_one_treatment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); out = root / 'benchmark-output-v1'
            cp = out / 'endpoint-1/seed0/treatment/contextual/final-resume.pt'; cp.parent.mkdir(parents=True); cp.write_bytes(b'cp')
            record = {'path': str(cp.relative_to(root)), 'sha256': sha(cp), 'curriculum_cursor': 64, 'global_cursor': 5184,
                      'seed': 0, 'curriculum_arm': 'treatment'}
            closed = {'checkpoint': record, 'scheduled_checkpoints': [record]}
            evidence = d.verify_final_checkpoints(root, out, closed)
            self.assertEqual([x['curriculum_arm'] for x in evidence], ['treatment'])
            control = dict(record, curriculum_arm='control')
            for bad in ({'checkpoint': record, 'scheduled_checkpoints': [control, record]},
                        {'checkpoint': control, 'scheduled_checkpoints': [control]},
                        {'checkpoint': dict(record, global_cursor=5248), 'scheduled_checkpoints': [dict(record, global_cursor=5248)]}):
                with self.assertRaises(ValueError):
                    d.verify_final_checkpoints(root, out, bad)

    def test_terminal_requires_16_native_and_144_calls(self):
        r = self.request()
        state = {'status': 'completed', 'accounting_complete': True, 'actual_child_exit_confirmed': True, 'launcher_exit_confirmed': True,
                 'optimizer_updates': 64, 'native_calls': 16, 'teacher_forced_calls': 64, 'endpoint_teacherforced_calls': 0,
                 'backward_calls': 64, 'model_calls': 144}
        evidence = [{'kind': 'checkpoint'}]
        terminal = d.continuation_terminal(r, 'h', state, evidence, 1.0, 1)
        self.assertEqual((terminal['endpoint_index'], terminal['native_calls'], terminal['prior_control_counts_included']), (1, 16, False))
        self.assertIn('core80+teacherforced64=144', terminal['model_calls_semantics'])
        for key, value in (('native_calls', 32), ('model_calls', 288), ('optimizer_updates', 128)):
            bad = dict(state); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.continuation_terminal(r, 'h', bad, evidence, 1.0, 1)

    def failed(self):
        return {'schema': w.SCHEMA, 'config_sha256': self.request()['continuation_config']['sha256'], 'endpoint_index': 1,
                'prior_control_counts_included': False, 'counters_exact': True,
                'inflight': dict.fromkeys(('cache', 'core', 'teacherforced', 'optimizer', 'native'), False),
                'automatic_retry_allowed': False, 'resume_dispatch_allowed': False, 'benchmark_checkpoint_promotion_allowed': False,
                'comparison_successor_authorized': False,
                'completed_counts': {'optimizer_updates': 10, 'teacherforced_calls': 10, 'core_forwards': 10, 'input_backbone_forwards': 1024},
                'model_cursor': 10, 'last_durable_raw_cursor': 9}

    def test_failed_bounds_single_endpoint(self):
        d.validate_failed(self.failed(), self.request())
        for mutate in (lambda v: v.__setitem__('endpoint_index', 0), lambda v: v.__setitem__('schema', w.PRIOR_CONTROL_SCHEMA),
                       lambda v: v['completed_counts'].__setitem__('optimizer_updates', 65),
                       lambda v: v['completed_counts'].__setitem__('generate_calls', 17),
                       lambda v: v['completed_counts'].__setitem__('input_backbone_forwards', 2048),
                       lambda v: v['inflight'].__setitem__('native', True), lambda v: v.pop('prior_control_counts_included')):
            bad = self.failed(); mutate(bad)
            with self.assertRaises(ValueError):
                d.validate_failed(bad, self.request())

    def test_queue_job_wall_600(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / 'request.json'; req.write_text(json.dumps(self.request()))
            auth = Path(tmp) / 'auth.json'; auth.write_text(json.dumps({'job_id': 'benchmark-treatment', 'authorized': False}))
            job = d.prepare_benchmark_queue_job({'path': str(req), 'sha256': sha(req)}, {'path': str(auth), 'sha256': sha(auth)})
            self.assertEqual([a['wall_cap_seconds'] for a in job['attempts']], [600])

    def test_main_uses_600_deadline_180_reserve_and_16_native(self):
        main = ast.get_source_segment((S / (NEW['driver'] + '.py')).read_text(),
                                      next(x for x in ast.parse((S / (NEW['driver'] + '.py')).read_text()).body if getattr(x, 'name', '') == 'main'))
        self.assertIn('started + WHOLE_JOB_SECONDS', main)
        self.assertIn('deadline - CLOSURE_SECONDS', main)
        self.assertIn('native_calls=16', main)
        self.assertNotIn('900', main)
        self.assertNotIn('native_calls=32', main)

    def test_native_cpu_proof_cpu_child_guide_unchanged_and_duplicate_marks_match(self):
        old, new = top_functions(S / (OLD['driver'] + '.py')), top_functions(S / (NEW['driver'] + '.py'))
        self.assertEqual(old['native_cpu_proof'], new['native_cpu_proof'])
        old_mod = {getattr(x.targets[0], 'id', None): ast.dump(x) for x in ast.parse((S / (OLD['driver'] + '.py')).read_text()).body if isinstance(x, ast.Assign)}
        new_mod = {getattr(x.targets[0], 'id', None): ast.dump(x) for x in ast.parse((S / (NEW['driver'] + '.py')).read_text()).body if isinstance(x, ast.Assign)}
        for name in ('CPU_CHILD', 'GUIDE', 'ORDER', 'OWNERSHIP_SHA256', 'ADAPTER_SHA256', 'QUEUE_SHA256'):
            self.assertEqual(old_mod[name], new_mod[name], name)
        source = (S / (NEW['driver'] + '.py')).read_text()
        for mark in ('benchmark_matched_template_curriculum_windows', 'execute_matched_template_curriculum_benchmark_windows'):
            self.assertIn(mark, source)
        self.assertIn('benchmark_matched_template_curriculum_windows', NEW['worker'])
        self.assertIn('execute_matched_template_curriculum_benchmark_windows', NEW['driver'])


class TransportRelayContracts(unittest.TestCase):
    def manifest(self, root, seconds=600):
        a = json.loads((B / 'ROOT-POSITIVE-STAGING-ASSEMBLY-v3.json').read_text())
        files = [{'localpath': f['local_source'], 'path': f['path'], 'sha256': f['sha256'], 'bytes': f['bytes']} for f in a['files']]
        request = root / 'request.json'; request.write_bytes(t.canonical(a['documents']['request']))
        request_rel = 'cfg/BENCHMARK-REQUEST-v1.json'
        files.append({'localpath': str(request), 'path': request_rel, 'sha256': t.sha(request), 'bytes': request.stat().st_size})
        relay = S / (NEW['relay'] + '.py'); rel = 'scripts/cap256_launch/' + relay.name
        files.append({'localpath': str(relay), 'path': rel, 'sha256': t.sha(relay), 'bytes': relay.stat().st_size})
        driver = 'scripts/cap256_launch/execute_matched_template_curriculum_benchmark_windows_v1.py'
        driver_sha = next(f['sha256'] for f in files if f['path'] == driver)
        start = dt.datetime.now(dt.timezone.utc); end = start + dt.timedelta(seconds=seconds)
        req = a['documents']['request']
        return {'schema': t.SCHEMA, 'ssh_alias': 'benspc', 'native_root': a['native_root'],
                'Mac_output_root': str(root / 'BENCHMARK-MAC-EXPORT-v1'),
                'qualification_window_utc': {'start': start.isoformat(), 'deadline': end.isoformat()},
                'staged_positive_files': files, 'readonly_native_pins': [req['runtime_adapter']],
                'request_relative': request_rel, 'request_sha256': t.sha(request), 'driver_relative': driver, 'driver_sha256': driver_sha,
                'python_exe': req['python_exe'], 'native_relay_relative': rel, 'native_relay_sha256': t.sha(relay),
                'original_checkpoint': {'nativepath': a['disposable_parent_copy_source'], 'sha256': n.CP_SHA, 'bytes': 60691431,
                                        'destination': 'input-copy/original-seed0-global5120.pt'},
                'export_roots': ['benchmark-output-v1', 'benchmark-controller-v1'], 'terminal_relative': req['terminal_path'],
                'old_lock_paths': [t.PROJECT + '/launch-cap256/LOCK.json']}

    def test_transport_validate_accepts_600_rejects_900(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(t.validate(self.manifest(Path(tmp)))['PC_calls'], 0)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'single600s'):
                t.validate(self.manifest(Path(tmp), 900))

    def test_relay_window_600(self):
        m = {'qualification_window_utc': {'start': '2026-10-02T21:00:00Z', 'deadline': '2026-10-02T21:10:00Z'}}
        start = t.utc(m['qualification_window_utc']['start'])
        self.assertEqual(n.window(m, start + 1), start + 600)
        for now in (start - 1, start + 600, start + 601):
            with self.assertRaises(ValueError):
                n.window(m, now)
        old = {'qualification_window_utc': {'start': '2026-10-02T21:00:00Z', 'deadline': '2026-10-02T21:15:00Z'}}
        with self.assertRaisesRegex(ValueError, 'aggregate600'):
            n.window(old, start + 1)

    def test_relay_single_popen_180_reserve_no_signals(self):
        source = (S / (NEW['relay'] + '.py')).read_text()
        calls = [x for x in ast.walk(ast.parse(source)) if isinstance(x, ast.Call)]
        self.assertEqual(sum(isinstance(x.func, ast.Attribute) and x.func.attr == 'Popen' for x in calls), 1)
        self.assertFalse(any(isinstance(x.func, ast.Attribute) and x.func.attr in ('kill', 'terminate', 'send_signal') for x in calls))
        self.assertIn('time.time()<end-180', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
