# slp-358n results (sleep research thread, 2026-09-26 ~00:35 UTC; CPU, $0)

**Verdict: registered FAIL.** One mark missed: M1 on grids, seed 2 (sleep − rehearsal-only night = +8, bar +20).
Every other mark passed on both seeds. "Proved wrong" did not trigger. Blind recount: see VERIFY.md.

Code and marks: sealed at main b071ed0f0 (SEAL-code.sha256.txt), run unchanged:
`python -B scripts/claude_slp358n_nights.py run --seed {1,2} --out DIR --threads 2` (20.1 and 20.9 minutes).
Raw: runs/slp358n-seed{1,2}.json and logs. Day items that equalled a test item: 0 (both seeds).

## After night 3 (fixed fresh tests; right answers after 8 rounds)
| test (items) | seed | S sleep | R rehearsal night | Z placebo | N no night | start |
|---|---|---|---|---|---|---|
| day_sums (400, 5-6 digits) | 1 | 287 | 229 | 8 | 125 | 125 |
| | 2 | 361 | 295 | 10 | 186 | 186 |
| day_grids (400, 5x5) | 1 | 82 | 47 | 2 | 35 | 35 |
| | 2 | 73 | 65 | 4 | 41 | 41 |
| harm_sums4 (300, practised) | 1 | 246 | 248 | 134 | 159 | 159 |
| | 2 | 296 | 294 | 129 | 234 | 234 |
| harm_grids4 (300, practised) | 1 | 142 | 152 | 128 | 115 | 115 |
| | 2 | 148 | 151 | 147 | 133 | 133 |
| transfer_sums8 (200, report) | 1 | 77 | 19 | 0 | 14 | 14 |
| | 2 | 103 | 50 | 0 | 39 | 39 |
| transfer_grids6 (200, report) | 1 | 14 | 0 | 0 | 1 | 1 |
| | 2 | 14 | 12 | 0 | 5 | 5 |

## Marks
| mark | seed 1 | seed 2 |
|---|---|---|
| M1 S − R, day_sums (≥ +20) | +58 PASS | +66 PASS (R 295 < 360, so no ceiling) |
| M1 S − R, day_grids (≥ +20) | +35 PASS | **+8 FAIL** |
| M2 S − Z, day_sums / day_grids (≥ +20 each) | +279 / +80 PASS | +351 / +69 PASS |
| M3 S ≥ N − 6, harm_sums4 / harm_grids4 | 246 ≥ 153 / 142 ≥ 109 PASS | 296 ≥ 228 / 148 ≥ 127 PASS |
| proved wrong (S − R ≤ +5 on both kinds, both seeds) | no | no |

## Report-only
- Mornings, S − R on day_sums / day_grids: seed 1 +19/+21, +39/+27, +58/+35; seed 2 +55/+4, +58/+8, +66/+8.
- The day's own tries (300 sums, 300 grids each day; days 2-3 come after a night): seed 1 day 3 S 194/65,
  R 163/45, N 104/40; seed 2 day 3 S 272/68, R 228/59, N 162/34.
- S is slightly below R on the practised 4x4 grids (142 vs 152; 148 vs 151), though well above no night.
- The placebo night (wrong answers) wrecked the day kinds (8-52 of 400) and hurt practised sums badly (seed 1 36
  after night 1), so a night's material matters a lot: wrong answers are strongly harmful.

## What it means (plain words)
Sleeping on the day's checked answers clearly made the small reasoner better at fresh long sums than an equally long
night of old practice (+58 and +66 of 400), with no harm to what it knew, and it carried over to even longer sums it
never saw (77 vs 19, 103 vs 50 of 200). On 5x5 grids the gain was big on one seed (+35) and small on the other (+8),
so the grid part did not clear the bar we set; that is the registered FAIL. Limits: small nets on CPU, 3 nights,
two kinds of puzzle, a starting net that was undertrained (so any extra practice helped, which is why the
rehearsal-only control matters). Not a claim about the full-size reasoner or the joined agent.

## Accepted from the blind recount (VERIFY.md; it agrees with every number and the FAIL)
- The "8-52" placebo range is sums only; grids under the placebo scored 0-11.
- The grid placebo was not a clean wrong-answer night: shuffling targets between grids with different blanks and
  different symbol names left ~48% of its answer cells blank and ~23% with symbols not in the puzzle. M2 on grids is
  therefore weak evidence; the sums placebo is clean.
- Unequal night mix (checked in the code): day batches pick a shape group at random, and sums come in two widths
  (5 and 6 digits) while grids are one shape, so grids got about a third of the day batches and sums two thirds.
  That likely explains part of the weaker grid gain. Suggested, not tested.
- The transfer gains had no pass mark: report only.
- Cause, stated carefully: the night is practice on the tested kinds and sizes with checked answers; the day's own
  tries are graded but not used as training material in this design. "No harm" is vs no night; sleep was 10 below the
  rehearsal-only night on seed 1's 4x4 grids.
