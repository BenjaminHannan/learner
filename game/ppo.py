"""A standard PPO agent as the "normal game AI" reference (mark GW3) for the game-world test.

  python -m game.ppo --steps N --out DIR [--seed 0] [--threads 2]

It plays the same Crafter game as the mode, sees exactly the same text view (view_text), and gets crafter's own reward.
The text is turned into numbers: the 63 map cells one-hot over the 24 characters the view can use, health/food/drink/energy
and the 12 inventory counts divided by 9, and the zz and dark flags. CleanRL ppo defaults (8 envs, 128 steps, 4 epochs,
4 minibatches, lr 2.5e-4 linearly decayed, gamma 0.99, lambda 0.95, clip 0.2, entropy 0.01, value 0.5, grad norm 0.5).
Saves DIR/ppo.pt and DIR/log.jsonl. load_policy(path) gives a policy for play.play (and game/score.py --arm ppo).
"""
import argparse
import json
import math
import re
import time

import numpy as np
import torch
import torch.nn as nn

from game import play
from game.crafter_text import ACTIONS, GRID, ITEM_WORDS, MATERIAL_CHARS, OUTSIDE_CHAR, FACING_CHARS, TextEnv

N_ACTIONS = len(ACTIONS)
WORDS = [w for _, w in ACTIONS]
# the characters a cell can show: materials, outside, player facings, creatures/plants/arrows
CHARS = ''.join(MATERIAL_CHARS.values()) + OUTSIDE_CHAR + ''.join(FACING_CHARS.values()) + 'CZS*pP'
CHAR_INDEX = {c: i for i, c in enumerate(CHARS)}
N_CELLS = GRID[0] * GRID[1]
N_ITEMS = len(ITEM_WORDS)
OBS_DIM = N_CELLS * len(CHARS) + 4 + N_ITEMS + 2
SEED_BASE = 5_000_000           # choice: disjoint from practice_seed (< 5_000_000) and the sealed worlds (7_000_000+)
ITEM_INDEX = {w: i for i, (_, w) in enumerate(ITEM_WORDS)}
_ITEM = re.compile(r'^([a-z]+)([0-9])$')

# CleanRL ppo defaults
ENVS, ROLLOUT, EPOCHS, MINIBATCHES = 8, 128, 4, 4
LR, GAMMA, LAMBDA, CLIP, ENT, VF, GRAD = 2.5e-4, 0.99, 0.95, 0.2, 0.01, 0.5, 0.5
HIDDEN = 256


def parse_obs(text):
    """The view_text string -> float32 vector of length OBS_DIM."""
    head, status, items = text[len('game: '):].split(' | ')
    rows = head.split('/')
    assert len(rows) == GRID[1] and all(len(r) == GRID[0] for r in rows), text
    v = np.zeros(OBS_DIM, np.float32)
    for k, c in enumerate(''.join(rows)):
        v[k * len(CHARS) + CHAR_INDEX[c]] = 1.0
    base = N_CELLS * len(CHARS)
    parts = status.split()
    for k in range(4):                       # h f d e, one digit each
        v[base + k] = int(parts[k][1]) / 9
    v[base + 4 + N_ITEMS] = 1.0 if 'zz' in parts else 0.0
    v[base + 5 + N_ITEMS] = 1.0 if 'dark' in parts else 0.0
    if items != 'none':
        for tok in items.split():
            w, n = _ITEM.match(tok).groups()
            v[base + 4 + ITEM_INDEX[w]] = int(n) / 9
    return v


class Net(nn.Module):
    """Separate policy and value MLPs, two hidden layers of 256 (tanh)."""

    def __init__(self):
        super().__init__()

        def mlp(out, gain):
            layers = [nn.Linear(OBS_DIM, HIDDEN), nn.Tanh(), nn.Linear(HIDDEN, HIDDEN), nn.Tanh(), nn.Linear(HIDDEN, out)]
            for l in layers:
                if isinstance(l, nn.Linear):
                    nn.init.orthogonal_(l.weight, math.sqrt(2)); nn.init.zeros_(l.bias)
            nn.init.orthogonal_(layers[-1].weight, gain)
            return nn.Sequential(*layers)
        self.pi, self.v = mlp(N_ACTIONS, 0.01), mlp(1, 1.0)


def train(steps, out, seed=0, threads=2, save_every=0):
    import os
    import crafter  # noqa: F401  (TextEnv needs it)
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    cap = play.load_constants()[0]['episode_cap']
    os.makedirs(out, exist_ok=True)
    net = Net()
    opt = torch.optim.Adam(net.parameters(), lr=LR, eps=1e-5)
    n_updates = math.ceil(steps / (ENVS * ROLLOUT))   # choice: round up to whole updates (steps actually run are logged)
    counter, reset_sec = 0, 0.0

    def new_env():
        nonlocal counter, reset_sec
        s = SEED_BASE + counter
        assert not play.is_sealed(s)
        counter += 1
        t = time.time()
        e = TextEnv(seed=s, length=int(cap))
        txt = e.reset()
        reset_sec += time.time() - t
        return e, txt
    envs, obs = [], []
    for _ in range(ENVS):
        e, t = new_env()
        envs.append(e); obs.append(parse_obs(t))
    ep_ret, ep_len, ep_unl = [0.0] * ENVS, [0] * ENVS, [0] * ENVS
    seen = [set() for _ in range(ENVS)]
    X = torch.from_numpy(np.stack(obs))
    nd = torch.zeros(ENVS)
    B, mb = ENVS * ROLLOUT, ENVS * ROLLOUT // MINIBATCHES
    t0, total = time.time(), 0
    ckpt = lambda: dict(state=net.state_dict(), obs_dim=OBS_DIM, seed=seed, steps=total)
    with open(f'{out}/log.jsonl', 'w') as log:
        for up in range(n_updates):
            for g in opt.param_groups:
                g['lr'] = LR * (1 - up / n_updates)
            bo = torch.zeros(ROLLOUT, ENVS, OBS_DIM); ba = torch.zeros(ROLLOUT, ENVS, dtype=torch.long)
            blp, br, bd, bv = (torch.zeros(ROLLOUT, ENVS) for _ in range(4))
            done_eps = []
            for t in range(ROLLOUT):
                bo[t], bd[t] = X, nd
                with torch.no_grad():
                    dist = torch.distributions.Categorical(logits=net.pi(X))
                    a = dist.sample()
                    bv[t] = net.v(X).squeeze(-1)
                ba[t], blp[t] = a, dist.log_prob(a)
                nobs, ndn = [], []
                for i, e in enumerate(envs):
                    txt, r, done, info = e.step(int(a[i]))
                    br[t, i] = r
                    ep_ret[i] += r; ep_len[i] += 1
                    seen[i].update(k for k, c in info['achievements'].items() if c > 0)
                    if done:
                        done_eps.append((ep_ret[i], len(seen[i]), ep_len[i]))
                        ep_ret[i], ep_len[i], seen[i] = 0.0, 0, set()
                        e, txt = new_env(); envs[i] = e
                    nobs.append(parse_obs(txt)); ndn.append(float(done))
                X, nd = torch.from_numpy(np.stack(nobs)), torch.tensor(ndn)
                total += ENVS
            with torch.no_grad():
                nv = net.v(X).squeeze(-1)
                adv, last = torch.zeros(ROLLOUT, ENVS), 0
                for t in reversed(range(ROLLOUT)):
                    nxt_v, nxt_nd = (nv, nd) if t == ROLLOUT - 1 else (bv[t + 1], bd[t + 1])
                    delta = br[t] + GAMMA * nxt_v * (1 - nxt_nd) - bv[t]
                    last = delta + GAMMA * LAMBDA * (1 - nxt_nd) * last
                    adv[t] = last
                ret = adv + bv
            fo, fa, flp, fadv, fret = (x.reshape(B, *x.shape[2:]) for x in (bo, ba, blp, adv, ret))
            for _ in range(EPOCHS):
                perm = torch.from_numpy(rng.permutation(B))
                for k in range(MINIBATCHES):
                    ix = perm[k * mb:(k + 1) * mb]
                    dist = torch.distributions.Categorical(logits=net.pi(fo[ix]))
                    ratio = (dist.log_prob(fa[ix]) - flp[ix]).exp()
                    ad = fadv[ix]; ad = (ad - ad.mean()) / (ad.std() + 1e-8)
                    pg = torch.max(-ad * ratio, -ad * ratio.clamp(1 - CLIP, 1 + CLIP)).mean()
                    vl = 0.5 * ((net.v(fo[ix]).squeeze(-1) - fret[ix]) ** 2).mean()
                    loss = pg - ENT * dist.entropy().mean() + VF * vl
                    opt.zero_grad(); loss.backward()
                    nn.utils.clip_grad_norm_(net.parameters(), GRAD)
                    opt.step()
            n = len(done_eps)
            rec = dict(update=up + 1, steps=total, episodes=n, seconds=round(time.time() - t0, 1),
                       reset_seconds=round(reset_sec, 1),
                       mean_return=sum(e[0] for e in done_eps) / n if n else None,
                       mean_unlocks=sum(e[1] for e in done_eps) / n if n else None,
                       mean_length=sum(e[2] for e in done_eps) / n if n else None)
            log.write(json.dumps(rec) + '\n'); log.flush()
            if save_every > 0 and total // save_every > (total - ENVS * ROLLOUT) // save_every:
                sp = f'{out}/ppo_steps_{total}.pt'
                torch.save(ckpt(), sp)
                log.write(json.dumps(dict(event='save', steps=total, path=sp)) + '\n'); log.flush()
    torch.save(ckpt(), f'{out}/ppo.pt')
    return dict(steps=total, seconds=time.time() - t0, reset_seconds=reset_sec, episodes_started=counter)


def load_policy(path, seed=0, sample=False):   # seed is accepted but unused: the policy is deterministic
    """policy(prompts) -> list of action words: the argmax word of the trained PPO policy logits (deterministic per world).
    sample=True: policy(prompts, us) draws each word from softmax(logits) by inverse CDF with the uniform us[j] (play's `samples` interface)."""
    ck = torch.load(path, map_location='cpu')
    net = Net()
    net.load_state_dict(ck['state'])
    net.eval()

    def policy(prompts, us=None):
        if not prompts:
            return []
        with torch.no_grad():
            logits = net.pi(torch.from_numpy(np.stack([parse_obs(p) for p in prompts])))
            if sample:
                from game.play import softmax_pick
                return [WORDS[softmax_pick(r, u)] for r, u in zip(logits.double().numpy(), us)]
            idx = logits.argmax(-1)
        return [WORDS[int(i)] for i in idx]
    policy.samples = sample
    return policy


def main(argv=None):
    ap = argparse.ArgumentParser(description='Train the PPO reference agent on Crafter text views.')
    ap.add_argument('--steps', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--save-every', type=int, default=0, help='also save DIR/ppo_steps_<S>.pt each time cumulative steps cross a multiple of N (0 = final only)')
    a = ap.parse_args(argv)
    res = train(a.steps, a.out, a.seed, a.threads, a.save_every)
    print(json.dumps(res), flush=True)


if __name__ == '__main__':
    main()
