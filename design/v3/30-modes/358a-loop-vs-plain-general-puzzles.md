# 358a: loop vs plain on general puzzles, practise small, test bigger (sleep research thread, 2026-09-25)

First registered step of 358 (the reasoner line leaves relation facts; Ben 19:22 UTC). One change against the
plain twin: thinking in rounds with a learned stop. Pass marks: artifacts/claude-rsn358a-20260925/PASSMARKS.md.

## Puzzles (scripts/claude_rsn358a_envs.py), none about relation facts
- sums: column addition with carries. Practise up to 4 digits; test 6 (graded) and 8 (reported).
- grids: Latin-square completion (Sudoku without boxes), unique solution, 9 anonymous symbols relabelled every
  time. Practise 4x4 and 5x5; test 6x6 (graded) and 7x7 (reported).
- numbers: the creative thread's number puzzles, using its solver and checker (scripts/claude_blurt1.py).
  Practise 3 numbers (targets 5-40) and 4 numbers (target 24, 1,062 hands); test the 300 held-out 4-number hands
  and 5 numbers (target 24, graded).

## Nets (scripts/claude_rsn358a_run.py), equal size (~6.4M weights)
Both read the puzzle as a grid and fill the blanks; attention only knows the row/column offset between two cells
(clipped at 4), so the same weights read any size. Plain: 8 layers, one pass. Loop: 2 wider layers applied in
rounds, the puzzle re-added each round, a stop head after each round. Trained on 1-16 rounds, tested up to 48.

## Why this step
It asks the question rsn-357r was going to ask (does thinking in rounds carry a method past what was practised?)
on three different kinds of puzzle instead of relation chains. If it passes, the next steps add kinds (mazes,
sorting, logic, program tracing, relation chains as one kind of many), move from copying solver answers to
reinforcement learning with the checkers, and let sleep practise on these puzzles and on the creative thread's
checked lucky hits. If it fails, the rounds/stop design changes before any of that (one change at a time).

## Overlaps
Creative: same number puzzles and checker, so its lucky hits can become this reasoner's practice. Fix sleep: the
puzzle makers are importable for practice school. Benchmarks: asked to name the public small-model puzzle tests
(Sudoku-Extreme, mazes, ARC-style) this line should be measured on next.
