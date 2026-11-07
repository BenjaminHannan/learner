"""Independent offline replay of server-checked goals and recording receipts."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from .bedwars_env import GOALS, check_goals, game_finished


def json_lines(path):
    with path.open(encoding='utf8') as source:
        return [json.loads(line) for line in source if line.strip()]


def audit(directory, verify_frames=True):
    directory = Path(directory)
    configuration = json.loads((directory / 'run.json').read_text())
    episodes = json_lines(directory / 'episodes.jsonl')
    actions = json_lines(directory / 'native-actions.jsonl')
    wire = json_lines(directory / 'BotHands1-wire.jsonl')
    frame_records = [item for item in wire if item['kind'] == 'frame']
    failures = []
    seen = set()
    verified = []
    counts = Counter()
    for row in episodes:
        match = row['match']
        if match in seen:
            failures.append('duplicate evaluated match: ' + match)
        seen.add(match)
        truth = json_lines(directory / 'truth' / (match + '.jsonl'))
        goals = check_goals(truth)
        headers = [item for item in truth if item.get('k') == 'hdr']
        ticks = [item for item in truth if item.get('k') == 't']
        full = game_finished(truth)
        if goals != row['goals'] or not full or not row['game_finished']:
            failures.append('referee mismatch or incomplete game: ' + match)
        if headers and headers[0]['t_ms'] < configuration['started_ms']:
            failures.append('game began before recording: ' + match)
        commands = [item for item in actions if item['match'] == match]
        generations = {item['generation'] for item in commands}
        applied = [item for item in wire if item['kind'] == 'act'
                   and item['generation'] in generations and item['active']]
        ack_sequences = {item['sequence'] for item in wire if item['kind'] == 'ack'}
        acknowledged = [item for item in applied if item['sequence'] in ack_sequences]
        nonneutral = [item for item in acknowledged if item.get('wire') and
                      (item['wire'][0] != 0 or item['wire'][1] != -1 or
                       item['wire'][2:4] != [5, 5] or item['wire'][6] != 0)]
        sequences = {item['sequence'] for item in applied}
        recorded_frames = [item for item in frame_records if item['sequence'] in sequences]
        if not commands or not nonneutral:
            failures.append('no applied/acknowledged HANDS commands: ' + match)
        if verify_frames and not recorded_frames:
            failures.append('no recorded frames for applied game actions: ' + match)
        policy_seed = row.get('policy_seed', (row['seed'] - 10000000) // 10000)
        tactics = Counter(item.get('tactics', {}).get('source', 'unknown') for item in commands)
        own_teams = [team['name'] for header in headers for team in header.get('teams', [])
                     if 'BotHands1' in team.get('members', [])]
        winners = [item.get('winner') for item in truth if item.get('k') == 'ev' and item.get('e') == 'gameend']
        outcome = 'draw' if not winners or not winners[-1] else ('win' if winners[-1] in own_teams else 'loss')
        events = Counter(item.get('e') for item in truth if item.get('k') == 'ev' and
                         (item.get('n') == 'BotHands1' or item.get('by') == 'BotHands1' or item.get('killer') == 'BotHands1'))
        verified.append({**row, 'policy_seed': policy_seed, 'recomputed_goals': goals,
            'truth_ticks': len(ticks), 'terminal_tick': ticks[-1]['tick'] if ticks else None,
            'terminal_events': [item for item in truth if item.get('k') not in {'hdr', 't'}][-4:],
            'native_actions': len(commands), 'active_wire_actions': len(applied),
            'acknowledged_wire_actions': len(acknowledged), 'tactics_sources': dict(tactics),
            'nonneutral_acknowledged_actions': len(nonneutral), 'recorded_game_frames': len(recorded_frames),
            'outcome': outcome, 'own_event_counts': dict(events),
            'truth_sha256': hashlib.sha256((directory / 'truth' / (match + '.jsonl')).read_bytes()).hexdigest()})
        counts.update(tactics)
    if verify_frames:
        for row in frame_records:
            path = directory / row['path'].replace('\\', '/')
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                failures.append('frame checksum mismatch: ' + str(path))
    rates = []
    phases = ['live'] if configuration.get('mode') == 'live' else ['baseline', 'final']
    for seed in configuration['seeds']:
        for phase in phases:
            group = [row for row in verified if row['policy_seed'] == seed and row['phase'] == phase]
            if len(group) != configuration['eval_games']:
                failures.append('missing evaluated games for %s/%s' % (seed, phase))
            rates.append({'seed': seed, 'phase': phase, 'games': len(group),
                          **{goal: sum(row['recomputed_goals'][goal] for row in group)
                             for goal in GOALS}})
    return {'verified_games': verified, 'rates': rates, 'tactics_sources': dict(counts),
            'frames_checked': len(frame_records) if verify_frames else 0,
            'failures': failures, 'passed': not failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--skip-frame-hashes', action='store_true')
    args = parser.parse_args()
    result = audit(args.run, not args.skip_frame_hashes)
    (args.run / 'audit.json').write_text(json.dumps(result, indent=2))
    with (args.run / 'goal-rates.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=['seed', 'phase', 'games', *GOALS])
        writer.writeheader()
        writer.writerows(result['rates'])
    print(json.dumps({key: value for key, value in result.items() if key != 'verified_games'}, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
