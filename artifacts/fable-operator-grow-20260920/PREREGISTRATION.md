# Canonical-operator variant `grow` — a story that starts small instead of a hint

Written 2026-09-20 EDT, before any `grow` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

`e0` (answer CE only, gold intermediates kept) never starts on 2 of 3 seeds. The
hypothesis is that the obstacle is *search*: picking the right line out of ~45 lines /
~300 tokens from answer feedback alone. If that is the obstacle, then making the haystack
small early and growing it back should let answer-only learning start, with no evidence
supervision at any point. If `grow` still fails, search is not the obstacle and the
supporting-line term is doing something else.

## The ONE change versus `e0`

There is **no supporting-line loss at any time** (pure answer cross-entropy at .75/.25 —
`e0`'s step verbatim). Instead the memory each record reads grows:

* **updates < G1** (`--grow-g1`, default **1500**): each visit keeps only the fact lines on
  its records' truth chains, plus **D** further fact lines per record (`--distractors`,
  default **2**) drawn uniformly from that world's other fact lines. Every other line is
  dropped, including all filler and gap lines. Measured: ~15.9 of ~44 visible lines per
  visit survive, and all of them are fact lines.
* **G1 <= updates < G2** (`--grow-g2`, default **3000**): the kept fraction of the
  remaining lines rises linearly from 0 to 1.
* **updates >= G2**: the batch is the un-reduced base-recipe batch, returned untouched
  (verified tensor-for-tensor in the checks).

Dropped lines are removed from the packed memory entirely, not masked. A kept line is
eligible for a question **iff it was eligible in the original visit** — the new
eligibility is the original mask gathered through the kept-line map, never recomputed. The
`random.Random(1101)` world stream is consumed exactly as in the base recipe (verified by
comparing RNG state after three batches).

## HONESTY: what is and is not label-free

* **The loss is label-free of everything except the answer.** No supporting line, no
  attention target, no evidence mask enters the objective at any update. Exactly `e0`.
* **The curriculum is NOT label-free.** Choosing which lines to keep reads each record's
  truth chain, and for two-hop-derived records that chain is the generator's `row.gold`
  annotation. Label information is used to *build an easier syllabus*, even though no
  label enters the loss. The check suite asserts this rather than hiding it: poisoning
  `row.gold` changes a `grow` batch.
* **The intermediate entity is still supervised.** Like `e0`, `grow` keeps the LINK and
  terminal decomposition with the true intermediate as the LINK target.

The fully label-free curriculum is the separate variant **`grow-blind`**; the removal of
the intermediate target is the separate variant **`marg-full`**. A `grow` pass is
therefore evidence that *search* is the start-up obstacle, not evidence that the model can
build its own syllabus.

## Base recipe

v3r, as `e0` is built (generator's own one-hop questions, 2 LINK + 2 terminal + 2
monolithic per visit, v3r lr decay, 6,000 updates, 16 visits per update, same model, same
optimiser, same overlap check, same ten panels, final-checkpoint-only scoring).
`--balance` is **OFF**: fresh seeds 3-5 showed the relation-rebalanced one-hop records are
not a net improvement. Extra randomness (line selection) comes from
`random.Random("fable-startup-grow:<seed>")`.

## Pass marks

Astra's ten R cutoffs, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate: every panel/side native LINK count >= 487, every terminal-oracle count >=
487, s3 native joint >= 461. Incomplete = failed. Wave 1 is seeds 0, 1, 2.

Secondary reading (descriptive): the 250-update logs carry `kept_fraction` and
`mean_kept_lines`, so a regression at G1 or at G2 is visible. A model that is at ceiling
on the small story and collapses when the story grows back is a *different* result from
one that never starts, and must be reported as such.

## Fable's predictions
