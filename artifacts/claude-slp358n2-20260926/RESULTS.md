# slp-358n2 results (sleep research thread, 2026-09-26 ~01:15 UTC; CPU, $0)

**Verdict: registered PASS** (M1, M2, M3 on both seeds). On seed 3 the sums sat at the ceiling (sleep 382, rehearsal
366, both ≥ 360), so that seed's sums say nothing; seed 3's pass rests on grids. Blind recount: see VERIFY.md.
Code and marks sealed at main 280d665a8, run unchanged (`scripts/claude_slp358n2_nights.py run --seed {3,4}`;
20.1 and 21.8 minutes). The one change from slp-358n: each night's day-practice split evenly between sums and grids.

## After night 3 (fixed fresh tests, same as slp-358n; right after 8 rounds)
| test (items) | seed | S sleep | R rehearsal night | Z placebo | N no night |
|---|---|---|---|---|---|
| day_sums (400) | 3 | 382 | 366 | 1 | 312 |
| | 4 | 332 | 264 | 4 | 187 |
| day_grids (400) | 3 | 228 | 149 | 20 | 116 |
| | 4 | 195 | 112 | 4 | 38 |
| harm_sums4 (300) | 3 | 300 | 300 | 119 | 297 |
| | 4 | 274 | 279 | 50 | 225 |
| harm_grids4 (300) | 3 | 213 | 213 | 189 | 208 |
| | 4 | 195 | 208 | 132 | 109 |
| transfer_sums8 (200, report) | 3 | 149 | 89 | 0 | 56 |
| | 4 | 76 | 44 | 0 | 21 |
| transfer_grids6 (200, report) | 3 | 65 | 23 | 0 | 15 |
| | 4 | 27 | 0 | 0 | 0 |

## Marks
| mark | seed 3 | seed 4 |
|---|---|---|
| M1 S − R day_sums (≥ +20, or both ≥ 360) | +16, both ≥ 360: PASS (ceiling, uninformative) | +68 PASS |
| M1 S − R day_grids (≥ +20) | +79 PASS | +83 PASS |
| M2 S − Z sums / grids (≥ +20) | +381 / +208 PASS | +328 / +191 PASS |
| M3 S ≥ N − 6 harm_sums4 / harm_grids4 | 300 ≥ 291 / 213 ≥ 202 PASS | 274 ≥ 219 / 195 ≥ 103 PASS |
| proved wrong | no | no |

## Report-only
- S − R on grids after nights 1/2/3: seed 3 +47/+51/+79; seed 4 +60/+73/+83 (grows every night).
- vs the rehearsal-only night, sleep is slightly lower on the practised sizes on seed 4 (sums4 274 vs 279, grids4
  195 vs 208); vs no night it is higher everywhere.
- Placebo nights (wrong answers) destroy the day kinds and hurt practised sums (50-119 of 300).

## What it means (plain words)
With the night split evenly, sleeping on the day's checked answers made the small reasoner much better at fresh
puzzles of the day's kind than an equally long night of old practice (grids +79 and +83 of 400; sums +68 where not
at the ceiling), better on bigger sizes it never practised (report only), and no worse than no sleep on what it
already knew. Limits: small nets on CPU, 3 nights, two puzzle kinds; the night's material is practice on the tested
sizes with code-checked answers (the day's own tries are graded but not reused); slp-358n (the uneven version) stays
a registered FAIL.

## Blind recount (VERIFY.md): agrees, registered PASS
No number above disagrees. Added from the recount's notes:
- Day tries (right of 300 sums / 300 grids, the morning's model on that day's fresh puzzles, before its night):
  seed 3 day 2 S 278/138, R 247/98, Z 75/10, N 230/72; day 3 S 282/165, R 265/121, Z 15/70, N 228/98.
  seed 4 day 2 S 217/105, R 200/59, Z 8/3, N 142/36; day 3 S 231/142, R 196/78, Z 6/1, N 124/27.
  (Day 1 is before any night, so all arms are equal: seed 3 233/82, seed 4 126/24.)
- excluded_day_items_in_tests = 0 on both seeds (no day puzzle was a test puzzle).
- Seed 3 passes M1 on sums only through the ceiling rule (+16), so seed 3's evidence is the grids (+79).
- Seed 4, sleep vs rehearsal-only on practised sizes: −5 sums, −13 grids (small, within the mark vs no night).
- The placebo teaches wrong answers, so M2 is an easy bar.
- Hand-written times in PASSMARKS/RESULTS are approximate; git holds the real times. The seal commit came before
  the run outputs, but nothing records the exact start time of seed 4 (about a minute after the seal).
