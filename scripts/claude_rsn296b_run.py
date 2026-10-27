#!/usr/bin/env python3
"""rsn-296b runner: rsn-296 exactly (varied practice generator, same arms, sizes, steps, reward,
fact-check, eval), with ONE change in the practice phase:

  TOLD THE ANSWER AFTER A MISS.  When none of an episode's 8 practice tries is right, the
  teacher shows the right answer for that episode (the same copy loss the copy phase uses:
  cross-entropy on the right action + 0.5 x the cited-facts loss), on that episode only.

Why (rsn-296 diagnosis, artifacts/claude-rsn296-20260924/diag-cpu, generated episodes only):
the practice-only kinds were never learned.  Counting: seed 1 answers right only when the count
is 1, 2 or 7 (0/117 on counts 3-6), seed 2 only on 3-5 and partly 6-7 (0/59 on counts 1-2): each
seed settled on a few fixed numbers.  Comparing: 88/200 on both seeds, bucket for bucket identical
(one fixed pick).  Before/after: all right with 2 dated facts, about half with 3-4.  With a
13-way or 2-way choice and a reward only for the exact answer, once the 8 tries agree there is
no signal left (294's D3).  A person who practises and keeps missing gets told the answer; that
is the one change.

  python claude_rsn296b_run.py train|dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import argparse
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode)
import claude_rsn294_core as C  # noqa: E402
import claude_rsn294_run as R  # noqa: E402

_rl_loss_294 = R.rl_loss


def rl_loss_296b(model, arm, batch, dev, rng, G=8):
    enc, ga, sup, golds, infos = batch
    enc_d, ga_d, sup_d = enc.to(dev), ga.to(dev), sup.to(dev)
    logits, sl = model(enc_d, R.steps_for(arm, rng)) if arm == "loop" else model(enc_d)
    dist = torch.distributions.Categorical(logits=logits)
    acts = dist.sample((G,))                                   # [G, B]
    m = sl > -1e8
    sprob = torch.sigmoid(sl).clamp(1e-4, 1 - 1e-4)
    sbits = torch.bernoulli(sprob.detach().expand(G, *sprob.shape)) * m
    acts_c = acts.cpu().tolist()
    match = ((sbits == sup_d.unsqueeze(0)) | ~m.unsqueeze(0)).all(-1).cpu().tolist()
    Rw = torch.zeros(G, len(golds))
    hit = [False] * len(golds)
    for g in range(G):
        for b in range(len(golds)):
            r = C.reward(C.decode(acts_c[g][b], infos[b]), golds[b])
            if r == 1.0:
                hit[b] = True
                if match[g][b]:
                    r += 0.2
            Rw[g, b] = r
    Rw = Rw.to(dev)
    adv = (Rw - Rw.mean(0, keepdim=True)) / (Rw.std(0, keepdim=True) + 1e-4)
    lp = dist.log_prob(acts)
    slp = ((sbits * torch.log(sprob) + (1 - sbits) * torch.log(1 - sprob)) * m).sum(-1)
    loss = -(adv.detach() * (lp + slp)).mean() - 0.01 * dist.entropy().mean()
    # the one change: told the answer after a miss (only where no try was right and a right action exists)
    miss = torch.tensor([not h for h in hit], device=dev) & (ga_d >= 0)
    if miss.any():
        la = F.cross_entropy(logits[miss], ga_d[miss])
        mm = m[miss]
        ls = F.binary_cross_entropy_with_logits(sl[miss][mm], sup_d[miss][mm]) if mm.any() else la * 0
        loss = loss + la + 0.5 * ls
    return loss, Rw.mean().item()


R.rl_loss = rl_loss_296b


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("train")
    t.add_argument("--arm", choices=["loop", "plain"], required=True)
    t.add_argument("--seed", type=int, default=1)
    t.add_argument("--out", required=True)
    t.add_argument("--size", default="30m")
    t.add_argument("--copy-steps", type=int, default=6000)
    t.add_argument("--rl-steps", type=int, default=6000)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--rl-batch", type=int, default=128)
    t.add_argument("--lr", type=float, default=3e-4)
    t.add_argument("--init", default=None, help="start from this checkpoint (dev only)")
    t.add_argument("--workers", type=int, default=6)
    t.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    d = sp.add_parser("dev")
    d.add_argument("--ckpt", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--n", type=int, default=100)
    d.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    e = sp.add_parser("eval")
    e.add_argument("--ckpt", required=True)
    e.add_argument("--panel", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = p.parse_args()
    {"train": R.train, "dev": R.dev, "eval": R.evaluate}[a.cmd](a)
