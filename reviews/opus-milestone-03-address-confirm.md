# Opus milestone 3, continuation 4: address-key confirmation on fresh examples

2026-09-19, 09:31–09:50 EDT.
- Local Mac only. **Rental, paid services and BensPC: $0.**
- No training, and no cap extension.
- `full_verdict: false`. H1 OFF. Defaults unchanged.
- The address and pooled checkpoints and all earlier results were preserved; they were loaded read-only.
- Stopped for review.

> **These are fresh examples from the existing task family:** the same synthetic-vocabulary toy ladder, generator,
> spec, label-free rule and privileged supplied cards. They are **not** evidence of general language ability.

## Result: CONFIRMED (predeclared rule)

**The rule.** The claim is confirmed only if, in every condition and on both seeds, the paired lower bound of
(address − pooled) is above 0 for choosing and for changed-fact pairs.

**The conditions:**
- O: original;
- N: consistent person renaming;
- P: changed card order;
- NP: both.

**The fresh examples:**
- 256 new worlds with 1,024 questions;
- 256 new oracle-verified triplets, each with an unchanged-fact version and a changed-fact version.

**Overlap:** zero world overlap with the 32,000 training worlds the models consumed, the ladder validation and test
splits, the triplet validation and test sets, and the overnight paired 2-hop sets. Zero exact-visit overlap as well.
The data was saved before any model was loaded.

**Address vs pooled.** Paired, visit- or triplet-clustered one-sided 99% bounds from 10,000 resamples:

| | Seed 0, O | Seed 0, NP | Seed 1, O | Seed 1, NP |
|---|---|---|---|---|
| Single-fact reading /512 | 512 vs 512 | — | 512 vs 480, +.063 [+.039, +.088] | — |
| **Choosing** /512 | **500 vs 147**, +.690 [+.641, +.736] | 496 vs 153, +.670 [+.621, +.719] | **466 vs 164**, +.590 [+.533, +.645] | 455 vs 165, +.566 [+.512, +.621] |
| **Changed-fact pair both correct** /256 | **238 vs 1**, +.926 [+.883, +.961] | 247 vs 1, +.961 [+.930, +.988] | **218 vs 1**, +.848 [+.793, +.898] | 231 vs 2, +.895 [+.848, +.938] |
| Unchanged-fact pair both correct /256 | 241 vs 54 | 247 vs 53 | 231 vs 51 | 234 vs 52 |
| 2-hop combining, practised /337 | 132 vs 136 (bounds span 0) | 124 vs 135 | 111 vs 114 | 106 vs 113 |
| 2-hop combining, held-out /175 | 65 vs 61 (bounds span 0) | 64 vs 63 | 55 vs 62 | 59 vs 64 |

- Conditions N and P look the same as these; all rows are in `confirm/compare.json`.
- Every choosing and changed-fact lower bound is at least +.51.
- Two-hop combining shows no difference in any condition.

**Stability of actual answers.** Counts are how often the answer is identical to the original run's.

| | Address s0 | Address s1 | Pooled s0 | Pooled s1 |
|---|---|---|---|---|
| Card order changed (O vs P), 1-hop /512 | 512 | 508 | 508 | 503 |
| Renaming (O vs N), 1-hop /512 | 483 | 416 | 498 | 496 |
| Renaming (O vs N), 2-hop practised /337 | 209 | 243 | 332 | 328 |
| Renaming (O vs N), 2-hop held-out /175 | 98 | 125 | 174 | 166 |

- The pooled models are more stable under renaming because their answers ignore the person.
- The address models' answers depend on person identity. That is the intended behaviour, but it also makes their
  (mostly wrong) two-hop answers shift under renaming. Seed 1 also changes 96 one-hop answers, with a net accuracy
  change of 466 → 455.

## Actual answers: predeclared examples

These are the first 3 fresh triplets, from `address-s0` and `pooled-s0`.

- **Triplet 0 (the relevant change is a relation swap).** Asked for P13's R0, with cards gold V1, same-person V6,
  same-relation V15, other V1.
  - Both models answer V1.
  - After the swap (gold V6, same-person V1) the address model answers **V6**, which is right. The pooled model still
    says **V1**.
- **Triplet 1.** Both answer V5 at first. After the swap the address model answers **V8** (right); the pooled model
  still says **V5**.
- **Triplet 2.** The address model answers V5 (right). The pooled model answers V12, the *other person's* value for
  the same relation. After the swap the address model answers **V12** (right); the pooled model says V13.
- **Under renaming and reordering (NP).** Same triplets with P13 renamed to P8, P1 to P0, and P0 to P13: every one of
  these answers is identical.

## Cost (charged to the amended shared cap; no extension)

| Step | Seconds |
|---|---|
| Model-free cost estimate (predicted 90.6 s including the reserve) | 0.03 |
| Tests (4 OK) | 1.36 |
| Fresh data, saving and overlap checks (no model loaded) | 8.81 |
| Evaluation: 4 checkpoints × 4 conditions | 26.31 |
| Comparison | 0.53 |
| Stability breakdown and examples | 0.69 |
| Final verification | 0.24 |
| **Total** | **37.97** |

**Ledger:** 1979.73 s of 2,100 s; **120.27 s left**.

## Limits

- **Fresh instances of the same task, not a new task.** Synthetic vocabulary; privileged supplied cards; the address
  variant's explicit layout help. Two seeds: a screen.
- **Renaming stays in range.** It keeps person ids within the 16 ids seen in training; there are no unseen names.
- **Selection only.** Two-hop composition is not improved.

## Next: proposal only

See `design/research/2026-09-19-two-lookup-proposal.md`:
- two sequential learned lookups, where lookup 1's own soft read of the linked person guides lookup 2;
- a matched "two lookups, unchained" control;
- explicit rules against gold-intermediate leakage.

It is not implemented. It needs about 850 s, a new allowance.

## Files

- **Harness:** `scripts/premonition_address_confirm.py`
- **Tests:** `tests/test_premonition_address_confirm.py`
- **Artifacts:** `artifacts/opus-m03-20260919-071009/confirm/`
  - JOURNAL.md, with the predeclaration
  - dry.json
  - data/ (manifest, fresh ladder and triplets, O and N versions, with their sha256)
  - answers.json, holding every actual answer
  - compare.json
  - examples_and_slices.py and examples_and_slices.json
  - checks/
  - SHA256SUMS
- **Archive:** `archive/opus-m03-20260919-071009-confirm/`
