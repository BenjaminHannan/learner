# rsn-358u2 blind recount (separate subagent, reply saved 2026-09-28T01:33:07Z)

The subagent read only PLAN.md's acceptance mark, the re-run's runs/loop-s13..16/train_summary.json and tests.json, 358u's
runs/loop-s13..16/tests.json (to recompute the reference means) and this folder's SEAL-run. It did not see RESULTS.md. It
edited nothing, trained nothing and used no GPU. Its reply, verbatim:

Blind recount: NOT ACCEPTED. The re-run meets A1 and the sums8 part of A2, but its grids7 mean is 9.5 points above the band. I only read files; I edited nothing, trained nothing and used no GPU.

Re-run (claude-rsn358u2-20260928), loop nets:
seed | steps_block_nograd | sums8 right | grids7 right | poison V1_identical (report only)
s13  | 0 | 265 of 300 | 206 of 300 | True
s14  | 0 | 250 of 300 | 257 of 300 | True
s15  | 0 | 266 of 300 | 195 of 300 | True
s16  | 0 | 260 of 300 | 176 of 300 | True
4-seed mean: sums8 260.25, grids7 208.50

358u reference (claude-rsn358u-20260927), loop nets, recomputed from its tests.json files:
s13 285 / 211; s14 265 / 187; s15 269 / 193; s16 278 / 145 (sums8 / grids7, each out of 300)
4-seed mean: sums8 274.25, grids7 184.00. Both match the reference numbers in PLAN.md.

Marks:
- A1 (steps_block_nograd = 0 in all 4 loop nets): 4 of 4. MET.
- A2 sums8: band [259.25, 289.25], re-run mean 260.25, difference -14.00. MET, with only 1.0 point to spare.
- A2 grids7: band [169.00, 199.00], re-run mean 208.50, difference +24.50. MISSED, 9.5 points above the top of the band.
- Overall: NOT ACCEPTED. PLAN.md says that if A1 or A2 is missed, the work stops and is reported, and slp-358n3 does not run on these nets.

Notes:
- Most of the grids7 excess comes from s14 (257 of 300). The seed-to-seed spread in grids7 is large in both runs: 358u's s16 scored 145.
- Seal: SEAL-run.sha256.txt has 4 lines naming loop-s13/final.pt through loop-s16/final.pt. The weights are not in the repo, so I could not check the hashes against actual files.
- All 4 loop nets came back, so the "fewer than 4" stop condition does not apply.

Agreement with RESULTS.md: every number matches (A1 4 of 4; sums8 260.25 vs 274.25; grids7 208.50 vs 184.00; V1 4 of 4).
The Mac copies' sha256 were checked by the guard and the collect job against SEAL-run (4 of 4, run-vast/COLLECT.txt).
