# rsn-358e blind recount (committed 2026-09-27 00:31 UTC)

A separate agent recounted from runs/{dense,moe,moe-grow}-s{1,2}/result.json and the pass marks (PASSMARKS.md and addenda 1-3) only. It saw some diagnostic numbers in git log subject lines (it said so) but used none. Its script was later overwritten in the scratchpad by the 358e3 recount, so only its report is kept here, word for word:

> 1. V: dense 199/200 and 198/200; moe 187/200 and 188/200; moe-grow 187/139 and 188/124 (grids5 after A / sums4 after B). All >= 120, so V is met.
> 2. F = grids5 after A - after B: dense 199, 198 (mean 198.5); moe 187, 188 (mean 187.5); moe-grow 147, 118 (mean 132.5).
> 3. moe-grow: FAIL, not proved wrong. Mean F 132.5 <= 168.5 (dense - 30): met. F below dense on each seed (147 < 199, 118 < 198): met. Mean sums4 after B 131.5 >= 180 (dense 200 - 20): NOT met. Proved wrong needs mean F >= 193.5; 132.5, so not proved wrong. Size: 1.64x dense's weights in phase B.
> 4. moe (report only): would fail; mean F 187.5 misses 168.5 (other two clauses met); middle band, not proved wrong.
> 5. S after B (block 0, block 1): moe s1 0.239, 0.378; s2 0.215, 0.146. moe-grow s1 0.779, 0.742; s2 0.131, 0.526.
> 6. maze7 after mazes: dense 154, 149; moe 140, 155; moe-grow 3, 3.
> 7. Flags: moe-grow "weights" is the pre-grow count; its expert_share was recorded after each grow step, so S was read on the grown net; moe-aux0 and dense-narrow were not yet run; all runs torch 2.14.0 on CPU; dense has expert_share null; seed 2 maze7 = 3 at start in every arm; seal hashes match.
