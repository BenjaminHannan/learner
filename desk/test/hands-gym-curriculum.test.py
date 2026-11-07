"""Reverse-start task and stage checks, with optional real Chromium input."""
import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/hands-gym'))
from hands_gym import tasks
from hands_gym.curriculum import ReverseCurriculum


class ReverseStartTests(unittest.TestCase):
    def test_default_and_large_k_are_normal_starts(self):
        for kind in tasks.TASK_TYPES:
            for seed in (7, 42, 99):
                normal = tasks.build(kind, seed)
                self.assertEqual(normal, tasks.build(kind, seed, start_k=None))
                self.assertEqual(normal, tasks.build(kind, seed, start_k=100))
                if kind not in tasks.MULTI_STEP_TYPES:
                    self.assertEqual(normal, tasks.build(kind, seed, start_k=1))
                else:
                    total = tasks.progress_units(kind, normal['spec'])
                    self.assertEqual(normal, tasks.build(kind, seed, start_k=total))
                    self.assertLessEqual(total, tasks.maximum_progress_units(kind))

    def test_reverse_starts_change_only_initial_state(self):
        for kind in tasks.MULTI_STEP_TYPES:
            normal = tasks.build(kind, 42)
            reverse = tasks.build(kind, 42, start_k=1)
            self.assertNotEqual(normal['html'], reverse['html'])
            self.assertEqual(reverse, tasks.build(kind, 42, start_k=1))
            for field in ('kind', 'seed', 'instruction', 'spec', 'max_steps'):
                self.assertEqual(normal[field], reverse[field])
        for value in (0, -1, True, 1.5, '1'):
            with self.assertRaises(ValueError):
                tasks.build('dropdown', 42, start_k=value)

    def test_strict_threshold_per_family_and_no_stale_evidence(self):
        curriculum = ReverseCurriculum()
        for episode in range(20):
            curriculum.record('type_text', 1, episode < 14)
        self.assertEqual(curriculum.for_kind('type_text'), 1)
        for episode in range(19):
            curriculum.record('type_text', 1, episode < 15)
        self.assertEqual(curriculum.for_kind('type_text'), 1)
        curriculum.record('type_text', 1, False)
        self.assertEqual(curriculum.for_kind('type_text'), 2)
        self.assertEqual(curriculum.for_kind('dropdown'), 1)
        self.assertIsNone(curriculum.for_kind('close_popup'))
        curriculum.record('type_text', 1, True)
        curriculum.record('close_popup', None, True)
        self.assertEqual(curriculum.pending['type_text'], [])
        self.assertEqual([row['promoted'] for row in curriculum.history], [False, True])

    def test_curriculum_checkpoint_preserves_pending_evidence_and_caps(self):
        original = ReverseCurriculum()
        for _ in range(13):
            original.record('dropdown', 1, True)
        restored = ReverseCurriculum()
        restored.load_state_dict(original.state_dict())
        for curriculum in (original, restored):
            for _ in range(7):
                curriculum.record('dropdown', 1, True)
            for _ in range(100):
                curriculum.record('dropdown', 2, True)
        self.assertEqual(original.state_dict(), restored.state_dict())
        self.assertEqual(restored.for_kind('dropdown'), 2)
        self.assertEqual(len(restored.history), 1)
        for start_k in (0, -1, True):
            with self.assertRaises(ValueError):
                ReverseCurriculum(start_k=start_k)

    def test_fixed_verdict_requires_three_pairs_and_single_step_safety(self):
        import brief7

        with tempfile.TemporaryDirectory(prefix='hands-gym-verdict-') as temporary:
            root = Path(temporary)
            def save_result(arm, seed, multi_rate, single_rate):
                directory = root / arm / ('seed-' + str(seed))
                directory.mkdir(parents=True, exist_ok=True)
                rates = {kind: {'rate': multi_rate if kind in tasks.MULTI_STEP_TYPES else single_rate}
                         for kind in tasks.TASK_TYPES}
                (directory / 'result.json').write_text(json.dumps({'final': {'per_task': rates}}))

            with mock.patch.object(brief7, 'RUN', root), mock.patch.object(brief7, 'ROOT', root):
                save_result('control', 11, 0.0, 0.5)
                brief7.summarize()
                self.assertIn('INCOMPLETE', json.loads((root / 'summary.json').read_text())['verdict'])
                for seed in (11, 22, 33):
                    save_result('control', seed, 0.0, 0.5)
                    save_result('reverse', seed, 0.1875 if seed != 33 else 0.0, 0.5)
                brief7.summarize()
                self.assertEqual(json.loads((root / 'summary.json').read_text())['verdict'], 'PASS')
                save_result('reverse', 22, 0.1875, 0.4375)
                brief7.summarize()
                self.assertEqual(json.loads((root / 'summary.json').read_text())['verdict'], 'FAIL')
                save_result('reverse', 11, 0.0, 0.5)
                save_result('reverse', 22, 0.0, 0.5)
                brief7.summarize()
                self.assertEqual(json.loads((root / 'summary.json').read_text())['verdict'], 'PROVES IT WRONG')


@unittest.skipUnless(os.environ.get('HANDS_GYM_BROWSER_TESTS') == '1',
                     'set HANDS_GYM_BROWSER_TESTS=1 for Chromium')
class ReverseBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_reverse_prefixes_are_unsolved_and_solvable(self):
        from playwright.async_api import async_playwright
        from hands_gym.browser_env import BrowserEnv

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=['--disable-gpu'])
            environment = BrowserEnv(browser, max_steps=20)
            await environment.start()
            cases = 0
            try:
                async def click(selector):
                    bounds = await environment.page.locator(selector).bounding_box()
                    return await environment.step({'kind': 'click',
                        'x': (bounds['x'] + bounds['width'] / 2) / 640,
                        'y': (bounds['y'] + bounds['height'] / 2) / 360})

                for kind in tasks.MULTI_STEP_TYPES:
                    normal = tasks.build(kind, 42)
                    total = tasks.progress_units(kind, normal['spec'])
                    for start_k in range(1, total + 2):
                        await environment.reset(kind, 42, start_k=start_k)
                        spec = environment.episode['spec']
                        self.assertFalse(tasks.check(kind, spec, environment.state,
                                                      environment.state, 0)[0])
                        steps = []
                        if kind in ('type_text', 'form_fill'):
                            fields = [('text', spec['target'])] if kind == 'type_text' else [
                                ('name', spec['name']), ('city', spec['city'])]
                            for field, value in fields:
                                steps.append(('click', '#' + field))
                                steps.extend(('key', ord(character)) for character in value)
                            steps.append(('key', 128) if kind == 'type_text' else ('click', '#submit'))
                        elif kind == 'dropdown':
                            steps = [('click', '#select'),
                                     ('click', '[data-value="' + spec['target'] + '"]')]
                        elif kind == 'menu_select':
                            steps = [('click', '#menubtn'),
                                     ('click', '[data-value="' + spec['target'] + '"]')]
                        if steps:
                            for action, value in steps[max(0, total - start_k):]:
                                if action == 'click':
                                    result = await click(value)
                                else:
                                    result = await environment.step({'kind': 'key', 'keyCode': value})
                        else:
                            initial = environment.state['value']
                            self.assertFalse(environment.state['dragged'])
                            self.assertEqual(abs(initial - spec['target']),
                                             min(abs(spec['start'] - spec['target']), start_k * 10))
                            bounds = await environment.page.locator('#slider').bounding_box()
                            result = await environment.step({'kind': 'drag',
                                'x': (bounds['x'] + 8 + (bounds['width'] - 16) * initial / 100) / 640,
                                'y': (bounds['y'] + bounds['height'] / 2) / 360,
                                'endX': (bounds['x'] + 8 + (bounds['width'] - 16) * spec['target'] / 100) / 640,
                                'endY': (bounds['y'] + bounds['height'] / 2) / 360})
                        self.assertTrue(result[3]['success'], (kind, start_k, environment.state))
                        cases += 1
                print('REVERSE CHROMIUM: %d unsolved prefixes completed with native suffix inputs' % cases,
                      flush=True)
            finally:
                await environment.close()
                await browser.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
