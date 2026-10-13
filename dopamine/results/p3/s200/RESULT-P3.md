# P3 session sheets (tool-computed extras), model seed 200

sealed person seed 93004, 400 sessions, mean requests 3.030

| Arm | mean effort |
|---|---|
| NONE | 3.0300 |
| EAGER-TOOL | 2.4750 |
| HELPER-TOOL | 2.5950 |
| P2 HELPER | 3.1862 |
| P2 EAGER | 3.5550 |
| HELPER-GATED (reported) | 2.8094 |
| ORACLE | 1.7300 |

| Paired difference | mean | 95% interval |
|---|---|---|
| HELPER-TOOL - NONE | -0.4350 | [-0.5131, -0.3575] |
| HELPER-TOOL - P2 HELPER | -0.5913 | [-0.6969, -0.4887] |
| HELPER-GATED - NONE (reported) | -0.2206 | [-0.2775, -0.1644] |

P3-1: PASS (pass: diff <= -0.10 and CI upper < 0; wrong: CI lower > -0.05 on either seed)
P3-2: PASS (pass: diff <= -0.15 and CI upper < 0)

HELPER-TOOL extras/session 1.685, wanted share 0.407, extras on last request 170

p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
