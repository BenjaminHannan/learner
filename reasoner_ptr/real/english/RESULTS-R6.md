# English, 12 practised kinds vs 6: results (6 paired seeds, 2026-10-04)

Marks: `PASS-MARKS-R6.md` (commit 04c4c528e, before training). Numbers: `ANALYSIS-R6.json`; rows in `results6/`.
Both runs: allptr, 8000 generated examples, 2000 updates, test words blocked from the generator (`--block-r6`).
Fast lane, not a sealed headline test.

## Goal (judged B): REACHED, but not because of the extra kinds
- twelve on the round-5 unseen kinds: **83.0%** vs bare 8-shot 67.7% (+15.3, CI +9.8 to +20.7). Goal was >= 80%.
- But the six-kind rerun also scored **81.1%** there (round 5: 79.9%; this rerun keeps test words out of the
  generator). So most of the gain over 80 comes from the rerun, not from the six extra kinds.

## Judged A, twelve - six on the round-5 unseen kinds: IN BETWEEN
+1.9 points, CI -3.9 to +7.7 (per seed -7 to +7). Mark was +5 with CI above 0. Not shown.

## The cleaner check, a second unseen-kinds set never scored before (read, not judged)
Speech, weather, price, direction, duration, origin (192 questions):

| | twelve | six | bare 1.2B, 8-shot |
|---|---|---|---|
| all | 78.2 | 75.3 | 77.6 |
| speech (what did X say) | 40.6 | 46.3 | 46.9 |
| direction | 75.5 | 60.9 | 75.0 |
| origin | 76.6 | 71.3 | 75.0 |
| price | 87.5 | 82.8 | 96.9 |
| duration | 94.3 | 95.3 | 96.9 |
| weather | 94.8 | 94.8 | 75.0 |

- twelve - six: +3.0 (CI -1.1 to +7.0). twelve - bare: +0.6 (CI -4.6 to +5.9). **On these kinds we only tie the bare
  model.** The round-5 margin (+12 to +15) did not carry over to a second set of new kinds.
- Old kinds (fresh set): twelve 92.0 vs six 92.2, so spreading practice over 12 kinds cost nothing.
- Zeroing the core's 8 vectors: 0% in both runs.

## What this means (suggested)
Adding six more practised kinds is at most a small help (+2 to +3, not shown). Beating the bare model on unseen
kinds depends on which kinds: we win where the bare model formats badly (why, how many, weather) and lose or tie
where answers are long quotes (speech) or the bare model is already near-perfect (price, duration, location).
A bigger lever is likely needed (more kinds by an order of magnitude, or a different skill, e.g. copying long spans).

## Caveats
Both unseen sets were written by helper agents and read once by me; the second set has some repetitive question
pairs. The round-5 set has now been scored twice. One bare-model prompt format.

## Cost
About $1.10 on vast for 6 RTX 3090s (no 5090s were free); credit $12.47 at 16:15 UTC (shared).
