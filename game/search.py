"""Search labels for game-world test SQ (addendum A24): the first move of the best of many random look-aheads on copies of the world.

  python -m game.search sq --out DIR [--workers 4] [--p-repeat 0.75] [--k 16] [--h 24] [--worlds N]
  python -m game.search report --out DIR [--json FILE]

A decision state is a live TextEnv. For each of the 17 first moves, K rollouts run on fresh deep copies (each given a fresh random future by
re-seeding the shared world.random): take the first move, then H - 1 more steps with a sticky random policy (repeat the last action with
chance P_REPEAT, else a uniform word). Return = sum of GAMMA^t * the game's reward. The label is the best first move when the signal rule
holds (pick), else none. Nothing about the view text, trees, water or cows is used; the oracle (game.oracle) only scores the test.
Practice worlds only (run seed 392); never a sealed world.
"""
import argparse
import copy
import json
import multiprocessing as mp
import os
import time
from collections import Counter

import crafter
import numpy as np

from game import oracle, play
from game.crafter_text import TextEnv

K, H, GAMMA, P_REPEAT = 16, 24, 0.95, 0.75
MIN_BEST, MIN_GAP = 0.20, 0.10
RUN_SEED = 392
CHANCE_ORACLE = 0.5       # as game.probe.CHANCE_ORACLE: the states are the probe's states
SAMPLE_FROM, SAMPLE_EVERY = 3, 4
MIN_WORLDS, MIN_NAV = 48, 300
SQ0_BAR, SQ1_PASS, SQ1_WRONG, SQ2_PASS, SQ2_WRONG = 0.80, 0.25, 0.10, 0.60, 0.35


def pick(means):
    """17 mean returns -> index of the labelled first move, or None when the signal rule fails (A24: best >= MIN_BEST and
    best - mean of all >= MIN_GAP). Ties go to the lowest index."""
    best = max(means)
    if best < MIN_BEST or best - sum(means) / len(means) < MIN_GAP:
        return None
    return means.index(best)


def rollout_return(env, first, rng, h=H, gamma=GAMMA, p_repeat=P_REPEAT):
    """Discounted game reward of one rollout from a copy of env that starts with action `first`. env is not changed."""
    e = copy.deepcopy(env)
    e._world.random.seed(int(rng.integers(2 ** 31 - 1)))
    total, disc, a = 0.0, 1.0, first
    for _ in range(h):
        _, r, done, _ = crafter.Env.step(e, a)
        total += disc * r
        disc *= gamma
        if done:
            break
        if rng.random() >= p_repeat:
            a = int(rng.integers(play.N_ACTIONS))
    return total


def search_means(env, rng, k=K, h=H, gamma=GAMMA, p_repeat=P_REPEAT):
    """Mean return of each of the 17 first moves over k rollouts (env is not changed)."""
    return [sum(rollout_return(env, a, rng, h, gamma, p_repeat) for _ in range(k)) / k for a in range(play.N_ACTIONS)]


def run_world(i, out, k=K, h=H, gamma=GAMMA, p_repeat=P_REPEAT, cap=None, every=SAMPLE_EVERY):
    """One practice world of the measurement: the probe's mixed policy plays it; at steps SAMPLE_FROM, +every, ... the state is searched.
    Writes OUT/world-i.json (skipped if it exists, so a restarted run continues). -> the list of decision dicts."""
    path = os.path.join(out, f'world-{i}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)['decisions']
    seed = play.practice_seed(RUN_SEED, 0, i)
    assert not play.is_sealed(seed), seed
    cap = cap or play.load_constants()[0]['episode_cap']
    env = TextEnv(seed=seed, length=cap)
    prng = np.random.default_rng(seed)
    view, done, t, rows, t0 = env.reset(), False, 0, [], time.time()
    while not done:
        word, reason = oracle.label(view)
        if t >= SAMPLE_FROM and (t - SAMPLE_FROM) % every == 0:
            s0 = time.time()
            means = search_means(env, np.random.default_rng([RUN_SEED, i, t]), k, h, gamma, p_repeat)
            j = pick(means)
            rows.append(dict(world=i, step=t, view=view, oracle=word, reason=reason, means=[round(m, 4) for m in means],
                             search=None if j is None else play.WORDS[j], seconds=round(time.time() - s0, 2)))
        u, r = prng.random(), int(prng.integers(play.N_ACTIONS))
        view, _, done, _ = env.step(play.WORDS.index(word) if u < CHANCE_ORACLE else r)
        t += 1
    res = dict(world=i, seed=seed, length=t, k=k, h=h, gamma=gamma, p_repeat=p_repeat, seconds=round(time.time() - t0, 1), decisions=rows)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(res, f)
    os.replace(tmp, path)
    return rows


def _job(args):
    return run_world(*args)


def stats(rows):
    """Coverage, agreement and the A24 verdicts for a list of decision dicts."""
    by = {}
    for reason in ('sleep', 'act', 'nav', 'craft', 'wander'):
        rs = [r for r in rows if r['reason'] == reason]
        lab = [r for r in rs if r['search'] is not None]
        agree = sum(r['search'] == r['oracle'] for r in lab)
        fixed = Counter(r['oracle'] for r in lab).most_common(1)
        by[reason] = dict(views=len(rs), labelled=len(lab), coverage=len(lab) / len(rs) if rs else None,
                          agree=agree, agreement=agree / len(lab) if lab else None,
                          best_fixed_word=fixed[0][0] if fixed else None, best_fixed_agreement=fixed[0][1] / len(lab) if lab else None)
    s = [r for r in rows if r['reason'] in ('nav', 'act')]
    lab = [r for r in s if r['search'] is not None]
    by['S'] = dict(views=len(s), labelled=len(lab), coverage=len(lab) / len(s) if s else None,
                   agreement=sum(r['search'] == r['oracle'] for r in lab) / len(lab) if lab else None)
    sq0, sq1, sq2 = by['act']['agreement'], by['nav']['coverage'], by['nav']['agreement']
    return dict(by_reason=by, decisions=len(rows), SQ0=sq0, SQ1=sq1, SQ2=sq2, verdict=verdict(sq0, sq1, sq2),
                seconds_per_decision=sum(r['seconds'] for r in rows) / len(rows) if rows else None,
                search_words=dict(sorted(Counter(r['search'] for r in rows if r['search'] is not None).items())))


def verdict(sq0, sq1, sq2):
    """A24 verdict from SQ-0 (instrument check), SQ-1 (nav coverage) and SQ-2 (nav agreement)."""
    if sq0 is None or sq1 is None:
        return 'incomplete'
    if sq0 < SQ0_BAR:
        return 'instrument check failed (SQ-0)'
    if sq2 is None:
        return 'proved wrong' if sq1 < SQ1_WRONG else 'no verdict'
    if sq1 < SQ1_WRONG or sq2 < SQ2_WRONG:
        return 'proved wrong'
    if sq1 >= SQ1_PASS and sq2 >= SQ2_PASS:
        return 'pass'
    return 'no verdict'


def load_all(out):
    rows, worlds = [], 0
    for name in sorted(os.listdir(out), key=lambda n: (len(n), n)):
        if name.startswith('world-') and name.endswith('.json'):
            with open(os.path.join(out, name)) as f:
                rows += json.load(f)['decisions']
            worlds += 1
    return rows, worlds


def sq(out, workers, k, h, p_repeat, worlds=None):
    """Worlds 0, 1, 2, ... in rounds of `workers` until both MIN_WORLDS worlds and MIN_NAV nav views are searched (or exactly `worlds`)."""
    os.makedirs(out, exist_ok=True)
    done = 0
    with mp.Pool(workers) as pool:
        while True:
            pool.map(_job, [(i, out, k, h, GAMMA, p_repeat) for i in range(done, done + workers)], chunksize=1)
            done += workers
            rows, n = load_all(out)
            nav = sum(r['reason'] == 'nav' for r in rows)
            print(f'worlds {n} decisions {len(rows)} nav {nav}', flush=True)
            if (worlds is not None and done >= worlds) or (worlds is None and done >= MIN_WORLDS and nav >= MIN_NAV):
                break
    return load_all(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Search labels (A24, SQ).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('sq')
    a.add_argument('--out', required=True)
    a.add_argument('--workers', type=int, default=4)
    a.add_argument('--k', type=int, default=K)
    a.add_argument('--h', type=int, default=H)
    a.add_argument('--p-repeat', type=float, default=P_REPEAT)
    a.add_argument('--worlds', type=int, default=None, help='exactly this many worlds (a multiple of --workers), ignoring the nav minimum')
    b = sub.add_parser('report')
    b.add_argument('--out', required=True)
    b.add_argument('--json', default=None)
    args = ap.parse_args(argv)
    if args.cmd == 'sq':
        sq(args.out, args.workers, args.k, args.h, args.p_repeat, args.worlds)
    rows, worlds = load_all(args.out)
    st = stats(rows)
    st['worlds'] = worlds
    print(json.dumps({k: v for k, v in st.items() if k != 'by_reason'}, indent=1))
    for reason, d in st['by_reason'].items():
        print(reason, json.dumps(d))
    path = getattr(args, 'json', None) or os.path.join(args.out, 'sq.json')
    with open(path, 'w') as f:
        json.dump(st, f, indent=1)


if __name__ == '__main__':
    main()
