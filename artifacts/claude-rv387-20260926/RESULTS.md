# rv-387 results (thought-memory thread; written 2026-09-26 16:12 UTC by date -u)

Raw output: run/ (commit 432cfea71, 358i's rental, started 15:34:55 UTC). Marks: PASSMARKS.md, sealed at 2d54b5992.
Seal re-checked here: all 4 lines OK; the script, marks and grids are unchanged since the seal. check-load: OK for all 4
nets (sha256 in run/check-load.jsonl). No grid used more than 48 rounds. Counted from the per-grid rows; the summary
numbers in each file agree with them. Blind recount: VERIFY-recount.md.

## Verdict: NO CLEAR RESULT (neither PASS nor PROVED WRONG), and going back was never tried

| grids7 (primary) | KEEP | GUESS | BACK | BACK - KEEP | BACK - GUESS | go-backs |
|---|---|---|---|---|---|---|
| seed 1 | 120 | 131 | 131 | +11 | 0 | 0 |
| seed 2 | 100 | 117 | 117 | +17 | 0 | 0 |
| seed 3 | 141 | 152 | 152 | +11 | 0 | 0 |
| seed 4 | 37 | 51 | 51 | +14 | 0 | 0 |

- PASS needs BACK >= KEEP + 15 and >= GUESS + 10 in 3 of 4 seeds: BACK >= GUESS + 10 holds in 0 of 4. Not PASS.
- PROVED WRONG needs BACK <= KEEP in 3 of 4 seeds: it holds in 0 of 4. Not PROVED WRONG.
- BACK went back 0 times in all 2,400 grid runs (4 seeds x 2 sizes x 300). Its per-grid rows are identical to GUESS in
  every seed and size. So rv-387 says nothing about going back itself: the trigger (q falls below the snapshot's q)
  never fired. Shown.

## Report-only rows

| grids6 (secondary) | KEEP | GUESS | BACK | go-backs |
|---|---|---|---|---|
| seed 1 | 192 | 214 | 214 | 0 |
| seed 2 | 155 | 194 | 194 | 0 |
| seed 3 | 220 | 241 | 241 | 0 |
| seed 4 | 72 | 95 | 95 | 0 |

- GUESS vs KEEP (same 48 rounds): writing the net's surest-but-unsure symbol as a given solved more grids in all 8
  seed-size pairs: +11, +17, +11, +14 on 7x7 and +22, +39, +21, +23 on 6x6. Grids KEEP solved and GUESS lost: 0, 1, 1, 0
  on 7x7 and 2, 0, 3, 0 on 6x6. Shown for these nets and grids; it was a report-only comparison, not a registered claim.
- Guesses written: 947, 1054, 946, 1384 on 7x7; 449, 640, 424, 1115 on 6x6. Rounds used, GUESS vs KEEP: slightly fewer
  in every pair (solved grids stop early).
- q at the end: on 6x6 GUESS, grids left unsolved end with a HIGHER median q (0.50 to 0.64 in seeds 1-3) than grids
  solved (0.43 to 0.55). After a guess the net can be confidently stuck. Shown; why is untested.
- Seed 4 is weak in every arm (37 of 300 on 7x7 KEEP), matching 358i's own finding that one loop seed never learned
  practice grids.
- This is search around the net, not skill inside it; per the agreement with Sleep research it is reported apart from
  the 3x goal and never counted toward it. Under Ben's 16:04 redirect, the guess-and-go-back code is disclosed
  bookkeeping around the learned net.

## Record-keeping notes (from the blind recount)
- The raw results reached main at 15:39:56 UTC. NOTE-rehearsal-2-before-result.md was committed at 15:44:09 UTC, after
  them. I had not fetched them when I wrote it, but the repo cannot show that, so treat that note as written during the
  run. It holds no prediction or mark this verdict uses. P387.4 is in the first note, committed at 15:05:35 UTC.
- The rental's step 1 writes to log.txt only if the seal check fails, so the log has no line showing it passed. The seal
  passes here now, and no sealed file changed in git after 2d54b5992.
- A guess written at round 48 is never tried, because the loop ends right after it. So the guess totals overstate the
  guesses that could have helped by about 14%. Suggested.

## Predictions
- P387.1 (GUESS solves fewer than KEEP in most seeds): WRONG. GUESS solved more in 4 of 4 seeds on both sizes.
- P387.2 (BACK beats GUESS in most seeds): WRONG. BACK = GUESS in 4 of 4 (no go-backs).
- P387.3 (BACK beats KEEP by 15: open): BACK - KEEP >= 15 in 1 of 4 seeds (seed 2, +17).
- P387.4 (added 15:05 UTC, before the result; BACK goes back rarely or never, close to GUESS): RIGHT. 0 go-backs.

## What it means (plain words)
Ben's idea is "go back to an old thought and try a different direction". This test built the going back, but the
signal for "this direction is failing" was the net's own confidence dropping, and the net never gets less confident
after something is written on its page. So it never went back. The part that ran, writing down the net's best guess
and carrying on, helped the net finish 11 to 17 more 7x7 grids out of 300.

## Brain first (Ben's 16:05 rule): what the next single change borrows from
- People do not go back because they feel less sure; they go back when something clashes. In the brain, a region in
  the frontal lobe (anterior cingulate cortex) responds to conflict and errors, and that response triggers a switch of
  strategy. Textbook-level, and the mapping to this net is a guess.
- So the next trigger should be a conflict signal from the net itself, not its confidence. The candidate with no
  hand-written puzzle rules: after the loop runs on, the net's own read-out at the written cell disagrees with what was
  written (the net "wants" to change its guess). Untested: the net may simply copy written cells, which would make the
  signal silent. That is measured first on practice grids, never on these test grids, before anything is registered.
- Why writing a guess helps is also a guess: a loop network stuck between two equally good answers settles once one
  is pushed (like pencilling in a number). Untested.

## Caveat added 2026-09-26 16:59 UTC (date -u)
The Thread manager (16:58 UTC) reports that 358i's loop nets were probably trained with a torch 2.8 bug that left the loop
block without a gradient on most steps. Sleep research is checking; it is not verified here. If so, these counts come
from undertrained loop nets. Comparisons within a net stay fair. See ../claude-rv390-20260926/NOTE-nets-hold.md.
