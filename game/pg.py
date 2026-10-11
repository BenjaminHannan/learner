"""Policy-gradient night (GW-P, addendum A12 of PLAN-AND-MARKS-2026-10-10.md): every awake move of the day nudges the add-on
up or down by its advantage, PPO clipped objective. Only the add-on trains; the base model is frozen.

  mu(a|s)     = (1 - explore) * pi_old(a|s) + explore / 17        (the act rule's odds at play time; pi_old = the model's 17-word softmax
                                                                  at night start, equal to play-time odds because the weights did not change)
  pi_new(a|s) = same mixture with the model's softmax now
  ratio       = pi_new / mu, loss = -mean(min(ratio A, clip(ratio, 1 - eps, 1 + eps) A)) - ent_coef * mean(entropy(softmax(model logits)))
The entropy bonus uses the model's own 17-word softmax, not the mixture. Fresh Adam each night (no carry-over state), no weight decay.
"""
import math
import time

import numpy as np
import torch

from game import play

CLIP, ENT_COEF, PASSES, MINIBATCH, LR, MAX_GRAD_NORM = 0.2, 0.01, 4, 256, 2.5e-4, 0.5
ADV_EPS = 1e-8


def normalise(adv):
    """Mean 0, std 1 (population std) over the given moves."""
    adv = np.asarray(adv, float)
    return (adv - adv.mean()) / (adv.std() + ADV_EPS) if len(adv) else adv


def mix_logp(logits, explore, temp=1.0):
    """log of the act-rule mixture over the 17 words, from the model's [n, 17] word log-probs / temp (a float, or a torch scalar
    tensor that may carry grad), renormalised to a softmax."""
    if isinstance(logits, torch.Tensor):
        return torch.log((1 - explore) * torch.softmax(logits / temp, -1) + explore / play.N_ACTIONS)
    z = np.asarray(logits, float) / temp
    z = z - z.max(-1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(-1, keepdims=True)
    return np.log((1 - explore) * p + explore / play.N_ACTIONS)


def entropy(logits, temp=1.0):
    """Mean entropy (nats) of the softmax of [n, 17] numpy or torch logits / temp."""
    if isinstance(logits, torch.Tensor):
        lp = torch.log_softmax(logits / temp, -1)
        return -(lp.exp() * lp).sum(-1).mean()
    z = np.asarray(logits, float) / temp
    lp = z - z.max(-1, keepdims=True)
    lp = lp - np.log(np.exp(lp).sum(-1, keepdims=True))
    return float(-(np.exp(lp) * lp).sum(-1).mean()) if len(z) else 0.0


def find_temp(logp, target=math.log(play.N_ACTIONS) / 2, steps=40, lo=-8.0, hi=8.0):
    """Bisection on log T (entropy of softmax(logp / T) rises with T): the T at which the mean entropy over the rows of logp
    [n, 17] is `target` (default ln 17 / 2). -> (T, entropy reached)."""
    logp = np.asarray(logp, float)
    for _ in range(steps):
        mid = (lo + hi) / 2
        if entropy(logp, math.exp(mid)) < target:
            lo = mid
        else:
            hi = mid
    T = math.exp((lo + hi) / 2)
    return T, entropy(logp, T)


def ppo_loss(new_logits, actions, adv, log_mu, explore, clip=CLIP, ent_coef=ENT_COEF, logT=None):
    """-> (loss, ratio, entropy, log pi_new of the taken moves). new_logits [n, 17] torch (grad), actions [n] long, adv [n] float, log_mu [n].
    logT: torch scalar (A13): the policy is softmax(new_logits / exp(logT)); None means T = 1."""
    temp = 1.0 if logT is None else torch.exp(logT)
    logp_new = mix_logp(new_logits, explore, temp).gather(1, actions[:, None]).squeeze(1)
    ratio = torch.exp(logp_new - log_mu)
    pg = -torch.min(ratio * adv, torch.clamp(ratio, 1 - clip, 1 + clip) * adv).mean()
    ent = entropy(new_logits, temp)
    return pg - ent_coef * ent, ratio, ent, logp_new


def night(m, addon, prompts, actions, adv, explore, seed, temp=1.0, bs_old=64, chunk=64, passes=PASSES, minibatch=MINIBATCH, lr=LR):
    """Train the add-on on one day's moves. prompts: list of n views; actions: [n] word indices; adv: [n] NORMALISED advantages.
    `temp` = T at night start (the play-time T); log T is learned with the add-on (same Adam).
    -> (stats dict incl. temp_before / temp_after, per-minibatch losses). Deterministic for `seed`."""
    n = len(prompts)
    assert n == len(actions) == len(adv)
    t0 = time.time()
    torch.manual_seed(seed)
    acts = torch.as_tensor(np.asarray(actions), dtype=torch.long)
    A = torch.as_tensor(np.asarray(adv), dtype=torch.float32)
    addon.on = True
    old = play.move_logprobs(m, prompts, bs_old)                       # pi_old, no grad, as at play time
    ent_before = entropy(old, temp)
    log_mu = torch.as_tensor(mix_logp(old, explore, temp)[np.arange(n), np.asarray(actions)], dtype=torch.float32)
    logT = torch.tensor(math.log(temp), dtype=torch.float32, requires_grad=True)
    params = addon.params() + [logT]
    opt = torch.optim.Adam(params, lr=lr)
    gen = torch.Generator().manual_seed(seed)
    losses, per_pass, clipped, kls, first = [], [], [], [], None
    for _ in range(passes):
        perm = torch.randperm(n, generator=gen)
        pl = []
        for i in range(0, n, minibatch):
            ix = perm[i:i + minibatch]
            # the minibatch is run in chunks of `chunk` prompts, gradients summed (the loss is a mean of per-move terms, so each chunk
            # contributes len(chunk)/len(minibatch) of it): the same gradient as one 256-prompt pass, about 2.5x faster and far less memory
            opt.zero_grad(set_to_none=True)
            mb_loss, mb_clip, mb_kl, mb_dev = 0.0, 0.0, 0.0, 0.0
            for c in range(0, len(ix), chunk):
                cx = ix[c:c + chunk]
                w = len(cx) / len(ix)
                lg = play.move_logprobs_grad(m, [prompts[j] for j in cx.tolist()])
                loss, ratio, _, logp_new = ppo_loss(lg, acts[cx], A[cx], log_mu[cx], explore, logT=logT)
                (loss * w).backward()
                r = ratio.detach()
                mb_loss += float(loss.detach()) * w
                mb_clip += float(((r - 1).abs() > CLIP).float().mean()) * w
                mb_kl += float((log_mu[cx] - logp_new.detach()).mean()) * w
                mb_dev = max(mb_dev, float((r - 1).abs().max()))
            if first is None:
                first = dict(ratio_max_dev=mb_dev, clipped=mb_clip)
            clipped.append(mb_clip)
            kls.append(mb_kl)
            torch.nn.utils.clip_grad_norm_(params, MAX_GRAD_NORM)
            opt.step()
            losses.append(mb_loss)
            pl.append(mb_loss)
        per_pass.append(round(float(np.mean(pl)), 5))
    temp_new = float(math.exp(float(logT.detach())))
    ent_after = entropy(play.move_logprobs(m, prompts, bs_old), temp_new)
    return dict(temp_before=round(temp, 6), temp_after=round(temp_new, 6), moves=n, passes=passes, minibatches=len(losses), entropy_before=round(ent_before, 4), entropy_after=round(ent_after, 4),
                clipped_fraction=round(float(np.mean(clipped)), 5), approx_kl=round(float(np.mean(kls)), 6),
                first_minibatch=first, loss_per_pass=per_pass, seconds=round(time.time() - t0, 1)), losses
