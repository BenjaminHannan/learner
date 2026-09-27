# dl-12 verdict: PROVED WRONG (registered; blind recount agrees)
Fix-sleep thread, written 2026-09-27T19:06:57Z from `date -u`. Results af6765ea7 (cpu/dl12_results.json, cpu/log.txt).
Run: this cloud CPU, 20 minutes, $0. Luna data sha256 35d5d52e... (d50ce62db, job 302). Seal: 0 lines not OK.
Blind recount: one read-only worker graded every bar from the raw counts before reading the file's marks; it matches
bar for bar.

## Counts (seed 18 / seed 19)
| bar | at 150 | at 750 | grade at 750 |
|---|---|---|---|
| P TEST sent to P | 100/100, 100/100 | 100/100, 100/100 | pass |
| Q TEST sent to Q | 200/200, 200/200 | 200/200, 200/200 | pass |
| panel sent to base | 124/300, 119/300 | 178/300, 185/300 | below 240: proved wrong |
| "bigger" sent to base | 0/119, 0/119 | 0/119, 6/119 | below 89: proved wrong |
| held-out Luna topics sent to base | 195/196, 195/196 | 196/196, 196/196 | pass |
R3: every reworded frame passes on both seeds (P 100/100 on 4 frames, Q 200/200 on 4 frames).

## What it shows
- Shown: the plain base 1B's last-layer state, read by a 3-way router, does not keep the panel's quiz items off the
  arithmetic skill. All 119 "bigger" items go to Q (the two-number sum skill) at 150, and 113-119 still do at 750.
  The panel's "count" and "order" items also go partly to Q at 150 (20/20 and 13/31).
- Shown: the same router separates P from Q perfectly, holds up under every rewording, and sends 195-196 of 196
  held-out Luna everyday number questions (unseen topics) to base.
- Shown, against my prediction: the words row ("nineteen times three" style) goes 100/100 to Q on every run, not
  to base. The router keys on the arithmetic meaning, not on symbols.
- Suggested, untested: "Which is bigger, 17 or 42?" is itself a number comparison, so the router may be grouping it
  with arithmetic because it is arithmetic-like. The registered design counts it as base, so it stays PROVED WRONG.
  Whether sending it to Q would hurt answers was not measured.

## Limits
Plain base only (not lis-320), two skills, 2 seeds, one feature layer. Measurement only: nothing is built, and
nothing here decides the experts card. It bears on Ben's 11:34 09-27 "automatically decide what": a label-free
router on this state alone mis-sends look-alike quiz items at every amount tried.
