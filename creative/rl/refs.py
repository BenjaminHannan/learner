"""Fixed reference methods for the C2 research loop (LOCKED; written 10-07 before any loop trial). Each takes the eval's ctx and returns a model.

  floor    N itself, no sleep
  memory   C2b's arm M: memory sleep on the night's W (+ 512 old notes, answer note off)
  job6     job 6's sleep B: fine-tune on the night's W, lr 1e-3, 16 visits (the setting the confirm chose on 4 of 6 parents)
  chainft  the 10-07 pilot BC: job6 with the same updates, on W + chain records for the pool questions W missed
  ceiling  NOT a learner: job6's fine-tune on the 512 `labelled` held-out questions with their reference programs (reads the key), at 16 visits
"""
from creative import fastsleep as fs, fewshot, rules_real as R
from creative import nightchain as NC


def floor(ctx):
    return ctx.N


def memory(ctx):
    W = ctx.night()
    m, _ = fs.m_knn(ctx.N, W, ctx.replay, ctx.vocab, ctx.device, len(W), c=50.0, theta=0.9, cal=0.99, old=512, ans=0, seed=ctx.seed)
    return m


def job6(ctx):
    W = ctx.night()
    m, _ = fs.m_ft(ctx.N, W, ctx.replay, ctx.vocab, ctx.device, len(W), lr=1e-3, visits=16, seed=ctx.seed)
    return m


def chain_records(W, pool):
    lib = NC.library(W)
    solved = {r['source'] for r in W}
    out = []
    for row in pool:
        if row['id'] in solved:
            continue
        t = NC.solve_chain(fewshot.parse(row['prompt']), lib)
        if t is not None:
            out.append(fewshot._record(dict(row), t, 'C', 0))
    return out


def chainft(ctx):
    W = ctx.night()
    C = chain_records(W, ctx.pool)
    m, _ = fs.m_ft(ctx.N, W + C, ctx.replay, ctx.vocab, ctx.device, len(W), lr=1e-3, visits=16, seed=ctx.seed)
    return m


def ceiling(ctx):
    gold = R.warm_records(R.load_split(fs.DATA, 'labelled'), allow=R.HELD_OUT)
    m, _ = fs.m_ft(ctx.N, gold, ctx.replay, ctx.vocab, ctx.device, len(gold), lr=1e-3, visits=16, seed=ctx.seed)
    return m
