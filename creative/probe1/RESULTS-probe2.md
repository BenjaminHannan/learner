# Probe-2 results: K2 INCONCLUSIVE, Haiku reference clears both marks

Prereg: `PREREG-probe2.md` (sealed 26f4be281e). One change from Probe-1: the test writer also sees the start state.
Kaggle T4, 7.2 min; replay gate 100%. Haiku via Batches (default sampling). Raw: `results/probe2/`.

| picker | all pools (%) | solvable (%) | AUROC |
|---|---|---|---|
| RAND | 19.7 | 29.1 | |
| SELF (Pick-1) | 34.4 | 50.8 | 0.692 |
| K2 tests, blind (Probe-1) | 29.7 | 43.8 | 0.578 |
| **K2 tests, sees the world** | **36.5** | 53.8 | 0.661 |
| Haiku tests, blind (Probe-1) | 27.1 | 40.0 | 0.566 |
| **Haiku tests, sees the world** | **44.3** | 65.4 | **0.759** |

Decision (K2): P1 (>= 39.4) FAIL, P2 (>= .75) FAIL, not <= 35.4 -> INCONCLUSIVE.
Reference arm: Haiku-with-state would pass both marks (44.3, .759); with random tie-breaks still 42.7.

## What it means
- shown: seeing the world is what blind tests lacked. Reference agreement of valid tests rose from 38.5% to 60.2%
  (K2) and 64.7% to 74.5% (Haiku); K2 all-tie pools fell from 34% to 12%.
- shown: with the world in view, Haiku's tests pick a winning try 44% of the time, versus 34% for K2 judging itself
  and 20% at random. Test-first picking works when the tests are good.
- suggested: K2's tests are now the bottleneck (60% vs 75% correct). Per the prereg, the next step is teaching K2
  to write Haiku-quality tests (distillation on other tasks), not more prompting.
- caveat: the 192 pools come from 48 tasks (tests are shared per task), so the effective sample is closer to 48.
