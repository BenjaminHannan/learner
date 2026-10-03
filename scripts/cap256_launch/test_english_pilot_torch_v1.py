"""Torch CPU tests for the English pilot: cap64 binding, feature cache, zero-update probe, training
worker (matched asserts, Adam aliasing regression, bit-exact resume), eval generation, config admission.
Uses tiny fake fixtures (fake tokenizer + fake frozen LM of width 2048, real reader/core/prefix/tool)."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_test_fixtures_v1 as fx  # noqa: E402
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import english_full_pilot_schedule_v1 as sched  # noqa: E402
import english_zero_update_probe_v1 as probe  # noqa: E402
import train_english_paraphrase_pilot_windows_v1 as worker  # noqa: E402
import eval_english_fresh_windows_v1 as fresh  # noqa: E402

RT = runtime.import_runtime()
torch = RT.torch


class Shared:
    ctx = None
    parents = {}

    @classmethod
    def get(cls):
        if cls.ctx is None:
            cls.tok, cls.bank = fx.FakeTokenizer(), fx.make_bank()
            cls.ctx = fx.make_context(RT, cls.tok, cls.bank)
            for seed in (0, 1):
                cls.parents[seed] = fx.make_parent(RT, cls.ctx, seed)
        return cls


def features_for(lm, n, seed=3):
    g = torch.Generator().manual_seed(seed)
    ids = torch.randint(8, 500, (1, n), generator=g)
    ids[0, -1] = 7
    mask = torch.ones((1, n), dtype=torch.bool)
    return RT.compare.extract_question_features(lm, ids, mask, 'contextual', torch), mask


class Cap64Tests(unittest.TestCase):
    def test_binding_parity_and_caps(self):
        s = Shared.get()
        saved = s.parents[0]
        bound = runtime.build_modules(RT, s.ctx.dec, 0, 'cpu')
        runtime.restore_parent_modules(RT, saved, bound, s.ctx.lm)
        plain = runtime.build_modules(RT, s.ctx.dec, 0, 'cpu')
        for name, module in plain:
            module.load_state_dict(saved[name], strict=True)
        core_b, reader_b = bound[0][1], bound[1][1]
        core_p, reader_p = plain[0][1], plain[1][1]
        self.assertEqual(RT.ordered.QUERY_CAP, 49)
        self.assertEqual(core_b.constructor(), core_p.constructor())
        self.assertTrue(RT.cap64.is_bound(core_b))
        self.assertFalse(RT.cap64.is_bound(core_p))
        before = {k: v.clone() for k, v in core_b.state_dict().items()}
        x, mask = features_for(s.ctx.lm, 49)
        h_b, _ = runtime.english_graph(RT, core_b, reader_b, x, mask)
        query = RT.compare.project_cached_question(reader_p, x, mask)
        with RT.ordered_attention_math():
            h_p, _, _ = RT.train_api.fixed4_training(core_p, query, None, query_mask=mask)
        self.assertTrue(torch.equal(h_b, h_p))
        x64, m64 = features_for(s.ctx.lm, 64)
        h64, _ = runtime.english_graph(RT, core_b, reader_b, x64, m64)
        self.assertEqual(tuple(h64.shape), (1, 64, 256))
        with self.assertRaises(ValueError):
            q = RT.compare.project_cached_question(reader_p, x64, m64)
            with RT.ordered_attention_math():
                RT.train_api.fixed4_training(core_p, q, None, query_mask=m64)
        x65, m65 = features_for(s.ctx.lm, 65)
        with self.assertRaises(ValueError):
            runtime.english_graph(RT, core_b, reader_b, x65, m65)
        self.assertTrue(all(torch.equal(before[k], v) for k, v in core_b.state_dict().items()))
        self.assertEqual(set(before), set(core_b.state_dict()))


class FeatureCacheTests(unittest.TestCase):
    def test_key_build_and_reuse(self):
        s = Shared.get()
        identity = {'contextual_layer': 'last'}
        frames = s.ctx.frames[:3]
        records = [RT.cache.frame_input_record(f) for f in frames]
        with mock.patch.object(RT.cache, 'load_compare_worker') as load:
            load.return_value = types.SimpleNamespace(validate_feature_identity=lambda i: True,
                                                      extract_question_features=RT.compare.extract_question_features)
            key = RT.cache.english_input_feature_key(records[0], identity)
            with_target = dict(records[0], target_text='secret', labels=frames[0]['labels'])
            self.assertEqual(RT.cache.english_input_feature_key(with_target, identity), key)
            self.assertNotIn('secret', json.dumps(key))
            bad = dict(records[0], input_ids=[records[0]['input_ids'][0][:-1]])
            with self.assertRaises(ValueError):
                RT.cache.english_input_feature_key(bad, identity)
            with tempfile.TemporaryDirectory() as tmp:
                kw = dict(device='cpu', directory=tmp, guard=lambda *a, **k: {}, gpu_guard=lambda: {},
                          max_seconds=60, max_bytes=64 * common.MIB)
                first, r1 = RT.cache.prepare_english_feature_cache(s.ctx.lm, records, identity, torch, **kw)
                second, r2 = RT.cache.prepare_english_feature_cache(s.ctx.lm, records, identity, torch, **kw)
                self.assertFalse(r1['reused'])
                self.assertTrue(r2['reused'])
                self.assertTrue(all(torch.equal(a, b) for a, b in zip(first, second)))
                self.assertTrue(torch.equal(first[0], s.ctx.features[frames[0]['frame_index']]))


class ProbeTests(unittest.TestCase):
    def test_probe_parent_contract_and_no_change(self):
        s = Shared.get()
        saved = copy.deepcopy(s.parents[0])
        before = common.tree_digest(saved, torch)
        ctx = copy.copy(s.ctx)
        ctx.frames = s.ctx.frames[:4]
        result = probe.probe_parent(RT, ctx, 0, saved, 3)
        self.assertTrue(result['gradient_contract_passed'])
        self.assertEqual(result['runs']['control']['probes'], 72)
        self.assertEqual(result['parameter_names'], 114)
        self.assertEqual(result['native_answer_count'], 4)
        self.assertEqual(common.tree_digest(saved, torch), before)
        with self.assertRaises(ValueError):
            probe.probe_parent(RT, ctx, 0, saved, 5120, generate=False)


def train_ctx(out, total=8, resume_every=4, segment=None):
    s = Shared.get()
    ctx = copy.copy(s.ctx)
    ctx.out, ctx.total_updates, ctx.resume_every = Path(out), total, resume_every
    ctx.segment_update_limit, ctx.run_order = segment, worker.RUN_ORDER[:2]
    return ctx


def final_state(out, seed, arm):
    return torch.load(worker.run_folder(out, seed, arm) / 'final-checkpoint.pt', map_location='cpu',
                      weights_only=True)


class WorkerTests(unittest.TestCase):
    def test_runs_aliasing_and_matched(self):
        s = Shared.get()
        records = sched.pilot_schedule(0)[:8]
        saved = s.parents[0]
        before = common.tree_digest(saved, torch)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = train_ctx(tmp)
            results = worker.execute_runs(RT, ctx, {0: records}, {0: (saved, 'p' * 64)})
            self.assertEqual(common.tree_digest(saved, torch), before)  # parent Adam moments not aliased
            self.assertEqual([r['arm'] for r in results], ['control', 'treatment'])
            for r in results:
                self.assertEqual(r['optimizer_updates'], 8)
                self.assertEqual(r['gradient_contract_failures'], 0)
                self.assertTrue(r['tool_bit_identical'] and r['halt_bit_identical'] and r['LM_unchanged'])
            self.assertEqual(results[0]['matched'] | {'arm': 'x'}, results[1]['matched'] | {'arm': 'x'})
            final_c, final_t = final_state(tmp, 0, 'control'), final_state(tmp, 0, 'treatment')
            for name in ('tool',):
                self.assertTrue(all(torch.equal(final_c[name][k], saved[name][k]) for k in saved[name]))
            self.assertFalse(all(torch.equal(final_c['reader'][k], final_t['reader'][k]) for k in saved['reader']))
            record = json.loads((worker.run_folder(tmp, 0, 'control') / 'MATCHED.json').read_text())
            tampered = dict(record, optimizer_sha256='0' * 64)
            with self.assertRaises(ValueError):
                worker.check_matched(tmp, 0, 'treatment', tampered)

    def test_resume_is_bit_exact(self):
        s = Shared.get()
        records = sched.pilot_schedule(1)[:8]
        saved = s.parents[1]
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ctx = train_ctx(a)
            ctx.run_order = ((1, 'treatment'),)
            worker.execute_runs(RT, ctx, {1: records}, {1: (saved, 'p' * 64)})
            ctx_b = train_ctx(b, segment=3)
            ctx_b.run_order = ((1, 'treatment'),)
            with self.assertRaises(worker.SegmentPaused):
                worker.execute_runs(RT, ctx_b, {1: records}, {1: (saved, 'p' * 64)})
            folder = worker.run_folder(b, 1, 'treatment')
            self.assertTrue((folder / 'resume-0003.pt').is_file())
            ctx_b.segment_update_limit = None
            worker.execute_runs(RT, ctx_b, {1: records}, {1: (saved, 'p' * 64)})
            straight, resumed = final_state(a, 1, 'treatment'), final_state(b, 1, 'treatment')
            self.assertEqual(sorted(straight), sorted(resumed))
            for key in straight:  # every saved field, incl. model, Adam, RNG, audit (file bytes may differ)
                self.assertTrue(common.state_equal(straight[key], resumed[key], torch), key)
            raw_a = (worker.run_folder(a, 1, 'treatment') / 'TRAIN-RAW.jsonl').read_text().splitlines()
            raw_b = (folder / 'TRAIN-RAW.jsonl').read_text().splitlines()
            strip = lambda line: {k: v for k, v in json.loads(line).items()  # noqa: E731
                                  if k not in ('update_seconds', 'gpu')}
            self.assertEqual([strip(x)['CE'] for x in raw_a], [strip(x)['CE'] for x in raw_b])
            self.assertFalse(list(folder.glob('resume-*.pt')))


class EvalTests(unittest.TestCase):
    def test_generate_state_and_seal(self):
        s = Shared.get()
        items = [{'item_id': 'f%d' % i, 'task': 'QA',
                  'learner_text': 'Answer from the passage.\nPassage: Mia has %d cats.\nQuestion: How many cats?' % i}
                 for i in range(3)]
        recs = fresh.tokenize_fresh(s.tok, items)
        ctx = copy.copy(s.ctx)
        ctx.tokenizer = s.tok
        ctx.fresh_features = {}
        for r in recs:
            ids = torch.tensor(r['input_ids'])
            mask = torch.tensor(r['input_mask'])
            ctx.fresh_features[r['input_id']] = RT.compare.extract_question_features(
                s.ctx.lm, ids, mask, 'contextual', torch)
        saved = copy.deepcopy(s.parents[0])
        before = common.tree_digest(saved, torch)
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / 'RAW-seed0-control.jsonl'
            with mock.patch.object(fresh, 'train_panel', return_value=[0, 1, 2]):
                result = fresh.generate_state(RT, ctx, 'seed0-control', saved, 0, 'control', recs, raw)
            rows = [json.loads(l) for l in raw.read_text().splitlines()]
            self.assertEqual(result['generations'], 6)
            self.assertEqual([r['panel'] for r in rows], ['fresh'] * 3 + ['TRAIN'] * 3)
            self.assertTrue(all(r['observation_valid'] for r in rows))
            self.assertTrue(all(len(r['MODEL_raw_generate_ids'][0]) <= 48 for r in rows))
            self.assertNotIn('canonical_answer', raw.read_text())
            self.assertEqual(common.tree_digest(saved, torch), before)
        with self.assertRaises(ValueError):
            fresh.validate_state({'update': 2304, 'seed': 0, 'arm': 'treatment', 'parent_checkpoint_sha256': 'x'},
                                 0, 'control', 'x')


class ConfigTests(unittest.TestCase):
    def test_native_config_admission(self):
        s = Shared.get()
        ser = fx.load_serializer()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def put(name, data):
                path = root / name
                path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
                return {'path': name, 'sha256': common.digest(path)}
            bank = put('bank.json', s.bank)
            frames = put('frames.json', ser.frames_document(s.ctx.frames, bank['sha256'], {'fixture': 1}))
            schedule = put('schedule.json', sched.schedule_document())
            parents = [{'seed': i, 'checkpoint': put('parent%d.pt' % i, b'parent%d' % i)} for i in (0, 1)]
            runner = put('runner.py', b'# runner')
            cfg = {'schema': runtime.CONFIG_SCHEMA, 'kind': 'probe', 'device': 'cpu',
                   'lm': {'model_path': 'lm', 'provenance': put('prov.json', {}), 'adapter': put('ad.pt', b'a')},
                   'feature_identity': {}, 'bank': bank, 'frames': frames, 'schedule': schedule,
                   'parents': parents, 'output_namespace': 'OUT', 'cache_namespace': 'CACHE',
                   'budget': {'worker_seconds': 2400, 'new_output_bytes': 1, 'cuda_peak_reserved_cap_bytes': 1,
                              'project_cap_bytes': 100000000000, 'retained_free_bytes': 2 * runtime.GIB,
                              'aggregate_spend_usd_cap': '0.00'},
                   'dispatch_allowed': False, 'runner': runner}
            shas = {i: parents[i]['checkpoint']['sha256'] for i in (0, 1)}
            with mock.patch.object(runtime, 'PARENT_SHAS', shas), \
                    mock.patch.object(runtime, 'BANK_SHA256', bank['sha256']), \
                    mock.patch.object(runtime, 'load_serializer', return_value=ser):
                admitted = runtime.validate_native_config(root, cfg, 'probe', root / 'runner.py')
                self.assertEqual(len(admitted['frames']), 96)
                for change in ({'budget': dict(cfg['budget'], aggregate_spend_usd_cap='1.00')},
                               {'output_namespace': '../x'}, {'extra': 1},
                               {'parents': [parents[1], parents[0]]}):
                    with self.assertRaises(ValueError):
                        runtime.validate_native_config(root, dict(cfg, **change), 'probe', root / 'runner.py')
                with self.assertRaises(ValueError):
                    runtime.validate_native_config(root, cfg, 'train', root / 'runner.py')
            with self.assertRaises(ValueError):
                runtime.validate_native_config(root, cfg, 'probe', root / 'runner.py')  # real parent pins


if __name__ == '__main__':
    unittest.main()
