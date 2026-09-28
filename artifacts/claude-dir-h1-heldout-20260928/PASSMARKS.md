# Pass marks: few-example learning on two more held-out kinds

Written 2026-09-28 19:22 UTC (`date -u`) by Director helper H1, **before any run they judge**. No model has been trained or scored on either new kind; this box has no torch. Design: `DESIGN.md` (same folder). Harness: `scripts/claude_dir_h1_bench.py`, kinds `scripts/claude_dir_h1_kinds.py`, arithmetic `scripts/claude_dir_h1_marks.py` (its selftest reproduces every published maze F_eq to two decimals). **These marks are not changed after any score is seen.** If a mark turns out to be badly chosen, the run is reported as it stands and a new test with a new addendum follows; nothing is re-scored.

## What is being judged

Claim under test (label: **untested** beyond mazes): *a practised looped reasoner learns a new kind of problem from fewer examples than a fresh looped net and than a same-size plain net that had the same practice, and this is not special to mazes.* Already **shown** on 9×9 mazes only (RESULTS-EQ.md: practised loop F_eq 51.00 / 51.29, practised plain 33.79 / 33.58, fresh loop 20.67 / 21.50, fresh plain 22.46 / 25.00).

Two new kinds, judged separately: **graph** (hop distance on a graph, graded at 14 nodes) and **rank** (rank the list, graded at 9 digits). Four arms each, two seeds each (16 training jobs): practised loop, fresh loop, practised plain, fresh plain. Ruler exactly as ADDENDUM-4 (eight rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384; 2,048 updates per rung; qualified 12,000-step sources; unweighted mean of the eight graded-size accuracies = **F_eq**). Accuracy is exact-answer count out of 300 on the graded size.

## Validity (per kind; failure = INCONCLUSIVE for that kind, its holdout stays unopened)

- **V0 kind self-test** (`claude_dir_h1_kinds.py selftest` prints `selftest ok` on the run machine): generator/checker agreement on 300 items per size; a one-cell change is always rejected; pools of 16,384 distinct keys for both seeds with 0 overlap with any dev/holdout panel; the ruler's visit-equality property for every rung; each code-made wrong-by-design predictor scores at most 15 of 300 on the dev graded panel; the reference loop finishes every item within 48 rounds (graph: at most 12; rank: 2).
- **V1 source guard:** the four qualified sources, recomputed on the untouched guard seed `SOURCE_SEED+300`, each at least 190 of 200 on sums and on grids and within 2 of the counts recorded in `source.json` (`check-source`). Any failure invalidates both kinds.
- **V2 live gradients:** the ruler's recorded source gradient check is `nonzero_all` for all four sources, **and V2k:** on a batch of the new kind, one fp32 CPU step of the adaptation loss gives a nonzero gradient to every two-dimensional matrix (the loop's stop head `halt.weight` is exempt because the adaptation loss has no stop term, exactly as in the maze ruler) for all eight (arm, seed) starting nets.
- **V3 usable ladder:** on the **dev** graded panel, at least one of the four arms in at least one seed has accuracy strictly above 10% and strictly below 90% (31 to 269 of 300) on at least three of the eight positive rungs. Not met: INCONCLUSIVE, stop, holdout unopened, never tune against the holdout.
- Only after a kind's dev gate (`DEV-GATE-<kind>.json`, written by `claude_dir_h1_marks.py gate`) says PASS may its holdout be scored, once, for all eight runs, with no model or recipe selection. A blind recount from the raw JSON and this file follows.

## Marks (each kind, each seed judged separately; seeds are never pooled)

Holdout, graded size, F_eq in percentage points. "Loop" means practised loop unless stated.

| Mark | Requirement in each of seeds 0 and 1 |
|---|---|
| **M1** | practised loop F_eq ≥ practised plain F_eq + **5.0** |
| **M2** | practised loop F_eq ≥ fresh loop F_eq + **5.0** |
| **M2b** | practised loop F_eq ≥ fresh plain F_eq + **5.0** |
| **M3** | practised loop is strictly higher than practised plain on at least **5 of the 8** rungs, and strictly higher than fresh loop on at least 5 of 8 (a tie is not a win) |
| **M4** | practised loop F_eq ≥ **20.0** by itself (so a "win" over arms stuck at the floor does not count) |
| **C1 carry-over** | F_low of practised loop ≥ F_low of fresh loop + **5.0**, where F_low is the mean accuracy over the five lowest rungs k = 1, 4, 16, 64, 256 |

**Kind advantage verdict:** PASS when M1, M2, M2b, M3 and M4 all hold in both seeds. REFUTED when, in both seeds, practised loop F_eq is at or below practised plain **or** at or below fresh loop. Anything else is NOT-SHOWN.
**Kind carry-over verdict:** SHOWN when C1 holds in both seeds; REFUTED when practised loop F_low is at or below fresh loop F_low in both seeds; otherwise NOT-SHOWN.

**Roll-up (the sentence Ben may quote, and no more):**
- Both kinds PASS: "shown on mazes and on two further held-out kinds, in two seeds each" (3 kinds).
- One kind PASS and the other not REFUTED: "shown on mazes and one further kind" (2 kinds; the other is reported as not shown).
- Any kind REFUTED: the advantage is **not** established as general; it is reported as mazes-only so far, with the refuting kind named.
- Carry-over is reported as its own row per kind. It is "shown" only for a kind whose C1 verdict is SHOWN.

## Why 5.0 points, 5 of 8 rungs, and 20.0

Numbers from RESULTS-EQ.md (one-time holdout, two seeds, mazes):
- Same arm, two seeds: F_eq differs by 0.29 (practised loop), 0.21 (practised plain), 0.83 (fresh loop), 2.54 (fresh plain). Largest seed-to-seed difference: **2.54** points.
- Same arm, dev versus holdout panel: differences of 0.2 to 1.3 points.
- Pure counting noise: a rung with 300 items near 50% has a standard error of 2.9 points; an eight-rung mean has about **1.0** point; a difference of two such means about **1.4**.
- Training instability is bigger than counting noise: one collapsed rung (fresh loop seed 1, k = 1,024: 0 of 300 between neighbours of 128 and 167) moves an eight-rung mean by roughly 5 points.

So 5.0 points is about 3.5 counting standard errors and about twice the largest seed-to-seed swing seen; it is also the margin the sealed design-race marks already use over plain and over the fresh copy (RACE-PASSMARKS.md). Because a single collapsed rung can still move F_eq by about 5 points, M3 asks for a majority of rungs (5 of 8), so no single rung, in either direction, decides a verdict. For reference, the maze results give practised loop wins over practised plain on 6 and 7 of 8 rungs and over fresh loop on 6 and 6 of 8, so 5 of 8 is a real bar but not a copy of the maze outcome. M4's 20.0 is roughly the level the weakest maze arm reached (fresh loop 20.67); below that, "beating" another arm means beating a floor.
C1 uses 5.0 for the same reason. **Disclosure:** applied to the published maze numbers the marks give M1 +17.21 / +17.71, M2 +30.33 / +29.79, M3 6 and 6 / 7 and 6, C1 +12.13 / +5.73 (the second is close to its bar). This calibration check was made after the mazes were known; it is not evidence about the new kinds.

## The result that would prove the claim wrong

Any of these, on a kind whose validity checks passed, is stated in advance as counting **against** the claim:
1. **REFUTED advantage on either new kind:** in both seeds the practised loop is not ahead of practised plain, or not ahead of fresh loop, on F_eq. Then "a practised loop learns new kinds with fewer examples" is a maze result and nothing more so far.
2. **REFUTED carry-over on both kinds:** in both seeds and both kinds the practised loop's low-example accuracy (F_low) is no better than the fresh loop's. Then skills from sums and grids are not what helped on mazes; the maze gain would need another explanation (for example, the practised loop simply trained more stably).
3. **Advantage only over the fresh loop but not over practised plain (M2 holds, M1 fails), in both seeds on a kind:** reported as "practice helps, the loop does not", which does not support the loop half of the design.

Results that are **not** evidence for the claim: a PASS on a kind whose dev gate failed; any pooled-seed win; k = 0 (cold) accuracy; E50 or E30 alone; a kind chosen or altered after seeing scores.

## Reported for every arm and seed, never gating

Every rung as "x of 300" for the graded size; 300-item secondary sizes (graph 12 and 16 nodes, rank 7 and 10 digits; small panels of 48 holdout items); k = 0 (cold, zero-shot) counts; E50 and E30 (first rung with at least 150 / 90 of 300, "not reached" otherwise); learned-stop versus fixed-depth gap, mean rounds and cap hits; old-kind sums and grids counts before adaptation and after k = 64 and k = 16,384 (forgetting); weights (loop 1,645,726 and plain 1,619,965, as in the ruler); training seconds; the two code-made baseline scores; the per-arm count of collapsed rungs (a rung at least 30 points of 300 below both neighbours). Sleep is **not** run in this test (untested here). Labels in the results file: **shown**, **suggested**, or **untested**.
