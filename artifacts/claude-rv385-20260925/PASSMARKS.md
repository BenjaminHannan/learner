# rv-385 pass marks (thought-memory thread, written 2026-09-25 20:20-20:55 UTC, BEFORE any test grid was made)

Idea (Ben, 19:28 UTC): "if it doesn't like where it is right now in its internal representation, it can revert to an
old one with the old thread as an input, and go a different direction." Ben chose "Build it" at 19:37 UTC.
Plan and research: design/v3/30-modes/384b-revert-and-retry.md (the "Correction to rv-385" section).
Code: scripts/claude_rv385.py (run), scripts/claude_rv385_count.py (re-check and count). Both sealed below.

## One change at a time
Test time only, no training. Plain MiniCPM5-1B (openbmb/MiniCPM5-1B, bf16 on CPU, enable_thinking=False) fills 5x5
Latin-square grids (each number 1-5 once per row and column; grids from the sleep research thread's generator,
claude_rsn358a_envs.make_latin_base, unique solution) one empty cell at a time in row-major order. It picks the number
from its next-token probabilities over "1".."5" after the answer prefix "The number in row R, column C is ",
temperature 1.5 (blurt-3's value, not tuned). The prompt shows the grid and, before the question, what the row and
column already hold ("Row 2 already has: 1, 4, 5. Column 3 already has: 2, 5."); it never says what is missing.
The only "don't like where I am" signal is the visible rule, checked after the model chose: the new number already appears in its row or column. Same step budget and same check in every arm.
- restart     : after a conflict, wipe all numbers the model wrote and start over (fresh tries).
- revert_ban  : go back to the state before the bad move; code rules that number out there; the model sees nothing.
                After 5 failures at one state, go back one more step and rule out the number written there.
- revert_note : go back the same way; no ban; the model is shown the abandoned path from that exact grid
                ("row 2, column 3 = 4, it broke the rule"; "..., then the next empty cell had no number that worked").
                Each distinct abandoned path is listed once (the first practice run listed repeats and the note grew
                without limit at the first cell; fixed before sealing). After 5 failures at one state (repeats count),
                go back one more step. Ben's version.
restart -> revert_ban changes one thing (where to go after a dead end); revert_ban -> revert_note changes one thing
(code bookkeeping replaced by the model reading its old thread).

## Test set (fixed now, never generated before the run)
Two seeds, each its own 80 fresh grids and its own sampling: --seed 385101 and --seed 385202, --n 80, --size 5.
Budget: 60 model choices per grid. Chosen on practice grids only (seed 9001, 12 grids, budget 200): the rule was the
smallest of {40, 60, 80, 120, 160, 200} at which revert_ban solves at least half the practice grids, so neither compared
arm starts at the floor or the ceiling. Practice 1 (grid only): 40 -> 5/12, 60 -> 8/12. Practice 2 (final prompt with
row and column contents): 40 -> 5/12, 60 -> 9/12. Both give 60.
Practice results (seed 9001, budget 200), for the record: practice 1 restart 0/12, revert_ban 11/12, revert_note 2/12
(after the note fix); practice 2 restart 0/12, revert_ban 12/12, revert_note 6/12. First choices matched the solution
19-27% of the time, near blind guessing (20%): the 1B has almost no skill at this task, which limits what the note can
do. Practice 2 note-repeat share 0.59 vs 0.36 for blind guessing.
Changes from the proposal in 384b, all decided on practice data only: the row/column line in the prompt (practice 1
showed first choices at chance); 5x5 instead of "small Sudoku-style grids" with boxes, and the budget rule uses
revert_ban (restart cannot reach a third at any practical budget).

## Marks (the unit is the grid; counts from claude_rv385_count.py, which re-checks every solved grid)
- PASS (Ben's idea helps): in BOTH seeds, revert_note solves at least 6 more grids than restart AND at least 2 more
  than revert_ban.
- PROVED WRONG (the note adds nothing over classic backtracking): in BOTH seeds, revert_note solves no more grids than
  revert_ban.
- Anything else: no clear result, reported as such.
- Validity (any failure voids the run): every grid reported solved passes the re-check; the three arms in a seed use
  the identical 80 grids; no arm exceeds 60 model choices on any grid.

## Predictions (numbered, written before the run)
- P385.1 revert_ban solves more grids than restart in both seeds (going back beats starting over on grids).
- P385.2 revert_note solves fewer grids than revert_ban in both seeds (a 1B does not read its old thread well enough
  to beat code bookkeeping).
- P385.3 revert_note solves more grids than restart in both seeds.
- P385.4 Report-only: in revert_note, the share of choices that repeat a number already listed in the note at that
  exact grid is higher than blind guessing would give (the 1B keeps returning to its favourite number).

## Report-only numbers
first-choice accuracy (share of first choices at a newly reached cell that match the unique solution), total steps,
steps on grids every arm solved, the note-repeat share and its blind-guess baseline.
