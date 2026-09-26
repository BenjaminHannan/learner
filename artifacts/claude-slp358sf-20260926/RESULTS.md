# slp-358sf results: INCONCLUSIVE as registered (seed 10's net never learned); on seed 9 mistakes-first was WORSE

Verdict: **INCONCLUSIVE** by the marks: V fails on seed 10 (S − N on day_grids +19, bar +20; its practice net was
badly undertrained: 59/300 on practised 4-digit sums with no night). Seed 9 meets V (+97) and **fails Q1, Q2 and Q3**:
the mistakes-first night was worse than the random night on every graded test but harm_grids4. It cannot PASS.
Proved-wrong clause (P − S ≤ +5 on day_grids and both transfer tests, both seeds): the counts meet it on both seeds
(seed 9: −14, −14, −8; seed 10: −4, +1, 0), but seed 10 is invalid, so only seed 9 counts as evidence against.
Code: scripts/claude_slp358sf_nights.py, sealed at 3e5c27016 before any run. Seeds 9 and 10, CPU, 2 threads each,
16.9 and 18.2 minutes. excluded_day_items_in_tests = 0 on both.

## After night 3 (S random / P mistakes first / N no night)
| test | seed | S | P | N |
|---|---|---|---|---|
| day_grids (400, V, Q1) | 9 | 184 | 170 | 87 |
| | 10 | 38 | 34 | 19 |
| day_sums (400, Q3) | 9 | 371 | 359 | 279 |
| | 10 | 89 | 76 | 48 |
| transfer_sums8 (200, Q2) | 9 | 128 | 114 | 73 |
| | 10 | 33 | 34 | 7 |
| transfer_grids6 (200, Q2) | 9 | 47 | 39 | 8 |
| | 10 | 4 | 4 | 0 |
| harm_sums4 (300, Q3) | 9 | 294 | 281 | 248 |
| | 10 | 92 | 94 | 59 |
| harm_grids4 (300, Q3) | 9 | 184 | 192 | 155 |
| | 10 | 97 | 97 | 64 |

## Marks
| mark | seed 9 | seed 10 |
|---|---|---|
| V S − N day_grids ≥ +20 | +97 met | +19 NOT MET (inconclusive) |
| Q1 day_grids P − S ≥ +20 | −14 FAIL | −4 (FAIL) |
| Q2 transfer P − S ≥ +10 on one | sums8 −14, grids6 −8 FAIL | +1, 0 (FAIL) |
| Q3 P ≥ S − 10 on harm_sums4 / harm_grids4 / day_sums | 281 < 284 FAIL / 192 ≥ 174 / 359 < 361 FAIL | 94 ≥ 82 / 97 ≥ 87 / 76 ≥ 79? no, 76 < 79 (FAIL) |

## Report-only
- Night pool sizes (P): seed 9 sums 84/33/58 misses, grids 229/185/183; seed 10 sums 266/225/241, grids 279/268/270.
  On seed 9 a sums night drew from only 33-84 puzzles.
- On seed 9, P after night 2 had dropped on day_sums (332 vs S 364) and sums8 (88 vs 114): repeating a few missed
  sums looks like it hurt.

## What it means (plain words)
Practising only the day's mistakes did not beat practising the whole day at random; on the valid seed it was worse,
especially on sums, where the misses were a small set practised over and over. The other seed's starting net had
barely learned anything, so it doesn't count. Limits: small nets on CPU, 3 nights, two puzzle kinds, one valid seed.
