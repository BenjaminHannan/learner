# Fair scaling on the real recipe: pass marks (fixed 2026-10-04 before any training run)

Ask: coordinator relay 14:36 UTC 10-04 (Ben: "start now"; budget cap about $7 of vast; keep the shared balance above $1). Design: `design/next-parts/fair-scaling-design.md` (PR #18). Ben's rulings of 10-03 12:09 UTC: no approval needed to scale the core.

## Recipe (identical in every arm except the size flag)
Real pipeline modules pinned at PR #33 commit 34608a1; frozen LFM2.5-1.2B-Instruct revision 0f604ada; contextual reader; copy path; the all-words + pointer exit (`--arm allptr`); practice = the English pilot bank (96 rows) + 8000 generated examples per seed (`--gen 8000`, generator seed 1000 + seed); 2000 updates of 16 rows, lr 1e-3, AdamW wd 0.1, 200 warmup then cosine; same row order per seed (`random.Random(100 + seed)`); exactly the PR #30 round-4 command line plus the size flags. The reader and prefix adapter start from the same weights at every size for a given seed (the core is built under a forked RNG).

## What scales: the core's distinct shared blocks (`--layers`), with width 256, 8 experts, top-2 and the four loops fixed
| size | flags | core params (counted by formula, asserted in code) |
|---|---|---|
| S1 (today's) | `--layers 2` | 9,007,790 |
| S2 | `--layers 4` | 17,949,662 (1.99x) |
| S3 | `--layers 8` | 35,833,406 (3.98x) |
Read, not judged: E32 = `--layers 2 --experts 32` (33,858,...; formula-asserted) as the wide-experts counterpart to S3.
Whole model for the comparison with 1-2B models (Ben): frozen LM 1,170,340,608 + core + reader/prefix/pointer (trained part).

## Test set (never used before)
- **NEW-KINDS-S.json** (sha256 ba9041683369…): written for this round by a helper agent and checked by script; six families that appear in no practice and in no earlier test (the 12 families of the practice bank, FRESH-EN-R3 and NEW-KINDS-R5 are excluded; the six are superlative_extreme, what_changed_state, sum_of_two_quantities, possession_transfer_result, passive_who_did_to_whom, exclusion_only_except). 8 passages per family, 2 questions each, asked of source_text and paraphrase: 192 questions. Independent blind check done before training: a separate agent that saw only passages and questions answered all 192; 192 of 192 match the keys (none flagged ambiguous).
- It is opened once per run (`--extra-eval`). Any change to the recipe after seeing a score on it consumes it.
- Read, not judged, on already-used sets: FRESH-EN-R3 (96 questions) and GEN-HELDOUT-R4.

## Seeds and noise
6 paired seeds (0 to 5). Pairing: seed s at every size. Score = exact-match accuracy on the 192 questions, per run. Intervals: 95% t-interval on the 6 per-seed differences (df 5, t = 2.571), as in PR #30.

## Judged A: does accuracy rise with core size? (S3 minus S1 on NEW-KINDS-S)
- **PASS (scaling shown):** mean difference >= +5.0 points, lower interval bound above 0, and at least 5 of 6 seeds positive.
- **NOT SCALING:** upper interval bound below +3.0.
- **WRONG WAY:** mean <= -5.0 and the upper bound below 0.
- **In between:** anything else (reported as in between, no scaling claim).
## Judged B: is the trend monotone? (needs A = PASS)
- S2 mean lies between S1 mean and S3 mean + 2.0, and S2 minus S1 has a positive mean. Otherwise B = FAILS (non-monotone; the trend is described by its three points only).
## Judged C: does the largest size beat the bare model? (S3 against lm_fewshot, the frozen 1.2B shown the same 8 examples, one deterministic run, same questions)
- **PASS:** lower bound of (seed score - bar) above 0. **FALSIFIED:** mean below bar - 10. **In between:** otherwise.

## What would prove the reading wrong (checks, read)
- Training fit (the 96 bank rows) at each size: if it rises while NEW-KINDS-S does not, the extra size only fits practice.
- The zero-pool lesion (allptr) and the share of wrong answers that are practice answers, per size.
- E32 against S3 at about equal total parameters; per-family scores; per-run training time (does bigger cost more than it gains).
- Learning rate was NOT retuned per size (same lr 1e-3 everywhere): a "not scaling" result may reflect that. One lr 5e-4 run of S3 on all six seeds is run only if budget remains and is reported as a read.

## Limits stated in advance
The interface (8 prefix vectors plus pointer slots, 32-wide translators) is fixed, so a flat result does not show that reasoning cannot scale. Only the distinct-block axis is judged. Claims are limited to the sizes tested (up to 4x) and to this practice recipe, and say nothing about the own-weights model.
