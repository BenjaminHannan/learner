# Stage 1 results (2026-10-23; numbers copied from the box logs' [result] lines, one seed)

Village `validation` = 8,675 questions held out by names, templates, styles and rule families. Dev = 4,000 sampled
from train shards 380-399. Sealed `test` never built or read.

| Arm | Steps | Dev | Validation |
|---|---:|---:|---:|
| D, premonition v1 FULL (REPORT-V1, 95k visits) | 12,000 | 80.1% | 44.7% |
| Qwen3.8-27B, untrained, instruction + 3-shot (dev n=1,000) | 0 | 45.8% | 39.3% |
| A: Qwen3.5-0.8B + LoRA | 537 | 81.65% | 67.46% |
| B: A + borrowed middle block looped 3x | 418 | 82.15% | 67.57% |
| B scored with 1 loop (lesion) | 418 | 72.90% | 59.88% |
| A at 418 steps (equal-steps check) | 418 | 81.30% | 67.78% |
| A2: Qwen3.5-2B + LoRA | 418 | 84.27% | 69.81% |

Both 0.8B arms hit their time budget, so steps were cut once at step 20 (RUNLOG.md). Train rows seen: ~8,600 (A),
~6,700 (B) of 86,238.

Marks (PREREG-stage1.md):
- P1 (A validation >= 55.0%): **PASS**, 67.46%.
- P2 (A dev - validation <= 25 points): **PASS**, 14.2 points (D: 35.4).
- P3 (B >= A + 2.0 AND 1-loop lesion drops >= 3.0): **FAIL**. Lesion half holds (-7.7 points), but B beats A by only
  0.1 points over the 537-step A, and is 0.2 points BELOW A at equal steps (67.78%). Not the "wrong if" either (B > A; lesion moves B).
  Reading (suggested): B uses its loop, but three passes of the borrowed block buy no more than one pass plus more steps.
- P4: pending A2.
- Untrained 27B is below D: the model knows English but not this task's answer conventions. Borrowing needs training.

## Addendum 1 results (PREREG-addendum-1.md; generalization probes, 4,329 questions each)

| Model | P0 (nothing switched) | Pword (wording switched) | drop | validation |
|---|---:|---:|---:|---:|
| v1 FULL (generalization thread) | 82.7 | 50.6 | 32.1 | 45.6 |
| A: 0.8B, 418 steps | 82.42 | 76.25 | 6.2 | 67.78 |
| A2: 2B, 418 steps | 83.95 | 78.38 | 5.6 | 69.81 |

- W1 (A Pword >= 65.0 and drop <= 16.0): **PASS** (76.25, 6.2). The pretrained reader removes most of the wording gap.
- P4 (A2 >= A + 3.0 on validation): **FAIL**, +2.03 (A2 is better, so not the "wrong if").
- Reading (suggested): for the borrowed models, wording is no longer the main gap; validation (67.8) sits ~9 points
  below Pword, so the rest comes from the other held-out axes (depth / rule families), untested here.

## Seed check (addendum 1, no mark; run on Ben's PC 2026-10-24)
| arm B, seed 1 | dev | validation | P0 | Pword |
|---|---|---|---|---|
| full (2 loops) | 82.45 | 66.33 | 82.88 | 76.88 |
| 1-loop lesion | 74.15 | 58.42 | 74.59 | 67.68 |

Seed spread on validation for B: |66.33 - 67.57| = 1.24 points. B vs A at equal steps (-0.2) is well inside that, so P3's
"loop beats no-loop" half stays a FAIL and is no better than a tie. The lesion half replicates: about -8 points on every set.

Arm A seed 1 (PC): dev 80.53, validation 66.06, P0 81.68, Pword 75.77. B minus A at seed 1: validation +0.27, dev +1.9.
Both seeds now give B within noise of A on validation (seed 0: -0.2, seed 1: +0.27). Seed 2 for both arms is running on the PC.

## Probes Pname / Pdepth / Prule (addendum 1, no marks; arm A seed 0, 418 steps, Vast box 57444974)
| set | n | accuracy |
|---|---|---|
| dev | 4000 | 81.60 |
| validation | 8675 | 65.94 |
| Pname (new names) | 4294 | 81.51 |
| Pdepth (deeper stories) | 4367 | 74.47 |
| Prule (new rules) | 4292 | 80.38 |
Earlier run (same arm and steps): P0 82.42 and Pword 76.25. New names cost about 1 point and new rules about 2; depth costs about 8.
Raw file: `results/probes2/result_a.json`.
Arm B seed 2 (PC): dev 82.13, validation 67.45, P0 81.96, Pword 75.88; 1-loop lesion: validation 59.98 (-7.5).
B validation over seeds 0/1/2: 67.57 / 66.33 / 67.45 (mean 67.12). A seed 2 is pending.
