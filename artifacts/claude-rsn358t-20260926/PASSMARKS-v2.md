# rsn-358t pass marks v2 (fixed before any 358t or 358i result; sleep research thread, 2026-09-26 15:18 UTC)

This replaces PASSMARKS.md (d870b8e66). That version never ran and no number existed for it.
Two reasons for the replacement, both from the Thread manager:
- 15:06: the schedule and EMA bundled together are two changes, so EMA is now report-only.
- 15:09: Ben's idea (cmsg_01FuvegZXjMmeUzStiEFVnEW75v99subJefwkcNdskEmas) is added as its own arm.

Question (unchanged from 358a and 358i): does a loop, which thinks in rounds and has a learned stop, solve BIGGER puzzles than it practised better than its plain same-size twin?

## Arms
Code: scripts/claude_rsn358t_run.py (docstring, `selftest`). Each graded arm is ONE change against 358i's loop arm.

| arm | what changes vs 358i's loop | role |
|---|---|---|
| loop-trm | Training schedule only (TRM-style), 2 x 512. The state is carried forward and detached. Each segment runs 4 rounds without gradient, then 4 with gradient, and is graded once on its final round. The answer is never graded on a fresh first pass alone. A puzzle leaves after being right at the end of 2 segments in a row. A batch lives up to 16 segments. | graded (test A) |
| loop8 | Architecture only (Ben's idea): the plain arm's own 8 x 256 stack, looped, with 358i's loop schedule, state norm and stop head. | graded (test B) |
| loop8-trm | Both changes together. | report only |
| EMA copies of every arm | Averaged weights (0.999). They never touch training. | report only |

Plain for grading is 358i's own plain arm: its runs/plain-s{1..4}/tests.json on origin/builder-outbox or origin/main. If a seed's file is missing, this job trains that plain seed with 358i's recipe (arm "plain" here) and uses it.
Everything else is 358i's: data stream, 60,000 optimizer steps, batch 256, lr and schedule, the v2 stop rule with 48 test rounds.
**Seeds:** 1-4 for loop-trm and loop8; 1-2 for loop8-trm.
**Tests:** artifacts/claude-rsn358i-20260926/tests/, byte-identical to 358i's sealed files. They are TEST-ONLY and each is run once per checkpoint file.

## Marks, applied to test A (loop-trm) and test B (loop8) separately; loop = the arm's raw final.pt

| mark | pass |
|---|---|
| G0 validity | On every seed, the arm and plain are right on >= 210/300 of the practised-size tests in at least 2 of 3 kinds. Otherwise INCONCLUSIVE. |
| G1 bigger | The 4-seed mean of loop - plain is >= +30 on at least 2 of sums6 / grids6 / numbers5, and >= -10 on the third. AND on at least 3 of 4 seeds, loop - plain > 0 on each of those (at least 2) tests. |
| G2 practised | The 4-seed mean of loop - plain is >= -10 on each practised-size test. |
| G3 stop | On at least 3 of 4 seeds: loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test. AND mean rounds on sums6 > on sums4. |
| G4 report | Every test per seed, for raw and EMA weights. Every arm at fixed rounds. sums8/10/12 and grids7. loop8 at fixed 1 round vs plain (the nearest thing to a plain pass). loop8-trm. |
| G5 report | "Does the gap grow?": each arm's loop - plain gap next to 358i's loop gap, per test. Report only. |

**PASS for a test = G0, G1, G2 and G3.** Anything else with G0 met is a FAIL, and it stays a FAIL.
**Proved wrong** (for that change): G0 met, and the mean loop - plain is <= +5 on all three bigger tests.
There are two graded tests, so the chance of one passing by luck roughly doubles. If exactly one passes, its change is re-run on fresh seeds (5-8) before anything is built on it.

**Next step after each outcome** (EXIT-RULE-ADDENDUM-1):
- Either passes: that change (or both, if loop8-trm is best) is carried into 358b3, 358s and 358m, after the seed 5-8 replication if it was the only pass.
- Both fail: the next learned design, two states (TRM row 3).

**Predictions before running:**
- loop-trm PASS 30%.
- loop8 PASS 25%. The deeper round may carry sums better, but a narrower state (256 vs 512) and 4x more sequential layers per round may train more slowly.
- Main risk for loop-trm: at equal optimizer steps each batch stays up to 16 segments, so it sees fewer distinct puzzles.
