# slp-358sf pass marks (fixed before any run; 2026-09-26 04:10 UTC, sleep research thread)

Question: does a night that practises the day's MISTAKES first (only the day puzzles the model got wrong, with their
code-checked answers) beat a night that practises the day's puzzles at random?
Code: scripts/claude_slp358sf_nights.py (docstring has the arms). Base = slp-358n2's sleep night (registered PASS).
Arms: S random (= slp-358n2 sleep), P mistakes first, N no night. Seeds 9 and 10 (fresh). Same fixed tests as
slp-358n2 (seed 58600). Scores after night 3.

| mark | what (each seed) | pass |
|---|---|---|
| V validity | S − N ≥ +20 on day_grids (400) | else INCONCLUSIVE |
| Q1 | day_grids (400): P − S | ≥ +20 |
| Q2 | transfer_sums8 or transfer_grids6 (200): P − S | ≥ +10 on at least one |
| Q3 | no forgetting vs random: P ≥ S − 10 on harm_sums4 and harm_grids4 (300 each), and on day_sums (400) | all three |
| report | nights 1-2, day tries, night pool sizes, P vs N on harm | - |

**PASS = V, Q1, Q2 and Q3 on both seeds.** V met on both seeds and anything else = FAIL (stays FAIL).
**Proved wrong** (mistakes-first helps at this scale): P − S ≤ +5 on day_grids and on both transfer tests, both seeds.

Why these marks: day_sums sits near the ceiling (342-393 of 400 in recent runs), so the day-size gain is judged on
grids; Q3 is against S (not N) because a mistakes-only night repeats a small set (sums misses can be ~20 puzzles) and
may forget. Prediction: uncertain; P may help grids (many misses) and overfit sums (few). Limits: small nets on CPU,
3 nights, two puzzle kinds; "mistakes" are misses at 8 rounds.
