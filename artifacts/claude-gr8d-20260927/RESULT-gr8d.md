# RESULT gr-8 dev (practice only): DEV-FAIL. The size pick fixes most wrong sizes, but the grids stay wrong

Owner: Plain-English puzzles thread. Times from `date -u`. Plan and seals: PLAN-gr8d.md (90f863ac9). Run notes:
run/RUN-NOTE.md. Count: run/logs/count.log (ede9539a3). Separate recount: recount/. Post-hoc breakdown: posthoc/. This
is dev on code-made practice data. It is not a test.

## What ran
- The chain ran once on this container's CPU at $0, from 09:36:38Z to 11:45:42Z (2 h 9 min).
- The seals, gr-7's adapter sha256 and both selftests passed before the run.
- In one pass per item, the reader (gr-7's adapter) gave its greedy copy and the size pick. The tasks were the replay
  (gr-7d's 200 unseen items), then 200 fresh squares, 200 fresh new-format squares and 150 fresh lookalikes.

## Marks
| Mark | Result | Bar | |
|---|---|---|---|
| R0 | the replay's greedy copy equals gr-7d's read on 200 of 200 | all 200 | pass |
| P | of gr-7d's 11 wrong-size reads, the pick is still a wrong size on 1 (too big on 1) | at most 3 | pass |
| D1 | wrong grids on the fresh new formats: greedy 37, pick 33 | pick at most 18 | **FAIL** |
| D2 | fresh squares exact: greedy 200, pick 200 | pick at least greedy | pass |
| D3 | fresh lookalikes read as a square: greedy 5, pick 5 | pick at most greedy | pass |
| D4 | exact greedy reads the pick spoiled: 0 (the pick fixed 4) | at most 2 | pass |

**The outcome is DEV-FAIL** (D1). It is not proved wrong: only 1 of the 11 is still picked too big, against the bar of
6. A FAIL stays a FAIL.

## Predictions
- **P:** "at most 1 still a wrong size, none too big". Wrong size was met (1). None too big failed: 1 was still too big.
- **D1:**
  - "greedy has 10 to 25 wrong grids" failed. It had 37.
  - "the pick cuts them by at least two thirds" failed. It cut them from 37 to 33.
- **D2 to D4:** "200 of 200, no lookalike changed, 0 harmed" was met.
- **Time:** "at most 3 times greedy" was met. On the same 200 replay items, the median was 12.4 s against gr-7d's 6.4 s,
  about 1.9 times.

## What the size pick did
- **The size is fixed.** On the fresh new formats, wrong-size reads fell from 21 to 7. On gr-7d's 11 wrong-size items, the
  pick found the true size for 10.
- **The cells are still wrong.** Of those 10, only 1 became exact. On the fresh new formats, exact reads rose only from
  162 to 166. On all 200 replay items, they rose from 179 to 180.
- **Where the errors are.** Almost every wrong grid is in a new-separator format: 36 of 37 greedy, 32 of 33 pick.
  Formats with a separator seen in training read 99 of 100 either way.

## What is still wrong (post hoc, report only)
posthoc/why.py was written after the count, so this section is a suggested reading and not a registered result.
- **By separator (pick, wrong of items):**
  - " . " 12 of 20
  - " * " 9 of 30
  - "=" 5 of 10
  - " : " 4 of 15

  The other new separators read almost all exactly.
- **No cell shares a tokenizer token with its neighbours** in any of the 200 items (the panel makers' "token clash"
  test). So merged tokens do not explain the errors.
- **The right-size wrong picks** are 26 grids, with 58 rows that differ from the truth:
  - 31 rows have a digit dropped or added
  - 8 have the same digits in moved places
  - 10 are another row of the square
  - 9 have a digit changed

  In three examples, a digit next to a run of blanks was dropped, or moved by one place, or a row was replaced by a later
  row.
- **Suggested reading.** Under an unfamiliar separator, the reader loses count inside runs of blanks and loses track of
  rows. A wrong size was one symptom of that, and fixing only the size leaves the rest.

## What follows from the plan, and a caveat
PLAN-gr8d named count-first training as the next step after a DEV-FAIL. This result argues against it. The size pick
already gives the reader the right size in most cases, and the grids stay wrong. A reader trained to count first would
fix the same size errors and likely leave the same slips. The next plan goes to the Thread manager before anything is
sealed.

## Disclosures
- **The count's squares lines are doubled** (400 for 200 squares), because the squares group has the same name as the
  task. D2 compares two doubled numbers, so its result is unaffected. The recount counts them once (200 and 200).
- **The owner read practice rows after the count:** three right-size wrong picks with " . " or " * " separators, printed
  to understand the errors. They are practice data and in no mark.
