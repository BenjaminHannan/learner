# P2 session sheets, model seed 200, helper rule top1

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s200-v7/night_7/checkpoint.pt
sealed person seed: 93003
sealed sessions: 400, mean requests per session 2.993

| Arm | mean effort (person actions / session) |
|---|---|
| NONE | 2.9925 |
| EAGER | 3.5025 |
| HELPER | 3.1025 |
| ORACLE | 2.4175 |

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| HELPER-NONE | +0.1100 | [+0.0425, +0.1762] |
| HELPER-EAGER | -0.4000 | [-0.4838, -0.3181] |

P2-1: PROVED WRONG (on this seed)  (pass: diff <= -0.05 and CI upper < 0; wrong: CI lower > 0 on either seed)
P2-2: PASS  (pass: diff <= -0.10 and CI upper < 0; wrong: diff >= 0 on both seeds)

ORACLE saving per session: 0.5750

| Arm | extras/session | wanted | right | unwanted | extras on last request |
|---|---|---|---|---|---|
| EAGER | 2.993 | 0.335 | 0.474 | 0.665 | 400 |
| HELPER | 1.140 | 0.351 | 0.546 | 0.649 | 131 |
| ORACLE | 0.575 | 1.000 | 1.000 | 0.000 | 0 |

Extras per kind (kind labels used for scoring only):

| Kind | EAGER | HELPER | ORACLE |
|---|---|---|---|
| SUM | 346 | 103 | 45 |
| MAX | 306 | 147 | 86 |
| MIN | 208 | 103 | 60 |
| PRODUCT | 9 | 6 | 0 |
| cell arithmetic | 29 | 11 | 12 |
| division | 4 | 0 | 0 |
| MOD | 148 | 36 | 6 |
| ABS | 107 | 36 | 21 |
| COUNTIF | 21 | 5 | 0 |
| IF | 19 | 9 | 0 |

p1_sessions.py sha256: de050bc9fc24dce08ba6e16eb80dfb1890836b49246169d7d9f9aa75c1f29950
