"""Learned keep rule (GW-D, addendum A9 of PLAN-AND-MARKS-2026-10-10.md): a value guesser plus RND curiosity picks the moves to copy.

Features are game/ppo.py's one-hot text view (parse_obs). Each day (Guesser.day):
  1. curiosity of each view = RND predictor error (predictor as it was BEFORE today) / running std of the discounted intrinsic returns (RND paper);
  2. quality check: Spearman(V trained to yesterday, actual game-only discounted return to come) on today's moves;
  3. train the RND predictor on every view so far, then V on every move so far (targets = discounted return of game + 1.0 * curiosity);
  4. advantage of each move = GAE(0.95, gamma 0.99) under the new V with today's rewards (episode end = terminal);
  5. select(): the N awake moves with the highest advantage, ties by (world seed, step).
"""
import numpy as np
import torch
import torch.nn as nn

from game import crafter_text
from game.ppo import OBS_DIM, parse_obs

GAMMA, LAMBDA, CURIOSITY_WEIGHT = 0.99, 0.95, 1.0
HIDDEN, RND_OUT = 256, 64
EPOCHS, LR, BATCH = 4, 3e-4, 256     # V; the RND predictor takes one pass over all views per day with the same lr and batch


def mlp(out):
    return nn.Sequential(nn.Linear(OBS_DIM, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, out))


def discounted_returns(r, gamma=GAMMA):
    """Return to come of each step of one episode (no bootstrap past the end)."""
    out, g = np.zeros(len(r)), 0.0
    for t in reversed(range(len(r))):
        g = r[t] + gamma * g
        out[t] = g
    return out


def gae(r, v, gamma=GAMMA, lam=LAMBDA):
    """GAE advantages of one episode. r[t] reward of step t, v[t] = V(view t); the episode end is terminal (V after the last step = 0)."""
    r, v = np.asarray(r, float), np.asarray(v, float)
    adv, last = np.zeros(len(r)), 0.0
    for t in reversed(range(len(r))):
        nxt = v[t + 1] if t + 1 < len(r) else 0.0
        last = r[t] + gamma * nxt - v[t] + gamma * lam * last
        adv[t] = last
    return adv


def ranks(x):
    """Average ranks (ties share the mean rank)."""
    x = np.asarray(x, float)
    order = np.argsort(x, kind='mergesort')
    rk = np.empty(len(x))
    rk[order] = np.arange(len(x))
    xs = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        rk[order[i:j + 1]] = (i + j) / 2
        i = j + 1
    return rk


def spearman(a, b):
    """Rank correlation, None when undefined (fewer than 2 points or a constant side)."""
    if len(a) < 2:
        return None
    ra, rb = ranks(a), ranks(b)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def select(adv, keys, awake, n):
    """Indices of the n moves with the highest advantage among those with awake[i] true; ties by keys[i] (world seed, step).
    Fewer than n candidates -> all of them. -> sorted list of indices."""
    cand = [i for i in range(len(adv)) if awake[i]]
    cand.sort(key=lambda i: (-adv[i], keys[i]))
    return sorted(cand[:n])


class Guesser:
    def __init__(self, seed):
        self.seed = seed
        with torch.random.fork_rng():
            torch.manual_seed(seed * 7919 + 1)
            self.target, self.pred, self.v = mlp(RND_OUT), mlp(RND_OUT), mlp(1)
        for p in self.target.parameters():
            p.requires_grad_(False)
        self.opt_pred = torch.optim.Adam(self.pred.parameters(), lr=LR)
        self.opt_v = torch.optim.Adam(self.v.parameters(), lr=LR)
        self.n_err, self.mean_err, self.m2_err = 0, 0.0, 0.0     # running stats over all discounted intrinsic returns so far
        self.X = []          # per day: float32 (moves, OBS_DIM)
        self.rewards = []    # per day: per move, game + weight * curiosity (as computed that day)
        self.starts = []     # per day: per episode (start index, length) into that day's moves
        self.days = 0

    def errors(self, X):
        with torch.no_grad():
            return ((self.pred(X) - self.target(X)) ** 2).mean(-1).numpy().astype(np.float64)

    def _update_stats(self, e):
        n = len(e)   # parallel (Chan) update of mean / M2
        if n == 0:
            return
        m, m2 = float(e.mean()), float(((e - e.mean()) ** 2).sum())
        tot = self.n_err + n
        d = m - self.mean_err
        self.m2_err += m2 + d * d * self.n_err * n / tot
        self.mean_err += d * n / tot
        self.n_err = tot

    def curiosity(self, X, lens=None):
        """Curiosity reward of the views X (tensor), predictor as it is now (RND paper): raw error / running std of the discounted
        intrinsic returns (gamma 0.99, backward sum of raw errors per episode, lens = episode lengths; default one episode).
        The std is updated with these returns first. No mean is subtracted."""
        e = self.errors(X)
        lens = [len(e)] if lens is None else lens
        rets, i = [], 0
        for n in lens:
            rets.append(discounted_returns(e[i:i + n]))
            i += n
        self._update_stats(np.concatenate(rets) if rets else np.zeros(0))
        std = float(np.sqrt(self.m2_err / max(self.n_err, 1)))
        return e / (std + 1e-8)

    def value(self, X):
        with torch.no_grad():
            return self.v(X).squeeze(-1).numpy().astype(np.float64)

    def _train(self, net, opt, X, y, epochs, gen):
        """Mean loss of the last epoch."""
        n, last = len(X), 0.0
        for _ in range(epochs):
            perm = torch.randperm(n, generator=gen)
            tot = 0.0
            for i in range(0, n, BATCH):
                ix = perm[i:i + BATCH]
                out = net(X[ix])
                loss = ((out.squeeze(-1) - y[ix]) ** 2).mean() if y.dim() == 1 else ((out - y[ix]) ** 2).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += loss.item() * len(ix)
            last = tot / n
        return last

    def day(self, day, eps):
        """Take one day's episodes (play.play with log_steps). -> (advantage per move in episode order, info dict)."""
        with torch.random.fork_rng():
            torch.manual_seed(self.seed * 1_000_003 + day)
            gen = torch.Generator().manual_seed(self.seed * 1_000_003 + day)
            views = [st[0] for e in eps for st in e['steps']]
            X = torch.from_numpy(np.stack([parse_obs(v) for v in views])) if views else torch.zeros(0, OBS_DIM)
            game = [np.array([st[3] for st in e['steps']], float) for e in eps]
            lens = [len(g) for g in game]
            starts = np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(int)
            cur = self.curiosity(X, lens) if len(views) else np.zeros(0)
            gr = np.concatenate(game) if game else np.zeros(0)
            rew = gr + CURIOSITY_WEIGHT * cur
            # quality: V as trained to yesterday vs actual game-only return to come today
            rho = None
            if self.days > 0 and len(views):
                true = np.concatenate([discounted_returns(g) for g in game])
                rho = spearman(self.value(X), true)
            # train: RND predictor on every view so far (incl. today), then V on every move so far
            self.X.append(X.numpy()); self.rewards.append(rew); self.starts.append([(int(s), int(n)) for s, n in zip(starts, lens)])
            self.days += 1
            allX = torch.from_numpy(np.concatenate(self.X))
            with torch.no_grad():
                tgt = self.target(allX)
            rnd_loss = self._train(self.pred, self.opt_pred, allX, tgt, 1, gen)
            ret = np.concatenate([discounted_returns(self.rewards[d][s:s + n]) for d in range(self.days) for s, n in self.starts[d]])
            v_loss = self._train(self.v, self.opt_v, allX, torch.from_numpy(ret).float(), EPOCHS, gen)
            vals = self.value(X) if len(views) else np.zeros(0)
            adv = np.concatenate([gae(rew[s:s + n], vals[s:s + n]) for s, n in zip(starts, lens)]) if views else np.zeros(0)
        tot_game, tot_cur = float(np.abs(gr).sum()), float(np.abs(CURIOSITY_WEIGHT * cur).sum())
        info = dict(moves=len(views), v_loss=round(v_loss, 5), rnd_loss=round(rnd_loss, 6),
                    curiosity_share=round(tot_cur / max(tot_cur + tot_game, 1e-12), 4),
                    mean_game_reward=round(float(gr.mean()), 5) if len(gr) else None, rank_corr=None if rho is None else round(rho, 4))
        return adv, info

    def save(self, path):
        torch.save(dict(seed=self.seed, days=self.days, target=self.target.state_dict(), pred=self.pred.state_dict(),
                        v=self.v.state_dict(), err_stats=(self.n_err, self.mean_err, self.m2_err)), path)


def episode_moves(eps, awake_only):
    """-> (keys [(world seed, step)], awake bools) over all moves of eps in order."""
    keys, awake = [], []
    for e in eps:
        for s, st in enumerate(e['steps']):
            keys.append((e['seed'], s))
            awake.append(not (awake_only and crafter_text.asleep(st[0])))
    return keys, awake
