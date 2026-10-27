# Pond (compute penalty on the loop's stop): pass marks

Written 2026-09-28 to 09-29 (began reading 23:59 UTC, `date -u`; the commit time is in git) by helper "pond" (thread "Charge for thinking"), on top of main `4307fb572`, **before any code for this test exists** and before any score of this design exists. No mark changes after this file is committed. Design: DESIGN.md. Numbers are "x of N". Labels: shown / suggested / untested.

## What is judged
- **Arms (one change each, the size of the penalty):** practised loop + plug-in `claude_dir_pond_{a,b,c}`, `--init pre`, seeds 0 and 1, dev panel only. lambda (weight on expected rounds, per-cell cross-entropy units): **a = 0.001, b = 0.004, c = 0.016**. Arm **z = 0.0** is a control (same plug-in, no penalty), report-only.
- **Control for every reading:** the baseline practised loop on main, `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/adapt.json` (not retrained). Same source net, pool, batches, learner apart from the one change.
- **Panel and fields:** dev 9x9, `rungs[k]["9"]` fields `right`, `fixed_right`, `mean_rounds`, `cap_hits`, of 300. The holdout is not opened. Blind panels never touched.
- Rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384. **Judged rungs J = {64, 256, 1024, 4096, 16384}.** k = 1, 4, 16 are reported only (the net is almost always wrong there, so a cap hit there says nothing).
- Each arm is judged **alone**, seeds never pooled. No arm's result can rescue another.

## Validity (before any mark is read; failure = INVALID, nothing else claimed)
V1 to V5 exactly as H12 PASSMARKS (`artifacts/claude-dir-h12-stop-20260928/PASSMARKS.md` "Validity"): 2,048 updates per rung, 1,645,726 weights and coefficients, same `fixed_depth`, `lr`, `support_sha256` as the baseline, cold-start and old-kind "before" counts within 1 of the baseline's. V3: `scripts/claude_dir_pond_selftest.py` and `scripts/claude_dir_pond_marks.py selftest` each end with an ok line, logs committed, before any run.

## Reference: the baseline on the same dev panel (shown, recounted from the two baseline `adapt.json`)
Cap hits of 300 at k = 64, 256, 1,024, 4,096, 16,384: seed 0: 300, 300, 300, 300, 143. seed 1: 265, 300, 61, 196, 194. So **1 of 5** judged rungs is under 150 in each seed (seed 0: k = 16,384; seed 1: k = 1,024).
Learned-stop `right` / fixed-16 `fixed_right` of 300 at the same rungs: seed 0: 126/122, 263/254, 275/272, 256/243, 286/285. seed 1: 173/171, 277/268, 233/220, 292/288, 261/259.
Baseline F_eq (mean of 8 rungs, points) learned / fixed-16: 51.21 / 49.83 (seed 0), 51.67 / 50.42 (seed 1). F_few (k = 1, 4, 16, 64): 12.42 / 11.83 and 14.75 / 14.58. The higher of the two reads is the learned read in both seeds and both scores, so that is the control value.
The plain net (`eq-runs/plain-s{0,1}-pre/adapt.json`, no stop head, one read) has F_eq 34.04 (seed 0) and 32.63 (seed 1).

## Marks
- **S1, the stop fires on its own** (the point of the test). A judged rung passes S1 when `cap_hits` < 150 of 300 (Ben's/Director's bar; the baseline is at or above 150 on 4 of 5 rungs in each seed). A seed passes S1 when **at least 4 of the 5** judged rungs pass (matches H12's 4-of-5; one rung of luck or one rung the net has not learned does not decide it). Reported beside it: whether all 5 pass.
- **S2, no stop failure.** A judged rung passes S2 when `right` >= `fixed_right` - 6 (the ruler's own limit, `PROTOCOL.md:23`, counts of 300). A seed passes S2 when **at least 4 of the 5** judged rungs pass (H12 asked for all 5; I relax it because the tolerance of 6 is only about 1.5 x the paired counting noise I estimate, so all-5 would fail a good stop about 3 times in 10 by luck; suggested, untested).
- **A1, F_eq not hurt.** Per seed, `F_eq` learned read of the arm minus the control (higher of the baseline's two reads) is >= -7.0 points, in **both** seeds.
- **A2, F_few not hurt** (its own required row, self-check 5). Same, >= -8.5 points on `F_few`, in **both** seeds.
- **P, the plain-net row.** Learned `F_eq` of the arm is >= the plain net's `F_eq` + 10.0 points (34.04 / 32.63 above), in **both** seeds. A plain same-size net scores +0.0 here by construction, so it cannot pass; it also cannot pass S1 (it has no rounds and no stop head; the scorer counts caps only for the loop arm, `claude_fewex_bench.py:87`). The baseline loop clears P by 17.2 and 19.0 points, so a stop that fires so early that the loop stops thinking would fail P. The dev panel layouts are banned from the training pool (`D.panels()` / `D.supports(seed, banned)`), so this is not memorised layouts.
- Report-only, no mark: `mean_rounds` on every rung, the body reading (fixed-16 `F_eq`/`F_few` of the arm against the baseline's fixed-16; a difference beyond 7.0 / 8.5 in either seed prints "BODY MOVED"), 7x7 and 11x11 dev, old-kind counts, both sleeps' rows, the doubt check (H12's, run once on saved checkpoints of the arms).

## Verdict words (per arm; seeds judged separately for S1 and S2)
1. **PONDER WORKS:** S1 and S2 pass in **both** seeds, and A1, A2 and P pass.
2. **FIRES BUT HURTS:** S1 passes in both seeds, but S2, A1, A2 or P fails.
3. **WRONG (for this lambda):** S1 fails in **both** seeds.
4. **NOT SHOWN:** anything else (for example S1 passes in exactly one seed).
**Overall reading:** the idea is **PROVEN WRONG in this form** only if arms a, b and c are all WRONG (a penalty that is too small and one that is large both fail to make the stop fire; result that would prove it wrong). It is **SHOWN** if at least one arm is PONDER WORKS; the recommended lambda is then the **smallest** passing one (Ben: as little as possible). Otherwise NOT SHOWN, with each arm's rung list.
**Control z:** if z (lambda 0) also reaches S1 in both seeds, the words add "PENALTY NOT NEEDED (the label-free halting objective alone fires the stop)". z never sets an arm's word.
Arms are three looks at one idea; I do not correct for that, so a single passing arm is read with the neighbouring arm (if b passes and a, c do not, the page says "isolated"); this is a reading rule, not a mark.

## MARKS SELF-CHECK (thread-helper-common.md), each point in this file
1. **Bars above noise.** S1 bar 150 vs baseline 143 to 300 on 8 of 10 seed-rungs (shown above); F_eq / F_few bars 7.0 / 8.5 are 2 x the noise SD of a difference of two runs' means, 3.33 and 4.17, taken from H12's PASSMARKS (from the baseline's two seeds, 8 and 4 rungs; reproduced by `scripts/claude_dir_pond_marks.py selftest`), and confirmed reproducing by the lr thread (board 21:50 UTC). S2's 6 is the ruler's own rule, a paired count inside one net.
2. **"Every seed" reading.** WRONG needs S1 to fail in both seeds; A1, A2, P need both seeds; PONDER WORKS needs both seeds; one passing seed is NOT SHOWN.
3. **Fair comparator.** Control = the higher of the baseline loop's learned and fixed-16 reads per seed (the plain net has no stop, so it is not a control for the stop; it is used only in P). H12's arm, if it lands, is not a comparator here (different change).
4. **Plain-net row.** P (above), with why memorising cannot pass it.
5. **F_few** is A2, its own required row.
6. **Sleep gates:** none. Sleep rows are report-only. If anyone later wants a gate it must be the mean of 3 sleep draws with margin max(6, 2 x SE).

## Order (fixed now)
1. Commit DESIGN.md and this file. 2. Write and commit the plug-in, marks script, selftests and their logs, and `SEAL-code.sha256.txt`. 3. Queue jobs `pond-a`, `pond-b`, `pond-c`, `pond-z`, then `pond-doubt`, on the Mac CPU ($0). 4. `python -B scripts/claude_dir_pond_marks.py judge` prints every number and word; this page wins if they disagree. 5. A separate blind recount from the raw JSON and this page only. 6. Nothing changes after any arm's dev score is seen. If a job dies or a run is INVALID it is re-run unchanged, never edited.
