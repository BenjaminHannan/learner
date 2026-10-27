# Reliability of the frozen label-free lookup recipe on 48 fresh seeds

Written 2026-09-20 EDT, before any reliability run. DRAFT, prepared by the build agent
from Ben's brief. **Review and amend before running `freeze`: `freeze` hashes this file
into the roster manifest and every worker and every wave re-verifies that hash, so it
cannot be edited once the roster exists.**

## The question

The registered `grow-blind` runs show the recipe working on six initialisation seeds —
but all six drew their worlds, memories and questions from the same training-data stream,
`random.Random(1101)`. That leaves two different claims tangled together: "the recipe is
robust to initialisation" and "the recipe works on this data". This run separates them.

> **How often does the frozen, label-free `grow-blind` recipe pass all ten of Astra's
> answer cutoffs when BOTH the initialisation seed AND the training-data stream are
> fresh?**

Nothing else changes. Each job's `--seed N` sets the initialisation, `A.new_model(N)`, and
the data stream, `random.Random(f"fable-reliability-stream-v1:{N}")`, replacing the fixed
`random.Random(1101)`. The stream is consumed exactly as the frozen recipe consumes it
(`toy_ladder.visit` once per visit plus one trailing `randrange` per batch), so a seed is
a genuinely fresh draw of worlds and questions, not a reshuffle of one draw.

## What is frozen, and re-verified before every job

Read out of the registered `grow-blind` launch manifest, never re-typed. `freeze` refuses
to write a roster whose hyperparameters or schedule differ from the registered run.

* Variant `grow-blind`: answer cross-entropy only (`e0`'s step, .75 canonical / .25
  monolithic), no supporting-line term at any update; random-subset small-story curriculum
  at `--blind-lines 16` for updates < `--grow-g1 1500`, grown linearly back to the full
  story by `--grow-g2 3000`; `--balance` OFF; `--distractors 2`.
* Schedule: 6,000 updates, 16 visits per update, training cap 1,500 s, work cap 1,740 s,
  terminate 1,770 s. Per-seed caps, measured from that seed's own launch.
* Model: `CanonicalOperator(vocab=68, width=48, heads=4, steps=3)`, 79,316 parameters,
  asserted in every worker. AdamW and the v3r lr schedule as frozen.
* Scoring: the final checkpoint only, reloaded from disk, fingerprint-checked before and
  after; the same ten panels at the same ten cutoffs, byte-identical to the registered run
  (sha256 of each panel copied from the registered launch manifest and re-checked in every
  worker).
* The semantic-overlap `forbidden` check stays armed for every record of every update, and
  is taken against the full story.

## Roster

**Seeds 100–147 inclusive: 48 seeds. Fixed before the first job runs.**

* **No replacement seeds.** If a seed fails for any reason it stays in the denominator
  unless it is reclassified as an infrastructure failure under the rule below.
* **Every seed is reported**, including ones that never started. A seed with no completion
  record counts as a failure, not as missing data.
* The roster is written into `reliability_launch.json` at `freeze` time; `wave` refuses any
  seed that is not on it. Seeds 0–5 (the registered runs) are refused outright.

## Pass mark

Astra's ten cutoffs, per seed, **nothing averaged**:

| cells | R cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

A seed passes only if it clears **all ten**. The primary result is the count of seeds that
do.

Reported beside it, never folded into the primary number: Astra's R gate (every panel and
side native LINK count >= 487, every terminal-oracle count >= 487, s3 native joint >= 461),
the ten M (monolithic) counts, and the per-seed training seconds.

## Primary result

`k` of 48 seeds passing all ten cutoffs, with an **exact Clopper–Pearson 95% interval** on
the pass rate. Every failing seed is listed by seed number with each cell it missed and the
R count it reached. No seed-level result is averaged, smoothed or pooled.

## Infrastructure failures

Listed **separately from the scientific result**, with evidence, and named explicitly in
any summary of the run. A seed may be reclassified as an infrastructure failure only if its
`failure.json` shows one of:

* the registered training-time or work deadline (`TimeoutError`) — the box was too slow,
  not the recipe;
* a host-level fault: OOM kill, non-zero exit with no `failure.json`, disk full, the
  supervisor's terminate path firing.

A `nonfinite training loss`, a `nonfinite gradient`, a semantic-overlap abort, or any
result below a cutoff is a **scientific failure**, never an infrastructure one. Both counts
are reported: `k / 48` over the whole roster, and, if any seed was reclassified,
`k / (48 - i)` alongside it with `i` named seed by seed and the evidence quoted.

If the pass rate has to be quoted as a single number, it is the one over the **full 48**.

## Execution

One process per seed, one torch thread per process, `--parallel` at most the roster size.
Local Mac: `PARALLEL=6`. Rented 96-vCPU Linux box: `PARALLEL=48`, whole roster in one
wave. The recipe is CPU-only and deterministic given (seed, stream); the same seed on a
different host may still differ in the last bits because BLAS kernels differ, so the host,
torch version, interpreter and platform are recorded in every `completion.json`.

## Deviations

Any deviation from this document is recorded here before the result is read, with the
reason and the time.

## Fable's predictions

Written 2026-09-20 by Fable before the bundle is shipped; no roster seed (100–147) has been trained anywhere.

Evidence so far: 6/6 seeds (0–5) perfect, but all six shared ONE training-data stream; this roster gives every seed its own stream, which is a
harder and more honest test. My record on this project's forecasts is 2 hits / 5 misses, so read these odds accordingly.

| id | forecast (seeds 100–147, ten answer cutoffs, every seed counted) | p | falsified by |
|---|---|---|---|
| P6 | ≥ 40/48 seeds pass all ten cutoffs | 0.85 | ≤ 39 pass |
| P7 | ≥ 44/48 pass | 0.60 | ≤ 43 pass |
| P8 | 48/48 pass | 0.25 | any scientific failure |
| P9 | every scientific failure is a "never started" seed (one-hop training accuracy < 0.5 at the end), not a near miss | 0.65 | a failing seed with one-hop accuracy ≥ 0.9 |

If fewer than 40 pass, the label-free start-up is not yet a dependable recipe and the start-size sweep moves ahead of everything else.
Remote x86/torch-2.8 results are a separate population from the Mac runs and are never merged with them.
