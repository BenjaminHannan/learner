"""Playing Crafter worlds with a policy, all episodes in lockstep (game-world test GW-S).

Design and sealed marks: /mnt/project-files/game-world/PLAN-AND-MARKS-2026-10-10.md (sec. 4, the act rule).

The act rule (the same for the mode, its quiz and every scored arm that uses it): each step the policy answers one word
per world. With probability `explore`, or when the answer is not one of the 17 action words, the step takes a random
action instead. Each episode has its own random stream, np.random.default_rng(act_seed); every step draws one uniform
number and one random action whether or not they are used, so the stream depends only on the step count.

World seeds: practice worlds come from practice_seed(); the sealed worlds (SEALED_BASE ... SEALED_BASE + SEALED_N - 1)
are ours, for scoring only. Only game/score.py may pass sealed seeds (allow_sealed=True).
"""
import json
import os

import numpy as np

from game.crafter_text import ACTIONS, TextEnv, parse_action

HERE = os.path.dirname(os.path.abspath(__file__))
CONST_PATH = os.path.join(HERE, 'constants.json')
SEALED_BASE, SEALED_N = 7_000_000, 100
N_ACTIONS = len(ACTIONS)
WORDS = [w for _, w in ACTIONS]
ACHIEVEMENTS = 22


def practice_seed(run_seed, day, i):
    """World seed of practice world i on day `day` (day 0 = the quiz) of run `run_seed`. Disjoint across runs and days."""
    assert 0 <= day < 100 and 0 <= i < 100 and 0 <= run_seed < 400, (run_seed, day, i)
    return 1_000_000 + run_seed * 10_000 + day * 100 + i


def is_sealed(seed):
    return SEALED_BASE <= seed < SEALED_BASE + SEALED_N


def load_constants():
    with open(CONST_PATH, 'rb') as f:
        raw = f.read()
    return json.loads(raw), raw


def play(policy, seeds, act_seeds, explore, cap, log_steps=False, allow_sealed=False):
    """One episode per world seed, all in lockstep, at most `cap` steps each.

    policy(prompts) -> list of answer strings (one per prompt), or None for the random arm (every step random).
    act_seeds[i] seeds episode i's random stream (an int or a list of ints, as numpy's default_rng takes).
    -> list of dicts, one per episode: seed, act_seed, length, end ('dead' or 'cap'), unlocks [(step, name)],
       sources {own, explore, invalid} counts, and with log_steps also steps [(prompt, action word, source, reward)] and final_health.
       An unlock at step t is caused by the action of step t (crafter's reward for that step)."""
    assert len(seeds) == len(act_seeds)
    if not allow_sealed:
        assert not any(is_sealed(s) for s in seeds), 'a sealed world outside game/score.py'
    envs = [TextEnv(seed=int(s), length=int(cap)) for s in seeds]
    rngs = [np.random.default_rng(a) for a in act_seeds]
    texts = [e.reset() for e in envs]
    eps = [dict(seed=int(s), act_seed=a, length=0, end=None, unlocks=[], sources=dict(own=0, explore=0, invalid=0),
                steps=[] if log_steps else None) for s, a in zip(seeds, act_seeds)]
    seen = [set() for _ in envs]
    prompts = list(texts)
    live = list(range(len(envs)))
    while live:
        answers = policy([texts[i] for i in live]) if policy is not None else [None] * len(live)
        assert len(answers) == len(live)
        nxt = []
        for i, ans in zip(live, answers):
            u, r = rngs[i].random(), int(rngs[i].integers(N_ACTIONS))
            a = parse_action(ans) if policy is not None else None
            if policy is None:
                src, act = 'explore', r
            elif a is None:
                src, act = 'invalid', r
            elif u < explore:
                src, act = 'explore', r
            else:
                src, act = 'own', a
            ep = eps[i]
            prompts[i] = texts[i]
            t = ep['length']
            ep['sources'][src] += 1
            texts[i], reward, done, info = envs[i].step(act)
            if log_steps:
                ep['steps'].append((prompts[i], WORDS[act], src, float(reward)))
            ep['length'] = t + 1
            for name, count in sorted(info['achievements'].items()):
                if count > 0 and name not in seen[i]:
                    seen[i].add(name)
                    ep['unlocks'].append((t, name))
            if done:
                ep['final_health'] = info['inventory']['health']
                ep['end'] = 'dead' if info['inventory']['health'] <= 0 else 'cap'
            else:
                nxt.append(i)
        live = nxt
    return eps


def progress(eps):
    """Mean unlocks per episode, as percent of the 22 achievements (Crafter 'progression')."""
    return 100.0 * sum(len(e['unlocks']) for e in eps) / (ACHIEVEMENTS * max(len(eps), 1))


def model_policy(m, bs=64):
    """The model's answers (greedy, calculator on) as a policy. The add-on, if any, is switched by the caller."""
    from domain.mode import greedy

    def pol(prompts):
        return [ans for _, ans in greedy(m, prompts, bs=bs)]
    return pol
