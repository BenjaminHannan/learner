# Creative stopping toy — result (Fable, 22 Sep 2026)

**Coded verdict: KEEP_FIXED_N, 3/3 seeds** (test suite run once, after freeze; 120 solvable + 60 unsolvable puzzles).

| seed | A smart stop: solved / correct give-ups / wrong give-ups / capped | B fixed 11 rounds: solved | C never stop: solved | false FOUND A/B/C | D (filter may say FOUND) false FOUND |
|---|---|---|---|---|---|
| 3101 | 117 / 44 / 2 / 17 | 119 | 119 | 0/0/0 | 143 |
| 3102 | 114 / 48 / 6 / 12 | 119 | 119 | 0/0/0 | 148 |
| 3103 | 115 / 44 / 5 / 16 | 117 | 117 | 0/0/0 | 154 |

Marks: 1 PASS, 2 PASS (A ≥ 95% of C in every seed), 3 FAIL (A used ~80% of C's dreams, mark was ≤70%),
4 FAIL (A never beat fixed-N), 5 FAIL (44/48/44 correct give-ups, needed 48 and ≤60% of cap), 6 PASS.
Secondary (descriptive, declared in FREEZE-NOTE): marks 1, 2, 6 + ≥60% correct give-ups → met 3/3.

Predictions: verdict KEEP_FIXED_N p=.90 → right; mark 2 3/3 p=.65 → right; zero false FOUND p=.97 → right; secondary 3/3 p=.55 → right.

## What it means
- The exact checker being the only thing allowed to say FOUND is the part that matters: 0 false FOUND in 540 puzzle-runs
  per arm, versus 143–154 when the filter is allowed to say it.
- What moved solving from ~25% to ~98% of solvable puzzles was not the stop rule. It was (a) the dreamer using the same
  judgement as the filter, (b) a filter with balanced yes/no evidence, (c) a backlog so good unchecked ideas are not forgotten.
- With those in place, a plain "think 11 rounds, then ask Ben" does as well as the smart rule. Keep the simple rule.

## What it does not mean
- Nothing about creativity or a neural dreamer: this is a 156-rule toy with a scripted dreamer and filter.
- Dreamer quality (sharpness 10) was set on the dev suite; a weak dreamer (sharpness 3) solved less (32–35/40 on dev).
- The smart rule is not shown to be useless, only not worth its complexity here: it saved ~15–20% of dreams and lost 2–5 solves.
