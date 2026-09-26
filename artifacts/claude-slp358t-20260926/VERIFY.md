# slp-358t blind recount: FAIL (agrees with RESULTS.md)

Verdict from the JSON alone (runs/slp358n-seed5.json, runs/slp358n-seed6.json, `morning` -> `"3"`): **FAIL**.
Seed 5 passes T1, T2 and T3. Seed 6 passes T1 and T3 but misses T2 (6x6 grids S − R = +12, bar +20).
Proved wrong: **no**. S − R is +48 to +88 on sums8 and +12 to +63 on grids6, all above +5.

## Marks (after night 3, integer counts)
| mark | seed 5 | seed 6 |
|---|---|---|
| T1 transfer_sums8 (200) S − R ≥ +20 | 134 − 46 = **+88 PASS** | 141 − 93 = **+48 PASS** |
| T2 transfer_grids6 (200) S − R ≥ +20 | 80 − 17 = **+63 PASS** | 16 − 4 = **+12 FAIL** |
| T3 harm_sums4 S ≥ N − 6 | 298 ≥ 184 PASS | 299 ≥ 286 PASS |
| T3 harm_grids4 S ≥ N − 6 | 214 ≥ 200 PASS | 153 ≥ 143 PASS |
| proved wrong (S − R ≤ +5 on both tests) | no | no |

Report-only (night 3): day_sums S − R +33 / +14, S − Z +375 / +383; day_grids S − R +87 / +20, S − Z +253 / +85
(seed 5 / seed 6). The S − R gap on transfer at nights 1, 2, 3: sums8 +72, +60, +88 (seed 5) and **+36, +8, +48 (seed 6)**;
grids6 +36, +57, +63 (seed 5) and +8, +8, +12 (seed 6).

## Disagreements with RESULTS.md
Every number in its tables, marks and verdict matches my counts. The disagreements are in the wording:
1. Report-only: "day_grids 61-90 of 400 in every arm" (seed 6) and "136-264" (seed 5) leave out the placebo. Z has
   5-19 (seed 6) and 6-11 (seed 5). The ranges cover S, R and N only.
2. Report-only: "The placebo ... hurts practised sums." On seed 5 after night 3, Z has 217 on harm_sums4, which is
   *above* N (190, the untrained base). It is below S and R (298/300). On seed 6 it is below N (179 vs 292). So "hurts" is
   true against the trained arms on both seeds, but against no night only on seed 6.
3. Plain words: "sleep ... made the small reasoner much better at 8-digit sums ... on both seeds" does not mention that on
   seed 6 the gap was only +8 after night 2 (122 vs 114). The seed 6 T1 pass rests on one reading that jumps around.
4. Plain words: "where the net had barely learned grids at all" goes beyond the numbers. Seed 6 gets about half the
   practised 4x4 grids right (149-161 of 300) and 61-90 of 400 on 5x5. The claim that weak grid skill caused the small
   transfer is suggested, not tested.
5. RESULTS never reports the day tries or nights 1-2, although PASSMARKS lists them under report. Omission only; no mark
   depends on them.

## Other checks
- **Seal:** `sha256sum -c` on both SEAL files gives all OK. The slp-358t seal adds no new hashes: its 4 script hashes
  are identical to the slp-358n2 seal. `git diff 280d665a8 HEAD` on all five sealed code files (including
  claude_blurt1.py, which envs imports) is empty. The seal commit 06342c903 (01:47:56) precedes the results commit
  fbfc4d1cd (02:53:31). Git shows only commit order, not when the run happened. The logs have no timestamps, so
  "relaunched ~01:50" cannot be checked, though 36 min per seed fits.
- **Logs vs JSON:** the base and morning 1-3 lines in seed5.log and seed6.log equal the JSON dicts exactly, and the
  minutes (36.2 / 36.0) match.
- **excluded_day_items_in_tests:** 0 on both seeds. For the transfer tests this could not be otherwise: the day items
  are 5-6 digit sums and 5x5 grids, while the transfer tests are 8-digit sums and 6x6 grids.
- **Code matches PASSMARKS:** tests come from `random.Random(58600)` and are the same for every seed and arm; arms are
  SRZN; cfg is 3 days, 300 night steps, and 400/300/200 test items. The JSON `seed` fields are 5 and 6. The wrapper's
  night_batches (kind first) and grid placebo take effect: they replace N's module globals, which `run` looks up
  when it is called. The thread count is not recorded in the JSON.

## Design notes (easier or harder than it looks)
- **Easier (T1/T2):** S is supervised training on code-checked answers at sizes closer to the tests (5-6 digit, 5x5).
  R never sees those sizes, and Z's wrong answers wreck everything (0/200 on transfer). No arm sees the day-size puzzles
  in a harmless neutral way. So S − R measures "trained on bigger sizes vs not," not anything specific to sleep.
- **Easier (T3):** N never trains, so N is simply the base net. Half of each S night is rehearsal on the practised
  sizes, so S ≥ N − 6 is nearly automatic (seed 5 sums 298 vs 190). A stricter harm check, S vs R, gives −2/−2 and
  0/−6. The 6x6-grids miss on seed 6 is not a harm miss.
- **Harder (T2 on seed 6):** the counts are near the floor (base 3/200, N 3, R 4). A +20 gap needs S ≥ 24 from a net
  that never passed 16. The mark is fixed per seed, so weak grid learning on one seed decides the verdict.
- **Not a first look:** the tests are the same fixed seed-58600 sets whose transfer counts were read in slp-358n2 before
  these marks were set (PASSMARKS says so). Only the training seeds are fresh.
- **Noise:** the shared loop-depth stream `rr` is used by S, then R, then Z in turn, so each arm gets different random
  draws. That adds noise, not bias. Seed 6's sums8 path (+36, +8, +48) shows how noisy one reading of 200 items is.
