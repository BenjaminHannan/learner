# H12 stop-on-mazes: pass marks

Written 2026-09-28 between 21:06:37 and 21:08:34 UTC (`date -u`; commit `21b03ae01` pushed at 21:08:34; the first version of this line carried an estimated 21:14, corrected in the next commit), after DESIGN.md and **before any code for this test exists** (no plug-in, selftest or marks script
has been written) and before any score of this design exists. No mark changes after this file is committed. Design: DESIGN.md.
Numbers are "x of N". Labels: shown / suggested / untested.

## What is judged
- **Variant H12:** practised loop, `--init pre`, seeds 0 and 1, plug-in `claude_dir_h12_stop` (the only change: the maze stop loss, DESIGN.md section 3), harness `scripts/claude_fewex_eq_bench.py` used unedited.
- **Control:** the baseline practised loop already on main, `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/adapt.json`. Same source net, same pool, same batches, same learner apart from the one change. Not retrained.
- **Panel and fields:** the **dev** 9x9 panel, from `adapt.json` `rungs[k]["9"]` (fields `right`, `fixed_right`, `mean_rounds`, `cap_hits`, of 300). **The holdout is not opened by this test.**
- **Type of test: diagnostic fix, report-only on F_eq** (recommended in DESIGN.md section 4). The race bar (F_eq +10) is not used. F_eq and F_few are read with the noise-based bars below, not as a promotion.
- Rungs: k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384. **Judged rungs J = {64, 256, 1024, 4096, 16384}** (5 rungs). k = 1, 4, 16 are reported only: the net gets at most 28 of 300 right there in the baseline (holdout), so nothing is there for a stop to fire on.

## Validity (all before any mark is read; if one fails the word is INVALID and nothing else is claimed)
- V1/V2: the ruler's source checks stand (`RESULTS-EQ.md:11-14`; the harness re-checks them, `identity_source`, `claude_fewex_eq_bench.py:61-69`).
- V3: `scripts/claude_dir_h12_selftest.py` and `scripts/claude_dir_h12_marks.py selftest` each end with an ok line, and their logs are committed, before any variant run.
- V4, per seed: `adapt.json` has `optimizer_updates_per_rung` = 2048, `weights` = 1,645,726 and `persistent_coefficients` = 1,645,726, `fixed_depth` and `lr` equal to the baseline's, and `support_sha256` equal to the baseline's for the same seed.
- V5, per seed: same start net. The cold `rungs["0"]["9"]` and `old.before` records match the baseline's within 1 of 300 on each 9x9 count and within 1 of 200 on each old-kind count (the start net is the same file, so they should be equal; the 1 is slack for a different torch build). If not: INVALID-START, no reading.

## Reference: the baseline on the same dev panel (shown, recounted from the two baseline `adapt.json`)
Learned-stop `right` / fixed-16 `fixed_right` / mean rounds / cap hits, 9x9 dev, of 300:

| k | seed 0 | seed 1 |
|---:|---|---|
| 64 | 126 / 122 / 48.0 / 300 | 173 / 171 / 43.8 / 265 |
| 256 | 263 / 254 / 48.0 / 300 | 277 / 268 / 48.0 / 300 |
| 1,024 | 275 / 272 / 48.0 / 300 | 233 / 220 / 19.9 / 61 |
| 4,096 | 256 / 243 / 48.0 / 300 | 292 / 288 / 34.7 / 196 |
| 16,384 | 286 / 285 / 29.4 / 143 | 261 / 259 / 35.3 / 194 |

Baseline `F_eq` (mean of the eight rungs, dev, learned stop / fixed 16): 51.21 / 49.83 (seed 0), 51.67 / 50.42 (seed 1). Baseline `F_few` (k = 1, 4, 16, 64): 12.42 / 11.83 (seed 0), 14.75 / 14.58 (seed 1).
The baseline's learned-stop `F_eq` is not below its fixed-16 `F_eq` in either seed, so the "higher of the two baseline reads" is the learned-stop read.

## Marks on the stop (the point of the test)
For a run, D = its `fixed_depth` (16), `right`, `fixed_right`, `mean_rounds`, `cap_hits` as above, n = 300.

- **S1, the stop fires on its own.** A judged rung k **passes S1** when all three hold:
  (a) `right` >= 31 (strictly above 10%, the ruler's usable-band floor: a rung the net has not learned cannot show a stop);
  (b) `cap_hits` <= (300 - `right`) + 30 (the stop stays at the cap on about the mazes it gets wrong, plus a fixed 30);
  (c) `mean_rounds` <= D + (48 - D) x (300 - `right`) / 300 (no slower on average than "16 rounds on every solved maze, 48 on every unsolved one").
  A seed **passes S1** when at least **4 of the 5** judged rungs pass. Baseline reference: 0 of 5 (seed 0) and 1 of 5 (seed 1, k = 1,024 only), so the baseline fails S1 in both seeds.
- **S2, no stop failure.** A judged rung passes S2 when `right` >= `fixed_right` - 6 (the ruler's own rule: a stop failure is a learned stop more than two points, more than 6 of 300, below the fixed-16 read; `PROTOCOL.md:23`).
  A seed **passes S2** when **all 5** judged rungs pass. Baseline reference: 5 of 5 in both seeds. This is a comparison inside one net, so run-to-run training noise cancels; only the 300-maze counting noise is left, which the 6 covers as the ruler chose it.

## Marks on accuracy (report-only for promotion; they set the accuracy words)
Per seed, Delta = H12 minus control, in percentage points, of `F_eq` (mean over all eight rungs of 100 x `right` / 300) and of `F_few` (mean over k = 1, 4, 16, 64), on dev.
The control value is the **higher of the baseline's learned-stop read and its fixed-16 read** for that seed (the learned read, in both seeds, unless the numbers change). The H12 value is its learned-stop read (what a user gets).
- **Bars, fixed now: `F_eq` +7.0 points and `F_few` +8.5 points.** How they were set (suggested; the estimate is rough): the baseline's two seeds give one pair of dev counts per rung. The seed-to-seed differences (seed 0 minus seed 1, counts of 300) at k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 are 2, 0, 17, -47, -14, 42, -36, 25.
  Their root mean square is 28.2 counts over the eight rungs (9.4 points) and 25.0 counts over the four few rungs (8.3 points). Each rung is a separate clean-start training (`claude_fewex_eq_bench.py:112`), so I treat rungs as independent and divide by the square root of the number of rungs:
  3.33 points (F_eq) and 4.17 points (F_few) is the noise SD of a difference of two runs' means. The bar is 2 x that (6.66 and 8.34), rounded up to 7.0 and 8.5. Counting noise alone (300 mazes per rung) is smaller: 0.84 and 1.11 points.
  Seed-to-seed differences also include different source nets, so this probably overstates the noise of a same-start comparison, and it rests on two seeds; both are suggested, untested. Under this noise one seed would reach a bar by luck about 2 in 100, both seeds about 5 in 10,000 (suggested).
- **Words, for F_eq and for F_few separately:** HELPS = Delta >= +bar in **both** seeds; HURTS = Delta <= -bar in **both** seeds; otherwise NOT SEPARABLE FROM NOISE, with the two Deltas shown. Never one seed alone.
- **Body reading (report, same words):** the same Deltas computed on the fixed-16 reads (`fixed_right`) of H12 against the baseline's fixed-16 reads. The fixed-16 read does not use the stop, so it shows whether the stop loss changed the body.

## Verdict words (judge each seed alone; seeds are never pooled)
1. **STOP LEARNED:** S1 and S2 pass in **both** seeds.
2. **FIRES BUT HURTS:** S1 passes in both seeds but S2 fails in at least one seed (the stop fires and costs accuracy).
3. **WRONG (the maze stop loss alone does not give a maze stop):** S1 fails in **both** seeds (fewer than 4 of 5 judged rungs pass in each). This is the result that proves the idea wrong, whatever S2 says.
4. **NOT SHOWN:** anything else (for example S1 passes in exactly one seed). Report each seed's rung list.
The accuracy words are a second line under the verdict, never a reason to change it. A verdict of STOP LEARNED **and** F_eq or F_few not HURTS is the only one that supports recommending the loss for the maze adaptation recipe; adopting it in any build is Ben's and the Director's decision, not this page's.

## Report-only (read after the verdict, cannot rescue or sink it)
Every rung's `right`, `fixed_right`, `mean_rounds`, `cap_hits` at 9x9, 7x7 (24) and 11x11 (300); mean rounds by maze size at k >= 256 (does the stop use more rounds on bigger mazes: 7x7 < 9x9 < 11x11?); E50 (first rung at or above 150 of 300);
old-kind counts `old.before`, `old.after_64`, `old.after_16384` and the two sleeps' old-kind and maze rows with their rounds and cap hits. **Old-kind and sleep rows are not marks.** A single sleep draw moves by about 14 of 200 on sums and
5 of 200 on grids with nothing changed (H8 REVIEW X1, from the distill raw files), more than any gap I could read. If anyone wants an old-kind gate later it must be the mean of 3 sleep draws for both arms with margin max(6, 2 x SE).
Training seconds per rung, optimizer updates (2,048 per rung, 512 per sleep), stored weights (1,645,726) and persistent coefficients (same), raw example memory (unchanged from the harness; the plug-in stores nothing).

## Clauses the H8 review flagged, and how they are handled here
- F_few row: `F_few` has its own bar and word (X3). F_eq alone would mostly read the k >= 256 rungs.
- Every-seed reading (X2): every verdict and accuracy word above says "both seeds" or names the seed; there is no "broke an old-kind gate" clause, so any/every cannot differ.
- "Not shown" unless both seeds agree (X4): WRONG needs S1 to fail in both seeds; HELPS and HURTS need both seeds.
- Sleep gates (X1): none used, see Report-only.
- Higher of the controls (P1): the control value is the higher of the baseline's two reads; there is no other control that has a stop head.

## Order (fixed now)
1. Commit DESIGN.md and this file (before any code). 2. Write and commit the marks script, plug-in, selftests and their logs, and `SEAL-code.sha256.txt`; V3 must hold. 3. The Director releases the HELD queue job `handoff/queue/h12-stop-1-dev.md`
(two dev runs on the Mac). 4. `python -B scripts/claude_dir_h12_marks.py judge` reads the two baseline and two H12 `adapt.json` and prints every number and word above; the page wins if the script and this page ever disagree.
5. A separate blind recount from the raw JSON and this page only. 6. Nothing changes after any H12 dev score is seen. The holdout stays sealed unless a later, separately approved step opens it once per run.
