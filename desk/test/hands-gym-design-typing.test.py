"""Brief 15b: plain-code character identity, learned emission and navigation."""
import asyncio
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/hands-gym'))
from hands_gym import tasks
from hands_gym.browser_env import BrowserEnv


class BatchTests(unittest.TestCase):
    def test_only_explicit_own_state_enters_batch(self):
        import numpy as np
        import torch
        from hands_gym.model import batch
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        default = {'overview': image, 'detail': image}
        own = np.zeros(12, dtype=np.float32)
        own[2:4] = [3 / 20, 10 / 20]
        flagged = {**default, 'own': own}
        inputs = batch([default, flagged], ['Type cat', 'Type cat'], 'cpu')
        self.assertEqual(inputs[3].dtype, torch.float32)
        self.assertTrue(torch.equal(inputs[3][0], torch.zeros(12)))
        self.assertTrue(torch.equal(inputs[3][1], torch.from_numpy(own)))

    def test_flag_defaults_off(self):
        self.assertFalse(BrowserEnv(None).design_typing)


@unittest.skipUnless(os.environ.get('HANDS_GYM_BROWSER_TESTS') == '1',
                     'set HANDS_GYM_BROWSER_TESTS=1 for Chromium')
class BrowserTypingTests(unittest.TestCase):
    def run_browser(self, check):
        from playwright.async_api import async_playwright
        async def run():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, args=['--disable-gpu'])
                try:
                    await check(browser)
                finally:
                    await browser.close()
        asyncio.run(run())

    def test_default_off_exact_observations_states_and_actions(self):
        async def check(browser):
            import numpy as np
            default = BrowserEnv(browser)
            explicit = BrowserEnv(browser, design_typing=False)
            await asyncio.gather(default.start(), explicit.start())
            try:
                for kind in tasks.TASK_TYPES:
                    observations = await asyncio.gather(default.reset(kind, 42), explicit.reset(kind, 42))
                    self.assertEqual(set(observations[0]), {'overview', 'detail'})
                    for key in observations[0]:
                        self.assertTrue(np.array_equal(observations[0][key], observations[1][key]))
                    self.assertEqual(default.episode, explicit.episode)
                    for action in ({'kind': 'key', 'keyCode': ord('z')},
                                   {'kind': 'click', 'x': 0.5, 'y': 0.4}):
                        replies = await asyncio.gather(default.step(action), explicit.step(action))
                        self.assertEqual(replies[0][1:], replies[1][1:])
                        self.assertEqual(default.state, explicit.state)
                        for key in replies[0][0]:
                            self.assertTrue(np.array_equal(replies[0][0][key], replies[1][0][key]))
                await default.reset('type_text', 42)
                await default.page.focus('#text')
                await default.step({'kind': 'key', 'keyCode': ord('z')})
                self.assertEqual(default.state['value'], 'z')
            finally:
                await asyncio.gather(default.close(), explicit.close())
        self.run_browser(check)

    def test_gate_uses_reference_index_not_sampled_letter_or_correct_prefix(self):
        async def check(browser):
            environment = BrowserEnv(browser, design_typing=True)
            await environment.start()
            try:
                observation = await environment.reset('type_text', 42, variant='letters_10')
                self.assertEqual(environment.typing['character'], environment.episode['spec']['target'][0])
                self.assertAlmostEqual(float(observation['own'][3]), 10 / 20)
                await environment.step({'kind': 'key', 'keyCode': ord('z')})
                self.assertEqual(environment.state['value'], '')
                await environment.page.focus('#text')
                observation = await environment.observe()
                target = environment.episode['spec']['target']
                self.assertAlmostEqual(float(observation['own'][3]), 10 / 20)
                for index in range(len(target)):
                    observation, _, _, _ = await environment.step({'kind': 'key', 'keyCode': ord('z')})
                    self.assertEqual(environment.state['value'], target[:index + 1])
                    self.assertAlmostEqual(float(observation['own'][2]), (index + 1) / 20)
                await environment.step({'kind': 'key', 'keyCode': ord('x')})
                self.assertEqual(environment.state['value'], target)
                await environment.step({'kind': 'key', 'keyCode': 129})
                self.assertEqual(environment.state['value'], target[:-1])
                await environment.step({'kind': 'key', 'keyCode': 32})
                self.assertEqual(environment.state['value'], target)
                await environment.page.fill('#text', 'xx')
                environment.state = await environment.page.evaluate('window.__gym.state()')
                await environment.observe()
                await environment.step({'kind': 'key', 'keyCode': ord('z')})
                self.assertEqual(environment.state['value'], 'xx' + target[2])
                self.assertFalse(environment.state['submitted'])
            finally:
                await environment.close()
        self.run_browser(check)

    def test_all_length_variants_solve_with_gates_and_explicit_navigation(self):
        async def check(browser):
            environment = BrowserEnv(browser, design_typing=True, max_steps=60)
            await environment.start()
            try:
                for kind, variant in (('type_text', None), ('type_text', 'letters_6'),
                                      ('type_text', 'letters_10'), ('form_fill', None),
                                      ('form_fill', 'fields_5')):
                    await environment.reset(kind, 42, variant=variant)
                    targets = ([('text', environment.episode['spec']['target'])]
                               if kind == 'type_text' else tasks.form_targets(environment.episode['spec']))
                    for field, target in targets:
                        bounds = await environment.page.locator('#' + field).bounding_box()
                        await environment.step({'kind': 'click',
                            'x': (bounds['x'] + bounds['width'] / 2) / environment.width,
                            'y': (bounds['y'] + bounds['height'] / 2) / environment.height})
                        for character in target:
                            await environment.step({'kind': 'key', 'keyCode': ord('z')})
                        self.assertFalse(environment.state['submitted'])
                        self.assertEqual(environment.typing['character'], '')
                    bounds = await environment.page.locator('#submit').bounding_box()
                    _, _, done, info = await environment.step({'kind': 'click',
                        'x': (bounds['x'] + bounds['width'] / 2) / environment.width,
                        'y': (bounds['y'] + bounds['height'] / 2) / environment.height})
                    self.assertTrue(done)
                    self.assertTrue(info['success'])
            finally:
                await environment.close()
        self.run_browser(check)

    def test_tab_and_backspace_stay_learned_no_automatic_field_advance(self):
        async def check(browser):
            environment = BrowserEnv(browser, design_typing=True)
            await environment.start()
            try:
                await environment.reset('form_fill', 42)
                await environment.page.focus('#name')
                await environment.observe()
                for character in environment.episode['spec']['name']:
                    await environment.step({'kind': 'key', 'keyCode': ord('z')})
                await environment.step({'kind': 'key', 'keyCode': ord('z')})
                self.assertEqual(environment.state['city'], '')
                await environment.step({'kind': 'key', 'keyCode': 130})
                observation, _, _, _ = await environment.step({'kind': 'key', 'keyCode': ord('z')})
                self.assertEqual(environment.state['city'], environment.episode['spec']['city'][0])
                self.assertAlmostEqual(float(observation['own'][2]), 1 / 20)
                await environment.reset('click_button', 42)
                self.assertIsNone(environment.typing)
                self.assertNotIn('own', await environment.observe())
            finally:
                await environment.close()
        self.run_browser(check)


if __name__ == '__main__':
    unittest.main()
