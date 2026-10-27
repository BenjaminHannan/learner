# slp-358t results: registered FAIL (T2 misses on seed 6); sleep carried to bigger sums on both seeds

Verdict: **FAIL**. Seed 5 passes every mark. Seed 6 passes T1 and T3 but misses T2 (6x6 grids: S − R = +12, bar
+20). Proved wrong: no (S − R is far above +5 on both transfer tests, both seeds).
Code: scripts/claude_slp358n2_nights.py, unchanged (sealed at 06342c903 before any run; SEAL-code.sha256.txt). Seeds 5
and 6, CPU, 2 threads each, ~36 minutes per seed. The first launch at ~01:48 UTC died at once (python without torch;
empty logs, no results); relaunched ~01:50 UTC with the torch environment, same code and arguments.
excluded_day_items_in_tests = 0 on both seeds.

## After night 3 (S sleep / R rehearsal-only night / Z wrong-answer placebo / N no night)
| test | seed | S | R | Z | N |
|---|---|---|---|---|---|
| transfer_sums8 (200, graded T1) | 5 | 134 | 46 | 0 | 53 |
| | 6 | 141 | 93 | 0 | 69 |
| transfer_grids6 (200, graded T2) | 5 | 80 | 17 | 0 | 11 |
| | 6 | 16 | 4 | 0 | 3 |
| harm_sums4 (300, T3) | 5 | 298 | 300 | 217 | 190 |
| | 6 | 299 | 299 | 179 | 292 |
| harm_grids4 (300, T3) | 5 | 214 | 216 | 174 | 206 |
| | 6 | 153 | 159 | 142 | 149 |
| day_sums (400, report) | 5 | 386 | 353 | 11 | 169 |
| | 6 | 389 | 375 | 6 | 322 |
| day_grids (400, report) | 5 | 264 | 177 | 11 | 136 |
| | 6 | 90 | 70 | 5 | 61 |

## Marks
| mark | seed 5 | seed 6 |
|---|---|---|
| T1 transfer_sums8 S − R ≥ +20 | +88 PASS | +48 PASS |
| T2 transfer_grids6 S − R ≥ +20 | +63 PASS | +12 FAIL |
| T3 S ≥ N − 6 on harm_sums4 / harm_grids4 | 298 ≥ 184 / 214 ≥ 200 PASS | 299 ≥ 286 / 153 ≥ 143 PASS |
| proved wrong (S − R ≤ +5 on both, both seeds) | no | no |

## Report-only
- Seed 6's net learned grids poorly overall (day_grids 61-90 of 400 in every arm, vs 136-264 on seed 5), so its 6x6
  counts are small (3-16 of 200); sleep still led (16 vs 4 vs 3) but under the bar.
- Sleep vs the rehearsal-only night on practised sizes: seed 5 −2 sums, −2 grids; seed 6 0 sums, −6 grids.
- The placebo (wrong answers) wipes out both bigger tests (0 of 200) and hurts practised sums.

## What it means (plain words)
Sleeping on checked 5-6 digit sums made the small reasoner much better at 8-digit sums it never practised, on both
seeds (+88 and +48 of 200 over an equally long night of old practice). On 6x6 grids it helped a lot on one seed (+63)
but only +12 on the other, where the net had barely learned grids at all, so the registered test fails. Limits: small
nets on CPU, 3 nights, two puzzle kinds; the marks were set after seeing slp-358n2's report-only transfer counts.

## Blind recount (VERIFY.md): agrees, registered FAIL. Wording corrections
- The day_grids ranges above (61-90, 136-264) leave out the placebo arm Z (5-19 and 6-11).
- The placebo is below S and R on harm_sums4 on both seeds, but below N only on seed 6 (seed 5: Z 217 vs N 190).
- Seed 6's sums8 gap was only +8 after night 2 (122 vs 114); its T1 pass rests on the night-3 reading.
- "Barely learned grids" overstates it: seed 6 gets 149-161 of 300 practised 4x4 grids. That weak grid skill caused
  its small 6x6 gain is a guess, not tested.
- Design: S − R compares nights with and without the day's checked puzzles; T3 against N (untrained base) is an easy
  bar, and vs R sleep is −2/−2 (seed 5) and 0/−6 (seed 6) on practised sizes.
