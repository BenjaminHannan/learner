# Sleep-B addendum 17: a steadier morning gate (written 2026-10-26 ~03:10Z, before the code and any run)

Labels: shown / suggested / untested. Model K2-Horizon-3.7B (bf16 base), Week-2, seed 1. Recipe: addendum 14's arm B (k2c_r2) exactly,
with one change. Not the village model, not the card experiments.

## Why
- Goal (Ben, 2026-10-25): two-hop >= 75 of 78.
- **Shown (addendum 14, arm B):**
  - Thinking chain cards cover 76 of 78 two-hop tests (was 5), and two-hop rose from 3.8 to 50.0.
  - The morning gate undid nights 1, 2, 3 and 7. Undoing night 7 alone explains B's recall loss: of the C2 facts first eligible on
    day 7, B gets 1 of 28 right, against 26 of 28 for k2s_bf16; of the other 72 C2 facts, it gets 68 right, against 70.
  - Night 7 also made 115 of the 261 chain dreams, and those never reached the final weights.
- **Shown:** the gate scores ARC-Easy on the first 100 validation questions and undoes a night if the score falls more than 3 points
  below the pre-sleep score on the same 100. B's night scores were 0.84, 0.86, 0.82, 0.88, 0.93, 0.89 and 0.86 against 0.90. After
  night 6, ARC-Easy on the 500-question test set was 89.2, against 89.4 before sleep.
- **Suggested:** on 100 questions, a 4-point drop is within the noise of the answers that flip from night to night, so some of those
  undone nights were false alarms. Whether night 7's drop was real is unknown.

## The arm
- **k2c_r2_g570:** B's flags plus `--gate-arc-n 570`. The gate scores all 570 ARC-Easy validation questions, both before sleep and each
  morning, with the same rule (undo if more than 3 points below). Everything else is exactly B:
  - `--rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2`;
  - `--gen-bs 48`, `--arc-base`, `--tok-budget 1024`, revision 9d280ff7, seed 1;
  - report-only `--think-eval` and `--reword data/week2_reworded.json`.
- The final ARC-Easy score uses the 500-question test split as always, which is disjoint from the validation questions.
- `--gate-arc-n` defaults to 100, which is today's gate byte for byte.

## Marks (fixed now; paired exact McNemar against B, same questions)
- **G (Ben's goal):** two-hop >= 75 of 78.
- **S1 (the steadier gate rescues good nights):** fewer nights undone than B's 4, and recall C2+C4 >= 93.5.
  - **Wrong if** night 7 is undone again, or the arm undoes as many nights as B.
- **S2 (kept nights carry two-step):** two-hop >= B's 39 + 8 (>= 47 of 78), with p < 0.05.
  - **Wrong if** two-hop <= 39 although night 7 is kept. Then the lost night was not what held two-step back; accuracy per dreamed test
    is.
- **No harm:**
  - ARC-Easy 500 >= pre - 5. This is the check that the old gate's undone nights were false alarms. If it fails, the 100-question gate
    was right, and a 570 gate with a 3-point rule is too lenient.
  - diary pooled >= base_diary - 5.
  - changed-new >= B's 53.3 (no drop).
- **Reported:** right-when-dreamed, chain pool per night, each night's 570-question gate score, new-wording recall and cramming gap,
  think-eval, and wall time.
- **Expectation (not a mark):** 1-2 nights undone (night 1 or 2, when tiny pools are drilled hard), recall 93-97, two-hop 50-70.

## Compute
About 3.3-3.5 h on an RTX 5090, or about 4.5 h on an RTX 4090, at roughly 18 GB peak. It runs on Ben's borrowed 4090s when they come up
(free). Otherwise it runs on a 5090 on Vast after the Nov 1 budget reset (about $1.70), or in a free PC slot. Arm A runs first on the PC,
and this test does not depend on it.
