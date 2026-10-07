"""The C2 research loop's editable learner (creative/rl/eval_c2.py scores it; see its docstring for what a method may see).

Start (10-07): the fast-sleep pilot BC. The night's W, plus chain records for the pool questions W missed (shortest P2(P1(x)) of two library programs
that fits the 3 examples), fine-tuned with job 6's settings and job 6's number of updates.
Trial H3 (tune): 48 visits per W record instead of 16 (3x the updates; the reader's place ids are pre-filled with numpy for speed, same values).
"""
from creative import fastsleep as fs, fewshot
from creative import nightchain as NC
from creative.rl.m import fast


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
    W = ctx.night()
    C = chain_records(W, ctx.pool)
    N = ctx.N
    fast.prefill(N, W + C + ctx.replay)
    m, _ = fs.m_ft(N, W + C, ctx.replay, ctx.vocab, ctx.device, len(W), lr=1e-3, visits=48, seed=ctx.seed)
    return m
