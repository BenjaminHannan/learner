"""Brief 15: inference-only, frozen-checkpoint length measurements."""
import argparse
import asyncio
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import time

from . import tasks


CELLS = (
    ('letters_3', 'type_text', None, 20),
    ('letters_6', 'type_text', 'letters_6', 40),
    ('letters_10', 'type_text', 'letters_10', 60),
    ('fields_2', 'form_fill', None, 20),
    ('fields_5', 'form_fill', 'fields_5', 60),
)
SEEDS = (11, 22, 33)
EXPECTED = {
    11: 'e6dc347caa4c585cad958e17dca4d5b2b8a3b14beb89b5f884a9418c1754dce9',
    22: 'c9b1945ac553f72c1f6fe81030baa768e9b51912badb5590ea931a2c14442956',
    33: '5b1166aed4f32449d1e30b6f9118e8562985de88b2c5df954e1cd221627ae19c',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def task_seed(seed, episode):
    return 80_000_000 + seed * 10_000 + episode


def verdict(short, long):
    if short['episodes'] != 100 or long['episodes'] != 100:
        return 'UNMEASURABLE'
    baseline = short['successes']
    if baseline < 10:
        return 'UNMEASURABLE'
    if 5 * long['successes'] >= 4 * baseline:
        return 'NO WALL'
    if 2 * long['successes'] <= baseline:
        return 'WALL'
    return 'PARTIAL'


def unmeasurable_baseline(row):
    return (row['cell'] in ('letters_3', 'fields_2') and row['episodes'] == 100
            and row['successes'] < 10)


def summarize(results):
    rows = []
    for seed in SEEDS:
        cells = {row['cell']: row for row in results if row['seed'] == seed}
        row = {'seed': seed}
        for family, short_label, long_label in (('typing', 'letters_3', 'letters_10'),
                                                ('forms', 'fields_2', 'fields_5')):
            short = cells.get(short_label)
            long = cells.get(long_label)
            if short is not None and unmeasurable_baseline(short):
                row[family] = 'UNMEASURABLE'
            elif short is not None and long is not None:
                row[family] = verdict(short, long)
            else:
                row[family] = 'UNMEASURED'
        rows.append(row)
    return rows


def verify_checkpoints(root):
    rows = []
    for seed in SEEDS:
        directory = Path(root) / ('seed-' + str(seed))
        checkpoint = directory / 'final.pt'
        observed = digest(checkpoint)
        if observed != EXPECTED[seed]:
            raise ValueError('brief-7 checkpoint hash mismatch: %s' % checkpoint)
        result = json.loads((directory / 'result.json').read_text())
        if result['train_steps'] != 12800 or result['args']['start_k'] is not None:
            raise ValueError('requires 12,800-step CONTROL, normal-start checkpoint')
        rows.append({'seed': seed, 'path': str(checkpoint.resolve()),
                     'sha256': observed, 'bytes': checkpoint.stat().st_size,
                     'train_steps': result['train_steps'], 'start_k': result['args']['start_k']})
    return rows


async def measure(net, envs, device, seed, cell, episodes, output):
    import torch
    from .model import batch, native_actions

    label, kind, variant, horizon = cell
    torch.manual_seed(seed + 15_000)
    started = time.monotonic()
    rows = []
    with (output / ('seed-%d-%s.jsonl' % (seed, label))).open('w', encoding='utf-8') as trace:
        for offset in range(0, episodes, len(envs)):
            active = envs[:min(len(envs), episodes - offset)]
            for env in active:
                env.max_steps = horizon
            observations = await asyncio.gather(*[
                env.reset(kind, task_seed(seed, offset + index), variant=variant)
                for index, env in enumerate(active)])
            instructions = [env.episode['instruction'] for env in active]
            initial_hashes = [hashlib.sha256(obs['overview'].tobytes()).hexdigest()
                              for obs in observations]
            alive = list(range(len(active)))
            histories = [[] for _ in active]
            successes = [False] * len(active)
            while alive:
                with torch.inference_mode():
                    actions, *_ = net.act(batch([observations[index] for index in alive],
                                               [instructions[index] for index in alive], device))
                decoded = native_actions(actions)
                for index, action in zip(alive, decoded):
                    histories[index].append(action)
                replies = await asyncio.gather(*[
                    active[index].step(action) for index, action in zip(alive, decoded)])
                following = []
                for index, (observation, _, done, info) in zip(alive, replies):
                    observations[index] = observation
                    if done:
                        successes[index] = info['success']
                    else:
                        following.append(index)
                alive = following
            for index, env in enumerate(active):
                row = {'seed': seed, 'cell': label, 'task_seed': env.episode['seed'],
                       'start_k': None, 'variant': variant, 'max_steps': horizon,
                       'success': successes[index], 'steps': env.t,
                       'instruction': instructions[index], 'spec': env.episode['spec'],
                       'html_sha256': hashlib.sha256(env.episode['html'].encode()).hexdigest(),
                       'initial_overview_sha256': initial_hashes[index],
                       'final_overview_sha256': hashlib.sha256(observations[index]['overview'].tobytes()).hexdigest(),
                       'terminal_state': env.state, 'actions': histories[index]}
                trace.write(json.dumps(row) + '\n')
                rows.append(row)
            trace.flush()
    successes = sum(row['success'] for row in rows)
    result = {'seed': seed, 'cell': label, 'episodes': episodes, 'successes': successes,
              'rate': successes / episodes, 'steps': sum(row['steps'] for row in rows),
              'max_steps': horizon, 'seconds': time.monotonic() - started,
              'trace_sha256': digest(trace.name)}
    print(json.dumps({'measurement': result}), flush=True)
    return result


async def run(args, checkpoints):
    import torch
    from playwright.async_api import async_playwright
    from .browser_env import BrowserEnv
    from .model import GymPolicy

    torch.set_num_threads(1)
    started = time.monotonic()
    output = Path(args.output)
    phase_output = output / args.phase
    phase_output.mkdir(parents=True, exist_ok=False)
    seeds = (11,) if args.phase == 'pilot' else SEEDS
    episodes = 8 if args.phase == 'pilot' else 100
    results = []
    stop_reason = None
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=['--disable-gpu'])
        envs = [BrowserEnv(browser) for _ in range(args.envs)]
        try:
            await asyncio.gather(*[env.start() for env in envs])
            net = GymPolicy().to(args.device)
            for seed in seeds:
                path = Path(args.checkpoints) / ('seed-' + str(seed)) / 'final.pt'
                net.load_state_dict(torch.load(path, map_location=args.device, weights_only=True))
                net.eval()
                weights_before = {name: value._version for name, value in net.state_dict(keep_vars=True).items()}
                for cell in CELLS:
                    results.append(await measure(net, envs, args.device, seed, cell,
                                                 episodes, phase_output))
                    save(phase_output / 'measurements.json', results)
                    if args.phase == 'wave' and unmeasurable_baseline(results[-1]):
                        stop_reason = '%s seed %d baseline below 10/100; fixed brief requires stop' % (cell[0], seed)
                        break
                if weights_before != {name: value._version for name, value in net.state_dict(keep_vars=True).items()}:
                    raise RuntimeError('evaluation changed model weights')
                if stop_reason:
                    break
        finally:
            await asyncio.gather(*[env.close() for env in envs])
            await browser.close()
    seconds = time.monotonic() - started
    receipt = {'phase': args.phase, 'seconds': seconds, 'measurements': results,
               'checkpoints': checkpoints, 'training_steps': 0, 'stochastic': True,
               'source_sha256': {path.name: digest(path) for path in Path(__file__).parent.glob('*.py')}}
    if args.phase == 'pilot':
        estimate = seconds * (100 / 8) * 3 * 1.5
        receipt.update({'conservative_full_wave_seconds': estimate, 'time_gate_passed': estimate <= 7200})
    else:
        receipt['verdicts'] = summarize(results)
        receipt['stop_reason'] = stop_reason
        receipt['stop_no_followup'] = any(
            'UNMEASURABLE' in (row['typing'], row['forms']) for row in receipt['verdicts'])
    save(phase_output / 'receipt.json', receipt)
    if verify_checkpoints(args.checkpoints) != checkpoints:
        raise RuntimeError('source checkpoints changed during evaluation')
    print(json.dumps({'receipt': receipt}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('pilot', 'wave'))
    parser.add_argument('--checkpoints', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--gpu-root', required=True)
    parser.add_argument('--envs', type=int, default=8)
    parser.add_argument('--device', default='cuda', choices=('cuda', 'cpu'))
    args = parser.parse_args()
    if args.envs < 1:
        parser.error('--envs must be positive')
    checkpoints = verify_checkpoints(args.checkpoints)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    save(output / 'checkpoint-verification.json', checkpoints)
    if args.phase == 'wave':
        pilot = json.loads((output / 'pilot/receipt.json').read_text())
        if not pilot['time_gate_passed'] or pilot['conservative_full_wave_seconds'] > 7200:
            raise RuntimeError('pilot exceeds two-hour gate; do not run wave')
    from .gpu_gate import Lease
    with Lease(Path(args.gpu_root)) if args.device == 'cuda' else nullcontext():
        asyncio.run(run(args, checkpoints))


if __name__ == '__main__':
    main()
