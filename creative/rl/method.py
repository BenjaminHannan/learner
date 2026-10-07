"""The C2 research loop's editable learner (creative/rl/eval_c2.py scores it; see its docstring for what a method may see).

Segment 1 (10-07, closed): BC pilot -> H3 train longer -> H14 per-record replay + batch-1024 sleep -> 80 visits (72.7% dev, 72.7% holdout on 2 seeds).
That recipe broke Ben's rule (10-07: everything must run on its own while deployed) in three places: the cached night used a temperature tuned on DEV,
and replay used C2's input range and format rules.

Segment 2 (compliant base): the same sleep, with
  - the night run by the model itself at a temperature it picks from its own tries (m/selfnight.py), instead of the cached DEV-tuned night;
  - replay inputs, output range and prompt text taken from the day's questions (m/replay.py).
Chain search (two stored programs chained to fit the examples) and the executor are tools the sleep calls itself.
"""
from creative import fastsleep as fs, fewshot
from creative import nightchain as NC
from creative.rl.m import fast, replay, selfnight


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


def train(ctx):
    N = ctx.N
    fast.prefill(N, ctx.pool + ctx.replay)
    W, _ = selfnight.night(N, ctx)
    C = chain_records(W, ctx.pool)
    inputs, lo, hi = replay.experience(ctx.pool)
    recs = W + C + replay.replay_per_record(W + C, 3, ctx.seed, inputs, lo, hi)
    fast.prefill(N, recs)
    m, _ = fs.m_ft(N, recs, ctx.replay, ctx.vocab, ctx.device, len(recs), lr=1e-3, visits=80, seed=ctx.seed, batch=1024)
    return m
