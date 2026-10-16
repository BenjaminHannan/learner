"""Step 1: GW-L 64k checkpoint plays practice games with the A26 iteration play rule (game.imitate.play_games, game.play.move_policy 'sample' T = 1,
explore 0.10, cap 1000, worlds game.play.practice_seed(run_seed, day, i), act stream [9, run_seed, day, i]).
Policy = load_model(merged checkpoint), no add-on: the model arm of game.score, so the same function of the view as the A23 sealed score
(score-sample.json: picker sample, T 1.0). imitate.play_iteration is the same loop with the add-on switched on.
Besides the imitate game format, each game also carries `answers` (the model's word each step) and `sources` (own / explore / invalid), rebuilt
from the recorded calls and the act streams (checked against the executed moves). The 17 log-probs of every step go to play-d{d}.lp.npz.

python play_run.py SEED [--root DIR] [--per-chunk 100] [--days 0 1 2 3] [--cap 1000] [--threads 2]"""
import argparse
import gzip
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from game import imitate, play
from game.crafter_text import parse_action


def play_chunk(m, run_seed, day, per_chunk, cap, explore, bs=64):
    seeds = [play.practice_seed(run_seed, day, i) for i in range(per_chunk)]
    acts = [[imitate.ACT_TAG, run_seed, day, i] for i in range(per_chunk)]
    pol = play.move_policy(m, 'sample', bs=bs, temp=1.0)
    lps, calls = [], []
    orig = play.move_logprobs

    def rec(m_, prompts, bs_=64):          # same function, only keeps the output (move_policy looks the name up in game.play at call time)
        lp = orig(m_, prompts, bs_)
        lps.append(lp)
        return lp

    def wrapped(prompts, us):
        ans = pol(prompts, us)
        calls.append(ans)
        return ans
    wrapped.samples = True
    play.move_logprobs = rec
    try:
        games = imitate.play_games(wrapped, seeds, acts, explore, cap)
    finally:
        play.move_logprobs = orig
    assert len(calls) == len(lps) == max(g['length'] for g in games)
    lp_per_game = [[] for _ in games]
    for t, (ans, lp) in enumerate(zip(calls, lps)):
        live = [i for i, g in enumerate(games) if g['length'] > t]   # play_games keeps `live` in ascending game order
        assert len(live) == len(ans) == len(lp)
        for j, i in enumerate(live):
            games[i].setdefault('answers', []).append(ans[j])
            lp_per_game[i].append(lp[j])
    for g, a in zip(games, acts):
        rng = np.random.default_rng(a)
        src = []
        for t in range(g['length']):
            u, r = rng.random(), int(rng.integers(play.N_ACTIONS))
            p = parse_action(g['answers'][t])
            s, act = ('invalid', r) if p is None else ('explore', r) if u < explore else ('own', p)
            assert act == g['actions'][t], (g['seed'], t)
            src.append(s)
        g['sources'], g['act_seed'] = src, a
    return games, np.concatenate([np.asarray(x, dtype=np.float32) for x in lp_per_game]) if games else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seed', type=int)
    ap.add_argument('--root', default=common.Z)
    ap.add_argument('--per-chunk', type=int, default=imitate.GAMES_PER_CHUNK)
    ap.add_argument('--days', type=int, nargs='+', default=list(common.DAYS))
    ap.add_argument('--cap', type=int, default=None)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    from custom_io.models import load_model
    run_seed = common.RUN_SEED[a.seed]
    assert run_seed in (398, 399) and not play.is_sealed(play.practice_seed(run_seed, 0, 0))
    cons = play.load_constants()[0]
    cap, explore = a.cap or cons['episode_cap'], cons['explore']
    out = common.outdir(a.seed, a.root)
    m = load_model(common.ckpt(a.seed)).eval()
    timing = []
    for d in a.days:
        path = f'{out}/play-d{d}.json.gz'
        if os.path.exists(path):
            print('have', path, flush=True)
            continue
        t0 = time.time()
        games, lp = play_chunk(m, run_seed, d, a.per_chunk, cap, explore)
        secs = time.time() - t0
        steps = sum(g['length'] for g in games)
        np.savez_compressed(f'{out}/play-d{d}.lp.npz', lp=lp, lengths=np.array([g['length'] for g in games]))
        tmp = path + '.tmp'
        with gzip.open(tmp, 'wt') as f:
            json.dump(games, f)
        os.replace(tmp, path)
        timing.append(dict(day=d, games=len(games), steps=steps, seconds=round(secs, 1), sec_per_game=round(secs / len(games), 2),
                           ms_per_step=round(1000 * secs / steps, 2)))
        print(timing[-1], flush=True)
        with open(f'{out}/play-timing-{d}.json', 'w') as f:
            json.dump(timing[-1], f)


if __name__ == '__main__':
    main()
