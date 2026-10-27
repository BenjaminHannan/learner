# slp-358t pass marks (fixed before any run; 2026-09-26 01:55 UTC, sleep research thread)

Question: does a night of sleep on the day's checked puzzles make the small reasoner better at BIGGER puzzles it never
practised or saw in a day (8-digit sums, 6x6 grids), compared with an equally long night of old practice?
slp-358n2 (registered PASS) graded only the day's sizes; there these bigger sizes were report-only.

Code: exactly scripts/claude_slp358n2_nights.py (sealed in artifacts/claude-slp358n2-20260926/SEAL-code.sha256.txt,
unchanged; hashes repeated in SEAL-code.sha256.txt here). The only change is what is graded, and fresh seeds 5 and 6.
Arms S (sleep on the day's checked answers), R (rehearsal-only night), Z (wrong-answer placebo), N (no night).
Scores after night 3.

| mark | what (each seed) | pass |
|---|---|---|
| T1 | transfer_sums8 (200): S − R | ≥ +20 |
| T2 | transfer_grids6 (200): S − R | ≥ +20 |
| T3 | harm: S ≥ N − 6 on harm_sums4 and harm_grids4 (300 each) | both |
| report | day_sums, day_grids (S − R, S − Z), placebo, nights 1-2, day tries | - |

**PASS = T1, T2 and T3 on both seeds.** Anything else = FAIL (stays FAIL).
**Proved wrong** ("sleep on day-size answers carries to bigger sizes"): S − R ≤ +5 on both transfer tests, both seeds.

Honest limits, written before running: these marks were set after seeing slp-358n2's report-only transfer counts
(seeds 3/4: sums8 S − R +60/+32, grids6 +42/+27), so this is a replication on fresh seeds (5, 6), not a first look.
The test sets are the same fixed code-made sets (seed 58600) for every seed; only counts were ever read. Small nets on
CPU, 3 nights, two puzzle kinds. Prediction: T1 likely, T2 uncertain (seed 4 had 27 vs 0: low counts).
