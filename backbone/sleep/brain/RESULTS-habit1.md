# Habit-1 results

## Stage 1 on Week-2 (Ben's M1 Pro, 2026-10-26 ~17:45Z, mlx_lm 0.32.2, Qwen3.6-35B-A3B 4-bit, thinking off, temperature 0; 95 replies in 131 s)

| set | what it is | valid "Sam usually" yes |
|---|---|---|
| Rall | each routine, all its days shown | **20 / 20** (15 name the activity) |
| R2 | each routine, first 2 days only | 9 / 20 |
| N | the non-routine questions the spotter would ask | 0 / 15 |
| F | fact pairs on 2+ days, not habits (never asked in a real run) | **23 / 40** (C4 19/20, C2 4/20) |

- **S1 FAIL (shown):** the false-yes mark (F <= 30%) missed: 57.5%. Rall passed easily (mark 16).
- All 23 false yeses have the same shape: "Sam usually mentions X and Y together (in every message)". None of the 20 routine yeses uses "mention".
  The model reads "comes up together on N days" as the habit itself.
- R2 9/20: with only 2 days shown, the model often says no. In a real week, the spotter asks again when a third day arrives
  (`hab_asked`), so R2 is a lower bound for night-by-night recall.
- Raw replies on the Mac: ~/learner-ops/habit1/replies.jsonl (and replies_slim.jsonl).

## Addendum 1 (PREREG-habit1-addendum1.md): one change, tested on a fresh week
The parser rejects a reply that says Sam "mentions / talks about / brings up / refers to" them. On Week-2 this is post-hoc (it would give F 0/40
and Rall 20/20, but it was tuned on these replies), so the pass/fail test is Week-1 (12 routines, 40 facts), which the model has not been asked about.
