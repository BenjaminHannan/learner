# rsn-358s pass marks: does a bigger loop reasoner still beat a plain net of its size? (fixed before any run; sleep research thread, 2026-09-27 00:57 UTC)

**Question (Ben 14:49 UTC 09-26):** "A bigger reasoner still beats other bigger models of its size." Size = the whole reasoner's weights. **"Same size" means the same number of weights, not the same compute.** The loop spends about its mean rounds times a plain pass's compute per answer (inferred from layer shapes). Whether a plain net given matching compute closes the gap is the open follow-up. It is not part of this test, since it would be a second change.
Draft history: PASSMARKS-v1-draft.md (da4a36fcc, 5e555090e), then the Thread manager's review at 00:55 UTC (4 points, all taken). The draft's plain-unrolled arm is removed from this test and named as the follow-up.

**1x pair = rsn-358i3, graded PASS** (VERIFY-recount.md, 23dbe806b): loop 2 x d512 (6,438,302) vs plain 8 x d256 (6,385,149), seeds 5-8, BensPC, torch 2.11. Reused as it stands.
**3x pair, new runs, ONE change (width):** loop 2 x d896 (19,524,254) vs plain 8 x d448 (19,430,589).
- Code: scripts/claude_rsn358s_run.py, which imports 358i2 unchanged.
- Identical to 358i3 otherwise: data stream, 60,000 steps, batch 256, lr and schedule, autocast cache off, v2 stop rule, 48 test rounds, and 358i's sealed tests (TEST-ONLY, counts only).
- **Seeds 9, 10, 11, 12**, both arms, all on BensPC. No seed is read (no verdict, no partial gap) until all 8 runs are in.

## Marks (gap = loop - plain, 4-seed means, of 300)
- **V:** V0 (steps_block_nograd = 0 on every loop run) and 358t's G0 on every 3x run. If either arm's training diverges on a seed (a non-finite loss in train_log.jsonl, or practised tests under G0), that seed is INCONCLUSIVE, not a gap. The run is INCONCLUSIVE if any seed is.
- **S2 (3x loop beats 3x plain):** mean gap >= +30 on sums6 AND on grids6, with the loop ahead on each on >= 3 of 4 seeds.
- **S3 (the gap doesn't shrink):** the mean of the sums6 and grids6 gaps at 3x >= the 1x mean - 20. The 1x mean is (124.00 + 52.00) / 2 = 88.00, so 3x must be >= 68.00.
- **PASS = V, S2 and S3.** (S1, the 1x pair, is already shown by 358i3.)
- **Proved wrong:** V met and the 3x mean gap <= +5 on both sums6 and grids6.
- In between: FAIL. If only "loop 3x > loop 1x" holds, it is reported as "a bigger reasoner helps", not as Ben's claim.

## Report only
- sums8/10/12, grids7, the practised sizes, fixed rounds and right at any round.
- Compute per answer on each test: loop = mean rounds x one round's weight-FLOPs (12 x 2 x 896^2 per cell); plain = one pass (12 x 8 x 448^2 per cell, about the same as one loop round). Plus the same row for the 1x pair.
- Minutes per run, and GPU memory per run from the first batch. It is reported before the second batch starts; whether 2 runs fit in 16 GB is read from that line, never guessed.
- The ratio of 3x to 1x on each test, for each arm.

**Prediction:** PASS 50%. S3 is the risk: extra width may help plain's long sums more than the loop's.
**Cost:** $0, BensPC. Estimate 10-16 h, cap 20 h. The Director orders the queue; the Thread manager recommends right after dl-9.
