# Experiment 27 / M1-F "new names", name loudness fixed at 1.2 — results

Fable (coordinator) · 20–21 September 2026 · run once under FREEZE-NOTE.md (sha a82e1167…), source fingerprint
6bb75f53…, after AUDIT-27-delta (FREEZE-READY: YES). Nine runs, 6,000 updates each, 620–695 s per run, run
integrity clean (9 runs, one source version). Source tables: `report.txt`, `gates.json`, `readouts/*.json`;
the wave-1 verdict was sealed in `wave1-verdict/` before wave 2 was trained and is unchanged by it.

## Registered verdict: PARTIAL — arm F 2/3 seeds. No claim. Control 3/3 (not VOID). Not INVALID.

## Every seed, every cell (R = fixed loop, correct out of 512, RESERVED never-trained codes)

| Cell | Cutoff | Control 2103/04/05 | F (fixed 1.2) 2103/04/05 | L (learned, start 1.2; descriptive) 2103/04/05 |
|---|---|---|---|---|
| c1 | 487 | 512/512/512 | 512 / 512 / 512 | 511 / 512 / 512 |
| c2 | 487 | 512/512/512 | 498 / 502 / 503 | 497 / 500 / 506 |
| c3 | 461 | 512/512/512 | 500 / 504 / 505 | 497 / 507 / 501 |
| c4 | 461 | 512/512/512 | 487 / 494 / 496 | 486 / 500 / 496 |
| c5 | 461 | 512/512/512 | 495 / 500 / 503 | 497 / 501 / 498 |
| c6 | 461 | 512/512/512 | 503 / 505 / 503 | 502 / 502 / 504 |
| p12-1 | 487 | 512/511/511 | 507 / 511 / 510 | 509 / 510 / 509 |
| p12-2 | 487 | 512/512/512 | **479** / 490 / 498 | **485** / 497 / 494 |
| p12-3 | 461 | 512/512/512 | 469 / 493 / 501 | 484 / 491 / 498 |
| s3 | 461 | 512/512/512 | 491 / 504 / 501 | 491 / 498 / 499 |

Paired mark (reserved minus training-pool, must be ≥ −13): F-2103 breaks it on p12-2 (−15) and p12-3 (−19);
every other cell in every seed is between −10 and +5. Two-sided warning: only those two cells.

Signatures: F-2103 and L-2103 = **reserved_gap** (pass on trained codes, miss on reserved). No name_blind, no
never_started, no copy_side_failure, no scale_collapsed, no unnamed. First-stage LINK accuracy on reserved
codes: F 0.918–0.992, chance 0.0625 (experiment 21: at chance).

Trace: arm F scale exactly 1.2000 throughout (buffer); effective name-logit scale 14.2–14.3 (control: 12.9–14.6).
Arm L: the learned scale dipped to 0.80–0.90 and ended 0.82 / 0.85 / 0.93 — it did not collapse.

Open-set read-out (descriptive): choosing the right name among all 4,096 codes instead of the 16 in the
world: pooled first-stage LINK 0.55–0.59 (F), 0.60–0.64 (L). Chance is 0.0002.

## What it means

- Experiment 27's diagnosis was right. Experiment 21 failed because the model turned the name volume to zero
  in the first 500 updates and zero is a trap. Remove that escape (F) — or just start the dial high enough
  (L) — and the same model learns to bind names it has never seen, 92–99 % per step, scoring 469–512 of 512
  where experiment 21 scored 0–149.
- The dial does not need to be hand-fixed: started at 1.2 and left free, it settles around 0.8–0.9 and the
  scores match arm F. The problem in 21 was the starting value (0.139), not learnability.
- Same seed (2103) is the weak one in both arms, on the same cell (12-person, two-step). The seeds share
  training worlds (Q1 limitation), so this looks like a slightly weaker draw, not noise in one arm.

## What it does not mean

- Not a pass. The registered rule is 3/3; the result is 2/3, reported as partial, no claim. No amendment.
- A real, small cost of new names remains: every F/L seed sits below the perfect control, and seed 2103 is
  measurably worse on never-trained names than trained ones on the two hardest cells.
- 16-candidate worlds only. Against all 4,096 codes the name pick is right only ~55–64 % of the time: not
  open-vocabulary naming.
- Arm F is not "one number changed": the scale left the parameter set, so gradient clipping ran over 66
  tensors, not 67 (audit C5). Arm L is the cleaner "only the start value changed" comparison, and it is
  descriptive.
- Nothing about the dispatcher or the talker with new names.

## Predictions (hashed before any code; rows in `artifacts/fable-predictions-ledger.md`)

| Statement | Reviewer | Coordinator | Outcome |
|---|---|---|---|
| F passes 3/3 | 0.40 | 0.30 | FALSE |
| F passes ≥ 1 seed | 0.72 | 0.65 | TRUE |
| Every F seed LINK on c2 ≥ 0.50 | 0.70 | 0.60 | TRUE |
| reserved_gap appears | 0.05 | 0.12 | **TRUE** (worst miss, Brier 0.90 / 0.77) |
| copy_side_failure appears | 0.07 | 0.12 | FALSE |
| L dips to ≤ 1.0 in 3/3 | 0.85 | 0.80 | TRUE |
| L scale_collapsed ≥ 1 seed | 0.25 | — | FALSE |
| L passes 3/3 | 0.30 | 0.22 | FALSE (2/3) |
| Open-set B LINK ≥ 0.90 in passing seeds | 0.30 | — | FALSE (0.58, 0.59) |

Mean Brier: reviewer 0.144 (14 rows), coordinator 0.157 (8 rows). Both of us treated "fails on reserved names
only" as nearly impossible; it is the one thing that happened.

## Next

No rerun or amendment of this registration. The follow-up (what is the smallest fair change that closes the
reserved-name gap on 12-person chained cells: more updates, more names per world in training, or a larger
code pool) goes to a Fable reviewer as a fresh registration with fresh seeds and panels. The pointer-head
(M1c) trigger, copy_side_failure, did not fire.
