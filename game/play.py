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
import torch

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
    A policy with attribute `samples` true is called policy(prompts, us) instead: us[j] is one uniform number drawn each step from
    episode j's extra stream np.random.default_rng([*act_seed, 1]) (made only then, so other results are unchanged).
    act_seeds[i] seeds episode i's random stream (an int or a list of ints, as numpy's default_rng takes).
    -> list of dicts, one per episode: seed, act_seed, length, end ('dead' or 'cap'), unlocks [(step, name)],
       sources {own, explore, invalid} counts, and with log_steps also steps [(prompt, action word, source, reward)] and final_health.
       An unlock at step t is caused by the action of step t (crafter's reward for that step)."""
    assert len(seeds) == len(act_seeds)
    if not allow_sealed:
        assert not any(is_sealed(s) for s in seeds), 'a sealed world outside game/score.py'
    envs = [TextEnv(seed=int(s), length=int(cap)) for s in seeds]
    rngs = [np.random.default_rng(a) for a in act_seeds]
    samples = getattr(policy, 'samples', False)
    srngs = [np.random.default_rng([*np.atleast_1d(a).tolist(), 1]) for a in act_seeds] if samples else None
    texts = [e.reset() for e in envs]
    eps = [dict(seed=int(s), act_seed=a, length=0, end=None, unlocks=[], sources=dict(own=0, explore=0, invalid=0),
                steps=[] if log_steps else None) for s, a in zip(seeds, act_seeds)]
    seen = [set() for _ in envs]
    prompts = list(texts)
    live = list(range(len(envs)))
    while live:
        if policy is None:
            answers = [None] * len(live)
        elif samples:
            answers = policy([texts[i] for i in live], [srngs[i].random() for i in live])
        else:
            answers = policy([texts[i] for i in live])
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


def _chunk_logprobs(m, chunk, ids, msk, n):
    """Torch [len(chunk), 17] log-probs of the 17 words for one chunk of prompts. Differentiable when called with grad enabled
    (and the add-on's parameters require grad); move_logprobs calls it under no_grad. One body for both, so they cannot differ."""
    from custom_io.data import Dataset, collate, to_device
    ds = Dataset([{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                  for i, p in enumerate(chunk)], m.vocab, strict=False)
    batch = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
    state = m.state_of(m.run(batch))
    R, Xt, idt, vis = state[:4]
    X, xm = m.read(batch, talker=True)
    Xc, mc = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1)
    idc = torch.cat([batch['prompt_ids'], idt.long()], 1)
    p, _ = m.gen_copy(R, Xc, mc, idc)                               # [B, 9, V]
    lp = p[:, :n].clamp_min(1e-12).log()                            # [B, n, V]
    g = lp[:, torch.arange(n)[None, :].expand(N_ACTIONS, -1), ids]  # [B, 17, n]: lp[b, k, ids[j, k]]
    return (g * msk).sum(-1)


def _words(m):
    from custom_io.data import EOS
    n = max(len(w) for w in WORDS) + 1
    ids = torch.zeros(N_ACTIONS, n, dtype=torch.long)
    msk = torch.zeros(N_ACTIONS, n, dtype=torch.bool)
    for j, w in enumerate(WORDS):
        t = m.vocab.encode(w[::-1]) + [EOS]
        ids[j, :len(t)], msk[j, :len(t)] = torch.tensor(t), True
    return ids, msk, n


def move_logprobs_grad(m, prompts):
    """As move_logprobs for ONE chunk of prompts (the caller sets the chunk size), but with gradients: torch float32 [len(prompts), 17]
    whose graph reaches the add-on's parameters (the base model is frozen). Call it with grad enabled; the model is put in eval mode."""
    ids, msk, n = _words(m)
    m.eval()
    return _chunk_logprobs(m, prompts, ids, msk, n)


def move_logprobs(m, prompts, bs=64):
    """Log-probability of each of the 17 move words as the complete answer -> float64 array [len(prompts), 17].
    Same readout as m.talk (custom_io/models/tool.py:390-402): GEN registers hold the answer units-first, one distribution per
    register from m.gen_copy; a word scores sum of log p(register k = letter k of the reversed word) + log p(register len = EOS).
    The registers are parallel (no feedback), so teacher forcing needs one run per prompt; the 17 words are scored together.
    The scoring itself is _chunk_logprobs, shared with move_logprobs_grad (the training version)."""
    ids, msk, n = _words(m)
    m.eval()
    out = []
    for s in range(0, len(prompts), bs):
        with torch.no_grad():
            out.append(_chunk_logprobs(m, prompts[s:s + bs], ids, msk, n).double().numpy())
    return np.concatenate(out) if out else np.zeros((0, N_ACTIONS))


def softmax_pick(scores, u, temp=1.0):
    """Index drawn from softmax(scores / temp) by inverse CDF with uniform u in [0, 1). temp 1.0 is the plain softmax (exactly)."""
    p = np.exp((scores - scores.max()) / temp)
    c = np.cumsum(p)
    return int(min(np.searchsorted(c, u * c[-1], side='right'), len(p) - 1))


def move_policy(m, picker, bs=64, temp=1.0):
    """The model's own odds over the 17 moves as a policy. picker 'top': highest log-prob (ties: lowest index in ACTIONS);
    'sample': draw by softmax of the log-probs / temp with the episode's uniform (play passes it because `samples` is set).
    temp (GW-P, addendum A13) only changes 'sample'; the default 1.0 is the old behaviour.
    Always answers one of the 17 words."""
    assert picker in ('top', 'sample'), picker

    def pick(prompts, us=None):
        lp = move_logprobs(m, prompts, bs)
        if picker == 'top':
            return [WORDS[int(np.argmax(r))] for r in lp]
        return [WORDS[softmax_pick(r, u, temp)] for r, u in zip(lp, us)]
    pick.samples = picker == 'sample'
    pick.picker = picker
    pick.temp = temp
    return pick


def picked_policy(m, picker, bs=64, temp=1.0):
    """picker 'greedy' = model_policy (as before); 'top' / 'sample' = move_policy."""
    assert picker in ('greedy', 'top', 'sample'), picker
    return model_policy(m, bs) if picker == 'greedy' else move_policy(m, picker, bs, temp)
