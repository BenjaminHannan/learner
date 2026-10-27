# rsn-358x pass marks v2: learning a new kind from fewer examples (fixed before any run; sleep research thread, 2026-09-26 15:54 UTC)

This replaces PASSMARKS.md (3220de680), which never ran and had no number.

Why it changed (Thread manager, 15:50 UTC): the primary mark is now sample efficiency. Ben's example (15:42, cmsg_01FuvegZXjMmeUzStiEFVnEWSwBn3kvRrNHJRVH9GEcD9v) is that a person learns to drive in about 40 hours by bringing in skills from other things. His goal (15:41) is to "apply skills learned to other places".

Question: after practising sums, grids and number puzzles, does a net need fewer examples to learn mazes, a kind it has never seen? And does the loop need fewer than the plain net of the same size with the same practice?

Code is scripts/claude_rsn358x_run.py (docstring and `selftest`).
When these marks were fixed, no 358i, 358t or 358x number was known. Only the unregistered small maze trial was known (artifacts/claude-rsn358m-20260926/trial/). In it, plain learned 7x7 fully in 2,000 steps, and the loop learned more slowly.

## Arms (for each of seeds 1-4)
- loop-pre: the 358i loop checkpoint.
- plain-pre: the 358i plain checkpoint.
- loop-fresh and plain-fresh: random weights, same shapes.
- The source checkpoints are used as they are, whatever 358i's verdict. Their sha256 must match artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt.

## Practice and checks
- Every net practises mazes only, for 4,000 steps. Sizes are 5 and 7, batch 256, lr 3e-4 after a 200-step warm-up.
- Each net keeps its own 358i training schedule. All four nets of a seed see the same maze stream.
- Checks happen after 0, 125, 250, 500, 750, 1000, 1500, 2000, 3000 and 4000 steps. That is 0 to 1,024,000 example mazes.
- Each check scores 200 fresh 7x7 and 200 fresh 9x9 dev mazes (seed 4300 + seed, never the test files).
- **Steps-to-bar** is the first check with at least 150/200 right on 7x7. It is 5,000 if the net never gets there.

## Marks
| mark | pass |
|---|---|
| X0 validity | plain-fresh reaches the bar by 4,000 steps on at least 3 of 4 seeds, and all 8 source sha256 values match. Otherwise the run is INCONCLUSIVE. |
| X1 practice carries over (loop) | On the 4-seed mean, loop-pre's steps-to-bar is at most 0.75 x loop-fresh's (at least 25% fewer examples). Also, loop-pre < loop-fresh on at least 3 of 4 seeds. |
| X2 loop learns faster than plain (same size, same practice) | On the 4-seed mean, loop-pre's steps-to-bar is at most 0.75 x plain-pre's. Also, loop-pre < plain-pre on at least 3 of 4 seeds. |
| X3 report | Every curve, 7x7 and 9x9. Solving cold (the 0-step check). plain-pre vs plain-fresh (plain's own carry-over). Steps to 100/200 on 9x9. The mean dev count over the checks. Test counts at the end for all 16 nets (maze7/9/11/13, artifacts/claude-rsn358m-20260926/tests, TEST-ONLY, run once per final-carry.pt). |

**PASS = X0, X1 and X2.** Anything else with X0 met is a FAIL, and it stays a FAIL.
**Proved wrong** ("the loop learns a new kind faster than a same-size plain net with the same practice"): X0 met, and the 4-seed mean steps-to-bar of loop-pre is at or above plain-pre's.
If X1 passes and X2 fails, the report says "practice carries over for the loop, but it does not learn faster than plain".

**Predictions:** X1 45%. X2 20%. The plain net learned mazes quickly from scratch in the small trial.

**Next step:**
- On a PASS: the test moves to 358t's winning arm, and a second held-out kind is added.
- On a FAIL: sample efficiency on a held-out kind joins the list of things the next learned design must show (EXIT-RULE-ADDENDUM-1).
