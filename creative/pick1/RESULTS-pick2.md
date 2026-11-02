# Pick-2 results: PROVED WRONG

Prereg: `PREREG-pick2.md` (sealed e4f97d2815, before any Pick-2 judging). Same 192 pools of 12 Guess-1 tries as Pick-1.
Run on Kaggle (one T4, K2-Horizon-3.7B fp16). Raw: `results/pick2/`.

| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 | |
| VOTE | 22.4 | 33.1 | |
| SELF (Pick-1: short tool output, no thinking) | 34.4 | 50.8 | 0.692 |
| FULL (fuller tool output) | 31.8 | 46.9 | 0.713 |
| THINK (thinks before scoring) | 30.2 | 44.6 | 0.646 |

Q1 (>= RAND+15) fails for both; Q2 (AUROC >= .70) holds only for FULL; Q3 (>= SELF+3) fails for both.
Both variants are at or below SELF+1, so the prereg's PROVED WRONG mark is hit. THINK parsed 2301/2304 replies.

## What it means (shown / suggested)
- shown: giving K2 more of the tool output, or letting it think first, does not make it a better judge of its own
  tries on this test bed. Thinking made it slightly worse.
- shown (Pick-1): K2's self-judge picks a winning try about 34% of the time vs 20% random, the same rate as Haiku.
- suggested: reading a transcript and guessing whether it worked is near its ceiling for a 3.7B judge here. Better
  picking needs a check that actually runs against the world (read-back probes of the end state), per the prereg.
