"""Wire protocol for remote HANDS gym workers (e.g. Brick's PC later).

One TCP connection carries one environment. Messages are single JSON lines:

    -> {"cmd": "reset", "kind": "click_button", "seed": 123}
    <- {"ok": true, "instruction": "...", "obs": {...}}
    -> {"cmd": "step", "action": {...}}
    <- {"ok": true, "obs": {...}, "reward": 0.1, "done": false, "info": {...}}

Observations are raw uint8 RGB frames, base64 encoded. The protocol is
deliberately transport-only so the same trainer can mix local Playwright
workers and remote workers.
"""
import base64
import json

MAX_MESSAGE_BYTES = 2 * 1024 * 1024



def encode_obs(obs):
    import numpy as np
    return {
        'overview': base64.b64encode(np.ascontiguousarray(obs['overview']).tobytes()).decode(),
        'detail': base64.b64encode(np.ascontiguousarray(obs['detail']).tobytes()).decode(),
        'overviewShape': list(np.asarray(obs['overview']).shape),
        'detailShape': list(np.asarray(obs['detail']).shape),
    }


def decode_obs(payload):
    import numpy as np
    overview = np.frombuffer(base64.b64decode(payload['overview']), dtype=np.uint8)
    detail = np.frombuffer(base64.b64decode(payload['detail']), dtype=np.uint8)
    return {
        'overview': overview.reshape(tuple(payload['overviewShape'])).copy(),
        'detail': detail.reshape(tuple(payload['detailShape'])).copy(),
    }


def encode_message(obj):
    return (json.dumps(obj, separators=(',', ':')) + '\n').encode('utf-8')


async def read_message(reader):
    line = await reader.readline()
    if not line:
        return None
    if len(line) > MAX_MESSAGE_BYTES:
        raise ProtocolError('message too large')
    return json.loads(line.decode('utf-8'))


class ProtocolError(RuntimeError):
    pass


def parse_request(message):
    if not isinstance(message, dict):
        raise ProtocolError('message must be an object')
    cmd = message.get('cmd')
    if cmd == 'reset':
        if not isinstance(message.get('kind'), str):
            raise ProtocolError('reset requires kind')
        seed = message.get('seed')
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ProtocolError('reset requires integer seed')
        max_steps = message.get('max_steps', 20)
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise ProtocolError('invalid max_steps')
        return {'cmd': 'reset', 'kind': message['kind'], 'seed': seed,
                'max_steps': max_steps}
    if cmd == 'step':
        action = message.get('action')
        if not isinstance(action, dict) or not isinstance(action.get('kind'), str):
            raise ProtocolError('step requires action object')
        return {'cmd': 'step', 'action': action}
    if cmd == 'state':
        return {'cmd': 'state'}
    if cmd == 'close':
        return {'cmd': 'close'}
    raise ProtocolError('unknown cmd: %r' % (cmd,))
