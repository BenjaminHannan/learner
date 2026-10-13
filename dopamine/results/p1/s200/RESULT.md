# P1 session sheets, model seed 200

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s200-v7/night_7/checkpoint.pt
sealed sessions: 400, mean requests per session 2.973

| Arm | mean effort (person actions / session) |
|---|---|
| NONE | 2.9725 |
| EAGER | 3.4700 |
| HELPER | 3.3875 |
| ORACLE | 2.3925 |

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| HELPER-NONE | +0.4150 | [+0.3581, +0.4706] |
| HELPER-EAGER | -0.0825 | [-0.1762, +0.0144] |

P1-1: PROVED WRONG (on this seed)  (pass: diff <= -0.05 and CI upper < 0; wrong: CI lower > 0 on either seed)
P1-2: neither pass nor wrong  (pass: diff <= -0.10 and CI upper < 0; wrong: diff >= 0 on both seeds)

ORACLE saving per session: 0.5800

| Arm | extras/session | wanted | right | unwanted | extras on last request |
|---|---|---|---|---|---|
| EAGER | 2.973 | 0.354 | 0.483 | 0.646 | 400 |
| HELPER | 2.072 | 0.107 | 0.403 | 0.893 | 273 |
| ORACLE | 0.580 | 1.000 | 1.000 | 0.000 | 0 |

Extras per kind (kind labels used for scoring only):

| Kind | EAGER | HELPER | ORACLE |
|---|---|---|---|
| SUM | 333 | 68 | 40 |
| MAX | 341 | 152 | 94 |
| MIN | 202 | 150 | 61 |
| PRODUCT | 6 | 41 | 1 |
| cell arithmetic | 40 | 59 | 6 |
| division | 4 | 10 | 1 |
| MOD | 134 | 39 | 6 |
| ABS | 93 | 69 | 21 |
| COUNTIF | 22 | 115 | 0 |
| IF | 14 | 126 | 2 |

p1_sessions.py sha256: 2f65e028470dffab18d6244e8cbb06f37755bd0e4fa593de7a453b96fdac1d7f
