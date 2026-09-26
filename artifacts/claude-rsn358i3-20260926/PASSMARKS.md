# rsn-358i3 pass marks: does the bug-fixed 358i loop beat its plain twin on fresh seeds, on one machine? (fixed before any run; sleep research thread, 2026-09-26 20:04 UTC)

**Why:** rsn-358i2 (artifacts/claude-rsn358i2-20260926/VERIFY-recount.md) confirmed the autocast cache bug and put the fixed loop well ahead of plain on sums6 (+100.50) and grids6 (+51.75). Two things stop that being "shown": the plain reference ran on a different machine and torch version (a torch 2.8 rental vs BensPC torch 2.11), and seeds 1-4 of the fixed loop have now been read. This job answers both with one run, as the Director's board tier T1 ("seeds 5-8, only if 358i2 G0-G3 read like a pass"; they did) and the Thread manager's plain-rerun request (19:59 UTC).
**Change vs 358i2:** none in code. The same sealed files (scripts/claude_rsn358i2_run.py and its imports, cache off, gradient logging), the same tests, 60,000 steps, batch 256, lr and schedule, v2 stop rule with 48 test rounds. New: fresh seeds 5-8 for BOTH arms, both trained on BensPC in this job.
**Arms:** loop (2 x d512) and plain (8 x d256), seeds 5, 6, 7, 8. Report only: plain seeds 1-4 retrained on BensPC.

## Graded test (one test): loop s5-8 vs plain s5-8, both from this job; loop = raw final.pt
The marks are 358t's PASSMARKS-v2 G0-G3, word for word, with plain = this job's BensPC plain on the same seeds.

| mark | pass |
|---|---|
| V0 validity | steps_block_nograd = 0 in every loop train_summary.json. Otherwise INCONCLUSIVE. |
| G0 validity | On every seed, loop and plain are right on >= 210/300 of the practised-size tests in at least 2 of 3 kinds. Otherwise INCONCLUSIVE. |
| G1 bigger | The 4-seed mean of loop - plain is >= +30 on at least 2 of sums6 / grids6 / numbers5, and >= -10 on the third. AND on at least 3 of 4 seeds, loop - plain > 0 on each of those (at least 2) tests. |
| G2 practised | The 4-seed mean of loop - plain is >= -10 on each practised-size test (sums4, grids5, numbers4). |
| G3 stop | On at least 3 of 4 seeds: loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test. AND mean rounds on sums6 > on sums4. |

**PASS = V0, G0, G1, G2 and G3.** Anything else with V0 and G0 met is a FAIL, and it stays a FAIL.
**Proved wrong:** V0 and G0 met, and the mean loop - plain is <= +5 on all three bigger tests.
Note, known before running: numbers4/5 were 0-3 of 300 on both arms in 358i2, so in practice G1 needs both sums6 and grids6 at >= +30.

## Report only
- Plain s1-4 on BensPC vs 358i's rental plain s1-4, per test: the machine difference. And loop s1-4 (358i2) minus BensPC plain s1-4: the 358i2 gaps on one machine.
- sums8/10/12, grids7, loop at fixed rounds, right at any round, mean rounds; torch/CUDA/GPU; minutes per run.

## What each outcome means
- PASS: "the loop beats its same-size plain twin" becomes SHOWN for these puzzle kinds at this size, on one machine. The fixed 358i loop becomes the net for 358b3 (the chat-puzzle gate), the 358x carry-over rerun and the 358y depth sweep.
- FAIL, not proved wrong: the 358i2 gaps were partly machine or seed luck; report the size of the drop.
- Proved wrong: the 358i2 lead does not hold on one machine; the loop design goes back to the exit rule's next step.

**Prediction:** PASS 70%. The 358i2 gaps (+100.50 sums6, +51.75 grids6) are large, and the audit's logs showed plain learning at the same speed on both machines, but grids6 at +30 per 4 fresh seeds is not certain.

**Cost:** $0 (BensPC). 8 graded runs plus 4 report-only runs. 358i2's 4 loops took 103-105 min together on BensPC; estimate 4-6 h in total. Cap 10 h; report-only plain s1-4 run last and are dropped first.
