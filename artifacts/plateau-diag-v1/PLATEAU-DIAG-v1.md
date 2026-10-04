# Plateau diagnosis v1: why do the skills runs stall near 72/100?

Written 2026-10-04 16:20 UTC, before any run. Fast lane (exploratory). Follows the stiffness test (NOT STIFF, `../stiffness-test-v1/results/RESULT-v1.md`).

## What we know
- skmain2 72, skmain3 (lr decay) 65, main4 (step supervision) 71, each scored on 100 in_dist rows spread evenly across the 34 training families (about 3 rows each), so no per-family picture exists yet.
- 50,000 updates over 34 families is about 1,500 updates per family, each row seen once.
- Online training exact match fell from 94% (stage 1) to about 70% (stage 3); rows never repeat, so online train accuracy is already held-out accuracy.

## Step 1: where are the errors? (eval only, no training)
Score main2 on all 1,360 in_dist rows (40 per family) and all 160 family-shift rows, per family.
Reported: per-family table. "Concentrated" if the 8 worst families hold 60% or more of the in_dist errors.

## Step 2: what limits the 8 worst families? (picked automatically from step 1)
All arms start from main2 (copy path, constant lr 1e-3, batch 1), train only on rows of the 8 worst families, and are scored on those families' 320 held-out in_dist rows.
- **F1-F3 (fixed set):** 2,000 rows drawn once (seed s), repeated for 6 passes (12,000 updates), reshuffled each pass. Also scored on 320 of the 2,000 training rows ("train fit").
- **N1-N3 (fresh rows):** 12,000 never-repeated rows of the same families (seed s).
Start = main2's score on the same 320 held-out rows (from step 1).

## Marks (fixed now; several can fire)
- **CAN-NOT-FIT** (the core/exit or the answer-only signal is the limit): mean F train fit < 85% after 6 passes.
- **UNDER-TRAINED** (the 50k mix gave these families too little practice): mean N held-out gain >= +15 points over start.
- **MEMORIZES** (more practice on the same rows doesn't transfer): F train fit >= 85%, N gain < +15 and F gain < +10.
- Otherwise **MIXED**, with the numbers.
What would prove each reading wrong is written into its rule: e.g. UNDER-TRAINED is wrong if fresh focused practice gains under 15 points.

## Run
One Vast RTX 5090. The curriculum is rebuilt on the box from PR #32 (`skills_curriculum`, branch claude/project-thread-y0sxwe @ 57c45293f, seed 1, 200k) and checked against `FULL-BUILD-MANIFEST-200k-seed1.json` (all 7 file hashes matched when rebuilt here). Trainer: `scripts/cap256_launch/skills_pretrain_v1.py` with `--eval-only`, `--dev-kinds`, `--sample-seed`, `--fixed-rows`, `--passes` (defaults unchanged). Scorer: `scripts/cap256_launch/score_plateau_v1.py`. Waves: eval; then F1 N1 F2 N2; then F3 N3. Results are copied back and their sha256 is checked before the box is destroyed.

## Limits
One main2 seed; 8 families; 12,000 updates; exact-match scoring. Says nothing about the vision or village models.
