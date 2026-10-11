"""Sealed scoring of Crafter arms (game-world test GW-S). The only module that plays sealed worlds.

  python -m game.score --arm model|random|ppo [--ckpt CKPT] [--gate GATE] [--picker greedy|top|sample] [--ppo-picker argmax|sample] --out OUT.json [--first 0] [--worlds 100] [--threads 2]

Worlds are SEALED_BASE + k for k in first .. first + worlds - 1, one episode each (the random arm: three, act seeds
[a, k] for a = 0, 1, 2, reported as the per-world mean). Model arm: act seed [7, k], explore from game/constants.json.
PPO arm: act seed [7, k], explore from game/constants.json, policy from game.ppo.load_policy(ckpt) (a callable prompts -> answers, as play wants).
--picker sample: the model arm draws a move by softmax of those log-probs. --ppo-picker sample: the PPO arm draws from its own
action probabilities. Samples use the episode's extra stream (play.play `samples`). --picker top: the model arm plays the move with the highest log-probability among the 17 words (play.move_policy); greedy
(default) is the model's own written answer. --gate is recorded only (the sealed score is of the model alone; routing is decided in game.analyze).
"""
import argparse
import json
import math
import time

import torch
from crafter import constants as crafter_constants

from game import play

ACH = list(crafter_constants.achievements)
assert len(ACH) == play.ACHIEVEMENTS


def crafter_score(rates):
    """Crafter score, percent: exp(mean over achievements of ln(1 + s_i)) - 1, s_i = success rate in percent."""
    return math.exp(sum(math.log(1 + 100.0 * rates[a]) for a in ACH) / len(ACH)) - 1


def summarize(arm, ckpt, per_world, cap, seconds, gate=None, picker='greedy', ppo_picker=None):
    n = len(per_world)
    # choice: per-world 'ach_rate' is the share of that world's episodes that unlocked it (0/1 unless random arm)
    share = {a: sum(w['ach_rate'][a] for w in per_world) / n for a in ACH}
    tot = {k: sum(w['sources'][k] for w in per_world) for k in ('own', 'explore', 'invalid')}
    steps = max(sum(tot.values()), 1)
    mean_u = sum(w['n_unlocks'] for w in per_world) / n
    return dict(arm=arm, ckpt=ckpt, gate=gate, picker=picker, ppo_picker=ppo_picker, worlds=n, cap=cap, per_world=per_world,
                share={a: round(100 * s, 4) for a, s in share.items()}, mean_unlocks=mean_u,
                progress=100.0 * mean_u / play.ACHIEVEMENTS, crafter_score=crafter_score(share),
                mean_length=sum(w['length'] for w in per_world) / n,
                sources_share={k: v / steps for k, v in tot.items()}, seconds=round(seconds, 1))


def world_record(seed, eps):
    k = len(eps)
    rate = {a: sum(any(n == a for _, n in e['unlocks']) for e in eps) / k for a in ACH}
    src = {s: sum(e['sources'][s] for e in eps) for s in ('own', 'explore', 'invalid')}
    return dict(seed=seed, unlocks=([[t, n] for t, n in eps[0]['unlocks']] if k == 1
                 else [[[t, n] for t, n in e['unlocks']] for e in eps]), n_unlocks=sum(len(e['unlocks']) for e in eps) / k,
                length=sum(e['length'] for e in eps) / k, end=eps[0]['end'] if k == 1 else [e['end'] for e in eps],
                sources=src, ach_rate=rate)


def run(arm, ckpt, first, worlds, cap, gate=None, picker='greedy', ppo_picker=None):
    t0 = time.time()
    seeds = [play.SEALED_BASE + k for k in range(first, first + worlds)]
    assert all(play.is_sealed(s) for s in seeds), 'worlds outside the sealed range'
    if arm == 'random':
        reps = 3
        eps = play.play(None, [s for s in seeds for _ in range(reps)], [[a, k] for k in range(first, first + worlds)
                                                                        for a in range(reps)],
                        0.0, cap, allow_sealed=True)
        groups = [eps[i * reps:(i + 1) * reps] for i in range(worlds)]
    else:
        if arm == 'model':
            from custom_io.models import load_model
            m = load_model(ckpt).eval()
            pol, explore = play.picked_policy(m, picker), play.load_constants()[0]['explore']
        else:
            from game.ppo import load_policy  # lazy: written by another helper
            pol, explore = load_policy(ckpt, sample=ppo_picker == 'sample'), play.load_constants()[0]['explore']
        eps = play.play(pol, seeds, [[7, k] for k in range(first, first + worlds)], explore, cap, allow_sealed=True)
        groups = [[e] for e in eps]
    per_world = [world_record(s, g) for s, g in zip(seeds, groups)]
    return summarize(arm, ckpt, per_world, cap, time.time() - t0, gate, picker if arm == 'model' else None,
                     ppo_picker if arm == 'ppo' else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Score one arm on the sealed Crafter worlds.')
    ap.add_argument('--arm', required=True, choices=['model', 'random', 'ppo'])
    ap.add_argument('--ckpt')
    ap.add_argument('--gate')
    ap.add_argument('--picker', default='greedy', choices=['greedy', 'top', 'sample'])
    ap.add_argument('--ppo-picker', default='argmax', choices=['argmax', 'sample'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--first', type=int, default=0)
    ap.add_argument('--worlds', type=int, default=100)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--cap', type=int, default=None, help=argparse.SUPPRESS)   # tests only; default: constants.json
    a = ap.parse_args(argv)
    assert a.arm == 'random' or a.ckpt, '--ckpt is required for the model and ppo arms'
    assert a.picker == 'greedy' or a.arm == 'model', '--picker top / sample is for the model arm'
    assert 0 <= a.first and a.first + a.worlds <= play.SEALED_N
    torch.set_num_threads(a.threads)
    cap = a.cap or play.load_constants()[0]['episode_cap']
    res = run(a.arm, a.ckpt, a.first, a.worlds, cap, a.gate, a.picker, a.ppo_picker)
    with open(a.out, 'w') as f:
        json.dump(res, f, indent=1)
    print(a.arm, 'worlds', res['worlds'], 'unlocks/ep', round(res['mean_unlocks'], 3), 'progress', round(res['progress'], 2),
          'crafter score', round(res['crafter_score'], 2), 'len', round(res['mean_length'], 1), flush=True)


if __name__ == '__main__':
    main()
