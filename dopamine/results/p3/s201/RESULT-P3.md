# P3 session sheets (tool-computed extras), model seed 201

sealed person seed 93004, 400 sessions, mean requests 3.030

| Arm | mean effort |
|---|---|
| NONE | 3.0300 |
| EAGER-TOOL | 2.4656 |
| HELPER-TOOL | 2.5281 |
| P2 HELPER | 3.0500 |
| P2 EAGER | 3.3506 |
| HELPER-GATED (reported) | 2.7581 |
| ORACLE | 1.7300 |

| Paired difference | mean | 95% interval |
|---|---|---|
| HELPER-TOOL - NONE | -0.5019 | [-0.5806, -0.4225] |
| HELPER-TOOL - P2 HELPER | -0.5219 | [-0.6169, -0.4263] |
| HELPER-GATED - NONE (reported) | -0.2719 | [-0.3381, -0.2069] |

P3-1: PASS (pass: diff <= -0.10 and CI upper < 0; wrong: CI lower > -0.05 on either seed)
P3-2: PASS (pass: diff <= -0.15 and CI upper < 0)

HELPER-TOOL extras/session 1.705, wanted share 0.435, extras on last request 161

p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
