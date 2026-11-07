"""Frozen brief-7 pilot and serial wave, reusing the existing PPO harness."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from hands_gym import tasks

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'runs/brief7'
SEEDS = (11, 22, 33)
MATRIX = [('control', 11), ('reverse', 11), ('control', 22),
          ('reverse', 22), ('control', 33), ('reverse', 33)]


def write_json(destination, data):
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(destination)


def digest(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def verify_payload():
    manifest = json.loads((RUN / 'deployment-manifest.json').read_text(encoding='utf-8'))
    for relative, expected in manifest['files'].items():
        if digest(ROOT / relative) != expected:
            raise RuntimeError('deployed payload changed: ' + relative)
    return manifest


def prepare():
    manifest = verify_payload()
    frozen = []
    for seed in SEEDS:
        for kind in tasks.TASK_TYPES:
            for offset in range(16):
                task_seed = 10_000_000 + (seed + 700) * 1000 + offset
                episode = tasks.build(kind, task_seed)
                frozen.append({'training_seed': seed, 'kind': kind, 'task_seed': task_seed,
                               'instruction': episode['instruction'], 'spec': episode['spec'],
                               'html_sha256': hashlib.sha256(episode['html'].encode()).hexdigest(),
                               'start_k': None})
    encoded = json.dumps(frozen, sort_keys=True, indent=2).encode()
    filename = RUN / 'held-out-tasks.json'
    if filename.exists() and filename.read_bytes() != encoded:
        raise RuntimeError('held-out suite differs from frozen manifest')
    filename.write_bytes(encoded)
    print(json.dumps({'event': 'verified', 'commit': manifest['commit'],
                      'held_out_tasks': len(frozen), 'held_out_sha256': digest(filename),
                      'preregistration_sha256': digest(RUN / 'PREREGISTRATION.md')}), flush=True)


def training_command(arm, seed):
    command = [sys.executable, '-u', '-m', 'hands_gym.train',
               '--output', 'runs/brief7/' + arm, '--seeds', str(seed),
               '--updates', '200', '--envs', '8', '--rollout', '8', '--max-steps', '20',
               '--eval-episodes', '16', '--epochs', '3', '--minibatch', '32',
               '--lr', '0.0003', '--entropy', '0.005', '--device', 'cuda',
               '--self-imitation-weight', '0.0', '--success-buffer-episodes', '128',
               '--eval-every', '200', '--task-families', *tasks.TASK_TYPES]
    if arm == 'reverse':
        command.extend(['--start-k', '1'])
    return command


def validate_result(directory, arm):
    result = json.loads((directory / 'result.json').read_text())
    settings = result['args']
    expected_start = 1 if arm == 'reverse' else None
    if (result['train_steps'] != 12800 or settings['self_imitation_weight'] != 0
            or settings['start_k'] != expected_start or settings['max_steps'] != 20
            or settings['task_families'] != list(tasks.TASK_TYPES)):
        raise RuntimeError('completed result does not match frozen protocol')
    if result['final_sha256'] != digest(directory / 'final.pt'):
        raise RuntimeError('final checkpoint hash mismatch')
    rates = result['final']['per_task']
    if set(rates) != set(tasks.TASK_TYPES) or any(row['episodes'] != 16 for row in rates.values()):
        raise RuntimeError('required held-out family score is unmeasurable')
    traces = [json.loads(line) for line in (directory / 'final-trace.jsonl').read_text().splitlines()]
    if len(traces) != 144 or any(row['start_k'] is not None for row in traces):
        raise RuntimeError('held-out scoring did not use the frozen normal starts')


def run_one(arm, seed):
    verify_payload()
    directory = RUN / arm / ('seed-' + str(seed))
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / 'execution.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {
        'arm': arm, 'seed': seed, 'attempts': [], 'active_seconds': 0.0,
        'gpu_wait_seconds': 0.0, 'completed': False}
    result_path = directory / 'result.json'
    if result_path.exists():
        validate_result(directory, arm)
        receipt['completed'] = True
        write_json(receipt_path, receipt)
        return receipt
    checkpoint = directory / 'training-state.pt'
    if (directory / 'initial.pt').exists() and not checkpoint.exists():
        raise RuntimeError('partial run has no recovery checkpoint; refuse fresh overwrite')
    while True:
        verify_payload()
        command = training_command(arm, seed)
        if checkpoint.exists():
            command.extend(['--resume-training', str(checkpoint.relative_to(ROOT))])
        attempt = len(receipt['attempts']) + 1
        log_path = directory / ('attempt-%03d.log' % attempt)
        started = time.monotonic()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(json.dumps({'event': 'launch', 'arm': arm, 'seed': seed,
                          'attempt': attempt, 'start_utc': timestamp, 'command': command}), flush=True)
        with log_path.open('w', encoding='utf-8') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        elapsed = time.monotonic() - started
        output = log_path.read_text(encoding='utf-8')
        busy = any(marker in output for marker in ('GPU busy; wait for owner:', 'GPU not idle:'))
        busy = busy or ('FileExistsError:' in output and 'GPU-OWNER.json' in output)
        yielded = 'foreign CUDA client appeared; checkpoint saved; yielding GPU' in output
        status = 'gpu_wait' if busy else 'yielded' if yielded else 'completed' if process.returncode == 0 else 'failed'
        attempt_row = {'command': command, 'start_utc': timestamp,
                       'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'seconds': elapsed, 'exit_code': process.returncode, 'status': status,
                       'log': str(log_path.relative_to(ROOT)), 'log_sha256': digest(log_path)}
        receipt['attempts'].append(attempt_row)
        receipt['gpu_wait_seconds' if busy else 'active_seconds'] += elapsed
        receipt['completed'] = process.returncode == 0
        write_json(receipt_path, receipt)
        print(json.dumps({'event': 'exit', 'arm': arm, 'seed': seed, **attempt_row}), flush=True)
        print(output[-2400:], flush=True)
        if process.returncode == 0:
            validate_result(directory, arm)
            return receipt
        if not busy and not yielded:
            raise RuntimeError('training failed; inspect preserved attempt log')
        wait_started = time.monotonic()
        time.sleep(45)
        receipt['gpu_wait_seconds'] += time.monotonic() - wait_started
        write_json(receipt_path, receipt)


def pilot():
    receipt = run_one('control', 11)
    estimate = 9 * receipt['active_seconds']
    gate = {'pilot_active_seconds': receipt['active_seconds'],
            'pilot_gpu_wait_seconds': receipt['gpu_wait_seconds'],
            'estimated_full_wave_seconds': estimate, 'limit_seconds': 7200,
            'continue_wave': estimate <= 7200, 'estimator': '3*A + 3*(2*A) = 9*A'}
    write_json(RUN / 'pilot-gate.json', gate)
    print(json.dumps({'event': 'pilot_gate', **gate}), flush=True)


def summarize():
    rows = []
    paired = {}
    checkpoint_hashes = {}
    for arm, seed in MATRIX:
        directory = RUN / arm / ('seed-' + str(seed))
        filename = directory / 'result.json'
        if not filename.exists():
            for kind in tasks.TASK_TYPES:
                rows.append({'arm': arm, 'seed': seed, 'kind': kind, 'status': 'unmeasured'})
            continue
        result = json.loads(filename.read_text())
        rates = result['final']['per_task']
        paired[arm, seed] = rates
        for kind, value in rates.items():
            rows.append({'arm': arm, 'seed': seed, 'kind': kind, 'status': 'measured', **value})
        for checkpoint in directory.glob('*.pt'):
            checkpoint_hashes[str(checkpoint.relative_to(ROOT))] = digest(checkpoint)
    comparisons = []
    for seed in SEEDS:
        if ('control', seed) not in paired or ('reverse', seed) not in paired:
            continue
        control = paired['control', seed]
        reverse = paired['reverse', seed]
        gain = 100 * sum(reverse[kind]['rate'] - control[kind]['rate']
                         for kind in tasks.MULTI_STEP_TYPES) / len(tasks.MULTI_STEP_TYPES)
        singles = {kind: 100 * (reverse[kind]['rate'] - control[kind]['rate'])
                   for kind in tasks.TASK_TYPES if kind not in tasks.MULTI_STEP_TYPES}
        comparisons.append({'seed': seed, 'multi_step_gain_points': gain,
                            'single_step_gain_points': singles})
    verdict = 'INCOMPLETE — required arms/seeds unmeasured'
    if len(comparisons) == 3:
        passes = sum(row['multi_step_gain_points'] >= 15 for row in comparisons)
        no_gain = sum(row['multi_step_gain_points'] <= 0 for row in comparisons)
        nonregression = all(gain >= -5 for row in comparisons
                            for gain in row['single_step_gain_points'].values())
        verdict = 'PASS' if passes >= 2 and nonregression else 'PROVES IT WRONG' if no_gain >= 2 else 'FAIL'
    write_json(RUN / 'final-success-per-family.json', rows)
    write_json(RUN / 'checkpoint-hashes.json', checkpoint_hashes)
    write_json(RUN / 'summary.json', {'verdict': verdict, 'comparisons': comparisons,
                                     'measured_runs': len(paired), 'required_runs': 6})
    print(json.dumps({'event': 'summary', 'verdict': verdict, 'comparisons': comparisons}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('pilot', 'wave', 'summarize', 'prepare'))
    args = parser.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    prepare()
    if args.phase == 'pilot':
        pilot()
        summarize()
    elif args.phase == 'wave':
        gate = json.loads((RUN / 'pilot-gate.json').read_text())
        if not gate['continue_wave']:
            raise RuntimeError('STOP: frozen two-hour pilot gate exceeded')
        for arm, seed in MATRIX:
            run_one(arm, seed)
            summarize()
    elif args.phase == 'summarize':
        summarize()


if __name__ == '__main__':
    main()
