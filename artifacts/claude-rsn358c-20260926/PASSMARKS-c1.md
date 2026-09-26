# rsn-358c1 pass marks (fixed before any 358a result is known; 2026-09-26 02:40 UTC, sleep research thread)

Question 1: does judging "thinking has settled" on the ANSWER cells only (instead of the whole predicted grid) fix the
loop's stop? Question 2 (problem #5 of Ben's overnight goal): with that stop, does the loop beat its plain twin on
fresh bigger puzzles?

ONE change, evaluation only: the stop rule compares answer cells (scripts/claude_rsn358c1_stop.py). No training: the
checkpoints are 358a's own (loop-s1/2, plain-s1/2, BensPC). Fresh sets made by code (seeds 36000+ "pick", 36100+
"check", 300 each), never the sealed 358a test files. The fixed round budget is picked on "pick" (best of
1/2/4/8/12/16/24/32/48; ties -> fewer rounds) and frozen before "check" is scored. Every count below is on "check".
Graded families: sums4, grids5 (practised sizes); sums6, grids6, numbers5 (bigger). Report only: sums8, grids7.

| mark | what (each seed) | pass |
|---|---|---|
| V validity | plain and loop (fixed budget) each ≥ 210/300 on sums4 and on grids5 | else K4 is INCONCLUSIVE |
| K1 | answer-cell stop ≥ fixed budget − 3, each graded family | all five |
| K2 | where the v2 stop is ≥ 10 below the fixed budget: answer-cell − v2 ≥ half that gap (rounded up) | every such family |
| K3 | answer-cell stop ≥ v2 stop − 3, each graded family (no early-stop harm) | all five |
| K4 | loop (answer-cell stop) − plain: ≥ +30 on at least 2 of sums6/grids6/numbers5 and ≥ −10 on the third; ≥ −10 on sums4 and grids5 | yes |

**Stop fix PASS = K1, K2 and K3 on both seeds.** If the v2 stop is never ≥ 10 below the fixed budget, K2 is "nothing
to recover" and the stop fix is NOT NEEDED (K1/K3 still reported).
**Loop beats plain PASS = V and K4 on both seeds.**
**Proved wrong (answer-cell stability is the fix):** on every family where v2 lost ≥ 10, answer-cell recovers less
than a quarter of the gap, on both seeds; or K3 fails by more than 10 anywhere.

Limits written before running: the loop does several times the plain net's compute per question (same weights, not
same compute), as in 358a. The 48 rounds are all computed; stop rounds are not measured savings. Fresh sums/grids come
from very large spaces but are not proven disjoint from training draws (as in 358a); numbers5 hands are fresh draws
and may overlap the sealed test's hands (no training on either). K4 is a second look at the same checkpoints after
358a with one changed rule; 358a's registered verdict stands whatever this shows.
