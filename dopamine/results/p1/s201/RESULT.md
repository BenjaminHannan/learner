# P1 session sheets, model seed 201

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt
sealed sessions: 400, mean requests per session 2.973

| Arm | mean effort (person actions / session) |
|---|---|
| NONE | 2.9725 |
| EAGER | 3.2606 |
| HELPER | 3.3325 |
| ORACLE | 2.2725 |

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| HELPER-NONE | +0.3600 | [+0.2994, +0.4188] |
| HELPER-EAGER | +0.0719 | [-0.0294, +0.1744] |

P1-1: PROVED WRONG (on this seed)  (pass: diff <= -0.05 and CI upper < 0; wrong: CI lower > 0 on either seed)
P1-2: wrong on this seed (diff >= 0; proved wrong only if also on the other seed)  (pass: diff <= -0.10 and CI upper < 0; wrong: diff >= 0 on both seeds)

ORACLE saving per session: 0.7000

| Arm | extras/session | wanted | right | unwanted | extras on last request |
|---|---|---|---|---|---|
| EAGER | 2.973 | 0.357 | 0.601 | 0.643 | 400 |
| HELPER | 2.260 | 0.115 | 0.572 | 0.885 | 293 |
| ORACLE | 0.700 | 1.000 | 1.000 | 0.000 | 0 |

Extras per kind (kind labels used for scoring only):

| Kind | EAGER | HELPER | ORACLE |
|---|---|---|---|
| SUM | 346 | 135 | 82 |
| MAX | 326 | 258 | 114 |
| MIN | 198 | 74 | 52 |
| PRODUCT | 6 | 53 | 1 |
| cell arithmetic | 57 | 138 | 7 |
| division | 2 | 14 | 4 |
| MOD | 125 | 18 | 3 |
| ABS | 114 | 64 | 17 |
| COUNTIF | 6 | 55 | 0 |
| IF | 9 | 95 | 0 |

p1_sessions.py sha256: 2f65e028470dffab18d6244e8cbb06f37755bd0e4fa593de7a453b96fdac1d7f
