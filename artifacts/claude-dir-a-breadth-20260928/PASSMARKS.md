# Pass marks: does spreading the same practice over ten kinds help a new kind? (test "A", practice breadth)

Written 2026-09-28 21:25 UTC (`date -u`) by Director helper A, **before any run they judge**. No breadth net has been trained or scored (this box has no torch). I have **not seen** any graph or rank score of the running H1 job (`artifacts/claude-dir-h1-heldout-20260928`), and no dev or holdout score of any breadth arm exists. I have seen the published maze numbers (`artifacts/claude-fewex-20260927/RESULTS-EQ.md`), which is disclosed under "Calibration". Design: `DESIGN.md` (same folder). Code: `scripts/claude_dir_a_kinds.py` (ten practice kinds, selftest run here: `SELFTEST-kinds.log`), `claude_dir_a_practice.py` (source practice), `claude_dir_a_bench.py` (ruler), `claude_dir_a_marks.py` (this file's arithmetic; selftest run here: `SELFTEST-marks.log`). **These marks are not changed after any score is seen.** If a mark turns out to be badly chosen, the run is reported as it stands and a new test with a new addendum follows; nothing is re-scored.

## The one change and the question

Today the reasoner's source practice is two kinds, half sums and half Latin squares, 12,000 batches of 64. **Single change:** the same 12,000 batches of 64, spread over **ten** kinds, exactly 1,200 batches each (sums, Latin squares, and eight new code-made kinds: assoc, compose, parity, member, multi, moddiff, odd, bitop). Same nets (loop: 2 shared width-256 blocks, learned stop, cap 48; plain: 8 blocks width 128), same optimiser and schedule, same seeds 0 and 1, same ruler afterwards.

Question, label **untested**: *does breadth of practice make a new, never-practised kind learnable from fewer examples?* Exam kinds (none is in the practice set, none is maze-shaped): **maze** (9×9), **graph** (hop distance, 14 nodes) and **rank** (rank the list, 9 digits). Ruler exactly as ADDENDUM-4 and H1: eight rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384; 2,048 updates per rung; graded size; accuracy = exact-answer count of 300. **F_eq** = unweighted mean of the eight rung accuracies; **F_few** = mean of the four lowest rungs (k = 1, 4, 16, 64).

## Arms (per kind, per seed; seeds are never pooled)

| Name | What it is | Where its numbers come from |
|---|---|---|
| **Bloop** | ten-kind practised loop | new (this test) |
| **Bplain** | ten-kind practised plain net (same size, same practice) | new (this test) |
| **Aloop** | current practice, two kinds, loop | existing runs: maze `eq-runs/loop-s{0,1}-pre/holdout.json`; graph and rank `dir-h1-heldout/runs/<kind>/loop-s{0,1}-pre/holdout.json` |
| **Aplain** | current practice, plain | same places, `plain-…-pre` |
| **Floop, Fplain** | fresh nets (no practice) | same places, `…-fresh` |

Same panels, same 16,384-item pools, same nested prefixes and batch order as the existing runs (the new bench imports the sealed code), so every comparison is paired by seed. Bloop and Bplain are the only new training.

## Validity (a failure means INCONCLUSIVE for what it covers; nothing is tuned on any held-out kind)

- **V0 kinds self-test:** `claude_dir_a_kinds.py selftest` prints `selftest ok`: generator and checker agree on 300 items per level of every kind; a one-cell change is always rejected (new kinds); no new kind uses a token that graph or maze owns; the schedule has exactly 1,200 steps of each of the ten kinds for both seeds; each wrong-by-design constant predictor scores at most 30 of 200 on a dev panel (run here; log in this folder).
- **V1a source qualified:** for each of the four breadth sources, on a fresh guard panel (seed `GUARD_SEED`, 200 per kind), at least **8 of the ten** practice kinds at **180 of 200 or more**, and the recomputed guard counts within 2 of `source.json`. The mastery of the old two kinds is reported, **not** required (with only 1,200 batches each it may fall below the 190 of 200 the old sources reached; that is the price of breadth and is the thing being measured, not a fault). **Bloop failing V1a in either seed: the whole test is INCONCLUSIVE** (an unqualified source cannot show what breadth does). **Bplain failing V1a:** the plain comparison (BM2) is labelled "expressivity" and is not quoted (a rule copied from H1's V4).
- **V2 live gradients:** the source gradient check is `nonzero_all` for all four breadth sources, and **V2k**: one fp32 CPU step of the adaptation loss on 32 items of each exam kind gives a nonzero gradient to every two-dimensional matrix (the stop head `halt.weight` exempt), for all four breadth nets, per kind.
- **V3 usable ladder (per kind):** on the **dev** graded panel, in at least one seed, **Bloop and Aloop are both** strictly between 10% and 90% (31 to 269 of 300) on the same at least **three** of the eight positive rungs. Not met: that kind is INCONCLUSIVE, its holdout stays unopened.
- **V4 plain label (per kind):** Bplain at k = 16,384 on dev below 270 of 300 in either seed, or Bplain source unqualified: BM2 is labelled "expressivity" (not quoted). Never a validity failure.
- **Comparator present:** a kind needs Aloop, Aplain, Floop, Fplain dev **and** holdout files in the places above. If H1's graph or rank comparator does not exist (that kind's dev gate INCONCLUSIVE, or not run), the kind is "NO COMPARATOR", not counted, not a failure.
- Only after a kind's dev gate (`DEV-GATE-<kind>.json` from `claude_dir_a_marks.py gate`) says PASS may its holdout be scored, once, for all four breadth runs, with no selection. A blind recount from the raw JSON and this file follows.

## Marks (each exam kind, each seed judged separately; holdout, graded size)

| Mark | Requirement in **each** of seeds 0 and 1 |
|---|---|
| **BM1 breadth gain** | Bloop F_eq ≥ Aloop F_eq **+ 5.0** points **and** Bloop F_few ≥ Aloop F_few **+ 5.0** points |
| **BM2 beats the same-size plain net with the same practice** | Bloop F_eq ≥ Bplain F_eq **+ 5.0** |
| **BM3 rungs** | Bloop strictly higher than Aloop on at least **5 of the 8** rungs (a tie is not a win) |
| **BM4 beats a fresh net, and is not a floor** | Bloop F_eq ≥ Floop F_eq **+ 5.0** and Bloop F_eq ≥ **20.0** by itself |

**Kind verdict:** CEILING (kind not counted) when Aloop F_eq ≥ 90.0 in either seed (no room to show a gain). Otherwise **PASS** when BM1 to BM4 all hold in both seeds; **HARMED** when in both seeds Bloop F_eq is at least 5.0 **below** Aloop; **REFUTED** when in both seeds Bloop F_eq is less than **2.0** above Aloop; anything else **NOT-SHOWN**.

**Roll-up (the sentence Ben may quote, and no more; counted over valid, non-ceiling kinds, n of 3):**
- **BREADTH-HELPS:** PASS on **at least 2 of the n** kinds and no kind HARMED: "spreading the same practice over ten kinds beat the two-kind practice on p of n held-out kinds, in two seeds each".
- **PROVED-WRONG-HERE:** at least 2 kinds REFUTED or HARMED: "spreading the same practice over ten kinds did not help on r of n held-out kinds".
- **ONE-KIND-ONLY:** exactly 1 PASS, nothing HARMED: reported as not shown to be general.
- Anything else: NOT-SHOWN. Any HARMED kind is named in the sentence. A kind labelled "expressivity" is quoted only with "the same-size plain-net comparison there is labelled expressivity and is not quoted".

## Why these numbers

- **5.0 points / 5 of 8 rungs / 20.0** are the margins of the sealed few-example marks (H1 PASSMARKS.md, RACE-PASSMARKS.md), calibrated there on RESULTS-EQ.md: largest seed-to-seed swing 2.54 points, an eight-rung F_eq mean has about 1.0 point of counting noise, a difference of two about 1.4, and one collapsed rung moves a mean by roughly 5. The same reasoning applies to a difference between two nets.
- **F_few** is required next to F_eq because Ben's measure is "how few examples": it is the four-rung mean of the cheapest rungs, and the H3 addendum uses the same row.
- **2.0 points (REFUTED)** is about 1.4 standard errors of a difference of two F_eq means, chosen as "not clearly above noise"; **HARMED at 5.0** mirrors the gain mark. Both are fixed now.
- **Ceiling 90.0:** an F_eq that high means the low rungs are already solved; a gain of 5.0 cannot appear.

## The result that would prove the idea wrong (stated in advance)

Any of these, on kinds whose validity checks passed, counts **against** "breadth of practice helps":
1. **REFUTED or HARMED on at least 2 of the n valid kinds** (roll-up PROVED-WRONG-HERE): with ten kinds instead of two, and the same total practice, the practised loop does not learn new kinds faster.
2. **HARMED on any kind in both seeds:** spreading the practice thinner makes the loop worse on a new kind (dilution beats variety); reported even if another kind passes.
3. **Practice helps but breadth does not** (`practice_helps_but_breadth_does_not` in `SCORE-<kind>.json`: BM4 holds and the gain over Aloop is below 2.0, in both seeds): the maze gain of the two-kind practice is real but more kinds add nothing.

Not evidence for the claim: a PASS on a kind whose dev gate failed; a pooled-seed win; k = 0 accuracy; E50 or E30 alone; a kind or practice-kind list altered after seeing scores.

## Reported for every arm and seed, never gating

Every rung as "x of 300" (graded size) and the secondary sizes; k = 0 cold counts; E50 and E30; learned-stop versus fixed-depth gap, mean rounds, cap hits; per practice kind mastery counts of each source (x of 200) and the old sums and grids counts before and after k = 64 and 16,384 (forgetting); Bplain minus Aplain and Aloop minus Aplain (report-only); collapsed rungs; weights (loop 1,645,726, plain 1,619,965); training seconds. **Carry-over row:** Bloop and Aloop F_low (k = 1 to 256) and k = 0, report-only. Sleep is **not** run (untested here). Labels in the results file: **shown**, **suggested**, **untested**.

## Calibration and disclosure

- Under these marks, applied to the published maze numbers with Aloop as the loop and no breadth net, nothing can be computed (there is no Bloop yet); the arithmetic itself is selftested in `claude_dir_a_marks.py` on the maze table (`SELFTEST-marks.log`). I chose the 5.0 and 2.0 margins knowing the maze table (loop F_eq 51.00 / 51.29): a gain of 5.0 is possible there (ceiling is 90).
- Aloop numbers come from runs made under the sealed ruler with a source trained for 12,000 steps; Bloop's source has the same total steps but a different item stream; so any F_eq difference is due to the mixture and the item stream. The **only** thing that changed is which puzzles the practice steps draw from (see DESIGN.md "What is identical").
- Nearest neighbours to the exam kinds inside the practice set (`multi` counts equal digits, `compose` chains two lookups, `bitop` and `moddiff` are digit arithmetic) are disclosed in DESIGN.md; a leave-out follow-up is listed there as untested and is **not** part of any mark.
