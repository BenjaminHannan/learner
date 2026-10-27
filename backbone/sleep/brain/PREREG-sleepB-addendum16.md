# Sleep-B addendum 16: learn more per step: the waste meter, skipping known cards, capping REM drill (written 2026-10-26 ~00:30Z, before any run)

Labels: shown / suggested / untested. Model Qwen3.5-2B, Week-2 world, seed 1, the adopted recipe `ab_ob_b4_nb` at 2x work. Not the village
model, not the card experiments. The design, the reasons and the literature are in
`research/sleep-efficiency-2026-10-25.md` (PR #130, sections 2 and 4: E0-E2). This file seals E0-E2 as written there, with the run
details added. E3-E7 are not part of this test.

## Why
- Ben (2026-10-26 00:12Z) shared the PR #130 report: practice is handed out by fixed rules that never ask whether the model already knows
  the card.
- **Shown (counts from `results_a9/result_ab_ob_b4_nb.json`):** REM gives its pool 11 of every 16 slots in 510 steps a night, however
  small the pool. Night 2's first chain dream was practised about 2,700 times. The mean per dream was 255 on night 3, 77 on night 4,
  and about 15 on night 7.
- **Suggested:** 61-77% of eligible facts are already right before nights 4-7 start, and they keep their share of practice.

## Runs (Week-2, seed 1, Qwen3.5-2B; all in one job, one after another on the same RTX 4090)
- **C (control, and E0's waste meter):** `--arm ab_ob_b4_nb --budget-scale 2 --card-stats`. `--card-stats` is report-only: training is
  bit-identical without it (checked on CPU before the run).
- **T1 (E1):** C + `--skip-known 0.25`. A card that was right at its last closed-book or text practice is kept with probability 0.25,
  else drawn again. A wrong morning probe resets that fact's cards.
- **T2 (E2):** C + `--rem-views 20`. About 20 practices per REM dream a night. Unused REM slots go to NREM cards.
- R (the 4x reference, not rerun) is addendum 9's nb seed 1: recall 91.5, two-hop 38.5, diary 86.4, ARC 92.2.
- Code: the commit that merges PR #130 into this branch, recorded in RESULTS before the run. The same `--gen-bs` and `--tok-budget` are
  used for all three runs.

## Measures
- **Primary:** recall C2+C4, forward, weights only, 200 questions. Pairs are compared question by question with the exact McNemar test
  (`paired.py`).
- **Reported:** two-hop (78), reverse, changed-new, ARC-Easy (500), diary pooled, train seconds per step, wall time, and the `cards`
  record per night.

## Marks (fixed now, as in the note)
- **E0 (waste meter, from C's `nights[i].cards`; decision marks, not pass/fail):**
  - If known_share averages >= 0.40 over nights 3-7, E1 has room. If it averages < 0.20, E1 is unlikely to pass, but it is still run
    and reported.
  - If `rem_cb` known_at_step >= 0.80 on nights 2-5, REM over-practice is confirmed (supports E2).
  - If the last quarter's known_share >= 0.80 on most nights, a plateau stop goes on the list.
  - **Wrong if** known_share stays under 0.20 on every night. That would mean the model still learns from almost every example.
- **E1 (T1) pass, both needed:**
  - T1 recall >= 90.0 (R - 1.5);
  - T1 - C >= +3 points, McNemar p < 0.05.
  - Also needed: T1 two-hop >= C - 5, and no harm.
  - **Wrong if** T1 recall <= C's, or T1's known_share is not below C's (the mechanism did not act).
- **E2 (T2) pass:** T2 - C >= +3 recall with p < 0.05, T2 two-hop >= C - 5, and no harm.
  - **Wrong if** T2 recall <= C's, or two-hop falls by more than 10 (the early REM drill was doing two-hop work).
  - Bonus check: no night whose REM pool is under 8 dreams is reverted.
- **No harm (every run):**
  - ARC-Easy >= 87.6;
  - diary pooled >= C's - 3;
  - changed-new >= C's - 10;
  - no more reverted nights than C.
- **Expectation (not a mark):** C recall 82-87.

## What comes next (not part of this test)
- A pass on seed 1 is rerun on seed 2 before adoption.
- If E1 or E2 passes on seed 2, E7 follows: the winner on K2-Horizon-3.7B with a 4-bit base at 4x, against a k2s_q4 rerun with
  `--card-stats`. It passes if recall >= 91.0, McNemar p < 0.05; it is wrong if recall <= 86.

## Compute
One RTX 4090 from Ben's borrowed pair (the GPU queue), free. About 50-60 min per run, so about 3 h for the job. The reference 2x runs took
about 1,900-2,200 s on a 5090. Qwen3.5-2B needs flash-linear-attention 0.6.0 for its fast kernels, and all three runs use the same
kernels.
