"""Search labels for game-world test SQ (addendum A24): the first move of the best of many random look-aheads on copies of the world.

  python -m game.search sq --out DIR [--workers 4] [--p-repeat 0.75] [--k 16] [--h 24] [--worlds N]
  python -m game.search report --out DIR [--json FILE]
  python -m game.search expert --out DIR [--workers 4] [--worlds 16] [--first 0] [--cap 1000]      (addendum A25, SE)
  python -m game.search expert-report --out DIR [--worlds 16]

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
EXPERT_RUN = 393          # practice run seed of the search expert's worlds (A25)
SE_PASS, SE_WRONG = 6.0, 4.5


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


def expert_episode(i, k=K, h=H, gamma=GAMMA, p_repeat=P_REPEAT, cap=None, explore=None, max_steps=None):
    """The search expert plays practice world i of run EXPERT_RUN: each step it searches a copy of the world (search_means, pick); with no
    signal it takes the sticky random policy's next action. The act rule is play.play's (A25): act stream default_rng([7, i]) draws one uniform
    number and one random action every step; below `explore` the step takes the random action instead. -> dict like play.play's episodes."""
    seed = play.practice_seed(EXPERT_RUN, 0, i)
    assert not play.is_sealed(seed), seed
    consts = play.load_constants()[0]
    cap = cap or consts['episode_cap']
    explore = consts['explore'] if explore is None else explore
    env = TextEnv(seed=seed, length=cap)
    env.reset()
    act, tail = np.random.default_rng([7, i]), np.random.default_rng([EXPERT_RUN, i, 10 ** 6])
    ep = dict(world=i, seed=seed, length=0, end=None, unlocks=[], sources=dict(search=0, fallback=0, explore=0), seconds=0.0)
    seen, last, done, t, t0 = set(), 0, False, 0, time.time()
    while not done and (max_steps is None or t < max_steps):
        j = pick(search_means(env, np.random.default_rng([EXPERT_RUN, i, t]), k, h, gamma, p_repeat))
        if j is not None:
            own, src = j, 'search'
        else:
            own, src = (last if tail.random() < p_repeat else int(tail.integers(play.N_ACTIONS))), 'fallback'
        last = own
        u, r = act.random(), int(act.integers(play.N_ACTIONS))
        if u < explore:
            own, src = r, 'explore'
        ep['sources'][src] += 1
        _, _, done, info = env.step(own)
        for name, count in sorted(info['achievements'].items()):
            if count > 0 and name not in seen:
                seen.add(name)
                ep['unlocks'].append((t, name))
        t += 1
    ep['length'], ep['seconds'] = t, round(time.time() - t0, 1)
    ep['end'] = 'dead' if info['inventory']['health'] <= 0 else 'cap'
    return ep


def run_expert_world(i, out, **kw):
    """expert_episode, written to OUT/expert-i.json (skipped if it exists)."""
    path = os.path.join(out, f'expert-{i}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    ep = expert_episode(i, **kw)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(ep, f)
    os.replace(tmp, path)
    return ep


def _expert_job(args):
    return run_expert_world(args[0], args[1], cap=args[2])


def reference_arms(worlds, first, cap):
    """The labeller and the random policy on the same worlds under the same act rule (act stream [7, i]). -> {arm: [episodes]}"""
    seeds = [play.practice_seed(EXPERT_RUN, 0, i) for i in range(first, first + worlds)]
    acts = [[7, i] for i in range(first, first + worlds)]
    explore = play.load_constants()[0]['explore']
    return dict(oracle=play.play(oracle.oracle_policy(), seeds, acts, explore, cap),
                random=play.play(None, seeds, acts, explore, cap))


def expert_verdict(mean):
    """A25 verdict from the search expert's mean unlocks a game on the practice worlds."""
    return 'pass' if mean >= SE_PASS else 'proved wrong' if mean <= SE_WRONG else 'no verdict'


def expert_report(out, worlds):
    from game import analyze
    eps = [json.load(open(os.path.join(out, f'expert-{i}.json'))) for i in range(worlds)]
    ref = json.load(open(os.path.join(out, 'ref.json')))
    u = {'search': [len(e['unlocks']) for e in eps], **{a: [len(e['unlocks']) for e in v] for a, v in ref.items()}}
    mean = {a: sum(v) / len(v) for a, v in u.items()}
    paired = {f'search_minus_{a}': analyze.boot_diff(u['search'], u[a]) for a in ('oracle', 'random')}
    names = sorted({n for e in eps for _, n in e['unlocks']})
    steps = sum(e['length'] for e in eps)
    src = {s: sum(e['sources'][s] for e in eps) / steps for s in ('search', 'fallback', 'explore')}
    return dict(worlds=worlds, mean_unlocks=mean, paired=paired, verdict=expert_verdict(mean['search']),
                achievements={n: sum(any(m == n for _, m in e['unlocks']) for e in eps) / worlds for n in names},
                mean_length=steps / worlds, ends=dict(Counter(e['end'] for e in eps)), sources_share=src,
                seconds_per_step=sum(e['seconds'] for e in eps) / steps)


def sq_expert(out, workers, worlds, first, cap):
    os.makedirs(out, exist_ok=True)
    ref_path = os.path.join(out, 'ref.json')
    if not os.path.exists(ref_path):
        ref = reference_arms(worlds, first, cap)
        with open(ref_path, 'w') as f:
            json.dump({a: [dict(unlocks=e['unlocks'], length=e['length']) for e in v] for a, v in ref.items()}, f)
    with mp.Pool(workers) as pool:
        for ep in pool.imap_unordered(_expert_job, [(i, out, cap) for i in range(first, first + worlds)], chunksize=1):
            print(f"world {ep['world']}: {len(ep['unlocks'])} unlocks, {ep['length']} steps, {ep['seconds']} s", flush=True)


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
    c = sub.add_parser('expert')
    c.add_argument('--out', required=True)
    c.add_argument('--workers', type=int, default=4)
    c.add_argument('--worlds', type=int, default=16)
    c.add_argument('--first', type=int, default=0)
    c.add_argument('--cap', type=int, default=None)
    d = sub.add_parser('expert-report')
    d.add_argument('--out', required=True)
    d.add_argument('--worlds', type=int, default=16)
    args = ap.parse_args(argv)
    if args.cmd == 'expert':
        sq_expert(args.out, args.workers, args.worlds, args.first, args.cap or play.load_constants()[0]['episode_cap'])
        print(json.dumps(expert_report(args.out, args.worlds), indent=1))
        return
    if args.cmd == 'expert-report':
        rep = expert_report(args.out, args.worlds)
        print(json.dumps(rep, indent=1))
        with open(os.path.join(args.out, 'expert-report.json'), 'w') as f:
            json.dump(rep, f, indent=1)
        return
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
