#!/usr/bin/env python3
"""Local Mac fallback harness for remote_runner.py.

Real-recording datasets keep trainer.production_gate exactly. Synthetic
datasets call trainer.train with a no-op gate because the 01:00-07:00 window
applies only to real recordings. trainer.py itself is not modified.
"""
import argparse
import json
import sys
from pathlib import Path

NIGHT = Path(__file__).resolve().parents[1] / 'night-learn'
sys.path.insert(0, str(NIGHT))

import trainer


def score_row(row):
    action = row['action']
    scored = {'id': row['id'], 'timeMs': row['timeMs'], 'kind': action['kind']}
    if action['kind'] == 'click':
        scored.update(x=action.get('screenX', action['x']), y=action.get('screenY', action['y']))
    elif action['kind'] == 'key':
        scored['key'] = str(action['keyCode'])
    return scored


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--steps', type=int)
    parser.add_argument('dataset')
    parser.add_argument('output')
    args = parser.parse_args()
    dataset_path, output = args.dataset, args.output
    with open(dataset_path, encoding='utf8') as handle:
        dataset = json.load(handle)
    if args.synthetic and dataset.get('synthetic') is not True:
        raise ValueError('real recordings cannot bypass the production gate')
    synthetic = dataset.get('synthetic') is True
    from remote_runner import check_stop
    gate = check_stop if synthetic else trainer.production_gate
    gate()
    previous = dataset.get('preSleepWeights')
    result = trainer.train(dataset, Path(output), gate=gate,
                           steps=args.steps or dataset.get('trainingSteps', 100),
                           previous=Path(previous) if previous else None)
    result['train'] = [score_row(row) for row in result['train']]
    result['held'] = [score_row(row) for row in result['held']]
    result['trainingBackend'] = 'mac-cpu-synthetic-fallback' if synthetic else 'mac-cpu-fallback'
    print(json.dumps(result))


if __name__ == '__main__':
    main()
