"""The C2 research loop's editable learner (creative/rl/eval_c2.py scores it; see its docstring for what a method may see).

Start (10-07): the fast-sleep pilot BC. The night's W, plus chain records for the pool questions W missed (shortest P2(P1(x)) of two library programs
that fits the 3 examples), fine-tuned with job 6's settings and job 6's number of updates.
Trial H3 (tune): 48 visits per W record instead of 16 (3x the updates; the reader's place ids are pre-filled with numpy for speed, same values).
Trial H14 (bold): a much bigger sleep. Every W and chain record also gets 3 replayed prompts (its program run on fresh inputs, generic filters only, so
the mix of rules stays the pool's), and the fine-tune runs at batch 1024 for about 9x the record rows of H3 (40 visits per record).
"""
from creative import fastsleep as fs, fewshot
from creative import nightchain as NC
from creative.rl.m import fast, replay


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
    recs = W + C + replay.replay_per_record(W + C, 3, ctx.seed)
    N = ctx.N
    fast.prefill(N, recs + ctx.replay)
    m, _ = fs.m_ft(N, recs, ctx.replay, ctx.vocab, ctx.device, len(recs), lr=1e-3, visits=40, seed=ctx.seed, batch=1024)
    return m
