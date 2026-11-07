"""Real 1.8.9 pixels/actions adapter; server truth is an isolated referee."""
import asyncio
import hashlib
import json
import math
from pathlib import Path
import socket
import struct
import threading
import time

import numpy as np
from PIL import Image

from .bedwars_tools import BRAIN_PORT, NAMES, ROOT


DXY = (-200, -100, -50, -20, -8, 0, 8, 20, 50, 100, 200)
KEY_BITS = {ord('w'): 0, ord('a'): 1, ord('s'): 2, ord('d'): 3,
            32: 4, ord('c'): 5, ord('r'): 6, ord('f'): 7, ord('g'): 8}
GOALS = ('reach_generator', 'collect_4_iron', 'survive_10_seconds')
DEFAULT_INSTRUCTION = 'Walk backwards into the iron generator. Collect four iron, then stay safe.'


def exact(connection, length):
    result = bytearray()
    while len(result) < length:
        chunk = connection.recv(length - len(result))
        if not chunk:
            raise ConnectionError('Minecraft bridge closed')
        result.extend(chunk)
    return bytes(result)


def read_message(connection):
    length = struct.unpack('<I', exact(connection, 4))[0]
    if not 1 <= length <= 2 * 1024 * 1024:
        raise ValueError('invalid bridge packet length')
    return exact(connection, length)


def parse_pixels(payload):
    if payload[0] != 1:
        raise ValueError('not an observation')
    sequence, captured, ready, sent, wall_ms = struct.unpack_from('<iqqqq', payload, 1)
    offset = 1 + 36 + 24
    screen = payload[offset]
    offset += 2
    _, sound_size = struct.unpack_from('<HH', payload, offset)
    offset += 4 + 4 * sound_size
    chat_count = struct.unpack_from('<H', payload, offset)[0]
    offset += 2
    for _ in range(chat_count):
        count = struct.unpack_from('<H', payload, offset)[0]
        offset += 2 + count
    width, height = struct.unpack_from('<HH', payload, offset)
    offset += 4
    if not 1 <= width <= 1024 or not 1 <= height <= 1024:
        raise ValueError('invalid frame dimensions')
    pixels = np.frombuffer(payload, dtype=np.uint8, count=width * height * 3,
                           offset=offset).reshape(height, width, 3).copy()
    return {'sequence': sequence, 'captured_ns': captured, 'ready_ns': ready,
            'sent_ns': sent, 'wall_ms': wall_ms, 'screen': screen, 'pixels': pixels}


def wire_action(action, screen=False):
    keys, hot, horizontal, vertical, click = 0, -1, 5, 5, 0
    pointer_x, pointer_y = float(action.get('x', .5)), float(action.get('y', .5))
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in (pointer_x, pointer_y)):
        raise ValueError('action coordinates must be normalized')
    kind = action.get('kind')
    if kind == 'key':
        code = int(action.get('keyCode', 0))
        if code in KEY_BITS:
            keys = 1 << KEY_BITS[code]
        elif ord('1') <= code <= ord('9'):
            hot = code - ord('1')
    elif kind in ('click', 'drag'):
        click = 1
        if not screen:
            keys = 1 << 7
            target_x = float(action.get('endX', pointer_x)) if kind == 'drag' else pointer_x
            target_y = float(action.get('endY', pointer_y)) if kind == 'drag' else pointer_y
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in (target_x, target_y)):
                raise ValueError('drag endpoint coordinates must be normalized')
            horizontal = min(range(len(DXY)), key=lambda index: abs(DXY[index] - (target_x - .5) * 160))
            vertical = min(range(len(DXY)), key=lambda index: abs(DXY[index] - (target_y - .5) * 120))
    elif kind == 'scroll':
        if float(action.get('dy', 0)):
            hot = 1 if float(action['dy']) > 0 else 0
    else:
        raise ValueError('unsupported HANDS action kind')
    return keys, hot, horizontal, vertical, min(15, int(pointer_x * 16)), min(8, int(pointer_y * 9)), click


class BridgeServer:
    def __init__(self, output, port=BRAIN_PORT):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.latest = {}
        self.actions = {}
        self.connections = {}
        self.errors = []
        self.readers = []
        self.closed = threading.Event()
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', port))
        self.listener.listen(2)
        self.listener.settimeout(1)
        self.thread = threading.Thread(target=self._accept, daemon=True)
        self.thread.start()

    def _accept(self):
        while not self.closed.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            connection.settimeout(5)
            reader = threading.Thread(target=self._client, args=(connection,), daemon=True)
            self.readers.append(reader)
            reader.start()

    def _client(self, connection):
        name = None
        try:
            hello = read_message(connection)
            if hello[0] != 0:
                raise ValueError('expected bridge hello')
            length = struct.unpack_from('<H', hello, 1)[0]
            if len(hello) != length + 7:
                raise ValueError('malformed bridge hello')
            name = hello[3:3 + length].decode('utf8')
            if name not in NAMES:
                raise ValueError('not an owned client')
            with self.lock:
                if name in self.connections:
                    raise ValueError('duplicate owned client')
                self.connections[name] = connection
            frames = self.output / 'frames' / name
            frames.mkdir(parents=True, exist_ok=True)
            frame_time, applied_generation = 0, -1
            with (self.output / (name + '-wire.jsonl')).open('a', buffering=1) as trace:
                while not self.closed.is_set():
                    payload = read_message(connection)
                    if payload[0] == 3:
                        sequence, captured, received, applied = struct.unpack_from('<iqqq', payload, 1)
                        trace.write(json.dumps({'kind': 'ack', 'sequence': sequence,
                            'captured_ns': captured, 'received_ns': received, 'applied_ns': applied}) + '\n')
                    if payload[0] != 1:
                        continue
                    observation = parse_pixels(payload)
                    observation['arrived_monotonic'] = time.monotonic()
                    with self.lock:
                        self.latest[name] = observation
                        action, deadline, generation = self.actions.get(name, ({'kind': 'key', 'keyCode': 0}, 0, 0))
                    active = time.monotonic() < deadline
                    command = wire_action(action, observation['screen']) if active else (0, -1, 5, 5, 8, 4, 0)
                    if applied_generation == generation:
                        command = command[:2] + (5, 5) + command[4:6] + (0,)
                    applied_generation = generation
                    packet = struct.pack('<BiqIbbbbbb', 2, observation['sequence'],
                                         observation['captured_ns'], *command)
                    connection.sendall(struct.pack('<I', len(packet)) + packet)
                    trace.write(json.dumps({'kind': 'act', 'sequence': observation['sequence'],
                        'wall_ms': observation['wall_ms'], 'generation': generation,
                        'wire': command, 'active': active}) + '\n')
                    if observation['wall_ms'] - frame_time >= 200:
                        path = frames / ('%013d-%08d.png' % (observation['wall_ms'], observation['sequence']))
                        Image.fromarray(observation['pixels']).save(path)
                        trace.write(json.dumps({'kind': 'frame', 'sequence': observation['sequence'],
                            'wall_ms': observation['wall_ms'], 'path': str(path.relative_to(self.output)),
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}) + '\n')
                        frame_time = observation['wall_ms']
        except (OSError, ValueError, struct.error, ConnectionError) as error:
            if not self.closed.is_set():
                self.errors.append({'name': name, 'error': str(error), 'wall_ms': int(time.time() * 1000)})
        finally:
            with self.lock:
                if name is not None and self.connections.get(name) is connection:
                    self.connections.pop(name, None)
                    self.latest.pop(name, None)
            connection.close()

    def command(self, name, action, duration=.25):
        wire_action(action)
        with self.lock:
            generation = self.actions.get(name, (None, 0, 0))[2] + 1
            self.actions[name] = (dict(action), time.monotonic() + duration, generation)
        return generation

    def observation(self, name):
        with self.lock:
            observation = self.latest.get(name)
        if observation is None or time.monotonic() - observation['arrived_monotonic'] > 5:
            raise TimeoutError('no fresh Minecraft pixels for ' + name)
        image = Image.fromarray(observation['pixels'])
        detail = image.resize((192, 192))
        return {'overview': np.array(image.resize((320, 180))), 'detail': np.array(detail)}

    def close(self):
        self.closed.set()
        with self.lock:
            connections = list(self.connections.values())
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.listener.close()
        self.thread.join(timeout=2)
        for reader in self.readers:
            reader.join(timeout=6)


def inventory_count(summary, material):
    total = 0
    for entry in summary.replace(',', ' ').replace(';', ' ').split():
        if entry.startswith(material + ':'):
            total += int(entry[len(material) + 1:])
    return total


def check_goals(rows, name=NAMES[0]):
    result = {goal: False for goal in GOALS}
    for row in rows:
        if row.get('k') != 't':
            continue
        for player in row.get('p', []):
            if player.get('n') != name:
                continue
            generator = {'Red': (-35.5, 64, .5), 'Blue': (36.5, 64, .5)}.get(player.get('team'))
            if generator and player.get('alive') == 1:
                distance = sum((player[axis] - value) ** 2 for axis, value in zip(('x', 'y', 'z'), generator)) ** .5
                result['reach_generator'] |= distance <= 1.5
                result['collect_4_iron'] |= inventory_count(player.get('inv', ''), 'IRON_INGOT') >= 4
                result['survive_10_seconds'] |= row.get('tick', 0) >= 200 and player.get('d', 0) == 0
    return result


def game_finished(rows):
    header = any(row.get('k') == 'hdr' for row in rows)
    playing = any(row.get('k') == 't' for row in rows)
    terminal = any((row.get('k') == 'ev' and row.get('e') == 'gameend') or
                   (row.get('k') == 'end' and row.get('why') == 'restarting') for row in rows)
    return header and playing and terminal


def publish_tactical_state(state, directory=None):
    directory = ROOT if directory is None else directory
    pending = directory / 'tactical-state.pending'
    pending.write_text(json.dumps(state))
    try:
        pending.replace(directory / 'tactical-state.json')
    except PermissionError:
        return False
    return True


class TruthReader:
    def __init__(self, directory=ROOT / 'truth'):
        self.directory = Path(directory)
        self.matches = {}
        self.offsets = {}

    def refresh(self):
        for path in sorted(self.directory.glob('match-*.jsonl')):
            with path.open(encoding='utf8') as source:
                source.seek(self.offsets.get(str(path), 0))
                while True:
                    position = source.tell()
                    line = source.readline()
                    if not line or not line.endswith('\n'):
                        self.offsets[str(path)] = position
                        break
                    row = json.loads(line)
                    self.matches.setdefault(path.stem, []).append(row)
        return self.matches


class BedwarsEnv:
    def __init__(self, bridge, truth, output, max_steps=80, step_seconds=.25, fixed_plan=None):
        self.bridge, self.truth = bridge, truth
        self.output = Path(output)
        self.max_steps, self.step_seconds = max_steps, step_seconds
        self.episode, self.match, self.steps = None, None, 0
        self.previous = {goal: False for goal in GOALS}
        self.started_ms = int(time.time() * 1000)
        self.fixed_plan = fixed_plan
        self.last_tactical_state = 0

    def instruction(self):
        if self.fixed_plan is not None:
            self.episode['instruction'] = self.fixed_plan['instruction']
            self.episode['tactics'] = self.fixed_plan
            return self.fixed_plan['instruction']
        try:
            record = json.loads((ROOT / 'tactics.json').read_text(encoding='utf8'))
            age = int(time.time() * 1000) - record['wall_ms']
            if not 0 <= age < 60000 or not isinstance(record['instruction'], str) or not record['instruction'].strip():
                raise ValueError('stale or invalid tactics')
        except (OSError, ValueError, KeyError, TypeError):
            record = {'instruction': DEFAULT_INSTRUCTION, 'source': 'scripted_fallback',
                      'reason': 'relay_unavailable_or_stale'}
        self.episode['instruction'] = record['instruction']
        self.episode['tactics'] = record
        return record['instruction']

    async def reset(self, kind='collect_iron', seed=0):
        if kind != 'collect_iron':
            raise ValueError('unknown Bedwars practice goal')
        previous_match = self.match
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            matches = self.truth.refresh()
            for match, rows in reversed(list(matches.items())):
                headers = [row for row in rows if row.get('k') == 'hdr']
                if not headers or headers[0]['t_ms'] < self.started_ms:
                    continue
                if match == previous_match or not any(row.get('k') == 't' for row in rows):
                    continue
                if any(row.get('k') == 'end' for row in rows) or game_finished(rows):
                    continue
                self.match = match
                self.steps = 0
                self.previous = {goal: False for goal in GOALS}
                self.episode = {'kind': kind, 'seed': seed, 'instruction': DEFAULT_INSTRUCTION,
                                'max_steps': self.max_steps, 'match': match}
                self.instruction()
                return self.bridge.observation(NAMES[0])
            await asyncio.sleep(.1)
        raise TimeoutError('no new real BedWars1058 game started in 180 seconds')

    async def step(self, action):
        if self.episode is None:
            raise RuntimeError('reset required')
        generation = self.bridge.command(NAMES[0], action, self.step_seconds)
        await asyncio.sleep(self.step_seconds)
        self.steps += 1
        rows = self.truth.refresh()[self.match]
        goals = check_goals(rows)
        if time.monotonic() - self.last_tactical_state >= 2:
            ticks = [row for row in rows if row.get('k') == 't']
            players = [player for player in ticks[-1].get('p', []) if player.get('n') == NAMES[0]] if ticks else []
            state = {'wall_ms': int(time.time() * 1000), 'match': self.match,
                     'tick': ticks[-1]['tick'] if ticks else None, 'game_checked_goals': goals,
                     'player': {key: value for key, value in players[-1].items()
                                if key in {'team', 'x', 'y', 'z', 'yaw', 'pitch', 'hp', 'inv', 'bed', 'k', 'd', 'alive'}} if players else {}}
            if not publish_tactical_state(state):
                with (self.output / 'tactical-publication-errors.jsonl').open('a') as trace:
                    trace.write(json.dumps({'wall_ms': state['wall_ms'], 'match': self.match,
                        'reason': 'atomic replace denied by concurrent reader; next publication retries'}) + '\n')
            self.last_tactical_state = time.monotonic()
        reward = sum(float(goals[goal] and not self.previous[goal]) for goal in GOALS)
        self.previous = goals
        finished = game_finished(rows)
        interrupted = any(row.get('k') == 'end' and row.get('why') != 'restarting' for row in rows)
        if interrupted:
            raise RuntimeError('server interrupted this game; do not count it')
        done = finished or self.steps >= self.max_steps
        info = {'match': self.match, 'goals': goals, 'success': goals['collect_4_iron'],
                'game_finished': finished, 'seed': self.episode['seed'], 'step': self.steps}
        with (self.output / 'native-actions.jsonl').open('a') as trace:
            trace.write(json.dumps({'wall_ms': int(time.time() * 1000), 'action': action,
                'generation': generation, 'instruction': self.episode['instruction'],
                'tactics': self.episode['tactics'],
                'reward': reward, **info}) + '\n')
        self.instruction()
        return self.bridge.observation(NAMES[0]), reward, done, info

    async def close(self):
        self.bridge.command(NAMES[0], {'kind': 'key', 'keyCode': 0}, 0)
        await asyncio.sleep(.15)
