# Canonical-operator variant `grow-blind` — the same curriculum, built without labels

Written 2026-09-20 EDT, before any `grow-blind` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

`grow` tests whether a small story lets answer-only learning start, but it builds the small
story out of each question's truth chain — label information. `grow-blind` asks the
harder question: does a small story still work when **nothing about the answer decides
which lines survive**? If `grow` passes and `grow-blind` fails, the win came from the
labels, not from the size.

## The ONE change versus `grow`

The kept lines are a **uniformly random subset of that world's fact lines** of the
scheduled size, and the questions are rebuilt to fit them.

* **updates < G1** (`--grow-g1`, default **1500**): keep `--blind-lines` (default **16**)
  of the visit's 24 fact lines, drawn uniformly at random. No filler or gap line is kept.
  16 is a fixed hyperparameter chosen to sit near `grow`'s measured kept-fact count
  (~15.9 lines per visit); it is not computed per visit and carries no label.
* **G1 <= updates < G2** (default G2 = **3000**): the kept fraction of the remaining lines
  rises linearly to 1, exactly as in `grow`.
* **updates >= G2**: the full story.

Fact lines are recognised from **visible tokens only** — `row[0] == [world]`, `row[1]` an
entity token 52..67, `row[2]` in 8..11 — the same visible-structure test
`A.visible_signature` already uses for the overlap audit.

Every record is then built from the **kept** facts:

* A generator question whose chain is inside the kept subset is used unchanged; its answer
  is read off the kept visible fact row.
* A one-hop question whose fact line was dropped is replaced with `balance`'s
  **constructor**: entity uniform over the world's six people, relation uniform 1/3 each
  (or (1/6, 1/6, 2/3) under `--balance`, which is OFF by default), rejecting draws whose
  fact line is not kept.
* A two-hop question is kept only when a's LINK line and the target's r line are both
  kept, r in {8, 9}. Otherwise a fresh `[4, a, 11, r, 5]` is drawn uniformly from the
  (a, r) pairs that ARE answerable from the kept facts. Measured at fraction 0: roughly
  half the generator's two-hop questions are replaced.
* Safety valve, counted and reported, never silent: if the kept facts support no two-hop
  question at all, a one-hop record is emitted in its place. At the default
  `--blind-lines 16` this did not fire in any probe batch.

Causal eligibility is preserved exactly: a kept line is eligible iff it was eligible in
the original visit, and the question-line index is remapped to the count of kept lines
before it. The `random.Random(1101)` world stream is consumed exactly as in the base
recipe (verified by RNG state after three batches).

## HONESTY: what is and is not label-free

* **The curriculum is label-free.** Line selection is a uniform draw over visible fact
  rows. `row.gold`, `row.supplied`, `row.answer`, `row.hops` and `row.relation` are never
  read — hop count and relation come from the visible question tokens and every answer is
  read off a kept visible fact row. The check suite proves this by poisoning all five
  fields and asserting the batch is bit-identical.
* **The loss is label-free of everything except the answer.** Pure answer cross-entropy at
  .75/.25 (`e0`'s step), no supporting-line term at any update.
* **The intermediate entity is STILL supervised.** The LINK/terminal decomposition gives
  the true intermediate as a target. `grow-blind` obtains it by reading the kept
  `[world] a LINK b` row rather than from `row.gold`, which removes the *annotation* but
  not the *supervision*. Do not describe `grow-blind` as learning two-hop composition
  without intermediate labels. Only `marg-full` removes the intermediate target itself.
* **Question selection is not the generator's.** Roughly half the two-hop questions and a
  quarter of the one-hop questions differ from the generator's. Every one of them is
  answerable from the eligible kept lines (checked with `A.truth_paths`), and relation 10
  is still never a two-hop terminal.
* **The overlap audit is taken against the FULL story**, not the reduced one. A reduced
  story is a subset of the full story, so checking the full story is the conservative
  test; checking the reduced story could never fire.

## Base recipe

v3r, as `e0` is built. `--balance` OFF by default (fresh seeds 3-5 showed the relation
rebalancing is not a net improvement); when set, it changes only the relation weights of
the replacement one-hop constructor. Extra randomness from
`random.Random("fable-startup-grow-blind:<seed>")`.

## Pass marks

Astra's ten R cutoffs, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate: every panel/side native LINK count >= 487, every terminal-oracle count >=
487, s3 native joint >= 461. Incomplete = failed. Wave 1 is seeds 0, 1, 2.

Reported alongside, descriptively: the per-visit census of kept vs replaced vs degraded
questions, and the 250-update `kept_fraction` / `mean_kept_lines` trace.

## Fable's predictions

## Fable's predictions (2026-09-20 ~11:05 EDT, before any run)
This is the fully label-free start-up aid (no supporting-line loss at any time; curriculum built without consulting gold chains). Gold intermediates are still used to build LINK/terminal records, as in e0.
Predictions: at least 2 of 3 seeds start learning (one-hop c1 >= 487/512) — ~55% confidence; the main risk is a relapse when stories grow from 16 lines to full size between updates 1,500 and 3,000. I give ~35% that all three seeds pass all ten R cutoffs. If it works, it becomes the base for the full-strength marginalisation run (no intermediate labels, no hints).
