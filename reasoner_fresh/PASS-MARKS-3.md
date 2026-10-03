# Pass marks for "think before calling", fixed before training (2026-10-03, fast lane; same sealed eval form)

Change (one): on top of the copy-path base (arm C), the calculator may not be called in loops 0 and 1 (forced NONE);
the first call is read from h+e after 2 core advances (loop 2) and its result is written before loop 3. Total loops stay 4.
Baseline: arm C re-run (call at loop 0). Seeds 0, 1, 2 for both arms (3000 x 16 updates, lr 1e-3).

HEADLINE: right-call rate on new-wording questions (96: seen and unseen answers pooled), per seed.
PASS: delay arm beats the C baseline on the same seed by >= 4 points on all 3 seeds AND by >= 8 points on average,
 AND delay-arm right-call rate on train-wording questions is not more than 3 points below the baseline (mean over seeds).
FALSIFIED: mean gain on new-wording right-call rate < 3 points, or negative on 2 of 3 seeds.
Between: partial, no claim.
Also reported, no mark: final accuracy per answer group (equals call rate with the copy path), operation-correct rate,
per-cell numbers, and the C baseline's seed-2 seen-answer drop versus pooled B seeds 0 and 1 (0.906, 0.854).
Per-question rows are copied back and counted (192 per run) before the box is destroyed.
