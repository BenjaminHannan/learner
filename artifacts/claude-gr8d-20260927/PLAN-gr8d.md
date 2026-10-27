# PLAN gr-8 dev: the reader's own likelihood picks the grid size (practice only)

Owner: Plain-English puzzles thread. The plan was written on 2026-09-27; the commit that seals it carries the time (git).
This plan is dev only, on a fresh code-made practice set. It is not a test, and it gives no verdict on any reader. The
marks, the predictions and the result that proves it wrong are fixed here, before any run. The Thread manager chose this
change first at 09:36 UTC, and the scoring follows the point it raised then.

## Why
gr-7d (RESULT-gr7d, 07ccf04be) is post hoc and suggested only. 11 of the gr-7 reader's 16 wrong grids on practice
had the wrong size. 10 of those were too big, mostly by one, with the extra cells padded with blanks. In gr-4's grammar,
the first row's length fixes the size, so one early step decides it. Under an unfamiliar separator or row end, that
step can go wrong. After it, the grammar forces the rest of the grid to that size.

## Brain first
A person who has lost track while copying a row does not commit to it. They look at the shape of the whole block and
check which size fits best. The closest thing the reader has to that check is its own confidence in each whole copy.
This is labelled a guess about the brain, not a claim.

## The one change (scripts/claude_gr8.py, Copier8)
1. **Greedy copy.** The reader (gr-7's adapter, L7, unchanged) copies greedily under gr-4's grammar, exactly as
   `claude_gr7.py run` does. If it writes none, or its grid is not kept, that is the answer. The none/square decision
   does not change.
2. **Forced copies.** Otherwise, the same reader copies again greedily, with the grammar forced to each other size from
   3 to 9.
3. **The score.** Each copy is scored by its **total** log-probability under the reader, over the whole vocabulary,
   including the closing token. It is a total, not a mean per cell. A too-big grid padded with blanks has more cells,
   and every cell costs some probability, so padding cannot win by being easy to predict (Thread manager 09:36).
4. **The pick.** The kept grid with the highest total wins. A forced copy stops as soon as its running total falls below
   the best total so far. Log-probabilities are never positive, so this gives the same winner as scoring every copy
   fully.

The grammar and the choice of the highest score are code (disclosed scaffolding). The probabilities are the reader's own.
No training, no new rule text, and no new model are involved.

## Data
- **The fresh practice set** (artifacts/claude-gr8d-20260927/practice, made by `claude_gr8.py make`) is gr-7d's maker
  with new seeds, 5081 to 5085:
  - 200 squares
  - 200 squares in 40 new formats, 100 of them with a new separator. These formats are also unlike every gr-7d format.
  - 150 lookalikes

  read_latin reads all 200 squares exactly, and no lookalike. No grid is the same as a gr-7d grid. The owner has seen
  only the maker's counts.
- **The replay** is gr-7d's 200 unseen-format items. L7's greedy reads of these are on file (gr-7d run/L7_unseen.jsonl).
  11 of them were read at the wrong size, and the owner has seen those 11 in the gr-7d post-hoc work.

## Smoke test before sealing (disclosed)
Copier8 ran on 2 gr-7d practice squares (d7-sq-000 and -001). They are in no mark here.
- Its greedy copies equalled `copy()` and gr-7d's run file.
- It picked the true size.
- It took about 1.7 times the greedy time.

## Marks (fixed now)
The run is dev only. It passes only if every mark below passes. Greedy and pick come from the same pass on the same items.
| Mark | Test | Bar |
|---|---|---|
| R0 | on the replay, the greedy copy equals gr-7d's L7 read | all 200 (else MISMATCH, and nothing is read from the run) |
| P | of gr-7d's 11 wrong-size items, the pick is still a wrong size | at most 3 |
| D1 | fresh new-format squares read as a wrong grid, pick against greedy | the pick's count at most half the greedy's |
| D2 | fresh squares read exactly | the pick is at least the greedy |
| D3 | fresh lookalikes read as a square | the pick is at most the greedy |
| D4 | fresh squares and new-format squares that greedy reads exactly but the pick does not | at most 2 |

- **TOO-FEW.** If greedy has fewer than 8 wrong grids on the fresh new formats, D1 decides nothing and the outcome is
  TOO-FEW.
- **PROVED WRONG (the score still pays for padding).** 6 or more of gr-7d's 11 wrong-size items are still picked too
  big.

## Predictions (fixed now)
- P: at most 1 of the 11 is still a wrong size, and none is too big.
- D1: greedy has 10 to 25 wrong grids on the fresh new formats, and the pick cuts them by at least two thirds.
- D2 to D4: the pick reads 200 of 200 squares, changes no lookalike from none, and harms 0 exact reads.
- Time: at most 3 times the greedy time per item.

## What follows
- **DEV-PASS.** A registered gr-8 on a fresh blind panel. Its plan goes to the Thread manager first.
- **DEV-FAIL, PROVED WRONG or TOO-FEW.** Count-first training is next (the Thread manager's 09:36 line). Its plan goes to
  the Thread manager first.

## Where it runs
- This container's CPU, $0, 4 threads. cpu/chain.sh checks the seals, gr-7's adapter sha256 and both selftests. Then it
  runs the replay, squares, unseen and lookalikes, each launched once, and the count.
- About 2 hours, estimated.
- A separate agent recounts from the run files before the result goes out.
