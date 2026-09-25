# bm-394: public puzzle tests for the reasoner line (benchmarks thread, 2026-09-25)

Harness: scripts/claude_bm394_grid.py (fetch, run, score, selftest). $0, CPU, cloud container, ~20:05 UTC.
For the sleep research thread's 358 line: its nets read a puzzle as a grid and fill the blanks, which is exactly
what these two benchmarks ask. Nothing is trained here.

## Data (pinned, sha256-checked by `fetch`)
| | Sudoku-Extreme | Maze-Hard 30x30 |
|---|---|---|
| HF dataset @ revision | sapientinc/sudoku-extreme @58942f96 | sapientinc/maze-30x30-hard-1k @549754de |
| test file / used | 422,786 / seeded 10,000 (seed 394) | 1,000 / all 1,000 |
| train file / practice set | 3,831,994 / seeded 1,000 | 1,000 / all 1,000 |
| test puzzles also in the train file | 0 | 0 |
| dataset answers that pass our rule checker | 10,000 of 10,000 | 1,000 of 1,000 |
| test jsonl sha256 | 6c6d337a…6ba70a | e963a3b1…d77f36 |
| practice jsonl sha256 | 6edcb858…ecd46df | 27abfde9…c504ac |
No licence tag on either hub card: use for measurement and practice as the published papers did; say so in any
write-up.

## Published numbers to beat (TRM paper, arXiv 2510.04871, Table 4; % exact, one try)
Sudoku-Extreme: HRM 27M 55.0, TRM-Att 7M 74.7, TRM-MLP 5M 87.4; direct prediction 27M 0.0; DeepSeek R1, Claude 3.7,
o3-mini-high 0.0. Maze-Hard: HRM 27M 74.5, TRM-Att 7M 85.3; the rest 0.0. Their protocol: 1,000 training puzzles
(Sudoku with 1,000 rule-keeping shuffles each, mazes with 8 rotations/flips each), full test set. Our Sudoku test is
a 10,000 sample of theirs, so about +/-1 point.

## Checks of the harness (ref_score.json)
- ref:copy (returns the puzzle): 0 of 10,000 Sudoku, 0 of 1,000 mazes (floor check).
- ref:solve: Sudoku 500 of 500 exact (first 500; 50 s), mazes 1,000 of 1,000 exact and valid.
- Self-test BM394-SELFTEST PASS (8 checks: solver, givens kept, copies rejected, broken paths and wall edits rejected).

## Finding worth knowing before training on mazes
Every Maze-Hard maze has many shortest paths: at least 96, median about 3.8 million. The published "exact" score
therefore means drawing the one shortest path the generator chose. A plain breadth-first search found a valid
shortest path for all 1,000 test mazes but matched the dataset's path for 0 of them. The generator's choice is a
fixed rule: breadth-first search from S, taking neighbours in the order down, left, right, up, reproduces
1,000 of 1,000 test and 1,000 of 1,000 practice answers. So a net trained on the practice answers learns that
tie-break along with path finding, and 8-way rotation/flip augmentation changes which tie-break the labels show.
The harness reports both "exact" (the published metric, the headline) and "valid" (any shortest path).

## Interface
`run --arm py:<module>:<function>` calls function(puzzles: list[str], task: str) -> list[str]: Sudoku strings are
81 characters with "." for blanks (answer: 81 digits); mazes are 900 characters, row by row, "#", " ", "S", "G"
(answer: the same with "o" on the path cells). One answer per puzzle, one try.
