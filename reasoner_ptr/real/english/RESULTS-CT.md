# Copy talker vs LM talker: results (6 paired seeds, 2026-10-04)

Marks: `PASS-MARKS-CT.md`, committed and pushed before any box was rented (commits 58d937e3c and 81866d3c8).
Numbers: `ANALYSIS-CT.json` (from `analyze_ct.py results_ct`). Rows: `results_ct/`, 6 boxes, every copy-back sha256-checked.
Control: round 6's `six` arm (same settings and seeds). Cost about $0.75. Vast credit was $9.17 at 21:07 UTC (shared).

## Verdict by the fixed marks
- **A (talker swap): FAILS.** On the unseen kinds the copy talker scores 13.6% against allptr's 78.2%, a gap of
  -64.5 points (CI -69.5 to -59.6). All 6 seeds are far outside 8 points, and it is below the bare 8-shot LM on both sets.
  The talk stage is 168x faster (0.15 vs 25.1 ms per question), but that does not rescue it.
- **B (the core does real work on unseen kinds): NOT SHOWN.** copytalk minus copytalk_nocore is +0.7 (CI -2.0 to +3.4).

| mean of 6 seeds (exact %) | allptr (R6 six) | copytalk | copytalk_nocore |
|---|---|---|---|
| **Unseen kinds, pooled (384 Qs)** | **78.2** | **13.6** | 12.9 |
| NEW-KINDS-R5 | 81.1 | 13.8 | 14.3 |
| NEW-KINDS2-R6 | 75.3 | 13.5 | 11.5 |
| GEN-HELDOUT-R4 (practised kinds, generated wording) | 99.7 | 97.4 | 41.6 |
| FRESH-EN-R3 (practised kinds, human wording) | 92.2 | 58.7 | 24.5 |
| train fit on the human-written bank | 83-97 | 64-72 | 28-39 |
| talk stage, ms per question (fp32, RTX 3090) | 25.1 (seed 0) | 0.06-0.16 | 0.08-0.17 |

## What it means
- **Shown:** answering through the core alone works on the question kinds it practised in generated wording
  (97.4%, against 41.6% with the core skipped). The core does real work there.
- **Shown:** it collapses on question kinds it never practised (13.6%), and it is weak even on practised kinds written
  by a person (58.7%).
- **Shown (one seed, read only):** the allptr talker barely uses the core on unseen kinds.
  - The control rerun scored 73.2% on unseen kinds.
  - Feeding it the core states of a *different* question (the shuffled-core lesion) still scores 73.2%.
  - 334 of its 384 answers were exactly the same as before.
  - So on new kinds, the 1.2B LM answers by re-reading the question.
  - The zero-pool lesion (0%) was a shock to the LM, not evidence that the core matters. The earlier rounds suspected this.
- **Suggested:** the "beats the bare LM on new kinds" results of rounds 5 and 6 are mostly the LM's own reading, steered by
  practice. The bottleneck is not the talker's cost. It is that the core and reader do not generalize past their
  practised templates. A cheap talker cannot replace the LM until that is fixed.
- **Shown, answer types (copytalk, unseen kinds):**
  - **yes/no:** 46.6%.
  - **one-word spans:** 5.6%.
  - **multi-word spans:** 11.3%.
  - Many misses point at the right place but take the boundaries from the practised kinds. "two plums" for "two", and
    "key was in the drawer" for "in the drawer". "Contains" accuracy is about 33-48% against roughly 86% for allptr.

## Caveats
- **Reproduction check missed** (read, not judged). The allptr seed-0 rerun gave 73.2% on unseen kinds against round 6's
  82.3%, outside the 3-point expectation. Same code path and seed, but a different GPU type (3090 Ti) and run-to-run
  nondeterminism. That is about 2.4 SDs of the seed spread. It does not change verdict A, where the gap is about 60 points.
- One copy-head design was tested: a linear start/end pointer plus a gate, with no dropout or regularization, and training loss went to about 0.
  A different head might do better on boundaries. It is unlikely to close a 64-point gap.
- **Fresh weights each run.** The eval files are the round 4-6 files. No GOLD or blind panels were used.

## Plain summary for Ben
We made the model answer only through its own thinking part, with a tiny "copy the right words" talker. It aces the
question kinds it practised (97%) but fails new kinds (14%), where the old setup scores 78%. A second check showed why:
on new kinds, the big language model in the old setup was answering on its own. It gave the same answers even when we fed
it another question's "thoughts". So the cheap talker isn't the problem. The core has to learn to generalize first.
