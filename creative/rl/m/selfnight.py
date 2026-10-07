"""The night, run by the model on its own (Ben's rule 10-07): it picks its own sampling temperature, the one whose tries fit the examples of the most
practice questions on a probe of 256 questions x 8 tries (no answers needed; ties go to the lower temperature), then tries every practice question 32
times; up to 2 distinct tries per question that fit all its examples become records (as the cached night's W, which used a temperature tuned on DEV)."""
import random
from creative import fewshot, legal

TEMPS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def _samples(m, ctx, rows, n, T, seed):
    return legal.raw_samples(m, [dict(r, answer='0') for r in rows], ctx.vocab, ctx.device, n=n, temperature=T, level=0, seed=seed, bs=8192)  # answer unused


def _fits(row, tries):
    p = fewshot.parse(row['prompt'])
    return [r.t for r in tries if fewshot.verdict(p, r.t)[0] == 'accept']


def pick_temperature(m, ctx, n_probe=256, n=8):
    rows = random.Random(f'probe|{ctx.seed}').sample(ctx.pool, min(n_probe, len(ctx.pool)))
    score = {}
    for i, T in enumerate(TEMPS):
        smp = _samples(m, ctx, rows, n, T, ctx.seed + 100 + i)
        score[T] = sum(bool(_fits(r, tr)) for r, tr in zip(rows, smp))
    return max(TEMPS, key=lambda T: (score[T], -T)), score


def night(m, ctx, n=32, per_cap=2, arm='S'):
    was = m.training
    m.eval()
    T, score = pick_temperature(m, ctx)
    smp = _samples(m, ctx, ctx.pool, n, T, ctx.seed + 1)
    rng = random.Random(f'selfnight|{ctx.seed}')
    out = []
    for row, tr in zip(ctx.pool, smp):
        p = fewshot.parse(row['prompt'])
        kept = fewshot._distinct(p, tr, rng, per_cap, lambda rules, full: full[0] == 'accept')
        for k, t in enumerate(kept):
            out.append(fewshot._record(dict(row), t, arm, k))
    m.train(was)
    return out, dict(T=T, probe=score)
