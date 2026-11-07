"""A real-browser environment for the HANDS practice gym.

Every task renders as a local HTML page in headless Chromium and the policy
acts through real Playwright mouse/keyboard input at pixel coordinates. The
observation matches the HANDS pipeline: a 320x180 overview plus a 192x192
detail crop around the last click (the real pipeline crops around the cursor).
"""
import io
import math

import numpy as np
from PIL import Image

from . import tasks
from .actions import key_name

OVERVIEW_WIDTH = 320
OVERVIEW_HEIGHT = 180
DETAIL_SIZE = 192


class BrowserEnv:
    def __init__(self, browser, width=tasks.VIEW_WIDTH, height=tasks.VIEW_HEIGHT, max_steps=tasks.MAX_STEPS):
        self.max_steps = max_steps
        self.browser = browser
        self.width = width
        self.height = height
        self.context = None
        self.page = None
        self.episode = None
        self.t = 0
        self.state = None
        self.prev_state = None
        self.focus = (width / 2.0, height / 2.0)
        self.done = True

    async def start(self):
        self.context = await self.browser.new_context(
            viewport={'width': self.width, 'height': self.height},
            device_scale_factor=1,
        )
        self.page = await self.context.new_page()

    async def reset(self, kind, seed):
        episode = tasks.build(kind, seed)
        episode['max_steps'] = self.max_steps
        await self.page.set_content(episode['html'])
        self.episode = episode
        self.t = 0
        self.focus = (self.width / 2.0, self.height / 2.0)
        self.prev_state = None
        self.state = await self.page.evaluate('window.__gym.state()')
        self.done = False
        return await self.observe()

    def text_chars(self):
        state = self.state or {}
        if self.episode is None:
            return 0
        kind = self.episode['kind']
        if kind == tasks.KIND_TYPE_TEXT:
            return len(state.get('value', ''))
        if kind == tasks.KIND_FORM_FILL:
            return len(state.get('name', '')) + len(state.get('city', ''))
        return 0

    async def step(self, action):
        if self.done:
            raise RuntimeError('reset required before step')
        self.prev_state = self.state
        await self._dispatch(action)
        self.state = await self.page.evaluate('window.__gym.state()')
        success, reward, done = tasks.check(
            self.episode['kind'],
            self.episode['spec'],
            self.state,
            self.prev_state,
            self.t,
            self.episode['max_steps'],
        )
        self.t += 1
        self.done = done
        observation = await self.observe()
        info = {'success': success, 'kind': self.episode['kind'],
                'seed': self.episode['seed']}
        return observation, reward, done, info

    async def observe(self):
        png = await self.page.screenshot(type='png')
        image = Image.open(io.BytesIO(png)).convert('RGB')
        overview = np.asarray(image.resize((OVERVIEW_WIDTH, OVERVIEW_HEIGHT),
                                           Image.BILINEAR), dtype=np.uint8)
        half = DETAIL_SIZE // 2
        fx = int(round(self.focus[0]))
        fy = int(round(self.focus[1]))
        x0 = min(max(fx - half, 0), self.width - DETAIL_SIZE)
        y0 = min(max(fy - half, 0), self.height - DETAIL_SIZE)
        detail = image.crop((x0, y0, x0 + DETAIL_SIZE, y0 + DETAIL_SIZE))
        detail = np.asarray(detail.resize((DETAIL_SIZE, DETAIL_SIZE), Image.BILINEAR),
                            dtype=np.uint8)
        return {'overview': overview, 'detail': detail}

    async def _dispatch(self, action):
        kind = action['kind']
        if kind in ('click', 'drag'):
            fields = ('x', 'y', 'endX', 'endY') if kind == 'drag' else ('x', 'y')
            if any(type(action.get(k)) not in (int, float) or not math.isfinite(action[k]) for k in fields):
                raise ValueError('finite coordinates required')
        x = self._px(action.get('x', 0.5))
        y = self._py(action.get('y', 0.5))
        if kind == 'click':
            self.focus = (x, y)
            await self.page.mouse.click(x, y)
        elif kind == 'drag':
            ex = self._px(action.get('endX', 0.5))
            ey = self._py(action.get('endY', 0.5))
            await self.page.mouse.move(x, y)
            await self.page.mouse.down()
            await self.page.mouse.move(ex, ey, steps=6)
            await self.page.mouse.up()
            self.focus = (ex, ey)
        elif kind == 'key':
            name = key_name(action.get('keyCode', 0))
            if name is not None:
                await self.page.keyboard.press(name)
        elif kind == 'scroll':
            await self.page.mouse.wheel(action.get('dx', 0.0) * self.width,
                                        action.get('dy', 0.0) * self.height)
        else:
            raise ValueError('unknown action kind: %r' % (kind,))

    def _px(self, value):
        return min(max(float(value) * self.width, 0.0), self.width - 1.0)

    def _py(self, value):
        return min(max(float(value) * self.height, 0.0), self.height - 1.0)

    async def close(self):
        if self.context is not None:
            await self.context.close()
            self.context = None
            self.page = None
