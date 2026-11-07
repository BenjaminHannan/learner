"""Daytime real-game HANDS evaluation and bounded CPU PPO practice."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import random
import time

os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np
import torch

from .bedwars_env import BedwarsEnv, BridgeServer, GOALS, NAMES, TruthReader
from .bedwars_tools import ROOT
from .model import GymPolicy, batch, native_actions


def save_checkpoint(policy, path):
    temporary = path.with_suffix('.pending')
    torch.save(policy.state_dict(), temporary)
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path, record):
    with path.open('a') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps(record), flush=True)


async def ready(bridge, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with bridge.lock:
            names = list(bridge.latest)
        if all(name in names for name in NAMES):
            print(json.dumps({'bridge_ready': names}), flush=True)
            return
        await asyncio.sleep(.5)
    raise TimeoutError('both owned Minecraft clients did not supply frames')


async def evaluate(policy, env, args, seed, phase):
    results = []
    for episode in range(args.eval_games):
        action_seed = 10000000 + seed * 10000 + episode
        torch.manual_seed(action_seed)
        observation = await env.reset(seed=action_seed)
        done = False
        latencies = []
        while not done:
            started = time.perf_counter()
            with torch.no_grad():
                actions, _, _, _ = policy.act(batch([observation], [env.episode['instruction']], 'cpu'))
            latencies.append((time.perf_counter() - started) * 1000)
            observation, _, done, info = await env.step(native_actions(actions)[0])
        row = {'phase': phase, 'policy_seed': seed, 'episode': episode, **info,
               'inference_ms_p50': float(np.percentile(latencies, 50)),
               'inference_ms_p95': float(np.percentile(latencies, 95))}
        results.append(row)
        emit(args.output / 'episodes.jsonl', row)
        if not info['game_finished']:
            raise RuntimeError('evaluation horizon expired before natural game end; not a full game')
    return {'phase': phase, 'seed': seed, 'games': len(results),
            'full_games': sum(row['game_finished'] for row in results),
            'goals': {goal: sum(row['goals'][goal] for row in results) / len(results) for goal in GOALS}}


async def practice(policy, env, args, seed):
    optimizer = torch.optim.Adam(policy.parameters(), lr=args.learning_rate)
    observation = await env.reset(seed=seed * 10000)
    started = time.monotonic()
    environment_steps, episodes, episode_reward = 0, 0, 0
    for update in range(args.updates):
        storage = []
        for _ in range(args.rollout):
            inputs = batch([observation], [env.episode['instruction']], 'cpu')
            with torch.no_grad():
                actions, log_probability, _, value = policy.act(inputs)
            observation, reward, done, info = await env.step(native_actions(actions)[0])
            storage.append((inputs, actions, log_probability, value, reward, done))
            environment_steps += 1
            episode_reward += reward
            if done:
                emit(args.output / 'training-episodes.jsonl', {'seed': seed, 'update': update,
                     'episode_reward': episode_reward, **info})
                episodes += 1
                episode_reward = 0
                observation = await env.reset(seed=seed * 10000 + episodes)
        with torch.no_grad():
            _, next_value = policy(*batch([observation], [env.episode['instruction']], 'cpu'))
        advantage = torch.zeros(1)
        advantages, returns = [], []
        for _, _, _, value, reward, done in reversed(storage):
            live = float(not done)
            delta = reward + .99 * next_value * live - value
            advantage = delta + .99 * .95 * live * advantage
            advantages.insert(0, advantage)
            returns.insert(0, advantage + value)
            next_value = value
        observations = tuple(torch.cat([row[0][index] for row in storage]) for index in range(4))
        actions = torch.cat([row[1] for row in storage])
        old_logp = torch.cat([row[2] for row in storage])
        advantages = torch.cat(advantages)
        returns = torch.cat(returns)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        losses = []
        for _ in range(2):
            _, logp, entropy, values = policy.act(observations, actions)
            ratio = (logp - old_logp).exp()
            loss = -torch.minimum(ratio * advantages, ratio.clamp(.8, 1.2) * advantages).mean()
            loss += .5 * (values - returns).square().mean() - .01 * entropy.mean()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), .5)
            optimizer.step()
            losses.append(float(loss.detach()))
        checkpoint = save_checkpoint(policy, args.output / ('seed-%d-latest.pt' % seed))
        state_path = args.output / ('seed-%d-training-state.pending' % seed)
        torch.save({'policy': policy.state_dict(), 'optimizer': optimizer.state_dict(),
                    'torch_rng': torch.get_rng_state(), 'numpy_rng': np.random.get_state(),
                    'python_rng': random.getstate(), 'update': update + 1,
                    'environment_steps': environment_steps, 'seed': seed}, state_path)
        state_path.replace(args.output / ('seed-%d-training-state.pt' % seed))
        emit(args.output / 'curve.jsonl', {'seed': seed, 'update': update + 1,
             'environment_steps': environment_steps, 'episodes': episodes, 'loss': losses,
             'elapsed_seconds': time.monotonic() - started, 'checkpoint_sha256': checkpoint,
             'rollout_reward': sum(row[4] for row in storage), 'device': 'cpu'})
        if time.monotonic() - started >= args.practice_minutes * 60:
            break


async def run(args):
    torch.set_num_threads(2)
    args.output.mkdir(parents=True, exist_ok=False)
    configuration = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    fixed_plan = None
    if args.plan:
        data = args.plan.read_bytes()
        plan = json.loads(data)
        if plan.get('source') != 'glim' or not isinstance(plan.get('instruction'), str) or not plan['instruction'].strip():
            raise ValueError('fixed plan must be a retained actual Glim response')
        fixed_plan = {**plan, 'source': 'glim_cached', 'plan_sha256': hashlib.sha256(data).hexdigest(),
                      'reason': 'frozen slow-brain plan for paired evaluation'}
        (args.output / 'fixed-plan.json').write_bytes(data)
    (args.output / 'run.json').write_text(json.dumps({**configuration,
        'policy': 'unchanged HANDS GymPolicy, ' + ('preselected practice checkpoint' if args.mode == 'live' else 'fresh initialization'), 'device': 'cpu',
        'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() if args.checkpoint else None,
        'started_ms': int(time.time() * 1000), 'truth_directory': str(ROOT / 'truth')}, indent=2))
    bridge = BridgeServer(args.output)
    truth = TruthReader()
    env = BedwarsEnv(bridge, truth, args.output, args.max_steps, args.step_seconds, fixed_plan)
    try:
        await ready(bridge)
        if args.mode == 'live':
            if args.checkpoint is None or len(args.seeds) != 1:
                raise ValueError('live play requires one preselected seed and a HANDS checkpoint')
            policy = GymPolicy().eval()
            policy.load_state_dict(torch.load(args.checkpoint, map_location='cpu', weights_only=True))
            result = await evaluate(policy, env, args, args.seeds[0], 'live')
            (args.output / 'results.json').write_text(json.dumps([result], indent=2))
            return
        if args.mode == 'smoke':
            policy = GymPolicy().eval()
            observation = await env.reset(seed=0)
            deadline = time.monotonic() + args.smoke_seconds
            while time.monotonic() < deadline:
                with torch.no_grad():
                    actions, _, _, _ = policy.act(batch([observation], [env.episode['instruction']], 'cpu'))
                observation, _, done, info = await env.step(native_actions(actions)[0])
                if done:
                    emit(args.output / 'episodes.jsonl', {'phase': 'smoke', **info})
                    observation = await env.reset(seed=0)
            return
        summaries = []
        for seed in args.seeds:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            policy = GymPolicy()
            initial_hash = save_checkpoint(policy, args.output / ('seed-%d-initial.pt' % seed))
            emit(args.output / 'checkpoints.jsonl', {'seed': seed, 'phase': 'initial', 'sha256': initial_hash})
            summaries.append(await evaluate(policy.eval(), env, args, seed, 'baseline'))
            await practice(policy.train(), env, args, seed)
            final_hash = save_checkpoint(policy, args.output / ('seed-%d-final.pt' % seed))
            emit(args.output / 'checkpoints.jsonl', {'seed': seed, 'phase': 'final', 'sha256': final_hash})
            summaries.append(await evaluate(policy.eval(), env, args, seed, 'final'))
            (args.output / 'results.json').write_text(json.dumps(summaries, indent=2))
    finally:
        await env.close()
        bridge.close()
        (args.output / 'bridge-errors.json').write_text(json.dumps(bridge.errors, indent=2))
        truth.refresh()
        (args.output / 'observed-matches.json').write_text(json.dumps({key: len(value) for key, value in truth.matches.items()}))
        recorded = args.output / 'truth'
        recorded.mkdir(exist_ok=True)
        for path in truth.directory.glob('match-*.jsonl'):
            if path.stem in truth.matches:
                (recorded / path.name).write_bytes(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smoke', 'practice', 'live'], default='smoke')
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[11, 22, 33])
    parser.add_argument('--eval-games', type=int, default=8)
    parser.add_argument('--updates', type=int, default=64)
    parser.add_argument('--rollout', type=int, default=16)
    parser.add_argument('--max-steps', type=int, default=1200)
    parser.add_argument('--step-seconds', type=float, default=.1)
    parser.add_argument('--learning-rate', type=float, default=.0001)
    parser.add_argument('--practice-minutes', type=float, default=15)
    parser.add_argument('--smoke-seconds', type=float, default=60)
    args = parser.parse_args()
    if args.rollout < 2 or args.practice_minutes * len(args.seeds) > 60:
        raise ValueError('practice must be bounded to at most one hour total')
    asyncio.run(run(args))


if __name__ == '__main__':
    main()
