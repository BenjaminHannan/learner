"""Client for remote gym workers, used to add machines such as Brick's PC."""
import asyncio

from . import protocol


class RemoteEnv:
    """Same async interface as BrowserEnv, but running on another machine."""

    def __init__(self, host, port, max_steps=20):
        self.max_steps = max_steps
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.episode = None
        self.t = 0
        self.state = None
        self.done = True
        self.text_chars_value = 0

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port, limit=protocol.MAX_MESSAGE_BYTES)

    async def _request(self, message):
        self.writer.write(protocol.encode_message(message))
        await self.writer.drain()
        reply = await protocol.read_message(self.reader)
        if reply is None:
            raise ConnectionError('remote gym worker closed the connection')
        if not reply.get('ok'):
            raise RuntimeError('remote gym error: %s' % (reply.get('error'),))
        return reply

    async def reset(self, kind, seed):
        reply = await self._request({'cmd': 'reset', 'kind': kind, 'seed': seed, 'max_steps': self.max_steps})
        self.episode = {'kind': kind, 'seed': seed,
                        'instruction': reply.get('instruction', '')}
        self.t = 0
        self.done = False
        self.state = reply.get('state')
        return protocol.decode_obs(reply['obs'])

    async def step(self, action):
        reply = await self._request({'cmd': 'step', 'action': action})
        self.t += 1
        self.done = bool(reply.get('done'))
        self.state = reply.get('state')
        self.text_chars_value = int(reply.get('textChars', 0))
        return (protocol.decode_obs(reply['obs']), float(reply['reward']),
                self.done, reply.get('info', {}))

    def text_chars(self):
        return self.text_chars_value

    async def close(self):
        if self.writer is not None:
            try:
                self.writer.write(protocol.encode_message({'cmd': 'close'}))
                await self.writer.drain()
            except (ConnectionError, OSError):
                pass
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            self.writer = None
            self.reader = None
