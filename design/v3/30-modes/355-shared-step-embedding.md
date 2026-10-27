# 355: one shared "chain step" input instead of one slot per step

Sleep research thread, 2026-09-25 02:25 UTC. Ben's night instruction (02:12 UTC, via the coordinator):
tonight's GPU jobs run on BensPC. The coordinator relayed the go-ahead for this fix (my recommendation,
well under $4; Ben did not answer the question before bed).

## Why
Sleep research round 2 (sleep-research-round2-2026-09-25.md), checked in code: each step of a
question's chain has its own input slot (Embed.slot, scripts/claude_rsn294_core.py:405-420). I
generated 300 items of every practice kind: all use 1 or 2 steps; only value3 (never practised) uses 3.
So slot 3 kept its random starting vector (as large as a word) in every checkpoint, and three-step was
0/30 in 294, 296, 350 and 351 by construction. Every "practise 2 steps, answer 3" test so far measured
an untrained input, not reasoning.

## The one change (scripts/claude_rsn355_run.py)
Each chain step's token = its relation + one shared learned "chain step" vector + (first step: a learned
"first" vector; later steps: a learned linear link from the previous step's relation). Everything else
is 296's plain arm unchanged: generator, practice kinds (value3 still never practised), steps, batch,
lr 3e-4, reward, fact-check, eval, seeds 1 and 2. Plain arm because the loop arm does not learn yet
(rsn-353 tests that separately).

Twin: 296 plain (fresh panel296 v2: 225 / 217; three-step 0/30 and 0/30).
Deviation to note: BensPC is Windows, where the data loader's worker processes cannot start (it passes
a lambda), so the builder runs with --workers 0 (same generator, same seeds, a different random stream
than the GPU-rental runs). This changes which practice puzzles are drawn, not what kind.

## What it would and would not show
A PASS shows the untrained slot was what blocked three-step, and that the plain net can chain one step
further than it practised once the input allows it. It does not show rule learning in general, and
three-step is still one step past practice, not open-ended depth (MAX_HOPS = 3; 4 steps can't be
written yet).
