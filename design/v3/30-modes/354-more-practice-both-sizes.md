# 354: twice the practice for both sizes (Ben's 3x goal, plan 352 step S2)

Sleep research thread, 2026-09-25 02:05 UTC. Goal (Ben, 00:04 UTC): the 3x model beats the 1x, genuinely.

## Why this change
rsn-351 (VERIFY.md) showed where the 3x loses: it is ahead after the copy phase (fresh 183 / 182 vs the
1x's 167 / 181) and falls behind during practice (gain +38 / +36 vs +58 / +36). Its practice reward
levels off at ~0.89 while the 1x reaches 0.93 / 0.98. Plan 352 fixed the next step in advance: "S2
(only if the 3x still gains less in practice than the 1x): more practice steps (2x) for BOTH sizes, as
one registered change." That condition is met, so this is S2, not a new idea picked after the fact.

## The one change
Practice (RL) steps 6,000 -> 12,000 for every arm. Nothing else changes: same generator (296's), copy
steps, batches, reward, fact-check, eval, seeds 1 and 2. Existing flag `--rl-steps`; no new code.
The learning-rate schedule is one cosine over all steps, so it stretches with the longer run (part of
"more steps").

Arms (runner scripts/claude_rsn350_run.py; for size 30m it builds 296's plain arm unchanged):
- A: 3x plain (90m), lr 1e-4 (its better rate: 351 beat 350)
- B: 1x plain (30m), lr 3e-4 (296's rate)
- C: 1x plain (30m), lr 1e-4 (the 1x never got the slower rate; this closes plan 352's fairness gap)

The 1x arm used in the comparison is the one with the higher dev-final checked-right, summed over both
seeds (dev = generated seed-777 items, not a panel; plan 352 rule 2). Ties go to B.

## What a win would and would not mean
A PASS here is not the goal met. Plan 352 rule 5 still applies: freeze both recipes, write the fresh blind
reasonpanel353, score once, blind recount. Panel296 has now scored five size runs, so it is only the gate.
