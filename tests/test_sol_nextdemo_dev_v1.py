"""Stdlib scaffolding tests. Doubles below never constitute model evidence."""
import copy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.sol_nextdemo_runtime_v1 import (check_lengths, read_pinned, final_query,
    safe_path, validate_checkpoint, validate_manifest, validate_continuation)
from scripts.sol_nextdemo_dev_v1 import Session, run_episode, validate_fixture, numeric_episodes
from scripts.sol_nextdemo_runtime_v1 import text_sha


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

    def test_continuation40_explicit_lineage(self):
        m = manifest(); m['schema'] = 'sol.nextdemo.continuation40-inference.v1'; m['update'] = 10240
        m['continuation'] = {key: {'path': '/tmp/'+key+'.json', 'sha256': digest*64}
            for key, digest in [('config','f'), ('source_plan','b'), ('closed','a')]}
        validate_manifest(m)
        cfg = dict(source_plan=m['continuation']['source_plan'], source_runner={'sha256': 'e'*64},
                   source_seal={'sha256':m['seal_sha256']}, sources=[dict(seed=0,arm='loop',checkpoint={'sha256':'d'*64})])
        plan = {'warmstart':{'tuples':{'0':m['binding']}}}
        raw = dict(schema='cap256.continuation40.v1', seed=0, arm='loop', update=10240,
            constructor=m['constructor'], config_sha256='f'*64, source_plan_sha256='b'*64,
            source_runner_sha256='e'*64, source_checkpoint_sha256='d'*64, additional_updates=5120,
            raw_watermark_update=10240, TRAIN_only=True, optimizer_reset=False, core={}, reader={}, prefix={})
        closed={k:raw[k] for k in ('schema','seed','arm','config_sha256','source_checkpoint_sha256')}
        closed.update(closed=True,optimizer_updates=10240,durable_model_and_Adam_reload_equal=True,checkpoint={'sha256':'a'*64})
        self.assertIs(validate_continuation(raw,m,{'base':'pinned'},cfg,plan,closed),raw)
        bad=copy.deepcopy(raw);bad['config_sha256']='0'*64
        with self.assertRaises(ValueError):validate_continuation(bad,m,{'base':'pinned'},cfg,plan,closed)


class TestSession(unittest.TestCase):
    def test_distinct_numeric_admission_and_isolated_missing_fact(self):
        data = [('I0', {'boxes':4,'items_per_box':6,'removed_items':1},8,'23','31'),
                ('I1', {'boxes':5,'items_per_box':7,'removed_items':2},9,'33','43'),
                ('P0', {'first_batch_items':16,'second_batch_items':14,'number_of_packs':3},22,'10','12'),
                ('P1', {'first_batch_items':20,'second_batch_items':24,'number_of_packs':4},28,'11','13')]
        notes=dict(schema='sol.nextdemo.numeric-notes.v1',origin='Luna-authored-numeric-wordproblem-development',source_pool='luna-notebook-wordproblem-dev-v1',training_eligible=False,episodes=[])
        targets=dict(schema='sol.nextdemo.numeric-targets.v1',source_pool=notes['source_pool'],training_eligible=False,episodes=[])
        receipt=dict(schema='sol.nextdemo.numeric-check.v1',writer_model_lineage='unit-test-writer-double',source_pool_id=notes['source_pool'],question_note_packet_sha256='a'*64,numeric_targets_sha256='b'*64,per_field_sha256={},independent_verifier_identity='unit-test-verifier-double',verifier_source_or_review_pin={'path':'unit-test-only','sha256':'c'*64},source_exclusion_metadata_pins=[{'path':'unit-test-exclusions','sha256':'d'*64}],token_cap_audit={},approved_episode_ids=[x[0] for x in data])
        for flag in ('per_world_givens_and_correction_verified','numeric_target_verification','wording_review','no_answer_or_intermediate_in_notes','query_identity_check','freshness_review','training_eligible_false'): receipt[flag]=True
        for identity,givens,new,old_target,new_target in data:
            changed='items_per_box' if identity[0]=='I' else 'first_batch_items'
            corrected={**givens,changed:new}
            episode=dict(id=identity,family=identity[0],question='query-'+identity[0],notes=' '.join(str(v) for v in givens.values()),correction=str(new),missing_notes=' '.join(str(v) for k,v in givens.items() if k!=changed),givens=givens,corrected_givens=corrected)
            notes['episodes'].append(episode)
            targets['episodes'].append(dict(id=identity,initial=old_target,corrected=new_target,missing_accepted=["I don't know", "I don't know.", "Not enough information", "Not enough information."]))
            receipt['per_field_sha256'][identity]={k:text_sha(v if type(v) is str else json.dumps(v,sort_keys=True,separators=(',',':'))) for k,v in episode.items() if k not in ('id','family')}
            receipt['token_cap_audit'][identity]=dict(question_tokens_before_EOS=4,notes_plus_correction_tokens=12,answer_tokens_before_EOS=2)
        admitted=numeric_episodes(notes,targets,receipt,{'notes':'a'*64,'targets':'b'*64})
        double=RecordingDouble();rows=run_episode(admitted[0],double)
        self.assertEqual(len(rows),3)
        self.assertEqual(double.calls[2][1],notes['episodes'][0]['missing_notes'])
        self.assertNotIn(notes['episodes'][0]['correction'],double.calls[2][1])
        self.assertNotIn('23',json.dumps(double.calls))
        self.assertEqual(rows[2]['supplied_notebook_event_count'],1)
        self.assertIsNone(rows[2]['model_selected_wrong_writes'])
        for change in ('origin','target','verification'):
            n,t,r=copy.deepcopy(notes),copy.deepcopy(targets),copy.deepcopy(receipt)
            if change=='origin': n['origin']='human-authored-development'
            elif change=='target': t['episodes'][0]['initial']='99'
            else: r['wording_review']=False
            with self.assertRaises(ValueError): numeric_episodes(n,t,r,{'notes':'a'*64,'targets':'b'*64})

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
        self.assertEqual(len(rows[1]['intended_source_writes']), 2)
        self.assertEqual(len(rows[1]['actual_source_writes']), 2)
        self.assertIsNone(rows[1]['model_selected_correct_writes'])

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
