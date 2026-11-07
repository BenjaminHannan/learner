"""Async server exposing local Playwright gym environments over TCP.

Run this on any machine with Playwright (BensPC now, Brick's PC later) and
connect ``hands_gym.remote.RemoteEnv`` clients to it from the trainer.
"""
import argparse
import asyncio

from . import protocol


async def handle_client(reader, writer, env_factory):
    env = None
    try:
        env = await env_factory()
        while True:
            message = await protocol.read_message(reader)
            if message is None:
                break
            try:
                request = protocol.parse_request(message)
            except protocol.ProtocolError as error:
                writer.write(protocol.encode_message({'ok': False, 'error': str(error)}))
                await writer.drain()
                continue
            if request['cmd'] == 'reset':
                env.max_steps = request['max_steps']
                obs = await env.reset(request['kind'], request['seed'])
                reply = {
                    'ok': True,
                    'instruction': env.episode['instruction'],
                    'state': env.state,
                    'obs': protocol.encode_obs(obs),
                }
            elif request['cmd'] == 'step':
                obs, reward, done, info = await env.step(request['action'])
                reply = {
                    'ok': True,
                    'obs': protocol.encode_obs(obs),
                    'reward': reward,
                    'done': done,
                    'info': info,
                    'state': env.state,
                    'textChars': env.text_chars(),
                }
            elif request['cmd'] == 'state':
                reply = {'ok': True, 'state': env.state, 't': env.t, 'done': env.done,
                         'textChars': env.text_chars()}
            else:
                reply = {'ok': True}
            writer.write(protocol.encode_message(reply))
            await writer.drain()
            if request['cmd'] == 'close':
                break
    except Exception as error:  # keep the client informed, then drop the socket
        try:
            writer.write(protocol.encode_message({'ok': False, 'error': repr(error)}))
            await writer.drain()
        except (ConnectionError, OSError):
            pass
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception:
                pass
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def serve(host, port, env_factory, ready_event=None):
    async def on_client(reader, writer):
        await handle_client(reader, writer, env_factory)

    server = await asyncio.start_server(on_client, host, port, limit=protocol.MAX_MESSAGE_BYTES)
    if ready_event is not None:
        ready_event.set()
    async with server:
        await server.serve_forever()


async def _main_async(args):
    from playwright.async_api import async_playwright
    from .browser_env import BrowserEnv

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)

    async def factory():
        env = BrowserEnv(browser)
        await env.start()
        return env

    try:
        await serve(args.host, args.port, factory)
    finally:
        await browser.close()
        await playwright.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(_main_async(args))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
