"""python -m logic_transfer.tests   (run from the repo root; the slow end-to-end test needs a parent checkpoint and is skipped without one)"""
import hashlib
import json
import os
import tempfile
import unittest

import numpy as np

from logic_transfer import course, ladder, rows, run_lt1, verify_rungs

PARENT = run_lt1.PARENTS['s200']


def gen_row(i=0, kind='logic', split='train', answer='true', proof=None):
    return {'id': f'{kind}-{split}-1-{i:06d}', 'kind': kind, 'split': split, 'question': 'Anne is red. Every red thing is big. Is it true that Anne is big?',
            'answer': answer, 'steps': proof or ['Anne is red.', '3 + 4 = 7', 'sum [1,2]', 'So Anne is big.'], 'program': 'F red(anne); R red(x)>big(x); Q big(anne)',
            'label': answer, 'depth': 1, 'n_rules': 1, 'n_facts': 1, 'n_distractors': 0, 'sampler': 'label-first', 'chars': 60}


class RowConverter(unittest.TestCase):
    def test_fields_and_no_program(self):
        from custom_io.models import progparse as pp
        for kind, ans in (('logic', 'unknown'), ('placebo', 'yes')):
            r = rows.convert_row(gen_row(5, kind, answer=ans))
            for k in ('id', 'prompt', 'answer', 'accepted', 'family', 'level', 'stage', 'variant', 'steps'):
                self.assertIn(k, r)
            self.assertEqual(r['steps'], ['none'])                       # arithmetic-looking proof lines must not leak into steps
            self.assertEqual(r['family'], {'logic': 'logic_fc', 'placebo': 'logic_placebo'}[kind])
            self.assertEqual(r['variant'], 'train')
            self.assertEqual(r['accepted'], [ans])
            self.assertEqual(r['meta']['proof'][1], '3 + 4 = 7')
            self.assertFalse(pp.row_targets(r)['prog'])

    def test_file_roundtrip_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, 'g.jsonl'), os.path.join(d, 'c.jsonl')
            with open(src, 'w') as f:
                for i in range(20):
                    f.write(json.dumps(gen_row(i, 'logic', answer=('true', 'false', 'unknown')[i % 3])) + '\n')
            self.assertEqual(rows.convert(src, dst), 20)
            v = rows.verify(dst)
            self.assertEqual((v['n'], v['no_program'], v['unk_chars']), (20, 20, 0))
            with open(src, 'a') as f:
                f.write(json.dumps(gen_row(3)) + '\n')                    # duplicate id
            with self.assertRaises(AssertionError):
                rows.convert(src, dst)

    def test_verify_rejects_long_prompt_and_unknown_char(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ('x' * 209, 'café is red. Is it true?'):
                g = gen_row(0); g['question'] = bad
                p = os.path.join(d, 'b.jsonl')
                open(p, 'w').write(json.dumps(rows.convert_row(g)) + '\n')
                with self.assertRaises(AssertionError):
                    rows.verify(p)


class Marks(unittest.TestCase):
    def test_parse_and_hold(self):
        m = course.parse_marks('dev>=90, gate@2>=65')
        self.assertEqual(m, [('dev', None, 90.0), ('gate', '2', 65.0)])
        res = {'dev': {'exact': 91.0, 'by_level': {}}, 'gate': {'exact': 50.0, 'by_level': {'2': {'correct': 70, 'n': 100}}}}
        self.assertTrue(course.marks_hold(res, m))
        res['gate']['by_level']['2']['correct'] = 64
        self.assertFalse(course.marks_hold(res, m))
        self.assertFalse(course.marks_hold({'dev': res['dev']}, m))             # a missing file is not a pass
        self.assertFalse(course.marks_hold(res, []))                            # no marks never stops a run


class LadderRows(unittest.TestCase):
    """Rungs 0-2: shape, exact label thirds, no train/eval prompt overlap, and the independent solver agrees on every row."""

    def test_build_and_independent_check(self):
        with tempfile.TemporaryDirectory() as d:
            for rung in (0, 1, 2):
                s = ladder.build(rung, d, n_train=300, n_eval=60, n_new=30)
                for name, info in s['files'].items():
                    self.assertEqual(info['independent_label_check']['agreement'], 1.0, (rung, name))
                    self.assertLessEqual(info['verify']['max_prompt_chars'], 208)
                    self.assertEqual(sorted(info['labels'].values()), [info['n'] // 3] * 3 if info['n'] % 3 == 0 else sorted(info['labels'].values()))
                    self.assertEqual(info['distinct_prompts'], info['n'])
                    if name != 'train':
                        self.assertEqual(info['overlap_with_train_prompts'], 0)

    def test_solver_catches_wrong_labels(self):
        with tempfile.TemporaryDirectory() as d:
            s = ladder.build(1, d, n_train=30, n_eval=30, n_new=30)
            p = os.path.join(d, 'rung1', 'dev.jsonl')
            rs = [json.loads(l) for l in open(p)]
            for r in rs:
                r['answer'] = {'true': 'false', 'false': 'unknown', 'unknown': 'true'}[r['answer']]
            bad = os.path.join(d, 'bad.jsonl')
            open(bad, 'w').write(''.join(json.dumps(r) + '\n' for r in rs))
            self.assertEqual(verify_rungs.check_file(bad)['agree'], 0)

    def test_r1_count_baseline_is_two_thirds(self):
        """negation count alone separates true/false from unknown only partly: the lookup scores 2/3 on R1 (the +25 rule then needs ~92%)."""
        with tempfile.TemporaryDirectory() as d:
            s = ladder.build(1, d, n_train=3000, n_eval=600, n_new=30)
            b = s['files']['dev']['count_baseline']['acc']
            self.assertTrue(60 <= b <= 72, b)

    def test_rung12_word_type_and_length_cues_are_gone(self):
        """v2 rows (Addendum 2): the nonsense/common word type of the predicates and the text length carry no label beyond polarity."""
        from logic_transfer import cues
        with tempfile.TemporaryDirectory() as d:
            for rung in (1, 2):
                ladder.build(rung, d, n_train=30000, n_eval=600, n_new=30)
                res = cues.audit(rung, os.path.join(d, f'rung{rung}'), ['dev'])
                self.assertTrue(res['train_holdout']['ok'], (rung, res['train_holdout']))
                self.assertLessEqual(res['dev']['class_share_gap'], 6.0, (rung, res['dev']['class_share']))

    def test_r1_unknown_replacement_has_same_length_and_type(self):
        from logicgen import rungs
        common = cues_common()
        for r in rungs.make_rows('rung1', 'dev', 300, 5):
            body, _ = verify_rungs.split_options(r['question'] + ' (true/false/unknown)')
            ss = [x.strip() for x in verify_rungs.sentences(body)]
            f, q = verify_rungs.FACT.match(ss[0]), verify_rungs.QUERY.match(ss[1])
            if r['answer'] == 'unknown':
                if f.group(1) != q.group(1):
                    self.assertEqual(len(f.group(1)), len(q.group(1)))
                if f.group(3) != q.group(3):
                    self.assertEqual(len(f.group(3)), len(q.group(3)))
                    self.assertEqual(f.group(3) in common, q.group(3) in common)

    def test_f2_key_has_entity_counts(self):
        import random
        from logicgen import matched
        row = None
        for t in range(200):
            row = matched.candidate('train', 'logic', 1, 'true', random.Random(f'k{t}'), 'x', 208)
            if row:
                break
        self.assertIsNotNone(row)
        self.assertEqual(len(matched.triple(row)), 5)


def cues_common():
    from logicgen.lexicon import COMMON_WORDS
    return frozenset(COMMON_WORDS)


class RunSummary(unittest.TestCase):
    """dev_at carries a stopping evaluation forward only for runs that stopped on their marks (review finding)."""

    def _run(self, work, name, evals, stop):
        rd = os.path.join(work, 'rung0', name)
        os.makedirs(rd)
        open(os.path.join(rd, 'eval.jsonl'), 'w').write(''.join(json.dumps(e) + '\n' for e in evals))
        open(os.path.join(rd, 'run.json'), 'w').write('{}')
        if stop:
            open(os.path.join(rd, 'stop.json'), 'w').write(json.dumps(stop))

    def test_carry_only_for_runs_that_stopped_on_marks(self):
        from logic_transfer import lt2
        ev = lambda u, name, x, full=True: dict(update=u, name=name, n=100, correct=int(x), exact=float(x), by_level={'0': [int(x), 100]}, by_label={'true': [int(x), 100]}, full=full, eval_s=1.0)
        th = [('dev', None, 90.0), ('wording', None, 80.0)]
        with tempfile.TemporaryDirectory() as d:
            self._run(d, 's200-s1', [ev(500, 'dev', 100), ev(500, 'wording', 100)], dict(reason='marks', update=500))
            # passed once at 250, then fell back and trained on to 8000: nothing may be carried
            self._run(d, 's201-s1', [ev(250, 'dev', 95), ev(250, 'wording', 95), ev(2000, 'dev', 40), ev(2000, 'wording', 40), ev(8000, 'dev', 41), ev(8000, 'wording', 41)],
                      dict(reason='max_updates', update=8000))
            a = lt2.run_summary(d, 0, 's200', 1, th)
            b = lt2.run_summary(d, 0, 's201', 1, th)
        self.assertEqual(a['dev_at'], {'2000': 100.0, '4000': 100.0, '8000': 100.0})
        self.assertEqual(a['dev_at_carried'], ['2000', '4000', '8000'])
        self.assertTrue(a['pass'])
        self.assertEqual(b['dev_at'], {'2000': 40.0, '4000': 40.0, '8000': 41.0})
        self.assertEqual(b['dev_at_carried'], [])
        self.assertEqual(a['label_recall_last'], {'true': 100.0})


class Thresholds(unittest.TestCase):
    def test_r1_mark_floors_so_the_exact_boundary_passes(self):
        from logic_transfer import lt2
        summ = {'files': {'dev': {'count_baseline': {'acc': 66.67, 'hit': 800, 'n': 1200}}}}
        th = lt2.thresholds(1, summ)
        self.assertEqual(th[0][0], 'dev')
        self.assertLessEqual(th[0][2], 100.0 * 1100 / 1200)       # 1100/1200 = 91.6667 passes
        self.assertGreater(th[0][2], 91.6)


class ThresholdsMore(unittest.TestCase):
    def test_r1_mark_without_hit_field_is_the_same(self):
        from logic_transfer import lt2
        summ = {'files': {'dev': {'count_baseline': {'acc': 66.67, 'n': 1200}}}}
        self.assertEqual(lt2.thresholds(1, summ)[0][2], 91.66)

    def test_r2_gate_has_hard_negative_subset(self):
        from logic_transfer import lt2
        summ = {'files': {'dev': {'count_baseline': {'acc': 45.33, 'hit': 544, 'n': 1200}}}}
        th = lt2.thresholds(2, summ)
        self.assertEqual([(f, v) for f, _, v in th], [('dev', 90.0), ('hard', 80.0)])
        self.assertIn('hard', lt2.EVALS[2])

    def test_marks_string_roundtrip_through_course_parser(self):
        from logic_transfer import lt2
        summ = {'files': {'gate': {'count_baseline': {'acc': 33.3, 'hit': 400, 'n': 1200}}}}
        th = lt2.thresholds(5, summ)
        back = course.parse_marks(lt2.marks_string(th))
        self.assertEqual([(f, lv) for f, lv, _ in back], [(f, lv) for f, lv, _ in th])


class HardNegatives(unittest.TestCase):
    def _row(self, facts, query, answer):
        return {'id': 'x', 'answer': answer, 'prompt': ' '.join(facts + [query]) + ' (true/false/unknown)'}

    def test_hard_needs_entity_and_predicate_in_different_facts(self):
        from logic_transfer import hard
        self.assertTrue(hard.is_hard(self._row(['Bob is not red.', 'Ann is blue.'], 'Is Bob blue?', 'unknown')))
        self.assertFalse(hard.is_hard(self._row(['Bob is not red.', 'Ann is green.'], 'Is Bob blue?', 'unknown')))       # predicate nowhere
        self.assertFalse(hard.is_hard(self._row(['Bob is blue.', 'Ann is green.'], 'Is Bob blue?', 'true')))             # answered row
        self.assertFalse(hard.is_hard(self._row(['Bob is blue.', 'Ann is blue.'], 'Is Bob not blue?', 'false')))

    def test_make_hard_is_deterministic_subset_of_dev(self):
        import tempfile, json as _j
        from logic_transfer import hard
        with tempfile.TemporaryDirectory() as d:
            rows = [self._row(['Bob is not red.', 'Ann is blue.'], 'Is Bob blue?', 'unknown'), self._row(['Bob is blue.'], 'Is Bob blue?', 'true')]
            with open(d + '/dev.jsonl', 'w') as f:
                for r in rows:
                    f.write(_j.dumps(r) + '\n')
            self.assertEqual(hard.make_hard(d), 1)
            a = open(d + '/hard.jsonl').read()
            hard.make_hard(d)
            self.assertEqual(a, open(d + '/hard.jsonl').read())
            self.assertTrue(_j.loads(a)['id'].endswith('-hard'))


class Schedule(unittest.TestCase):
    def test_sk_slots_identical_across_arms(self):
        a = course.schedule(7, 200000, None, 64, 0.25, 300)             # control arm
        b = course.schedule(7, 200000, 70000, 64, 0.25, 300)            # logic arm
        c = course.schedule(7, 200000, 55555, 64, 0.25, 300)            # placebo arm (other pool size)
        self.assertEqual(a[0].shape, (300, 48))
        self.assertEqual(b[1].shape, (300, 16))
        self.assertTrue((a[0] == b[0]).all() and (a[0] == c[0]).all())
        self.assertTrue((a[1] != b[1]).any() or a[1].shape == b[1].shape)   # the extra stream is its own
        self.assertEqual(b[1].max() < 70000, True)

    def test_extra_stream_independent_of_sk_stream(self):
        a = course.schedule(7, 1000, None, 64, 0.25, 20)
        self.assertFalse((a[0][:, :16] == a[1]).all())                  # control rows are not just the sk rows again

    def test_determinism_and_seed(self):
        a, b = course.schedule(3, 5000, 900, 64, 0.25, 50), course.schedule(3, 5000, 900, 64, 0.25, 50)
        self.assertTrue(all((x == y).all() for x, y in zip(a, b)))
        c = course.schedule(4, 5000, 900, 64, 0.25, 50)
        self.assertFalse((a[0] == c[0]).all())

    def test_no_repeat_within_epoch(self):
        sk, ex = course.schedule(1, 100000, 70000, 64, 0.25, 4000)       # 192,000 sk draws from 200k-style pool: wraps once here
        self.assertEqual(len(set(ex.ravel().tolist())), 64000)           # 64,000 mix draws from 70,000 rows: no repeats
        self.assertEqual(course.n_mix(64, 0.25), 16)


class Jobs(unittest.TestCase):
    def test_job_list(self):
        jobs = run_lt1.build_jobs()['jobs']
        by = {}
        for j in jobs:
            by.setdefault(j['stage'], []).append(j)
        names = {j['name'] for j in jobs}
        self.assertEqual(len(names), len(jobs))
        self.assertEqual(sorted(j['name'] for j in by['course']),
                         sorted(f'course-{p}-{a}-s1' for p, a in [('s200', 'L'), ('s200', 'C'), ('s200', 'P')] + [(q, x) for q in ('s201', 's204') for x in 'LPC']))
        self.assertNotIn('far', by)                                            # no far jobs by default
        self.assertTrue(all(j['args'].get('logic_only') for j in by['score']))   # no full scoring queued
        pr = {j['name']: j['priority'] for j in by['course']}
        self.assertEqual((pr['course-s200-L-s1'], pr['course-s200-C-s1'], pr['course-s200-P-s1'], pr['course-s201-L-s1'], pr['course-s204-C-s1']), (0, 0, 1, 1, 2))
        self.assertTrue(all(j['args']['updates'] == 8000 and j['args']['save_every'] == 1000 for j in by['course']))
        self.assertEqual(len([j for j in by['score'] if j['name'].startswith('scoreL-s200-L-s1-u')]), 8)
        self.assertIn('far', {j['stage'] for j in run_lt1.build_jobs(far=True)['jobs']})
        self.assertEqual(len([j for j in run_lt1.build_jobs('gate')['jobs'] if j['stage'] == 'course']), 2)

    def test_resolve(self):
        paths = dict(run_lt1.DEFAULT_PATHS, ROOT='/r', THREADS='2')
        names = {j['name']: j for j in run_lt1.build_jobs(far=True)['jobs']}
        cmd, extra, waits = run_lt1.resolve(names['far-s201-L-s1'], paths)
        self.assertEqual((extra, waits), (['course-s201-L-s1'], []))
        self.assertIn('/r/jobs/course-s201-L-s1/out/checkpoint.pt', cmd)
        self.assertEqual(cmd[cmd.index('--steps') + 1], '0,500,1000,2000')
        cmd, extra, waits = run_lt1.resolve(names['scoreL-s204-P-s1-u3000'], paths)
        self.assertEqual((extra, waits), ([], [('course-s204-P-s1', '/r/jobs/course-s204-P-s1/out/checkpoint-3000.pt')]))
        self.assertIn('--logic-only', cmd)
        cmd, _, _ = run_lt1.resolve(names['course-s204-P-s1'], paths)
        self.assertEqual(cmd[cmd.index('--mix') + 1], '/r/rows/placebo_train.jsonl')
        self.assertEqual(cmd[cmd.index('--save-every') + 1], '1000')
        cmd, _, _ = run_lt1.resolve(names['course-s200-C-s1'], paths)
        self.assertNotIn('--mix', cmd)

    def test_scheduler(self):
        """priority order, waiting for a file a running job writes, dependency failure -> BLOCKED, DONE markers skip."""
        import sys
        def fake(job, paths):
            root = paths['ROOT']
            f = f'{root}/jobs/A/out/f.txt'
            cmds = {'A': "import time,os;time.sleep(1.5);open('%s','w').write('x');time.sleep(1.5)" % f,
                    'B': "pass", 'C': "pass", 'D': "import sys;sys.exit(3)", 'E': "pass"}
            return [sys.executable, '-c', cmds[job['name']]], [d for d in job['deps']], ([('A', f)] if job['name'] == 'B' else [])
        orig = run_lt1.resolve
        run_lt1.resolve = fake
        try:
            with tempfile.TemporaryDirectory() as d:
                doc = {'paths': {}, 'jobs': [
                    {'name': 'C', 'stage': 'x', 'args': {}, 'deps': [], 'priority': 2},
                    {'name': 'B', 'stage': 'x', 'args': {}, 'deps': [], 'priority': 0, 'light': True},     # waits for A's file
                    {'name': 'A', 'stage': 'x', 'args': {}, 'deps': [], 'priority': 1},
                    {'name': 'D', 'stage': 'x', 'args': {}, 'deps': [], 'priority': 1},
                    {'name': 'E', 'stage': 'x', 'args': {}, 'deps': ['D'], 'priority': 1}]}
                st = run_lt1.run(doc, d, workers=1, threads=1, poll=0.1)
                self.assertEqual(st, {'A': 'done', 'B': 'done', 'C': 'done', 'D': 'failed', 'E': 'blocked'})
                lines = [l for l in open(os.path.join(d, 'driver.log')) if 'started' in l]
                order = [l.split()[2].rstrip(':') for l in lines]
                self.assertEqual(order, ['A', 'B', 'D', 'C'])          # A (prio 1, first runnable), B once A wrote its file, ...
                st2 = run_lt1.run(doc, d, workers=1, threads=1, poll=0.1)    # second launch: only D retried
                self.assertEqual(st2['A'], 'done')
                self.assertEqual(len([l for l in open(os.path.join(d, 'driver.log')) if ' A: started' in l]), 1)
        finally:
            run_lt1.resolve = orig


@unittest.skipUnless(os.path.exists(PARENT), 'no parent checkpoint')
class EndToEnd(unittest.TestCase):
    """3-update courses on a 300-row sk subset + converted logic rows: determinism, equal sk rows across arms, loadable output."""

    @classmethod
    def setUpClass(cls):
        sk = os.environ.get('LT1_SK200K', os.path.join(str(run_lt1.SP), 'data/sk200k'))
        if not os.path.exists(os.path.join(sk, 'train.jsonl')):
            raise unittest.SkipTest('no sk200k build')
        cls.d = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(cls.d.name, 'data'))
        with open(os.path.join(sk, 'train.jsonl')) as f, open(os.path.join(cls.d.name, 'data/train.jsonl'), 'w') as o:
            for _ in range(300):
                o.write(f.readline())
        cls.mix = os.path.join(cls.d.name, 'mix.jsonl')
        with open(cls.mix, 'w') as o:
            for i in range(100):
                o.write(json.dumps(rows.convert_row(gen_row(i, answer=('true', 'false', 'unknown')[i % 3]))) + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.d.cleanup()

    def go(self, name, mix=None, seed=1):
        out = os.path.join(self.d.name, name)
        argv = ['--parent', PARENT, '--data', os.path.join(self.d.name, 'data'), '--updates', '3', '--warmup', '2', '--seed', str(seed),
                '--threads', '1', '--out', out, '--log-every', '1', '--slice-every', '1', '--save-every', '2']
        run = course.main(argv + (['--mix', mix] if mix else []))
        return out, run

    def test_arms(self):
        import torch
        from custom_io.models import load_model
        c1, r1 = self.go('c1')
        log = [json.loads(l) for l in open(os.path.join(c1, 'log.jsonl'))]
        self.assertTrue(log[-1]['loss_cur'] is not None and log[-1]['loss_mix'] is not None)
        c2, r2 = self.go('c2')
        l1, rl = self.go('l1', self.mix)
        self.assertEqual(r1['sk_idx_sha256'], rl['sk_idx_sha256'])        # same sk200k rows in the same order for C and L
        self.assertNotEqual(r1['ex_idx_sha256'], rl['ex_idx_sha256'])
        s1, s2 = (torch.load(os.path.join(c, 'checkpoint.pt'), weights_only=True) for c in (c1, c2))
        self.assertTrue(all(torch.equal(s1['model'][k], s2['model'][k]) for k in s1['model']))     # deterministic
        sl = torch.load(os.path.join(l1, 'checkpoint.pt'), weights_only=True)
        self.assertFalse(all(torch.equal(s1['model'][k], sl['model'][k]) for k in s1['model']))
        self.assertEqual(set(sl), {'model', 'name', 'cfg', 'chars', 'step'})
        self.assertEqual(sl['step'], 24003)
        self.assertTrue(os.path.exists(os.path.join(l1, 'checkpoint-2.pt')))
        load_model(os.path.join(l1, 'checkpoint.pt'))
        for f in ('log.jsonl', 'run.json'):
            self.assertTrue(os.path.exists(os.path.join(l1, f)))
        self.assertEqual(rl['mix_sha256'], hashlib.sha256(open(self.mix, 'rb').read()).hexdigest())


    def test_eval_and_early_stop(self):
        """--eval / --stop-marks: marks that always hold stop the run at the second periodic eval (after a full confirm); marks that never hold
        run to the budget and end with a full eval; eval.jsonl and stop.json are written; the saved step is the stopped one."""
        import torch
        ev = os.path.join(self.d.name, 'ev.jsonl')
        with open(ev, 'w') as o:
            for i in range(12):
                g = gen_row(i, split='dev', answer=('true', 'false', 'unknown')[i % 3]); g['id'] = g['id'].replace('train', 'dev')
                o.write(json.dumps(rows.convert_row(g, options=True)) + '\n')
        base = ['--parent', PARENT, '--data', os.path.join(self.d.name, 'data'), '--updates', '8', '--warmup', '2', '--seed', '1', '--threads', '1',
                '--log-every', '2', '--slice-every', '0', '--eval', f'dev={ev}', '--eval-every', '2', '--eval-n', '6']
        out = os.path.join(self.d.name, 'stop')
        run = course.main(base + ['--mix', self.mix, '--out', out, '--stop-marks', 'dev>=0'])
        st = json.load(open(os.path.join(out, 'stop.json')))
        self.assertEqual((st['reason'], st['update']), ('marks', 4))
        self.assertEqual(run['updates_done'], 4)
        self.assertEqual(torch.load(os.path.join(out, 'checkpoint.pt'), weights_only=True)['step'], 24004)
        el = [json.loads(l) for l in open(os.path.join(out, 'eval.jsonl'))]
        self.assertEqual([(e['update'], e['n'], e['full']) for e in el], [(2, 6, False), (4, 6, False), (4, 12, True)])
        self.assertIn('dev', st['full_eval'])
        out2 = os.path.join(self.d.name, 'nostop')
        run2 = course.main(base + ['--mix', self.mix, '--out', out2, '--stop-marks', 'dev>=101'])
        st2 = json.load(open(os.path.join(out2, 'stop.json')))
        self.assertEqual((st2['reason'], st2['update'], st2['marks_hold']), ('max_updates', 8, False))
        self.assertEqual(run2['updates_done'], 8)
        el2 = [json.loads(l) for l in open(os.path.join(out2, 'eval.jsonl'))]
        self.assertEqual([(e['update'], e['full']) for e in el2], [(2, False), (4, False), (6, False), (8, True)])
        self.assertEqual(st2['full_eval']['dev']['n'], 12)


if __name__ == '__main__':
    unittest.main(module='logic_transfer.tests', verbosity=2)
