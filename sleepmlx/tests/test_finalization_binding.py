"""Offline finalization binding regressions; every adapter/backend is synthetic."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from sleepmlx import gate
from sleepmlx.checkpoint import Checkpoints
from sleepmlx.paths import Paths, read_json, write_json
from .helpers import Env
from . import test_checkpoint as checkpoint_tests
from .test_checkpoint import DurableBackend


def snapshot(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


def run_rejected_until_exit(root, boundary):
    root = Path(root)
    env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=100)
    env.paths = Paths(root / 'home', root / 'raw', root, root / 'userdata')
    sleeper = env.sleeper(DurableBackend(env.time))
    original_gate = sleeper._gate
    def gate_with_previous_training(*args):
        # Represent one item trained on an earlier night; rejection must keep
        # that flag and must not mark the remaining pending items trained.
        sleeper.items[sorted(sleeper.items)[0]].trained = True
        original_gate(*args)
    sleeper._gate = gate_with_previous_training
    def fault(stage):
        if boundary == 'rejection_ready':
            if stage == 'manifest_published' and sleeper.N['phase'] == 'finalize': os._exit(73)
        elif stage == boundary:
            os._exit(73)
    sleeper.checkpoint_hook = fault
    sleeper.run(env.week())
    raise AssertionError('rejection fault boundary was not reached: ' + boundary)


class FinalizationBindingTests(unittest.TestCase):
    def pending(self, stage='promotion_ready'):
        env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=0)
        self.addCleanup(env.close)
        checkpoint_tests.CrashRecoveryTests().crash(env, stage)
        return env

    def blocked(self, env):
        before = snapshot(env.paths.home)
        sleeper = env.sleeper(DurableBackend(env.time))
        sleeper.exporter = lambda *args, **kwargs: self.fail('blocked finalization exported')
        with patch.object(Checkpoints, 'promote', side_effect=AssertionError('blocked finalization promoted')):
            result = sleeper.run(env.week())
        self.assertEqual(result['status'], 'stopped')
        self.assertTrue(result['blocked'])
        self.assertTrue(result['interrupted'])
        self.assertTrue(result['gate_recheck_required'])
        self.assertEqual(result['stop_reason'], 'gate_recheck_required')
        self.assertIsNone(result['quiz'])
        self.assertEqual(result['steps'], 0)
        self.assertIn('explicit re-gate', result['message'])
        self.assertEqual(before, snapshot(env.paths.home))
        self.assertTrue(env.paths.work_adapter.exists())
        self.assertTrue(env.paths.night_json.exists())
        return result

    def test_new_decision_binds_version_grader_and_night(self):
        env = self.pending()
        night, _ = Checkpoints(env.paths).load()
        final = night['finalization']
        self.assertEqual(final['version'], 1)
        self.assertEqual(final['grader'], gate.GRADER)
        self.assertEqual(final['night_id'], night['id'])
        # promotion_ready created a destination but did not publish adapters.json.
        self.assertFalse(Checkpoints(env.paths).is_committed(night))

    def test_stale_or_missing_uncommitted_decisions_block_in_every_final_phase(self):
        env = self.pending()
        checkpoints = Checkpoints(env.paths)
        original, items = checkpoints.load()
        variants = ('missing_version', 'wrong_version', 'boolean_version', 'wrong_grader', 'missing_identity', 'wrong_identity')
        for phase in ('finalize', 'done', 'export_marked'):
            for variant in variants:
                with self.subTest(phase=phase, variant=variant):
                    night = copy.deepcopy(original)
                    night['phase'] = 'done' if phase == 'done' else 'finalize'
                    final = night['finalization']
                    if phase == 'export_marked':
                        final['export_started'] = True
                        final['result']['gguf'] = {'ok': True, 'message': 'uncommitted old export'}
                    if variant == 'missing_version': final.pop('version')
                    elif variant == 'wrong_version': final['version'] = 2
                    elif variant == 'boolean_version': final['version'] = True
                    elif variant == 'wrong_grader': final['grader'] = 'obsolete-grader'
                    elif variant == 'missing_identity': final.pop('night_id')
                    else: final['night_id'] = '0' * 32
                    checkpoints.publish(night, items)
                    self.blocked(env)

    def test_direct_finalize_has_the_same_guard(self):
        env = self.pending()
        original, _ = Checkpoints(env.paths).load()
        for variant in ('missing_version', 'wrong_grader', 'missing_identity', 'missing_night_identity'):
            with self.subTest(variant=variant):
                sleeper = env.sleeper(DurableBackend(env.time))
                sleeper.N = copy.deepcopy(original)
                if variant == 'missing_version': sleeper.N['finalization'].pop('version')
                elif variant == 'wrong_grader': sleeper.N['finalization']['grader'] = 'obsolete-grader'
                elif variant == 'missing_identity': sleeper.N['finalization'].pop('night_id')
                else: sleeper.N.pop('id')
                before = snapshot(env.paths.home)
                result = {'status': 'done', 'quiz': 100}
                with patch.object(Checkpoints, 'promote', side_effect=AssertionError('direct blocked promotion')):
                    sleeper._finalize(result)
                self.assertEqual(result['status'], 'stopped')
                self.assertTrue(result['gate_recheck_required'])
                self.assertIsNone(result['quiz'])
                self.assertEqual(before, snapshot(env.paths.home))

    def test_missing_or_invalid_payload_blocks_even_with_committed_adapter(self):
        env = self.pending('promotion_published')
        original, items = Checkpoints(env.paths).load()
        variants = ('missing_final', 'non_dict', 'missing_result', 'invalid_state', 'wrong_state_night',
                    'wrong_result_date', 'wrong_result_day', 'wrong_night_count', 'non_boolean_reverted', 'invalid_extra')
        for variant in variants:
            with self.subTest(variant=variant):
                sleeper = env.sleeper(DurableBackend(env.time))
                sleeper.N = copy.deepcopy(original)
                final = sleeper.N['finalization']
                if variant == 'missing_final': sleeper.N.pop('finalization')
                elif variant == 'non_dict': sleeper.N['finalization'] = 'invalid'
                elif variant == 'missing_result': final.pop('result')
                elif variant == 'invalid_state': final['state'] = []
                elif variant == 'wrong_state_night': final['state']['last_night']['id'] = '0' * 32
                elif variant == 'wrong_result_date': final['result']['date'] = '2020-01-01'
                elif variant == 'wrong_result_day': final['result']['day'] += 1
                elif variant == 'wrong_night_count': final['result']['night'] += 1
                elif variant == 'non_boolean_reverted': final['result']['reverted'] = 1
                else: final['extra'] = []
                before = snapshot(env.paths.home)
                result = {}
                with patch.object(Checkpoints, 'promote', side_effect=AssertionError('invalid payload promoted')):
                    sleeper._finalize(result)
                self.assertEqual(result['status'], 'stopped')
                self.assertTrue(result['blocked'])
                self.assertIsNone(result['quiz'])
                self.assertEqual(before, snapshot(env.paths.home))
        # Also exercise the public run path for a done manifest with no payload.
        original.pop('finalization')
        original['phase'] = 'done'
        Checkpoints(env.paths).publish(original, items)
        self.blocked(env)

    def test_grader_change_before_publication_blocks_without_rotating(self):
        env = self.pending('promotion_ready')
        with patch.object(gate, 'GRADER', 'strict-next-test'):
            self.blocked(env)
        self.assertFalse((env.paths.home / 'adapters.json').exists())

    def test_committed_recovery_after_grader_change_is_idempotent_at_each_boundary(self):
        for stage in ('promotion_published', 'state_written', 'items_written', 'history_written', 'finalized'):
            with self.subTest(stage=stage):
                env = self.pending(stage)
                night, _ = Checkpoints(env.paths).load()
                self.assertTrue(Checkpoints(env.paths).is_committed(night))
                manifest = (env.paths.home / 'adapters.json').read_bytes()
                committed = snapshot(env.paths.adapter)
                sleeper = env.sleeper(DurableBackend(env.time))
                sleeper._gate = lambda *args: self.fail('committed decision was regraded')
                with patch.object(gate, 'GRADER', 'strict-next-test'):
                    result = sleeper.run(env.week())
                self.assertEqual(result['status'], 'done')
                self.assertEqual(result['steps'], 0)
                self.assertEqual(manifest, (env.paths.home / 'adapters.json').read_bytes())
                self.assertEqual(committed, snapshot(env.paths.adapter))
                self.assertEqual(read_json(env.paths.state)['nights'], 1)
                history = [json.loads(line) for line in env.paths.nights.read_text().splitlines()]
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]['night_id'], night['id'])
                self.assertFalse(env.paths.work.exists())

    def test_legacy_binding_bypasses_only_exact_validated_committed_identity(self):
        env = self.pending('promotion_published')
        checkpoints = Checkpoints(env.paths)
        night, items = checkpoints.load()
        night['finalization'].pop('version')
        checkpoints.publish(night, items)
        manifest_path = env.paths.home / 'adapters.json'
        original = read_json(manifest_path)
        for changes in ({'version': 9}, {'version': True}, {'night_id': '0' * 32}, {'current': 'adapter'}):
            with self.subTest(changes=changes):
                write_json(manifest_path, dict(original, **changes))
                self.blocked(env)
        write_json(manifest_path, original)
        weight = env.paths.adapter / 'adapters.safetensors'
        saved = weight.read_bytes()
        weight.unlink()
        self.blocked(env)
        weight.write_bytes(saved)
        result = env.sleeper(DurableBackend(env.time)).run(env.week())
        self.assertEqual(result['status'], 'done')
        self.assertEqual(read_json(env.paths.state)['nights'], 1)

    def test_revision_still_invalidates_general_and_incumbent_recall_baselines(self):
        env = Env()
        self.addCleanup(env.close)
        sleeper = env.sleeper(env.backend())
        held = [{'q': 'Who employs Marta?', 'a': 'Orbix', 'dir': 'forward'}]
        before_general = sleeper.general_base_identity()
        before_recall = sleeper.measure_incumbent_recall(held)
        self.assertTrue(sleeper.recall_baseline_valid(before_recall, held))
        with patch.object(gate, 'GRADER', 'strict-next-test'):
            self.assertNotEqual(before_general, sleeper.general_base_identity())
            self.assertFalse(sleeper.recall_baseline_valid(before_recall, held))

    def test_saved_rejection_completes_without_promotion_or_new_trained_flags(self):
        for stage in ('rejection_ready', 'state_written', 'items_written', 'history_written', 'finalized'):
            for upgrade in (False, True):
                with self.subTest(stage=stage, upgrade=upgrade):
                    env = Env(ckpt_every=10, dreamcheck_share=0.0, gate_min_gain=100)
                    self.addCleanup(env.close)
                    child_env = dict(os.environ, SLEEPMLX_HOME=str(env.paths.home), SLEEPMLX_DIARY_DIR=str(env.paths.diary_dir),
                                     SLEEPMLX_USERDATA=str(env.paths.userdata_dir), LEARNER_OPS=str(env.paths.home.parent))
                    child = subprocess.run([sys.executable, '-c',
                                            'from sleepmlx.tests.test_finalization_binding import run_rejected_until_exit; import sys; run_rejected_until_exit(*sys.argv[1:])',
                                            str(env.paths.home.parent), stage], env=child_env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(child.returncode, 73, child.stdout + child.stderr)
                    checkpoints = Checkpoints(env.paths)
                    night, items = checkpoints.load()
                    self.assertTrue(night['finalization']['result']['reverted'])
                    self.assertFalse(checkpoints.is_committed(night))
                    expected = {key: item['trained'] for key, item in items['items'].items()}
                    self.assertIn(True, expected.values())
                    self.assertIn(False, expected.values())
                    night['finalization'].pop('version')  # actual old-record shape
                    checkpoints.publish(night, items)
                    sleeper = env.sleeper(DurableBackend(env.time))
                    sleeper._gate = lambda *args: self.fail('saved rejection was regraded')
                    sleeper.exporter = lambda *args, **kwargs: self.fail('rejection exported')
                    with patch.object(gate, 'GRADER', 'strict-next-test' if upgrade else gate.GRADER), \
                            patch.object(Checkpoints, 'promote', side_effect=AssertionError('rejection promoted')):
                        result = sleeper.run(env.week())
                    self.assertEqual(result['status'], 'done')
                    self.assertTrue(result['reverted'])
                    self.assertEqual(result['steps'], 0)
                    self.assertFalse((env.paths.home / 'adapters.json').exists())
                    self.assertEqual(expected, {key: item['trained'] for key, item in read_json(env.paths.items)['items'].items()})
                    self.assertEqual(read_json(env.paths.state)['nights'], 1)
                    history = [json.loads(line) for line in env.paths.nights.read_text().splitlines()]
                    self.assertEqual(len(history), 1)
                    self.assertTrue(history[0]['reverted'])
                    self.assertFalse(env.paths.work.exists())


if __name__ == '__main__':
    unittest.main()
