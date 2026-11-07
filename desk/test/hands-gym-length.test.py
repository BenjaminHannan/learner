"""Optional brief-15 variants; the frozen default task stream must not change."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/hands-gym'))
from hands_gym import tasks
from hands_gym.length_check import CELLS, summarize, task_seed, unmeasurable_baseline, verdict


class LengthTests(unittest.TestCase):
    def test_default_stream_matches_brief7_exactly(self):
        rows = [tasks.build(kind, seed, start_k=start_k)
                for kind in tasks.TASK_TYPES for seed in range(100)
                for start_k in (None, 1, 3, 100)]
        observed = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        self.assertEqual(observed, 'fb597dcfaac774bde3b9cffe7e7fd78cea6363b76b70a2d4da428910661d4eac')
        self.assertEqual(len(tasks.TASK_TYPES), 9)

    def test_variants_are_opt_in_deterministic_and_exact_length(self):
        for variant, length in (('letters_6', 6), ('letters_10', 10)):
            self.assertEqual(len(tasks.LENGTH_WORDS[variant]), 8)
            for word in tasks.LENGTH_WORDS[variant]:
                self.assertEqual(len(word), length)
                self.assertTrue(word.isascii() and word.islower() and word.isalpha())
            for seed in range(100):
                episode = tasks.build('type_text', seed, variant=variant)
                self.assertEqual(episode, tasks.build('type_text', seed, variant=variant))
                self.assertEqual(len(episode['spec']['target']), length)
                self.assertNotIn('value=', episode['html'])
        for kind in tasks.TASK_TYPES:
            self.assertEqual(tasks.build(kind, 42), tasks.build(kind, 42, variant=None))

    def test_forms_require_all_five_values_and_submit(self):
        episode = tasks.build('form_fill', 42, variant='fields_5')
        spec = episode['spec']
        targets = dict(tasks.form_targets(spec))
        self.assertEqual(len(targets), 5)
        for field in targets:
            self.assertIn("id='%s'" % field, episode['html'])
        correct = {**targets, 'submitted': True}
        self.assertTrue(tasks.check('form_fill', spec, correct, {}, 0)[0])
        self.assertFalse(tasks.check('form_fill', spec, targets, {}, 0)[0])
        for field in targets:
            wrong = {**correct, field: ''}
            self.assertFalse(tasks.check('form_fill', spec, wrong, {}, 0)[0])
        reward = tasks.check('form_fill', spec, targets, {}, 0)[1]
        self.assertAlmostEqual(reward, 0.12 * sum(map(len, targets.values())))

    def test_invalid_combinations_fail_closed(self):
        for kind, variant in (('type_text', 'fields_5'), ('form_fill', 'letters_6'),
                              ('click_button', 'letters_10'), ('type_text', ''),
                              ('type_text', 6), ('type_text', True)):
            with self.assertRaises(ValueError):
                tasks.build(kind, 42, variant=variant)
        with self.assertRaises(ValueError):
            tasks.build('type_text', 42, variant='letters_6', start_k=1)

    def test_fixed_verdict_including_unmeasurable_baseline(self):
        def cell(successes, episodes=100):
            return {'successes': successes, 'episodes': episodes}
        self.assertEqual(verdict(cell(50), cell(40)), 'NO WALL')
        self.assertEqual(verdict(cell(50), cell(25)), 'WALL')
        self.assertEqual(verdict(cell(50), cell(26)), 'PARTIAL')
        self.assertEqual(verdict(cell(0), cell(0)), 'UNMEASURABLE')
        self.assertEqual(verdict(cell(9), cell(100)), 'UNMEASURABLE')
        self.assertEqual(verdict(cell(10), cell(8)), 'NO WALL')
        self.assertEqual(verdict(cell(10), cell(5)), 'WALL')
        self.assertEqual(verdict(cell(50, 8), cell(40)), 'UNMEASURABLE')

    def test_held_out_seeds_and_raised_horizons(self):
        seeds = {task_seed(seed, episode) for seed in (11, 22, 33) for episode in range(100)}
        self.assertEqual(len(seeds), 300)
        self.assertGreater(min(seeds), 80_000_000)
        self.assertEqual([cell[3] for cell in CELLS], [20, 40, 60, 20, 60])

    def test_unmeasurable_baseline_stops_without_zero_filling_missing_cells(self):
        row = {'seed': 11, 'cell': 'letters_3', 'episodes': 100, 'successes': 0}
        self.assertTrue(unmeasurable_baseline(row))
        self.assertFalse(unmeasurable_baseline({**row, 'episodes': 8}))
        self.assertFalse(unmeasurable_baseline({**row, 'cell': 'letters_10'}))
        self.assertFalse(unmeasurable_baseline({**row, 'successes': 10}))
        self.assertEqual(summarize([row]), [
            {'seed': 11, 'typing': 'UNMEASURABLE', 'forms': 'UNMEASURED'},
            {'seed': 22, 'typing': 'UNMEASURED', 'forms': 'UNMEASURED'},
            {'seed': 33, 'typing': 'UNMEASURED', 'forms': 'UNMEASURED'}])


@unittest.skipUnless(os.environ.get('HANDS_GYM_BROWSER_TESTS') == '1',
                     'set HANDS_GYM_BROWSER_TESTS=1 for Chromium')
class BrowserLengthTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_lengths_solve_with_only_native_actions(self):
        from playwright.async_api import async_playwright
        from hands_gym.browser_env import BrowserEnv

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=['--disable-gpu'])
            environment = BrowserEnv(browser, max_steps=60)
            await environment.start()
            try:
                for _, kind, variant, horizon in CELLS:
                    for seed in (11, 22, 33):
                        environment.max_steps = horizon
                        await environment.reset(kind, task_seed(seed, 0), variant=variant)
                        self.assertFalse(tasks.check(kind, environment.episode['spec'],
                                                     environment.state, environment.state, 0)[0])
                        self.assertEqual(environment.text_chars(), 0)
                        targets = (('text', environment.episode['spec']['target']),) if kind == 'type_text' else tasks.form_targets(environment.episode['spec'])
                        for field, target in targets:
                            bounds = await environment.page.locator('#' + field).bounding_box()
                            self.assertGreaterEqual(bounds['x'], 0)
                            self.assertGreaterEqual(bounds['y'], 0)
                            self.assertLessEqual(bounds['x'] + bounds['width'], 640)
                            self.assertLessEqual(bounds['y'] + bounds['height'], 360)
                            await environment.step({'kind': 'click',
                                'x': (bounds['x'] + bounds['width'] / 2) / 640,
                                'y': (bounds['y'] + bounds['height'] / 2) / 360})
                            for character in target:
                                await environment.step({'kind': 'key', 'keyCode': ord(character)})
                        self.assertEqual(environment.text_chars(), sum(len(target) for _, target in targets))
                        bounds = await environment.page.locator('#submit').bounding_box()
                        result = await environment.step({'kind': 'click',
                            'x': (bounds['x'] + bounds['width'] / 2) / 640,
                            'y': (bounds['y'] + bounds['height'] / 2) / 360})
                        self.assertTrue(result[3]['success'], (kind, variant, seed))
                        self.assertLessEqual(environment.t, horizon)
            finally:
                await environment.close()
                await browser.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
