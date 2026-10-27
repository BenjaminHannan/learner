# Preregistration — story-size stress test of the short-story lookup rule

**Date:** 2026-09-20 (EDT) · **Track A** · **Evaluation only — no training of any kind.**

## What kind of evidence this is

This is **exploratory DEVELOPMENT evidence, not a confirmation run.** It reuses the
development-side checkpoints and a freshly built probe grid to map out where a known
transfer result stops holding. Nothing here is a sealed test, nothing here licenses a
generalization claim, and any cell that looks interesting is a candidate for a separate
registered confirmation, not a conclusion on its own. Written before any stress cell was
evaluated; its sha256 is recorded in `manifest.json` and in `REPORT.md`.

## The result that motivates it

Checkpoints from the startup factorial's **arm A** were trained only on tiny stories —
16 fact rows, no filler or gap rows at all — for 2,500 updates, and were then **never
trained again**. Evaluated with no further training on ordinary full 6-person stories
(24 fact rows plus the generator's normal filler and gap rows) they score about
**99%** on one-call attribute questions (`A/seed-0,1,2`: 1.000 / 0.986 / 0.986 on the
registered `c1` panel; 0.998 / 0.998 / 0.984 on a fresh full-story probe).

The question here is **how far that holds as the story grows, and where it breaks.**

## The models (all loaded read-only; sha256 verified and recorded)

| family | checkpoints | trained on LINK? | role |
| --- | --- | --- | --- |
| `factorial-A` | `<worktree>/artifacts/fable-startup-factorial-20260920/A/seed-{0,1,2}/final.pt` | no | the freeze-before-growth models under test |
| `grow-blind` | `<BASE>/artifacts/fable-operator-grow-blind-20260920/astra_canonical_operator_seed-{0..5}/final.pt` | yes | models that did see growth and LINK |
| `factorial-D` | `<worktree>/artifacts/fable-startup-factorial-20260920/D/seed-{0,1,2}/final.pt` | no (never learned at all) | **negative control**: should sit at chance in every cell |

Arm-A and arm-D checkpoints were never trained on LINK queries. Their LINK and two-hop
numbers are **reported but are not part of their verdict**.

Chance is 1/16 = 0.0625 for attribute questions (16 value tokens) and also 1/16 for LINK
(16 entity tokens).

## The grid — paired and nested

Built once in the fresh RNG namespace `fable-size-stress-v1`.

* **64 base worlds**, each a **full 16-person world: 64 fact rows** (16 people × 3
  attributes + 16 LINK rows) — the most this vocabulary can hold.
* A fixed **6-person subset** per world carries **every** question, so the same questions
  are answerable in every cell. The subset's friend map is closed inside the subset
  (declared deviation, see below) so two-hop questions stay answerable in `F24`.
* **Questions, bit-identical in every cell:**
  * **512 one-call attribute** questions `[4, ENT, REL, 5]`, REL ∈ {8, 9, 10}, balanced
    170 / 171 / 171 (8 per world; counts 3/3/2 with the short relation rotating by world).
  * **256 one-call LINK** questions `[4, ENT, 11, 5]` (4 distinct people per world).
  * **256 two-hop** questions `[4, ENT, 11, REL, 5]` for the two-call executor
    (4 per world) — scored for the `grow-blind` family only.
* **Fact conditions (columns):** `F24` = only the subset's own 24 fact rows.
  `F64` = all 64 fact rows, adding 10 other people whose rows use the same relations and
  the same value pool — distractors by construction.
* **Filler conditions (rows):** 0×, 1×, 3×, 10×, 30× the generator's own filler-only and
  gap rows. **1× is the visit's own filler/gap rows, verbatim.** Blocks 1…29 are fresh
  draws from the **same grammar** (4 distractor rows of `randint(3,6)` filler tokens, then
  gap rows of `randint(4,8)` filler tokens until the 128-token gap budget is met — exactly
  `premonition.toy_ladder.visit`). Multiple *m* keeps blocks 0…*m*−1, so **filler sets are
  nested**: every smaller cell's rows are a subset of every larger cell's.
* **Order:** fact rows keep the generator's order; filler rows are interleaved **uniformly
  at random** using one sort key per filler row drawn once for all 30 blocks, so deleting
  filler rows from a large cell reproduces a smaller cell's row order exactly.
* **Causal eligibility** follows the registered one-hop panels: the question sits after
  every story row, so **every story row is eligible for every question**.

This directly answers the design owner's two criticisms of the old size sweep
(`design/v3/18-audit-before-fable-continues.md` §2): sizes are **paired** (same worlds,
same questions, same answers across every cell) and **full 64-fact worlds are included**.

## What is measured, per cell and per checkpoint — never averaged across seeds

* accuracy: attribute overall and **per relation** (8 / 9 / 10); **LINK separately**;
* **mean attention mass on the correct supporting row**, averaged over the 4 heads and 3
  read steps exactly as the factorial measures it, and its **ratio to uniform** attention
  over that question's eligible tokens;
* **rows and tokens per story**;
* **answer-logit margin** (gold logit minus the best competing logit);
* **two-call execution** on the 256 two-hop questions through
  `astra_canonical_operator.execute`, `grow-blind` only, same grid: final accuracy, the
  accuracy of the intermediate LINK call, and calls per question.

## Exclusion check

Every question's semantic signature (`A.visible_signature` over the eligible visible fact
rows, which ignores filler and row order) is checked against the registered development
panels' forbidden set
(`artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_panels/forbidden-semantics.json`).
This **is** feasible for 16-person worlds, so it is run and the overlap count is reported.
Because the signature ignores filler, the two fact conditions give the only two distinct
signature sets; the filler axis cannot change them.

## Declared deviations and judgment calls

1. **Subset-closed friend map.** Each world's friend map is redrawn until every subset
   person's friend is also in the subset (in addition to `toy_ladder`'s own drawability
   condition). Without this, a two-hop question about a subset person would be unanswerable
   in the `F24` cell and the grid would not be paired. The consequence is that a subset
   person's friend is uniform over the other 5 subset people instead of the other 15; the
   10 other people's friends, all attribute values, row order, filler and the fact grammar
   are untouched.
2. **Uniform interleaving.** The generator shuffles its 4 distractor rows in among the fact
   rows and appends its gap rows at the end. Here all filler rows are interleaved uniformly
   at random among the fact rows, which is what makes the cells nested. Fact-row order is
   the generator's.
3. **Trailing filler tokens inside fact rows** are the generator's own and are left alone;
   the filler axis is the number of filler-**only** rows, as in the factorial.
4. Arm-A/arm-D LINK and two-hop numbers are out-of-distribution for those checkpoints and
   are reported for completeness only.

## Fable's predictions

Reproduced **verbatim**; they were fixed before any stress cell was evaluated.

> Fable's predictions (fixed 2026-09-20 before any stress cell was evaluated): P31 —
> factorial-A checkpoints reach ≥95% attribute accuracy at F24 / 10× filler in ≥2/3 seeds:
> p = 0.60. P32 — ≥90% at F64 / 10× filler in ≥2/3 seeds: p = 0.45. P33 — some cell up to
> 30× filler drops below 80% for ≥2/3 factorial-A seeds: p = 0.50. Expected failure shape
> if it breaks: gradual decline as filler grows (attention spread over more tokens), not a
> cliff.

Scoring: each prediction is a hit (outcome 1) or a miss (outcome 0) against the stated
condition, with Brier score (p − outcome)². Reported in `REPORT.md`.

## Checks that must pass before the numbers mean anything

`tests/test_fable_story_size_stress.py`:

1. **Pairing** — the same questions with the same answers in every cell, for both fact
   conditions and every filler multiple.
2. **Nesting** — every smaller cell's rows are a subset (in order) of every larger cell's,
   and the fact rows are identical across the filler axis.
3. **Answers derivable from the visible rows** — `A.truth_paths` re-derives every answer
   and every two-hop intermediate from the eligible visible rows alone.
4. **Filler rows cannot answer anything** — no filler row matches the fact pattern
   (`row[1]` is never an entity token, `row[2]` is never a relation or LINK), so no filler
   row can be mistaken for a supporting row by the evaluator or serve as an answer.
5. **Determinism** — rebuilding from the namespace gives bit-identical tensors.
6. **Sanity (printed, not asserted)** — the 1× / `F24` cell reproduces roughly the known
   ~99% for arm A.

## Resource discipline

The Mac is running registered training workers. One evaluation process at a time, each
invocation under about five minutes, small per-world batches so attention memory stays
modest, `torch.set_num_threads(1)` and `OMP_NUM_THREADS=1`. No checkpoint folder is ever
written to; everything this run produces lives under
`<worktree>/artifacts/fable-story-size-stress-20260920`.
