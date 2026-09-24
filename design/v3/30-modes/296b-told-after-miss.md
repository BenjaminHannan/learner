# 296b: told the answer after a miss (296's one follow-up)

Reasoning line, 2026-09-24. 296 = registered FAIL on P296.4 only (fresh total 225 and 217 vs 228). It made 0 made-up answers after the fact-check, and it transferred well (238 and 238).

## Diagnosis this answers
artifacts/claude-rsn296-20260924/DIAG-director.md used generated practice-style episodes only. It showed that the models don't count or compare; each one settled on a few fixed answers.
- Counting: seed 1 is right only on counts 1, 2 and 7. Seed 2 is 0/59 on counts 1–2.
- Comparing: one fixed pick, 88/200.
- Before/after: fails once there are more than 2 dated facts.

The practice reward goes only to the exact answer. Once all 8 tries agree, there is no signal left (294's D3).

## The one change
scripts/claude_rsn296b_run.py: in practice, when none of an episode's 8 tries is right, the teacher shows the right answer for that episode. This is the copy phase's own loss, on that episode only. Everything else is 296: the generator, the plain arm, sizes, steps, reward, fact-check, seeds 1 and 2, and eval. It is brain-like in the plain sense: practise, and when you keep missing, someone tells you the answer.

Only the plain arm runs. The loop arm's copy failure (294 D2, reproduced in 296) is unfixed, so running it again would only spend money.

## Untested risk (from scratch CPU checks, tiny model, not registered)
A tiny model shown every counting and comparing answer for 3,000 steps still didn't learn them. A "tally" readout didn't help at that size either. So 296b may show that the 30M model can't count even when told the answer. P296b.2 is the mark that would prove that.

## Cost
Two plain runs in parallel on one 5090, about 40 minutes, about $0.5–1. The $4 combined cap and the guard stay as in 296.
