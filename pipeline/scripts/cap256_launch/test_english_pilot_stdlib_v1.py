"""Stdlib-only tests for the English pilot (serializer, schedule, source diffs, eval seal, scorer,
blind sheet, driver). Runs under any Python >= 3.9 without Torch."""
import ast
import difflib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_test_fixtures_v1 as fx  # noqa: E402
import english_full_pilot_schedule_v1 as sched  # noqa: E402
import eval_english_fresh_windows_v1 as fresh  # noqa: E402
import score_english_free_answer_v1 as scorer  # noqa: E402
import english_blind_paraphrase_sheet_v1 as sheet  # noqa: E402
import execute_english_paraphrase_pilot_windows_v1 as driver  # noqa: E402


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_source(path, name):
    text = Path(path).read_text()
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node).splitlines()
    raise KeyError(name)


def changed_lines(a, b):
    return [l for l in difflib.unified_diff(a, b, lineterm='', n=0)
            if l[:1] in '+-' and not l.startswith(('+++', '---'))]


class SerializerTests(unittest.TestCase):
    def setUp(self):
        self.ser = fx.load_serializer()
        self.v1 = load_path('_ser_v1', fx.SERIALIZER_PATH / 'english_clean_train_input_v1.py')
        self.tok, self.bank = fx.FakeTokenizer(), fx.make_bank()

    def test_learner_text_parity_with_v1(self):
        for i in range(96):
            task, qi, text, _ = self.ser.frame_texts(self.bank, i)
            row = self.bank['examples'][i // 4]
            q = row['questions'][qi]['question'] if task == 'QA' else None
            self.assertEqual(text, self.v1.learner_text(task, row['source_text'], q))
        self.assertEqual(self.ser.TASK_INSTRUCTIONS, self.v1.TASK_INSTRUCTIONS)

    def test_frames_eos_numerals_and_document(self):
        frames = self.ser.build_all_frames(self.tok, self.bank)
        self.assertEqual(len(frames), 96)
        for f in frames:
            self.assertEqual(f['input_ids'][0][-1], 7)
            self.assertEqual(f['labels'][0][-1], 7)
            self.assertNotIn(7, f['input_ids'][0][:-1])
            self.assertLessEqual(len(f['input_ids'][0]), 64)
            self.assertLessEqual(len(f['labels'][0]), 48)
        self.assertTrue(frames[0]['input_numeral_spans'])
        doc = self.ser.frames_document(frames, 'a' * 64, {'fixture': True})
        self.assertEqual(len(self.ser.validate_frames_document(doc, self.bank, 'a' * 64)), 96)
        doc['frames'][5]['target_text'] += ' x'
        with self.assertRaises(Exception):
            self.ser.validate_frames_document(doc, self.bank, 'a' * 64)

    def test_overflow_raises_listing_all_no_truncation(self):
        bank = fx.make_bank()
        long = ' '.join('w%d' % i for i in range(70))
        bank['examples'][3]['source_text'] = long
        bank['examples'][7]['paraphrase'] = long
        with self.assertRaises(Exception) as caught:
            self.ser.build_all_frames(self.tok, bank)
        message = str(caught.exception)
        for idx in (12, 13, 14, 15, 31):
            self.assertIn(str(idx), message)


class ScheduleTests(unittest.TestCase):
    def test_counts_arms_determinism_and_document(self):
        for seed in (0, 1):
            records = sched.pilot_schedule(seed)
            self.assertEqual(len(records), 2304)
            self.assertEqual(sum(r['task_role'] == 'QA' for r in records), 1536)
            qa_c = [r['control_frame_index'] for r in records if r['task_role'] == 'QA']
            qa_t = [r['treatment_frame_index'] for r in records if r['task_role'] == 'QA']
            self.assertEqual(qa_c, qa_t)
            self.assertEqual(records, sched.pilot_schedule(seed))
        self.assertNotEqual(sched.pilot_schedule(0), sched.pilot_schedule(1))
        doc = sched.schedule_document()
        self.assertEqual(set(sched.validate_schedule_document(doc)), {0, 1})
        doc['schedules']['0'][0], doc['schedules']['0'][1] = doc['schedules']['0'][1], doc['schedules']['0'][0]
        with self.assertRaises(ValueError):
            sched.validate_schedule_document(doc)

    def test_written_file_matches_generator(self):
        path = ROOT / sched.DEFAULT_OUT
        if path.is_file():
            sched.validate_schedule_document(json.loads(path.read_bytes()))


class SourceDiffTests(unittest.TestCase):
    def test_observer48_differs_only_in_name_and_cap(self):
        original = function_source(ROOT / 'scripts/sol_cloud_capability256_v1.py', 'observe_generation')
        copy = function_source(HERE / 'english_observe_generation48_v1.py', 'observe_generation48')
        changed = changed_lines(original, copy)
        self.assertEqual(len(changed), 6, changed)  # def line + guard line + message, each - and +
        joined = '\n'.join(l for l in changed if l.startswith('+'))
        self.assertIn('ENGLISH_OUTPUT_CAP', joined)
        self.assertIn('observe_generation48', joined)

    def test_cap64_differs_only_in_name_and_guard(self):
        original = function_source(ROOT / 'scripts/sol_spatial_poc_ordered_v2.py', 'ordered_begin')
        copy = function_source(HERE / 'english_ordered_begin_cap64_v1.py', 'english_ordered_begin')
        changed = changed_lines(original, copy)
        self.assertEqual(len(changed), 4, changed)
        plus = [l for l in changed if l.startswith('+')]
        self.assertTrue(plus[0].startswith('+def english_ordered_begin('))
        self.assertIn('ENGLISH_QUERY_CAP', plus[1])


def fake_eval(tmp, outputs, train_outputs, two_option=()):
    """Gold file, RAW files and SEALED.json for six states. outputs[state][item_id] = text."""
    tmp = Path(tmp)
    items, gold, passages = [], [], []
    for subset, prefix in ((scorer.P1_SUBSET, 'fc'), (scorer.P2_SUBSET, 'mt')):
        for i in range(16):
            iid = '%s-%02d' % (prefix, i)
            items.append({'item_id': iid, 'learner_text': 'Answer from the passage.\nPassage: x', 'task': 'QA'})
            canonical = 'yes' if i < 3 else 'Ana %d' % i
            gold.append({'item_id': iid, 'task': 'QA', 'subset': subset, 'canonical_answer': canonical,
                         'accepted_answers': [canonical, 'Ana'] if i == 5 else [canonical], 'passage_id': 'P' + iid,
                         'question_type': 'yes_no' if i < 3 else 'open', 'two_option_choice': iid in two_option})
            passages.append({'passage_id': 'P' + iid, 'passage': 'Passage for ' + iid})
    items.append({'item_id': 'pp-0', 'learner_text': 'Restate the passage with the same meaning.\nPassage: x',
                  'task': 'paraphrase'})
    gold.append({'item_id': 'pp-0', 'task': 'paraphrase', 'subset': scorer.P2_SUBSET, 'passage_id': 'Ppp',
                 'required_propositions': ['Ana gave apples', 'before lunch'], 'reference_paraphrase': 'r'})
    passages.append({'passage_id': 'Ppp', 'passage': 'Ana gave apples before lunch.'})
    eval_items = tmp / 'eval_items.json'
    eval_items.write_text(json.dumps({'model_inputs': items, 'grading_metadata': gold, 'passages': passages}))
    frozen = common.digest(eval_items)
    out = tmp / 'EVAL'
    out.mkdir()
    states = []
    for state in scorer.STATES:
        raw = out / ('RAW-%s.jsonl' % state)
        for item in items:
            text = outputs.get(state, {}).get(item['item_id'], 'nothing')
            common.append_jsonl(raw, {'state_id': state, 'panel': 'fresh', 'item_id': item['item_id'],
                                      'task': item['task'], 'output_text': text, 'observation_valid': True})
        arm = None if 'parent' in state else state.split('-')[1]
        for fi in fresh.train_panel(arm):
            p, q = divmod(fi, 4)
            text = train_outputs.get(state, lambda p, q: 'Ana')(p, q)
            common.append_jsonl(raw, {'state_id': state, 'panel': 'TRAIN', 'frame_index': fi,
                                      'output_text': text, 'observation_valid': True})
        states.append({'state_id': state, 'raw_sha256': common.digest(raw)})
    fresh.seal(out, states, 'b' * 64, 'c' * 64, {'fresh_source_sha256': frozen})
    return out, eval_items, frozen


def train_bank():
    bank = fx.make_bank()
    return bank


def answers_for(n_fc, n_mt):
    """Correct answers for the first n items in each subset."""
    out = {}
    for i in range(n_fc):
        out['fc-%02d' % i] = 'Yes.' if i < 3 else ' "ana  %d"! ' % i
    for i in range(n_mt):
        out['mt-%02d' % i] = 'YES' if i < 3 else 'Ana %d.' % i
    return out


RECEIPTS = [{'closed': True, 'optimizer_updates': 2304, 'cap_violations': 0, 'finite_loss_all_updates': True,
             'gradient_contract_failures': 0, 'seed': s, 'arm': a, 'matched': {'m': s}}
            for s in (0, 1) for a in ('control', 'treatment')]


def good_train(p, q):
    return 'Ana' if q == 0 else str(p + 2)


class ScorerTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(scorer.normalize('  “Ana’s  Dog.” '), "ana's dog")
        self.assertEqual(scorer.normalize('Yes!'), 'yes')
        self.assertEqual(scorer.normalize('Café'), scorer.normalize('Café'))
        self.assertTrue(scorer.is_correct('ana', 'Ana 5', ['Ana']))
        self.assertFalse(scorer.is_correct('Ana 5 apples', 'Ana 5', []))

    def test_end_to_end_pass_and_breakdowns(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = {s: answers_for(8, 8) for s in scorer.STATES}
            outputs['seed0-treatment'] = outputs['seed1-treatment'] = answers_for(10, 10)
            train = {s: good_train for s in scorer.STATES}
            out, items, frozen = fake_eval(tmp, outputs, train, two_option=('fc-04',))
            result = scorer.score(out, items, frozen, train_bank(), RECEIPTS)
            self.assertEqual(result['primaries']['N'], {'P1': 16, 'P2': 16})
            self.assertEqual(result['primaries']['seed0-control'], {'P1': 8, 'P2': 8})
            self.assertEqual(result['per_state']['seed0-control'][scorer.P1_SUBSET]['yes_no'], {'correct': 3, 'N': 3})
            self.assertEqual(result['per_state']['seed0-control'][scorer.P1_SUBSET]['two_option'], {'correct': 1, 'N': 1})
            self.assertEqual(result['TRAIN_fit']['seed0-control'], {'correct': 48, 'N': 48})
            self.assertEqual(result['verdict'], 'PASS')  # D=2 = ceil(16/8)

    def test_underfit_void_and_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = {s: answers_for(8, 8) for s in scorer.STATES}
            train = {s: good_train for s in scorer.STATES}
            train['seed1-control'] = lambda p, q: good_train(p, q) if q == 0 or p < 16 else 'wrong'  # 40/48
            train['seed1-treatment'] = lambda p, q: good_train(p, q) if q == 0 or p < 15 else 'wrong'  # 39/48
            out, items, frozen = fake_eval(tmp, outputs, train)
            result = scorer.score(out, items, frozen, train_bank(), RECEIPTS)
            self.assertEqual(result['TRAIN_fit']['seed1-control']['correct'], 40)
            self.assertEqual(result['verdict'], 'UNDERFIT-VOID')
            self.assertEqual(result['underfit_states'], ['seed1-treatment'])
            self.assertEqual(scorer.score(out, items, frozen, train_bank(), None)['verdict'], 'VOID')

    def test_seal_verified_before_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, items, frozen = fake_eval(tmp, {}, {})
            raw = out / 'RAW-seed0-treatment.jsonl'
            raw.write_text(raw.read_text().replace('nothing', 'changed', 1))
            with mock.patch.object(scorer, 'load_gold') as gold:
                with self.assertRaises(ValueError):
                    scorer.score(out, items, frozen, train_bank(), RECEIPTS)
                gold.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            out, items, frozen = fake_eval(tmp, {}, {})
            with self.assertRaises(ValueError):
                scorer.verify_seal(out, 'd' * 64, items)

    def test_verdict_rules(self):
        def p(c0, t0, c1, t1, parent=(8, 8)):
            v = {'N': {'P1': 32, 'P2': 32}, 'seed0-parent': {'P1': parent[0], 'P2': 0},
                 'seed1-parent': {'P1': parent[1], 'P2': 0}}
            for name, (a, b) in (('seed0-control', c0), ('seed0-treatment', t0),
                                 ('seed1-control', c1), ('seed1-treatment', t1)):
                v[name] = {'P1': a, 'P2': b}
            return v
        fit = {s: {'correct': 48} for s in scorer.STATES}
        self.assertEqual(scorer.verdict(p((8, 8), (12, 12), (8, 8), (12, 12)), fit, True)['verdict'], 'PASS')
        self.assertEqual(scorer.verdict(p((8, 8), (12, 12), (8, 8), (12, 12), parent=(11, 8)), fit, True)['verdict'],
                         'NULL')  # control lost 3 > ceil(32/16) vs parent
        self.assertEqual(scorer.verdict(p((8, 8), (8, 7), (8, 8), (6, 8)), fit, True)['verdict'], 'FAIL')
        self.assertEqual(scorer.verdict(p((8, 8), (4, 8), (8, 8), (4, 8)), fit, True)['verdict'], 'HARM')
        self.assertEqual(scorer.verdict(p((8, 8), (12, 12), (8, 8), (9, 12)), fit, True)['verdict'], 'NULL')
        self.assertEqual(scorer.verdict(p((8, 8), (4, 9), (8, 8), (4, 9)), fit, True)['verdict'], 'HARM')
        self.assertEqual(math.ceil(32 / 8), 4)


class FreshInputTests(unittest.TestCase):
    def test_extract_inputs_only_and_length_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, items, frozen = fake_eval(tmp, {}, {})
            dest = Path(tmp) / 'inputs.json'
            fresh.extract_fresh_inputs(items, dest)
            loaded, source = fresh.load_fresh_inputs(dest)
            self.assertEqual(source, frozen)
            self.assertNotIn('grading_metadata', dest.read_text())
            self.assertEqual(len(loaded), 33)
            tok = fx.FakeTokenizer()
            records = fresh.tokenize_fresh(tok, loaded)
            self.assertTrue(all(r['input_ids'][0][-1] == 7 for r in records))
            long = [{'item_id': 'x', 'task': 'QA', 'learner_text': ' '.join('w%d' % i for i in range(64))},
                    {'item_id': 'y', 'task': 'QA', 'learner_text': ' '.join('v%d' % i for i in range(63))}]
            with self.assertRaises(ValueError) as caught:
                fresh.tokenize_fresh(tok, long)
            self.assertIn('1 fresh input', str(caught.exception))
            with self.assertRaises(ValueError):
                fresh.validate_model_inputs([{'item_id': 'a', 'learner_text': 't', 'task': 'QA', 'canonical_answer': 'x'}])

    def test_train_panels(self):
        self.assertEqual(len(fresh.train_panel(None)), 96)
        self.assertEqual(len(fresh.train_panel('control')), 72)
        self.assertNotIn(3, fresh.train_panel('control'))
        self.assertNotIn(2, fresh.train_panel('treatment'))


class BlindSheetTests(unittest.TestCase):
    def test_sheet_has_no_arm_and_tallies(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = {s: {'pp-0': 'Ana gave apples before lunch (%d)' % i} for i, s in enumerate(scorer.STATES)}
            out, items, frozen = fake_eval(tmp, outputs, {})
            built, key = sheet.build_sheet(out, items, frozen)
            text = json.dumps(built)
            for word in ('control', 'treatment', 'parent', 'seed'):
                self.assertNotIn(word, text)
            self.assertEqual(len(built['rows']), 6)
            again, _ = sheet.build_sheet(out, items, frozen)
            self.assertEqual(built, again)
            with self.assertRaises(ValueError):
                sheet.tally(built, key)
            for row in built['rows']:
                for prop in row['required_propositions']:
                    prop['mark'] = 'kept'
                row['added_claims'] = 0
            tally = sheet.tally(built, key)
            self.assertEqual(tally['seed0-treatment']['all_kept_none_added_none_reversed'], 1)


WORKER = textwrap.dedent('''
    import json, os, sys, time
    args = sys.argv
    sha = args[args.index('--config-sha256') + 1]
    mode = os.environ.get('FAKE_MODE', 'ok')
    print(json.dumps({'event': 'actual-worker-ready', 'pid': os.getpid() if mode != 'wrongpid' else 1,
                      'config_sha256': sha}), flush=True)
    go = sys.stdin.readline()
    if go != 'BEGIN ENGLISH ZERO UPDATE PROBE\\n':
        sys.exit(9)
    if mode == 'sleep':
        time.sleep(60)
    print(json.dumps({'event': 'done'}), flush=True)
''')


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'worker.py').write_text(WORKER)
        cfg = {'kind': 'probe', 'dispatch_allowed': True,
               'runner': {'path': 'worker.py', 'sha256': common.digest(self.root / 'worker.py')},
               'budget': {'worker_seconds': 100, 'retained_free_bytes': 1}}
        (self.root / 'cfg.json').write_text(json.dumps(cfg))
        self.marker = self.root / 'GPU-BUSY.txt'

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, seconds=60):
        return ['--root', str(self.root), '--config', str(self.root / 'cfg.json'),
                '--config-sha256', common.digest(self.root / 'cfg.json'), '--python', sys.executable,
                '--gpu-busy-marker', str(self.marker), '--driver-namespace', 'R', '--whole-job-seconds', str(seconds),
                '--job-name', 'test']

    def test_success_and_marker_removed(self):
        self.assertEqual(driver.main(self.args()), 0)
        self.assertFalse(self.marker.exists())
        folder = next((self.root / 'R').iterdir())
        self.assertTrue((folder / 'DRIVER-CLOSED.json').is_file())
        self.assertIn('done', (folder / 'WORKER-STDOUT.log').read_text())

    def test_busy_marker_is_left_alone(self):
        self.marker.write_text('queue job other')
        self.assertEqual(driver.main(self.args()), driver.EXIT_BUSY)
        self.assertEqual(self.marker.read_text(), 'queue job other')

    def test_wrong_ready_and_wall_kill(self):
        with mock.patch.dict('os.environ', {'FAKE_MODE': 'wrongpid'}):
            with self.assertRaises(RuntimeError):
                driver.main(self.args())
        self.assertFalse(self.marker.exists())
        with mock.patch.dict('os.environ', {'FAKE_MODE': 'sleep'}):
            with self.assertRaises(RuntimeError) as caught:
                driver.main(self.args(seconds=3))
        self.assertIn('wall cap', str(caught.exception))
        self.assertFalse(self.marker.exists())

    def test_tampered_worker_rejected(self):
        (self.root / 'worker.py').write_text(WORKER + '\n# changed\n')
        with self.assertRaises(ValueError):
            driver.main(self.args())
        self.assertFalse(self.marker.exists())


class CheckRunsIgnoresArmKey(unittest.TestCase):
    def test_matched_records_differing_only_in_arm_pass_v1(self):
        import score_english_free_answer_v1 as sc
        base = {k: 'x' for k in sc.MATCHED_FIELDS}
        runs = [dict(seed=s, arm=a, closed=True, optimizer_updates=2304, cap_violations=0,
                     finite_loss_all_updates=True, gradient_contract_failures=0, matched=dict(base, arm=a))
                for s in (0, 1) for a in ('control', 'treatment')]
        self.assertEqual(sc.check_runs(runs), (True, 'ok'))
        runs[1]['matched']['schedule_sha256'] = 'y'
        self.assertFalse(sc.check_runs(runs)[0])


if __name__ == '__main__':
    unittest.main()
