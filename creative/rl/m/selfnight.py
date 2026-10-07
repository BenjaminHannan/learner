"""The night, run by the model on its own (Ben's rule 10-07): it picks its own sampling temperature, the one whose tries fit the examples of the most
practice questions on a probe of 256 questions x 8 tries (no answers needed; ties go to the lower temperature), then tries every practice question 32
times; up to 2 distinct tries per question that fit all its examples become records (as the cached night's W, which used a temperature tuned on DEV).
Speed: fewshot.verdict builds tiny torch tensors, which are slow under the eval's FLOP counter, so each distinct try is first screened in pure Python
(structure + the Python executor) and only the survivors get the full verdict: the accepted set is the same."""
import random
from creative import fewshot, legal
from creative.programs import result_key, run

TEMPS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def _samples(m, ctx, rows, n, T, seed):
    return legal.raw_samples(m, [dict(r, answer='0') for r in rows], ctx.vocab, ctx.device, n=n, temperature=T, level=0, seed=seed, bs=8192)  # answer unused


def _accepts(p, tries):
    """[bool per try]: verdict(p, t)[0] == 'accept', computed once per distinct try, cheap screen first."""
    memo, out = {}, []
    for r in tries:
        t = r.t
        key = (t.ops, t.a, t.b, t.ans)
        if key not in memo:
            ok = fewshot.structure(p, t)[0]
            if ok:
                o = fewshot.outputs_py(p, t)
                ok = None not in o and o[:-1] == p['ys']
            memo[key] = ok and fewshot.verdict(p, t)[0] == 'accept'
        out.append(memo[key])
    return out


def pick_temperature(m, ctx, n_probe=256, n=8):
    rows = random.Random(f'probe|{ctx.seed}').sample(ctx.pool, min(n_probe, len(ctx.pool)))
    score = {}
    for i, T in enumerate(TEMPS):
        smp = _samples(m, ctx, rows, n, T, ctx.seed + 100 + i)
        score[T] = sum(any(_accepts(fewshot.parse(r['prompt']), tr)) for r, tr in zip(rows, smp))
    return max(TEMPS, key=lambda T: (score[T], -T)), score


def _distinct(p, tries, rng, n):
    """fewshot._distinct with want = fits all examples, using the fast screen (same pool, same shuffle, same pick)."""
    pool = [r.t for r, ok in zip(tries, _accepts(p, tries)) if ok]
    rng.shuffle(pool)
    seen, out = set(), []
    for t in pool:
        key = result_key(t, run(p['nums'], t)[1])
        if key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) == n:
            break
    return out


def night(m, ctx, n=32, per_cap=2, arm='S'):
    was = m.training
    m.eval()
    T, score = pick_temperature(m, ctx)
    smp = _samples(m, ctx, ctx.pool, n, T, ctx.seed + 1)
    rng = random.Random(f'selfnight|{ctx.seed}')
    out = []
    for row, tr in zip(ctx.pool, smp):
        p = fewshot.parse(row['prompt'])
        for k, t in enumerate(_distinct(p, tr, rng, per_cap)):
            out.append(fewshot._record(dict(row), t, arm, k))
    m.train(was)
    return out, dict(T=T, probe=score)
