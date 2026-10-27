# dl-5 verify (Fix-sleep thread, 2026-09-26)
Blind recount (a separate agent read only PASSMARKS.md and the raw gpu/dl5_results.json per-night rows, not the
builder's report): **registered FAIL, agrees with the stored marks block with no disagreements.**
- G1 PASS: S final 93.8 and 93.4 points vs night 0 48.8 (needs 63.8).
- G2 PASS: S 93.8 / 93.4 vs placebo 6.6 / 7.2.
- G2b PASS: open states S 67.8 / 65.0 vs placebo 35.0 / 38.5 (97 and 93 of 143 vs 50 and 55).
- G3 FAIL: S lost 98 (seed 8) and 61 (seed 9) of the base's 200 right panel items (bar 20).
- Not INCONCLUSIVE (night-1 rows 1144, 925); not proved wrong.
- Limit of the recount: the results file keeps no per-item harm lists, so lost was checked only for consistency
  (200 - lost + gained = right holds on every checked night), not item by item.
Status under Ben's "Use GLM" rule (Thread manager 16:49): the training target carried a Claude-written prefix ("The
number in row R, column C is "), so this verdict is a FINDING only and feeds no build.

## What it shows (plain words)
Grid nights taught the 1B the day's work fast: 48.8 -> 93.8 points on fresh grids after ONE night (714/762 on night 1,
then flat), well above the wrong-answer placebo, including on open cells where a wrong number that fits the row and
column was practised. But forgetting kept growing every night while grid skill stayed flat: seed 8 lost 8, 21, 38,
46, 98; the answer-key arm lost 135 by night 5. Nights trained 925-1337 rows each, 3-4x copy nights. Reading
(suggested): after the skill is learned, further nights only cost general knowledge, so a night should stop or shrink
once the day's work is already right (a test for this is not yet designed).
