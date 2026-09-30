"""Stdlib scaffolding tests. Doubles below never constitute model evidence."""
import copy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.sol_nextdemo_runtime_v1 import (check_lengths, read_pinned, final_query,
    safe_path, validate_checkpoint, validate_manifest)
from scripts.sol_nextdemo_dev_v1 import Session, run_episode, validate_fixture


class TokenizerDouble:
    def encode(self, text, **kwargs):
        return list(text.encode('utf8'))


class RecordingDouble:
    def __init__(self):
        self.calls = []

    def answer(self, question, context, intervention):
        self.calls.append((question, context, intervention))
        return {'text': 'unit-test-result'}


def manifest():
    return dict(schema='sol.nextdemo.numeric-inference.v1', runtime_root='/workspace/learner',
                checkpoint={'path': '/tmp/model.pt', 'sha256': 'a' * 64}, seed=0, arm='loop',
                update=800, plan_sha256='b' * 64, seal_sha256='c' * 64,
                constructor={'family': 'ordered-loop-D256-v2'}, device='cpu',
                binding={'base': 'pinned', 'connected_resume_path': '/tmp/prior.pt', 'connected_resume_sha256': 'd' * 64},
                code_pins={name: 'e' * 64 for name in ('scripts/sol_cloud_numeric_fit_v2.py',
                    'scripts/sol_nextdemo_runtime_v1.py', 'scripts/sol_nextdemo_dev_v1.py')})


def fixture():
    # Arbitrary sentinel strings verify plumbing, never serve as model episodes.
    return dict(schema='sol.nextdemo.human-dev.v1', origin='human-authored-development',
                source_ref='unit-test-double-only', training_eligible=False,
                episodes=[dict(id='test', events=[
                    dict(kind='teach', text='source-sentinel'),
                    dict(kind='ask', text='question-before', accepted=['unit-test-result'], measure='before'),
                    dict(kind='correct', text='correction-sentinel'),
                    dict(kind='ask', text='question-after', accepted=['secret-label-sentinel'], measure='corrected')])])


class TestAdmission(unittest.TestCase):
    def test_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'data.json'; p.write_bytes(b'{}')
            self.assertEqual(read_pinned(p, hashlib.sha256(b'{}').hexdigest()), b'{}')
            with self.assertRaises(ValueError): read_pinned(p, '0' * 64)
            with self.assertRaises(ValueError): read_pinned(p, 'bad')

    def test_protected_paths_and_symlinks(self):
        with self.assertRaises(ValueError): safe_path('/tmp/readpanel320/payload')
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'ordinary'
            p.symlink_to('/tmp/reserved-panel')
            with self.assertRaises(ValueError): safe_path(p)

    def test_exact_manifest(self):
        self.assertEqual(validate_manifest(manifest())['seed'], 0)
        for key, value in [('seed', True), ('arm', 'table'), ('update', 0), ('device', 'auto')]:
            m = manifest(); m[key] = value
            with self.assertRaises(ValueError): validate_manifest(m)
        m = manifest(); m['optimizer'] = {}
        with self.assertRaises(ValueError): validate_manifest(m)

    def test_checkpoint_identity_and_lineage(self):
        m = manifest()
        raw = {key: copy.deepcopy(m[key]) for key in ('seed', 'arm', 'update', 'plan_sha256', 'seal_sha256', 'constructor', 'binding')}
        raw.update(schema='sol.cloud.numeric-fit.identity.v1', core={}, reader={}, prefix={}, sleep_enabled=False, activation=False)
        self.assertIs(validate_checkpoint(raw, m, {'base': 'pinned'}), raw)
        for key, value in [('seed', 1), ('update', 200), ('schema', 'unknown'), ('table', {}), ('sleep_enabled', True)]:
            bad = copy.deepcopy(raw); bad[key] = value
            with self.assertRaises(ValueError): validate_checkpoint(bad, m, {'base': 'pinned'})
        with self.assertRaises(ValueError): validate_checkpoint(raw, m, {'base': 'different'})

    def test_overlength_no_truncation(self):
        tokenizer = TokenizerDouble()
        self.assertEqual(check_lengths(tokenizer, 'q' * 48, 'c' * 512), (48, 512))
        for q, c in [('q' * 49, ''), ('q', 'c' * 513), ('', ''), (' ', '')]:
            with self.assertRaises(ValueError): check_lengths(tokenizer, q, c)

    def test_native_core_shape_and_reader_only_boundary(self):
        class QueryDouble:
            ndim = 4
            shape = (1, 1, 3, 256)
            def flatten(self, start, end):
                self.flatten_axes = (start, end)
                return 'reader-export'
        query = QueryDouble(); calls = []
        def core_call(core, q, memo, **metadata):
            calls.append((core, q, memo, metadata))
            return 'final-export', None, None
        runtime = dict(ordered_math=nullcontext, fixed4=core_call, core='native-core')
        self.assertEqual(final_query(runtime, query, None, 'valid', 'mvalid', 'full'), 'final-export')
        self.assertIs(calls[0][1], query)
        self.assertIsNone(calls[0][3]['notebook_mask'])
        self.assertEqual(final_query(runtime, query, None, 'valid', None, 'reader_only'), 'reader-export')
        self.assertEqual(query.flatten_axes, (1, 2)); self.assertEqual(len(calls), 1)
        query.ndim = 3
        with self.assertRaises(ValueError): final_query(runtime, query, None, 'valid', None, 'full')


class TestSession(unittest.TestCase):
    def test_order_and_hash_chain(self):
        session = Session(); session.append('teach', 'original'); session.append('correct', 'replacement')
        self.assertEqual(session.context(), 'original\nreplacement')
        self.assertEqual(session.events[1]['previous'], session.events[0]['sha256'])
        self.assertNotEqual(session.events[0]['sha256'], session.events[1]['sha256'])

    def test_fixture_scope(self):
        self.assertEqual(len(validate_fixture(fixture())['episodes']), 1)
        for key, value in [('origin', 'model-generated'), ('training_eligible', True), ('source_ref', '')]:
            p = fixture(); p[key] = value
            with self.assertRaises(ValueError): validate_fixture(p)
        p = fixture(); p['episodes'] *= 3
        with self.assertRaises(ValueError): validate_fixture(p)

    def test_labels_never_enter_backend(self):
        double = RecordingDouble()
        rows = run_episode(fixture()['episodes'][0], double)
        self.assertEqual(double.calls, [('question-before', 'source-sentinel', 'full'),
            ('question-after', 'source-sentinel\ncorrection-sentinel', 'full')])
        self.assertEqual([r['exact_text_match'] for r in rows], [True, False])
        self.assertTrue(all(r['backend'] == 'unit-test-only' for r in rows))
        self.assertNotIn('secret-label-sentinel', json.dumps(double.calls))

    def test_pre_correction_control(self):
        double = RecordingDouble()
        run_episode(fixture()['episodes'][0], double, 'pre_correction')
        self.assertEqual(double.calls[1][1], 'source-sentinel')

    def test_interventions_explicit(self):
        for intervention in ('no_notebook', 'zero_final', 'reverse_final', 'reader_only'):
            double = RecordingDouble()
            rows = run_episode(fixture()['episodes'][0], double, intervention)
            self.assertTrue(all(c[2] == intervention for c in double.calls))
            self.assertTrue(all(r['intervention'] == intervention for r in rows))
        with self.assertRaises(ValueError): run_episode(fixture()['episodes'][0], RecordingDouble(), 'oracle')

    def test_episode_isolation_and_deterministic_replay(self):
        episode = fixture()['episodes'][0]
        a, b = RecordingDouble(), RecordingDouble()
        self.assertEqual(run_episode(episode, a), run_episode(episode, b))
        self.assertEqual(a.calls, b.calls)

    def test_malformed_answers_fail(self):
        class BadDouble:
            def answer(self, *args): return {'text': None}
        with self.assertRaises(ValueError): run_episode(fixture()['episodes'][0], BadDouble())


if __name__ == '__main__':
    unittest.main()
