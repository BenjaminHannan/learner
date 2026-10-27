# Opus milestone 3, continuation 3: address-keyed evidence selection — results

2026-09-19, 09:16–09:35 EDT. Local Mac only. **Rental, paid services and BensPC: $0.** `full_verdict: false`.
H1 OFF. Model defaults unchanged; the variant is default-off. This is a diagnostic on the synthetic-vocabulary toy
ladder with privileged supplied cards, **and the variant is given explicit structural help** (see below). Stopped for
review.

## In plain language

- **What changed.** The answer part now picks a memory card by its person and relation words (its "address"),
  matched against the question, and then reads the card as before.
- **Result: choosing jumps from about 1 in 3 to about 9 in 10.** With look-alike cards present it chose right 503
  and 467 times out of 512, against 164 and 161 for the old model.
- **When a fact changes, the answer now changes with it.** For pairs where the relevant fact was swapped, both
  answers were right in 239 and 222 of 256 cases. The old model got 0.
- **Two-step questions did not improve.** A two-step question names only the first person, so the address match
  cannot find the second fact directly.
- **The catch.** The model was *told* where the person and relation sit in each line. That is real help the old
  models didn't get, so this shows the repair works when the address is handed over. It does not show that a model
  would learn to find addresses by itself.

## Budget amendment and corrections

- **Budget amendment.** The shared local-compute cap was extended from 1,800 s to **2,100 s total**, keeping all
  1569.21 s already charged.
  - Recorded as a 0-second `budget-amendment` ledger row and in `artifacts/opus-m03-20260919-071009/BUDGET-AMENDMENT.json`.
  - The ledger was not reset.
  - The amended cap is enforced by `scripts/premonition_address_keys.py`. The frozen baseline source
    `premonition_pool_controls.py` still says 1,800 and was not modified.
- **Correction to the prepared report.** The address-swap test shows that the decoder's *internal* first-answer
  outputs change, not necessarily the generated answers. The test was renamed to say so; its assertions are
  unchanged.
- **Harness v2.** Changes:
  - the amended cap;
  - the dry run keeps the earlier estimate (`dry-before-091706.json`) instead of overwriting it;
  - the comparison refuses a verdict unless both runs completed 2,000 steps;
  - the test split is labelled previously consulted.

Data, losses, schedule, model code and evaluation rules are unchanged.

## What was run (all charged)

| Step | Seconds | Result |
|---|---|---|
| Earlier, under the 1,800 s cap: tests, dry run, verification | 16.49 | 54 OK; did not fit |
| Address tests after the harness change | 1.67 | 6 OK |
| Refreshed dry run | 5.39 | 445.9 s needed (463.5 s under the earlier estimate) vs 523.7 s left, so it fit |
| Train `answer-address-s0` | 182.90 | **completed 2,000 steps** |
| Train `answer-address-s1` | 160.41 | **completed 2,000 steps** |
| Validation evaluation, s0 / s1 | 7.46 / 7.01 | saved outputs match every correctness bit |
| Test evaluation, s0 / s1 (previously consulted) | 3.43 / 3.26 | saved outputs match |
| Paired comparison | 0.68 | verdicts issued after the completion check |
| Final identity verification | 0.34 | all hashes OK |
| **Total for this step** | **389.04** | 372.55 s after the amendment |

**Ledger:** 1941.76 s of 2,100 s used; 158.24 s left.

**Controls, reused and compatible:** pooled `answer-original-s{0,1}`, with the same build, frozen data stream, loop,
schedule, answer loss and card-order generator. The direct-reader `answer-direct-s{0,1}` checkpoints are reported
descriptively. The address arm adds 2,080 parameters, initialised from a dedicated generator; all shared starting
weights are identical to the controls'.

## Results

**Validation** (used for decisions). Address vs pooled, paired, with visit- or triplet-clustered one-sided 99% bounds
from 10,000 resamples.

| | Seed 0 | Seed 1 |
|---|---|---|
| **Single-fact reading** /512 | 512 vs 512 | 512 vs 485, +.053 [+.029, +.080] |
| **Choosing** 1-hop /512 | **503 vs 164, +.662 [+.607, +.713]** | **467 vs 161, +.598 [+.543, +.652]** |
| **Changed-fact pairs, both correct** /256 | **239 vs 0, +.934 [+.895, +.969]** | **222 vs 0, +.867 [+.816, +.914]** |
| Unchanged-fact pairs, both correct /256 | 243 vs 57 | 223 vs 59 |
| Prediction changed on the relevant swap /256 | 243 vs 7 | 241 vs 7 |
| Two-hop combining, practised /341 | 122 vs 118, +.012 [−.063, +.085] | 110 vs 119, −.026 [−.099, +.045] |
| Two-hop combining, held-out /171 | 60 vs 52 | 54 vs 60 |

Against the direct reader the result is the same: choosing 503 vs 170 and 467 vs 162; changed-fact pairs 239 vs 0
and 222 vs 0.

**Predeclared verdicts on validation:**
- **choosing: BETTER**;
- **changed-fact binding: BETTER**.

Both lower bounds are above 0 on both seeds, and both runs were confirmed complete first.

**Unchanged gate, reported only.** It would pass:
- reading 512 and 512;
- choose lower bounds .969 and .885, both above .537;
- seed 1's choose point is .912, below .95.

**H1 stays OFF**, as instructed.

**No constant answers.** With cards there are 16 distinct first tokens. Removing the cards changes 471 and 481 of
512 one-hop answer sequences and drops accuracy to 40 and 33 of 512.

**Test split**, *previously consulted*, descriptive only:
- choosing 495 vs 167 and 458 vs 161;
- changed-fact pairs, both correct: 244 vs 1 and 220 vs 1;
- reading 512 vs 512 and 512 vs 482.

It agrees with validation.

## Limits

- **Explicit structural help.** The variant is told the line layout (token 1 is the person, token 2 the relation or
  LINK) and uses those words' plain embeddings as the only selection key. This shows that *selecting by address*
  fixes one-step choosing and binding once the address is given. It does not show that the model can discover
  addresses from raw text.
- **Two-hop composition is not helped.** Combining is unchanged, with bounds spanning 0. The second fact's person is
  not in the question, so one address match cannot reach it.
- **Screen, not finalist.** Two seeds; finalists need three. Synthetic vocabulary. The supplied cards are privileged
  and identical for every arm. The test split was consulted before.
- **Extra parameters.** The variant has 2,080 more parameters than the controls.

## Files

- **Source:**
  - `premonition/address_reader.py`
  - `scripts/premonition_address_keys.py` (v2)
- **Tests:** `tests/test_premonition_address_keys.py`
- **Artifacts:** `artifacts/opus-m03-20260919-071009/address/`
  - JOURNAL.md, dry.json, dry-before-091706.json
  - runs/, ckpt/ (`answer-address-s0` `7cd5315b…`, `answer-address-s1` `787f79bd…`)
  - eval/, tests/, outputs/
  - compare.json
  - checks/
  - SHA256SUMS (18 files)
- **Budget amendment:** `artifacts/opus-m03-20260919-071009/BUDGET-AMENDMENT.json`
- **Archive:** `archive/opus-m03-20260919-071009-address/` (63 files)
- **Earlier report:** `reviews/opus-milestone-03-address-keys-prepared.md`, with the correction applied.
