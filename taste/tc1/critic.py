"""Taste critic: small conv net on the one-hot 5x12x12 picture."""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def onehot(grids):
    g = torch.from_numpy(np.asarray(grids).astype(np.int64))
    return F.one_hot(g, 5).permute(0, 3, 1, 2).float()


class Critic(nn.Module):
    def __init__(self, seed=0, lr=1e-3):
        super().__init__()
        gen = torch.get_rng_state()
        torch.manual_seed(1_000_003 + int(seed))
        self.c1, self.c2, self.c3 = nn.Conv2d(5, 32, 3, padding=1), nn.Conv2d(32, 64, 3, padding=1), \
            nn.Conv2d(64, 64, 3, padding=1)
        self.fc = nn.Linear(64, 1)
        torch.set_rng_state(gen)
        self.opt = torch.optim.Adam(self.parameters(), lr=lr)

    def forward(self, x):
        x = F.relu(self.c1(x))
        x = F.relu(self.c2(x))
        x = F.relu(self.c3(x))
        return self.fc(x.mean(dim=(2, 3)))[:, 0]

    @torch.no_grad()
    def logits(self, grids, chunk=2048):
        grids = np.asarray(grids)
        if len(grids) == 0:
            return np.zeros(0)
        return np.concatenate([self(onehot(grids[i:i + chunk])).numpy() for i in range(0, len(grids), chunk)])

    def score(self, grids):
        return 1 / (1 + np.exp(-self.logits(grids)))


def daily_train(critic, examples, fake_buffer, steps=300, batch=128, r1_weight=1.0, rng=None):
    """BCE + R1 on real inputs. Real = examples + mirror flips; fake = uniform from the buffer.
    Continues from the critic's current weights and optimiser state; last step kept."""
    rng = rng or np.random.default_rng(0)
    fake_buffer = np.asarray(fake_buffer)
    if len(fake_buffer) == 0:
        return {"steps": 0}
    real_pool = np.concatenate([examples, np.asarray(examples)[:, :, ::-1]])
    half = batch // 2
    critic.train()
    stats = {}
    for _ in range(steps):
        real = onehot(real_pool[rng.integers(0, len(real_pool), half)]).requires_grad_(True)
        fake = onehot(fake_buffer[rng.integers(0, len(fake_buffer), half)])
        lr_, lf = critic(real), critic(fake)
        bce = F.binary_cross_entropy_with_logits(torch.cat([lr_, lf]),
                                                 torch.cat([torch.ones(half), torch.zeros(half)]))
        g, = torch.autograd.grad(lr_.sum(), real, create_graph=True)
        r1 = 0.5 * g.pow(2).sum(dim=(1, 2, 3)).mean()
        loss = bce + r1_weight * r1
        critic.opt.zero_grad(set_to_none=True)
        loss.backward()
        critic.opt.step()
    critic.eval()
    stats = {"steps": steps, "bce": float(bce.detach()), "r1": float(r1.detach())}
    return stats


def auc(pos, neg):
    """P(pos > neg) + 0.5 P(tie)."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    s = np.sort(neg)
    lo, hi = np.searchsorted(s, pos, "left"), np.searchsorted(s, pos, "right")
    return float((lo + 0.5 * (hi - lo)).sum() / (len(pos) * len(neg)))


def critic_exam(critic, data, fresh):
    """AUCs: held-back vs fresh tries, novel vs fresh tries, held-back vs broken houses."""
    lh, ln = critic.logits(data.heldback), critic.logits(data.novel)
    lf = critic.logits(fresh) if len(fresh) else np.zeros(0)
    out = {"heldback_vs_fresh": auc(lh, lf), "novel_vs_fresh": auc(ln, lf), "n_fresh": int(len(fresh))}
    allb = []
    for kind, g in data.broken.items():
        lb = critic.logits(g)
        out[f"heldback_vs_broken_{kind}"] = auc(lh, lb)
        allb.append(lb)
    out["heldback_vs_broken"] = auc(lh, np.concatenate(allb))
    return out
