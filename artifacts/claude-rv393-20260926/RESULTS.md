# rv-393 results: pencil marks (thought-memory thread; written from 07:32 UTC 2026-09-27 by date -u)

Raw output: run/ (BensPC job 175-rv393-pencil-pc, 06:02 to 07:02 UTC, $0). The seal checked 19 of 19, the selftest passed,
and all four nets matched their NETS-358i2 lines (run/SOURCES.txt, run/info-sN.json). The code was not edited. The builder
reported 2 deviations, neither touching the numbers: it launched the four runs through Windows WMI because a plain
background launch died when ssh closed, and it wrote SOURCES.txt on the Mac and copied it over.
Marks: PLAN.md, sealed at da1250e65 before any run. Counter: count/count.py, committed at ae754ac18 before any result.
It recounts every number from the rows files and checks them against the run's own summaries: 0 differences.
Blind recount: a separate agent recounted from the rows files only, without seeing count/ or this file (verify/). It
agrees with the summaries on every count, and on every rate and AUC to their 4 decimals. It reaches the same verdict,
the same clauses and the same prediction outcomes. Its bootstrap (seed 393) gives -0.159 to -0.056; count/ (seed 0)
gives -0.154 to -0.058.

## Verdict: PROVED WRONG

VALID: steps_block_nograd is 0 in all 8 fine-tunes, and each ran the sealed 3,000 steps.

| pp-grids7 (fresh practice), PENCIL arm | net 1 | net 2 | net 3 | net 4 | mean |
|---|---|---|---|---|---|
| wrong marks overruled | 8 of 116 | 15 of 71 | 11 of 120 | 4 of 64 | |
| rate (needs at least 60%) | 6.9% | 21.1% | 9.2% | 6.3% | |
| right marks overruled (needs at most 10%) | 9 of 281 | 16 of 185 | 18 of 242 | 6 of 171 | |
| CLEAN: wrong marks overruled | 0 of 113 | 0 of 101 | 0 of 128 | 0 of 117 | |
| dead-page AUC (1 - lowest mark probability) | 0.768 | 0.719 | 0.814 | 0.721 | 0.756 |
| count-only AUC (number of marks) | 0.894 | 0.773 | 0.920 | 0.864 | 0.863 |

- All four nets count (at least 30 wrong marks judged in the PENCIL arm).
- WORKS clause 1: 0 of 4 nets meet all three conditions. No net reaches 60% of wrong marks overruled. Net 2 is the only one
  that beats CLEAN by 20 points (21.1% against 0%). All four keep right-mark overrules under 10%.
- WORKS clause 2: the page score trails counting by 0.107 (0.756 against 0.863). It needed to lead by 0.05.
- PROVED WRONG fires on two of its three clauses:
  - PENCIL overrules fewer than 30% of wrong marks in all 4 counted nets (at least 3 needed);
  - its mean AUC, 0.756, is no better than its mean count-only AUC, 0.863.
  - The third clause (no higher than CLEAN in at least 3 nets) does not fire: PENCIL is above CLEAN's 0% in all 4.
- NO HARM holds. PENCIL minus ORIG, mean over the 4 nets, out of 300: grids6 +9.5, grids7 +94.0, sums6 -3.75 (floor -5).
  sums6 per net: -9, -1, -3, -2.

## The three readings (as for the critic)

| reading | value |
|---|---|
| per-net-mean margin (the one the mark uses) | -0.107 |
| puzzle-level bootstrap, 95% range of that margin (1,000 resamples) | -0.154 to -0.058 (recount's seed: -0.159 to -0.056) |
| share of resamples above 0 / at least +0.05 | 0.000 / 0.000 |
| PENCIL mean AUC minus one pooled count-only AUC (pooled 0.867) | -0.112 |

All three readings agree, and the whole bootstrap range is below 0.

## Predictions (fixed in PLAN.md)
- P393.1 WORKS (about 35%): WRONG.
- P393.2 ORIG overrules fewer than 30% of wrong pencil marks in at least 3 of 4 nets (about 70%): RIGHT. ORIG overrules
  0 of 354, 0 of 253, 0 of 418 and 0 of 414. It copies whatever sits in the answer cell.
- P393.3 CLEAN overrules more wrong marks than ORIG but fewer than PENCIL (about 50%): WRONG. CLEAN overrules 0 in every
  net, the same as ORIG.

## Report-only rows
- ORIG and CLEAN meet clause 1's first two thresholds in 0 nets.
- The extra 7x7 practice made the nets much better at 7x7. The fine-tune added 7x7 pages, which the original training
  never had (grids were 4x4 and 5x5 only). Both arms show it, so the pencil marks are not the cause:

  | out of 300 | ORIG | PENCIL | CLEAN |
  |---|---|---|---|
  | grids7 test, net 1 / 2 / 3 / 4 | 186 / 241 / 173 / 177 | 285 / 288 / 291 / 289 | 286 / 290 / 291 / 288 |
  | grids6 test | 292 / 296 / 283 / 287 | 300 / 300 / 298 / 298 | 299 / 299 / 299 / 299 |
  | sums6 test | 299 / 299 / 298 / 297 | 290 / 298 / 295 / 295 | 299 / 297 / 296 / 299 |

  The day pass on the 1,000 practice 7x7 puzzles leaves 303, 145, 362 and 347 unfinished for ORIG, and 24 to 41 for
  PENCIL and CLEAN. These are no-harm and practice rows, not a registered test of 7x7 training. The grids7 test was only
  measured, never trained on (data/make-data.json: the training puzzles repeat no test puzzle).
- The pencil worker, which never goes back, finishes 4, 6, 4 and 2 of PENCIL's unfinished practice puzzles (41, 32, 38,
  24). ORIG finishes 199, 47, 203 and 218 of its 303, 145, 362 and 347.
- p-grids7 (the critic's 300 practice puzzles): PENCIL overrules 0 of 37, 2 of 19, 2 of 29 and 1 of 29 wrong marks. Its
  AUC is 0.798, 0.791, 0.731 and 0.598, against count-only 0.958, 0.915, 0.893 and 0.816.
- Mark-level doubt (post hoc, not in PLAN.md; suggested only). Does the net give its wrong marks a lower probability than
  its right ones, even when it does not overrule them? The AUC of (1 - p), wrong marks against right marks, is
  0.537, 0.612, 0.612 and 0.571 for PENCIL, against 0.427 to 0.511 for ORIG and 0.468 to 0.511 for CLEAN.
  PENCIL's mean probability on its wrong marks is 0.89, 0.74, 0.83 and 0.86, against 0.92, 0.86, 0.87 and 0.91 on its
  right ones. So pencil training added a little doubt, far short of overruling.
- Training logs: whole-page exact on replayed trace pages rose from 11-29% (PENCIL) and 37-53% (CLEAN) at step 100 to
  99.5-99.8% at step 3,000 in both arms. Exact on the usual 4x4/5x5 stream went from 97.4-99.98% to 95.7-98.8%.
- Traces: the untouched nets left 1,368, 669, 1,520 and 1,503 of the 4,000 training puzzles unfinished, and wrote
  guesses on 1,092, 561, 1,084 and 1,200 of them (7,679, 5,004, 8,901 and 8,902 check-round states).

## Why it failed (suggested, untested)
- On its training replays the PENCIL net ends up right on 99.6% to 99.8% of whole pages, and 43% to 60% of the trace
  states it replays hold a wrong mark. So it does correct those marks there. But the replay drew about 192,000 pages (about 1,500 replay steps of 128)
  from only 5,004 to 8,902 states of 561 to 1,200 puzzles. Each state came up about 20 to 40 times, so it may simply have
  memorised those puzzles' answers. The critic failed the same way: too few distinct examples.
- The marks it is judged on at the end are its own guesses. It wrote each one because that symbol was its best belief,
  and 8 rounds later the page rarely holds new evidence against it. In training, the wrong marks were the untouched net's
  mistakes, which the fine-tuned net may not share. PLAN.md disclosed this mismatch before the run.
- Neither cause is tested. The fine-tuned weights stay on BensPC, so a check would be a new job.

## What it means (plain words)
We tried writing the solver's guesses in pencil and training it on its own old attempts, so it would learn to say "that
pencil mark is wrong". It did not learn that. It crossed out only 6 to 21 of every 100 wrong marks, and simply counting
the marks on the page still says better whether a page is ruined. One thing did change a lot: the extra practice on
7x7 puzzles made every net far better at 7x7 (from 173 to 241 of 300 on the 7x7 test before, to 285 to 291 after),
with or without pencil marks. That is ordinary practice at a new size, not going back.

## Next (fixed in PLAN.md before this number)
- The time slice (W = 16) stays as the go-back trigger for registered rv-391. rv-391 waits on the rv-390 and rv-392
  re-run on rsn-358i2 (BensPC job 173; 170 to 172 ran nothing).
- Going back goes to Ben through the Thread manager as a brainstorm, per the goals page ("when the ideas run out").
- The 7x7 gain belongs to whoever owns the reasoner's training (Sleep research). It is a report-only row here.
