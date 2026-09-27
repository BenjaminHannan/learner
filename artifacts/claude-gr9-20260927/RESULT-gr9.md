# RESULT gr-9 (dev only, practice data): DEV-FAIL

- **Run.** Sealed in 98b53d445 and re-launched once as chain-r1 (addendum 2). The outcome is from run-r1/logs/count-main.log.
- **Recount.** A separate agent's blind recount (recount/output.txt) matches the owner's count on every figure.
- **What is left.** The report-only L7c control is still training. Its line will be added in an addendum.

## Marks (greedy read; L9 = the new reader, L7 = gr-7's reader)
| Mark | Result | Bar | Verdict |
|---|---|---|---|
| M1 held-out exact | 94 of 100 | at least 90 | pass |
| M2 practice squares exact | 197 of 200 | at least 199 | **fail** |
| M3 seen-separator squares exact | 97 of 100 | at least 98 | **fail** |
| M4 lookalikes read as a square | L9 5, L7 8 | L9 at most L7 + 1 | pass |

- **Outcome.** DEV-FAIL, because M2 and M3 fail.
- **Not proved wrong.** L9 read 94 held-out squares and L7 read 44, a gain of 50 on the same items with the same read.
- **Not TOO-EASY.** L7 read 44, under the 85 bar.

## Report only
- **The four forced marks.** L9 read 35 of 40 exactly, and L7 read 23. By mark, L9 against L7: " . " 9 v 8, " * " 10 v 4,
  "=" 7 v 6, " : " 9 v 5.
- **What L9's misses are.**
  - Held-out: all 6 misses are "none", never a wrong grid. 5 of the 6 carry ".", "=" or ":".
  - L7 on the same held-out items: 48 wrong grids and 8 none.
- **The harm.** L9 got 3 practice squares wrong (2 wrong grids at the right size, 1 none) and 3 seen-separator
  squares wrong (2 and 1). L7 did not read these two sets in this run, so no harm is shown on these items.
  - Practice squares: in gr-7d and gr-8 dev, L7 read 200 of 200 on other items of the same kind. A small loss is
    **suggested**.
  - Seen-separator squares: on other items, L7 read 96 of 100 (gr-7d) and 99 of 100 (gr-8 dev). L9's 97 is inside
    that range, so no loss is suggested there. The 98 bar was stricter than gr-7's own record.
- **Blank-run caveat.** Of L9's right-size held-out rows, 0 of 57 dot or star rows with blanks side by side were
  wrong, against 2 of 34 for L7. The feared "_ . _" failure did not show for L9 on this set.
- **Size pick.** It gave the same exact counts as the greedy read on all three sets.
- **Training.** The mean loss by epoch was 0.0109, 0.0038 and 0.0011, over 173 minutes.

## Predictions against results
- **L7 held-out:** predicted 45 to 70, got 44, just outside.
- **L9 held-out:** predicted 92 to 98, got 94.
- **Gain:** predicted at least 25, got 50.
- **Practice squares:** predicted 200, got 197, missed.
- **Seen-separator squares:** predicted 99 or 100, got 97, missed.
- **Lookalikes:** predicted within 1 of L7, with L7 at most 8. L7 had 8 and L9 had 5.
- **Last-epoch loss:** predicted at most 0.01, got 0.0011.

## What it means (plain words)
- **The good part (shown on practice data).** Training on 28 new separator marks taught the reader to copy grids
  written with separators from families it never saw: 94 of 100 against 44. When it is unsure, it now says "none"
  instead of copying a wrong grid.
- **The bad part.** It missed 3 of 200 ordinary practice squares, which the marks did not allow. gr-7's reader read
  200 of 200 of these kinds before, on other items. It also missed 3 of 100 seen-separator squares, which is no worse
  than gr-7 did before (96 and 99).
- **The next change** goes to the Thread manager first.
