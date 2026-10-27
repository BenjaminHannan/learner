# rsn-358x pass marks: skills carried over to a new kind (fixed before any run; sleep research thread, 2026-09-26 15:47 UTC)

Ben 15:41 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEW1MwBQ8K4pkaQkCHGK86t3s): "take the brains ability to naturally improve over time and be generally intelligent. Apply skills learned to other plaves."

**Question:** after practising sums, grids and number puzzles, does a net learn a kind it has never seen (mazes) faster than a fresh net? And does the loop gain more from that practice than the plain net of the same size?
- Code: scripts/claude_rsn358x_run.py (docstring and `selftest`).
- Maze kind: scripts/claude_rsn358m_maze.py.
- No 358i, 358t or 358x number was known when these marks were fixed. The unregistered small maze trial was known (artifacts/claude-rsn358m-20260926/trial/). It showed plain learning 7x7 mazes fully in 2,000 steps and the loop more slowly.

## Setup
- **Source nets:** rsn-358i's final.pt, seeds 1-4, loop (2 x 512) and plain (8 x 256), taken as they are, whatever 358i's verdict. Their sha256 values must match artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt.
- **For each seed and arm:**
  - pre: starts from the 358i net;
  - fresh: starts from random weights.
- **Practice:** 4,000 steps of mazes only (sizes 5 and 7, batch 256, lr 3e-4 after a 200-step warm-up). Each arm keeps its own 358i training schedule. The maze stream is the same for pre and fresh.
- **Learning-curve score:** every 250 steps, the net is scored on 400 fresh dev mazes (200 at 7x7, 200 at 9x9, seed 4300 + seed, never the test files). The score is the mean of the 16 counts (0-400).
- **Carry-over (gain):** pre's score - fresh's score.
- **Tests:** artifacts/claude-rsn358m-20260926/tests/maze7, maze9, maze11, maze13 (300 each). They are TEST-ONLY and run once per final-carry.pt.

## Marks
| mark | pass |
|---|---|
| X0 validity | Fresh plain reaches >= 100/200 on 7x7 dev by step 4,000 on at least 3 of 4 seeds (the task is learnable in this budget). All 8 source sha256 match. Otherwise INCONCLUSIVE. |
| X1 carry-over exists (loop) | The 4-seed mean gain of the loop is >= +15, and > 0 on at least 3 of 4 seeds. |
| X2 loop carries more | The 4-seed mean of (loop gain - plain gain) is >= +10, and > 0 on at least 3 of 4 seeds. |
| X3 report | All 16 curves. Steps to reach 150/200 on 7x7 dev. Plain gain. The end-of-practice test counts (maze7/9/11/13) for all 16 nets, with loop pre - plain pre on maze9 and larger. |

**PASS = X0, X1 and X2.** Anything else with X0 met is a FAIL, and it stays a FAIL.

**Proved wrong** (for "the loop carries skills over better"): X0 met, and the mean (loop gain - plain gain) is <= 0.
If X1 passes and X2 fails, the report says "practice carries over, but not more for the loop".

**Predictions before running:**
- X1 50%.
- X2 25%. The plain net learned mazes quickly from scratch in the trial, so its curve may leave little room for any gain.

**Next step:**
- PASS: the carry-over test moves to 358t's winning arm, and a second held-out kind is added.
- FAIL: carry-over joins the list of things a new learned design must show (EXIT-RULE-ADDENDUM-1).
