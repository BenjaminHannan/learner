# rsn-358s size scaling, v1 DRAFT for the Thread manager's review (2026-09-27 00:55 UTC; unsealed, not run)

**Question (Ben 14:49 UTC 09-26):** "A bigger reasoner still beats other bigger models of its size." Size = the whole reasoner's weights.
**1x pair = rsn-358i3, already graded PASS** (VERIFY-recount.md, 23dbe806b): loop 2 x d512 (6,438,302) vs plain 8 x d256 (6,385,149), seeds 5-8, BensPC, torch 2.11. Its numbers are reused as they stand; the 1x pair is not rerun.
**3x pair, new runs, ONE change (width only):** loop 2 x d896 (19,524,254) vs plain 8 x d448 (19,430,589), 3.03x and 3.04x. Code: scripts/claude_rsn358s_run.py, which imports 358i2 unchanged. Everything else is identical to 358i3: data stream, 60,000 steps, batch 256, lr and schedule, cache off, v2 stop rule, 48 test rounds, and 358i's sealed tests (TEST-ONLY; counts only, never tuned on). Seeds 9-12, fresh. Both arms run on BensPC.

## Marks (the loop's gap = loop - plain on the bigger tests sums6 and grids6, 4-seed means, of 300)
- **V:** V0 (steps_block_nograd = 0 on every loop run) and 358t's G0 on every 3x run. Otherwise INCONCLUSIVE.
- **S2 (3x loop beats 3x plain):** mean gap >= +30 on sums6 AND on grids6, with the loop ahead on each on >= 3 of 4 seeds.
- **S3 (the gap doesn't shrink):** mean over sums6 and grids6 of the 3x gap >= mean of the 1x gap - 20. 1x: (124.00 + 52.00) / 2 = 88.00, so the 3x mean must be >= 68.00.
- **PASS = V, S2 and S3.** S1 (1x) is already shown by 358i3.
- **Proved wrong:** V met and the 3x mean gap <= +5 on both sums6 and grids6 (a bigger loop no longer beats plain of its size).
- In between: FAIL. If only "loop 3x > loop 1x" holds, it is reported as "a bigger reasoner helps", not as Ben's claim.
- **Why sums6 and grids6 only:** they are 358i3's headline bigger tests. numbers5 is 0 for both arms at 1x.

## Report only
- sums8/10/12, grids7, the practised sizes, fixed rounds, mean rounds, minutes and GPU memory per run.
- The ratio of loop 3x to loop 1x on each test.

**Prediction:** PASS 50%. The plain arm may gain more from width than the loop does (plain's sums gaps came from failing at length, which width can help), so S3 is the risky mark.
**Compute (estimate):** a 3x run is about 3x the FLOPs of a 358i3 run (75-82 min each, 4 at once). If BensPC's 16 GB fits 2 at once, 8 runs is roughly 4 batches of 2 x 2.5-4 h, so 10-16 h in total. Cap 20 h. $0 on BensPC. A rental would cost money and needs Ben's ELI5 plan. **Question for the review:** is a BensPC slot of that length acceptable, or should this start with 2 seeds (9-10) under the same marks, applied to 2 seeds (S2's seed rule becomes "both seeds")?

## Added 00:56 UTC after the Thread manager's 00:54 review: a compute-matched plain arm (report only)
- **plain-unrolled**: 16 layers x d512, 50,572,157 weights. It is the loop's 2-layer block unrolled 8 times with separate weights, so one pass costs about 8 loop rounds, near the loop's mean on sums6 (inferred).
- It asks whether a plain net given about the loop's compute per answer, with no weight sharing and about 8x the weights, closes the gap. Seeds 9-10, BensPC, the same recipe. **Report only.** It is graded neither way, since it breaks same size by design.
- Reported beside it: each arm's inferred FLOPs per answer (loop at its measured mean rounds per test).
- Cost: about 8x a 1x plain run's FLOPs. Estimate 2 runs x 3-6 h. Run after the graded 3x runs, dropped first if time is short.
