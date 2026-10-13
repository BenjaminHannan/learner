# P2 session sheets, model seed 201, helper rule top1

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt
sealed person seed: 93003
sealed sessions: 400, mean requests per session 2.993

| Arm | mean effort (person actions / session) |
|---|---|
| NONE | 2.9925 |
| EAGER | 3.3806 |
| HELPER | 3.0312 |
| ORACLE | 2.3075 |

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| HELPER-NONE | +0.0387 | [-0.0325, +0.1100] |
| HELPER-EAGER | -0.3494 | [-0.4263, -0.2725] |

P2-1: neither pass nor wrong  (pass: diff <= -0.05 and CI upper < 0; wrong: CI lower > 0 on either seed)
P2-2: PASS  (pass: diff <= -0.10 and CI upper < 0; wrong: diff >= 0 on both seeds)

ORACLE saving per session: 0.6850

| Arm | extras/session | wanted | right | unwanted | extras on last request |
|---|---|---|---|---|---|
| EAGER | 2.993 | 0.321 | 0.568 | 0.679 | 400 |
| HELPER | 1.315 | 0.350 | 0.643 | 0.650 | 160 |
| ORACLE | 0.685 | 1.000 | 1.000 | 0.000 | 0 |

Extras per kind (kind labels used for scoring only):

| Kind | EAGER | HELPER | ORACLE |
|---|---|---|---|
| SUM | 354 | 152 | 86 |
| MAX | 291 | 163 | 96 |
| MIN | 205 | 81 | 47 |
| PRODUCT | 7 | 2 | 5 |
| cell arithmetic | 64 | 32 | 12 |
| division | 3 | 0 | 0 |
| MOD | 133 | 33 | 3 |
| ABS | 116 | 53 | 25 |
| COUNTIF | 9 | 3 | 0 |
| IF | 15 | 7 | 0 |

p1_sessions.py sha256: de050bc9fc24dce08ba6e16eb80dfb1890836b49246169d7d9f9aa75c1f29950
