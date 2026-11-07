"""Offline Bedwars protocol, referee, pixel isolation and lifecycle safety checks."""
import asyncio
import json
from pathlib import Path
import runpy
import socket
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/hands-gym'))
from hands_gym.bedwars_env import (
    BedwarsEnv, BridgeServer, GOALS, NAMES, TruthReader, check_goals,
    game_finished, inventory_count, parse_pixels, publish_tactical_state, read_message, wire_action,
)
from hands_gym.bedwars_tools import detached, join
from hands_gym.bedwars_audit import audit
from hands_gym import bedwars_env


def observation(sequence=1, private=(1, 2, 3, 4, 5, 6)):
    return (bytes([1]) + struct.pack('<iqqqq', sequence, 20, 21, 22, 1000 + sequence)
            + struct.pack('<ffffff', *private) + bytes([0, 1])
            + struct.pack('<HHH', 0, 0, 0) + struct.pack('<HH', 2, 2)
            + bytes(range(12)))


class BedwarsTests(unittest.TestCase):
    def test_tactical_snapshot_reader_conflict_does_not_abort_game(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'tactical-state.json'
            target.write_text('{"previous":true}')
            with mock.patch.object(Path, 'replace', side_effect=PermissionError('reader sharing conflict')):
                self.assertFalse(publish_tactical_state({'new': True}, root))
            self.assertEqual(json.loads(target.read_text()), {'previous': True})
            self.assertTrue(publish_tactical_state({'new': True}, root))
            self.assertEqual(json.loads(target.read_text()), {'new': True})

    def test_queued_glim_instruction_preserves_request_context(self):
        relay = runpy.run_path(str(Path(bedwars_env.__file__).resolve().parents[1] / 'bedwars-tactics.py'))
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / 'state.json'
            stamp = int(time.time() * 1000)
            decision = {'source': 'glim', 'instruction': 'Move toward the generator.',
                        'wall_ms': stamp, 'state': {'match': 'request-context'}}
            inbox = context.with_name('queued-glim.json')
            inbox.write_text(json.dumps(decision))
            self.assertEqual(relay['choose'](context), decision)
            self.assertFalse(inbox.exists())
            self.assertTrue(context.with_name('consumed-glim-%d.json' % stamp).exists())

    def test_pixels_exclude_client_truth(self):
        first = parse_pixels(observation())
        second = parse_pixels(observation(private=(99, 98, 97, 96, 95, 94)))
        self.assertEqual(set(first), {'sequence', 'captured_ns', 'ready_ns', 'sent_ns', 'wall_ms', 'screen', 'pixels'})
        self.assertTrue((first['pixels'] == second['pixels']).all())
        self.assertEqual(first['pixels'].shape, (2, 2, 3))
        for payload in [b'', b'\x01', observation()[:-1]]:
            with self.assertRaises((ValueError, IndexError, struct.error)):
                parse_pixels(payload)

    def test_native_actions_and_bounds(self):
        self.assertEqual(wire_action({'kind': 'key', 'keyCode': ord('s')})[0], 4)
        self.assertEqual(wire_action({'kind': 'key', 'keyCode': ord('w')})[0], 1)
        self.assertEqual(wire_action({'kind': 'key', 'keyCode': ord('9')})[1], 8)
        self.assertEqual(wire_action({'kind': 'click', 'x': .5, 'y': .5})[2:4], (5, 5))
        self.assertEqual(wire_action({'kind': 'click'}, True)[0], 0)
        for action in [{'kind': 'key', 'x': float('nan')}, {'kind': 'click', 'x': 1.1},
                       {'kind': 'drag', 'endX': -1}, {'kind': 'unsupported'}]:
            with self.assertRaises(ValueError):
                wire_action(action)

    def test_truth_goals_are_game_checked(self):
        self.assertEqual(inventory_count('IRON_INGOT:2,IRON_INGOT:3,WOOL:16', 'IRON_INGOT'), 5)
        player = {'n': NAMES[0], 'team': 'Red', 'x': -35.5, 'y': 64, 'z': .5,
                  'alive': 1, 'd': 0, 'inv': 'IRON_INGOT:4'}
        rows = [{'k': 't', 'tick': 200, 'p': [player]}]
        self.assertTrue(all(check_goals(rows).values()))
        player['n'] = NAMES[1]
        self.assertFalse(any(check_goals(rows).values()))
        player.update(n=NAMES[0], alive=0)
        self.assertFalse(any(check_goals(rows).values()))
        player.update(alive=1, d=1, team='Blue', x=36.5)
        self.assertTrue(check_goals(rows)['reach_generator'])
        self.assertFalse(check_goals(rows)['survive_10_seconds'])

    def test_full_game_not_plugin_disable(self):
        rows = [{'k': 'hdr'}, {'k': 't'}]
        self.assertFalse(game_finished(rows))
        self.assertFalse(game_finished(rows + [{'k': 'end', 'why': 'plugin disable'}]))
        self.assertTrue(game_finished(rows + [{'k': 'end', 'why': 'restarting'}]))
        self.assertTrue(game_finished(rows + [{'k': 'ev', 'e': 'gameend'}]))
        self.assertFalse(game_finished([{'k': 'end', 'why': 'restarting'}]))

    def test_partial_truth_line_is_retried_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'match-test.jsonl'
            path.write_text('{"k":"hdr"}\n{"k":')
            reader = TruthReader(directory)
            self.assertEqual(len(reader.refresh()['match-test']), 1)
            with path.open('a') as output:
                output.write('"t"}\n')
            self.assertEqual(len(reader.refresh()['match-test']), 2)
            self.assertEqual(len(reader.refresh()['match-test']), 2)

    def test_packet_size_and_eof(self):
        for length in [0, 2 * 1024 * 1024 + 1]:
            left, right = socket.socketpair()
            try:
                right.sendall(struct.pack('<I', length))
                with self.assertRaises(ValueError):
                    read_message(left)
            finally:
                left.close()
                right.close()

    def test_real_loopback_frame_action_and_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = BridgeServer(directory, port=0)
            client = socket.create_connection(bridge.listener.getsockname(), timeout=2)
            def send(payload):
                client.sendall(struct.pack('<I', len(payload)) + payload)
            try:
                name = NAMES[0].encode()
                send(bytes([0]) + struct.pack('<H', len(name)) + name + struct.pack('<HH', 2, 2))
                bridge.command(NAMES[0], {'kind': 'key', 'keyCode': ord('s')}, 2)
                send(observation())
                reply = read_message(client)
                self.assertEqual(struct.unpack_from('<I', reply, 13)[0], 4)
                send(struct.pack('<Biqqq', 3, 1, 20, 25, 26))
                send(observation(2))
                read_message(client)
                pixels = bridge.observation(NAMES[0])
                self.assertEqual(set(pixels), {'overview', 'detail'})
                self.assertEqual(pixels['overview'].shape, (180, 320, 3))
            finally:
                bridge.close()
                client.close()
            rows = [json.loads(line) for line in (Path(directory) / (NAMES[0] + '-wire.jsonl')).read_text().splitlines()]
            self.assertTrue(any(row['kind'] == 'ack' for row in rows))
            self.assertTrue(any(row['kind'] == 'frame' for row in rows))
            self.assertFalse(bridge.errors)

    def test_lifecycle_rejects_benspc_rendering(self):
        with self.assertRaisesRegex(RuntimeError, 'rendering disabled'):
            join(NAMES[0])
        with self.assertRaises(ValueError):
            detached([], Path('.'), 'foreign')

    def test_running_task_guard_precedes_wrapper_write(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch('hands_gym.bedwars_tools.ROOT', Path(directory)):
                with mock.patch('hands_gym.bedwars_tools.subprocess.run', side_effect=RuntimeError('running')):
                    with self.assertRaisesRegex(RuntimeError, 'running'):
                        detached([], Path(directory), 'controller')
            self.assertFalse((Path(directory) / 'controller-job.py').exists())

    def test_stale_tactics_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch('hands_gym.bedwars_env.ROOT', Path(directory)):
                env = BedwarsEnv(None, None, directory)
                env.episode = {}
                self.assertIn('four iron', env.instruction())
                record = {'instruction': 'Hold S briefly.', 'source': 'glim', 'wall_ms': int(time.time() * 1000)}
                (Path(directory) / 'tactics.json').write_text(json.dumps(record))
                self.assertEqual(env.instruction(), record['instruction'])
                record['wall_ms'] -= 61000
                (Path(directory) / 'tactics.json').write_text(json.dumps(record))
                self.assertNotEqual(env.instruction(), record['instruction'])

    def test_fixed_plan_is_stationary(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = {'instruction': 'Collect four iron.', 'source': 'glim_cached', 'plan_sha256': 'retained'}
            env = BedwarsEnv(None, None, directory, fixed_plan=plan)
            env.episode = {}
            self.assertEqual(env.instruction(), plan['instruction'])
            self.assertEqual(env.episode['tactics'], plan)

    def test_slow_state_is_separate_from_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            player = {'n': NAMES[0], 'team': 'Red', 'x': -35.5, 'y': 64, 'z': .5,
                      'alive': 1, 'd': 0, 'inv': 'IRON_INGOT:4', 'private_extra': 'excluded'}
            rows = [{'k': 't', 'tick': 200, 'p': [player]}]
            bridge = mock.Mock()
            bridge.command.return_value = 1
            bridge.observation.return_value = {'overview': 'pixels', 'detail': 'pixels'}
            truth = mock.Mock()
            truth.refresh.return_value = {'match-test': rows}
            with mock.patch('hands_gym.bedwars_env.ROOT', Path(directory)):
                env = BedwarsEnv(bridge, truth, directory, step_seconds=.001)
                env.episode = {'seed': 1}
                env.match = 'match-test'
                env.instruction()
                pixels, reward, _, _ = asyncio.run(env.step({'kind': 'key', 'keyCode': 0}))
                self.assertEqual(set(pixels), {'overview', 'detail'})
                self.assertEqual(reward, 3)
                state = json.loads((Path(directory) / 'tactical-state.json').read_text())
                self.assertTrue(all(state['game_checked_goals'].values()))
                self.assertNotIn('private_extra', state['player'])

    def test_independent_audit_rejects_false_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'truth').mkdir()
            (root / 'run.json').write_text(json.dumps({'started_ms': 100, 'seeds': [11], 'eval_games': 1}))
            episodes = []
            for phase in ['baseline', 'final']:
                match = 'match-' + phase
                rows = [{'k': 'hdr', 't_ms': 200}, {'k': 't', 'tick': 1, 'p': []},
                        {'k': 'end', 'why': 'restarting'}]
                (root / 'truth' / (match + '.jsonl')).write_text(''.join(json.dumps(row) + '\n' for row in rows))
                episodes.append({'phase': phase, 'policy_seed': 11, 'seed': 10110000,
                                 'match': match, 'goals': {goal: False for goal in GOALS}, 'game_finished': True})
            (root / 'episodes.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in episodes))
            (root / 'native-actions.jsonl').write_text(''.join(json.dumps({'match': row['match'], 'generation': 1}) + '\n' for row in episodes))
            (root / 'BotHands1-wire.jsonl').write_text(json.dumps({'kind': 'act', 'generation': 1, 'active': True, 'sequence': 1, 'wire': [4, -1, 5, 5, 8, 4, 0]}) + '\n' + json.dumps({'kind': 'ack', 'sequence': 1}) + '\n')
            self.assertTrue(audit(root, verify_frames=False)['passed'])
            self.assertFalse(audit(root)['passed'])
            episodes[0]['goals']['collect_4_iron'] = True
            (root / 'episodes.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in episodes))
            self.assertFalse(audit(root, verify_frames=False)['passed'])


if __name__ == '__main__':
    unittest.main()
