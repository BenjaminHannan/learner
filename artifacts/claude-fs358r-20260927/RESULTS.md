# fs-358r verdict: PASS (registered marks 370eb499a; blind recount agrees)
Fix-sleep thread, written 2026-09-27T22:34:46Z from `date -u`. This cloud CPU, torch 2.14.0+cpu, 1 thread per run, 96-99 minutes
per run, $0. Launch log: go.log (seeds 9-10 at 19:15:17Z, seeds 11-12 at 20:52:48Z, done 22:32:03Z).
Validity: replay counts read B 250 grids in all 8 runs; C 75 + 75 in every baseline and 150 + 150 in every
candidate. Seal: 6 of 6 OK.

| seed | grids5 after B | base grids5 after C | cand grids5 after C | g | base maze7 C | cand maze7 C | m |
|---|---|---|---|---|---|---|---|
| 9 | 160 | 119 | 162 | +43 | 132 | 137 | +5 |
| 10 | 162 | 105 | 162 | +57 | 141 | 147 | +6 |
| 11 | 158 | 77 | 139 | +62 | 151 | 124 | -27 |
| 12 | 185 | 149 | 174 | +25 | 148 | 160 | +12 |
| mean | 166.25 | 112.50 | 159.25 | +46.75 | 143.00 | 142.00 | -1.00 |

PASS: mean g +46.75 (bar +25), g > 0 on 4 of 4 seeds (bar 3), mean m -1.00 (bar -15), worst m -27 (bar -30).
sums4 after C: base 192-198, cand 199-200 (report only).

## What it shows
- Shown (dev set, 4 seeds): doubling phase C's replay share keeps almost all of the grids the dense loop had after
  phase B (mean 159.25 of 166.25, against 112.50 for the baseline). The low replay share in C is the main cause of
  the grids loss there.
- Mazes were not hurt on average (-1.00), even with 1,200 maze steps instead of 1,350. Seed 11 lost 27, near the
  -30 line, so the maze cost is not shown to be zero.
- Prediction (mean g about +20, PASS 30%) was too low.

## Limits
One net size, CPU, dev sets read before (seed 48000), 4 seeds. It keeps 358e4's kind embedding.

## Plain words
When the small reasoner learned mazes, it forgot grid puzzles because grids were practised only once every 20
steps. Practising them once every 10 steps (like in the earlier phase) kept the grid skill almost whole, and the
mazes came out about the same.
