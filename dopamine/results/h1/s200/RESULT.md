# H-1 learned help chooser, model seed 200

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s200-v7/night_7/checkpoint.pt
sealed sessions: 400 (easygoing 183, tidy 217), mean requests 3.035, training days 20

| Arm | all | easygoing | tidy |
|---|---|---|---|
| NONE | 3.0350 | 3.1038 | 2.9770 |
| EAGER-TOOL | 3.0938 | 2.4186 | 3.6632 |
| HELPER-TOOL | 2.8423 | 2.7646 | 2.9077 |
| CHOOSER | 2.9159 | 2.7844 | 3.0268 |
| ORACLE | 1.6150 | 1.6339 | 1.5991 |

Mean effort = person actions per session + 0.02 per tool call (lower is better).

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| CHOOSER-HELPER-TOOL | +0.0737 | [-0.0141, +0.1617] |
| CHOOSER-EAGER-TOOL | -0.1779 | [-0.2905, -0.0682] |

H1-1: PROVED WRONG (on this seed)  (pass: CHOOSER - HELPER-TOOL <= -0.10 and CI upper < 0; wrong: diff >= 0 on either seed)
H1-2: PASS  (pass: CHOOSER - EAGER-TOOL <= -0.05 and CI upper < 0)
H1-3: PROVED WRONG (on this seed)  offer rate after thanks 15.0% (n 240) vs after plain 23.0% (n 574), gap -8.00 points  (pass: |gap| <= 3 points; wrong: |gap| > 5 points)
H1-4: meets 90%  368 of 368 shown extras used the tool (100.0%)
H1-1..3 all pass on this seed: False (H-1 passes only if so on both seeds)

| CHOOSER action shares (sealed, rounds with a candidate) | rounds | quiet | own answer | tool |
|---|---|---|---|---|
| all | 1214 | 0.697 | 0.000 | 0.303 |
| easygoing | 568 | 0.688 | 0.000 | 0.312 |
| tidy | 646 | 0.704 | 0.000 | 0.296 |
| position 1 | 400 | 0.500 | 0.000 | 0.500 |
| position 2 | 400 | 0.700 | 0.000 | 0.300 |
| position 3 | 276 | 0.866 | 0.000 | 0.134 |
| position 4 | 138 | 0.920 | 0.000 | 0.080 |

| Arm | extras/session | tool calls/session | wanted share | accepted share |
|---|---|---|---|---|
| EAGER-TOOL | 3.035 | 3.035 | 0.394 | 0.394 |
| HELPER-TOOL | 0.988 | 0.988 | 0.509 | 0.509 |
| CHOOSER | 0.920 | 0.920 | 0.481 | 0.481 |

ORACLE saving per session: 1.4200

| Training day | reward/round | quiet | own | tool | entropy |
|---|---|---|---|---|---|
| 1 | -0.3758 | 0.36 | 0.32 | 0.32 | 0.977 |
| 2 | -0.0434 | 0.32 | 0.10 | 0.58 | 0.550 |
| 3 | -0.0736 | 0.62 | 0.13 | 0.25 | 0.708 |
| 4 | -0.0347 | 0.69 | 0.10 | 0.21 | 0.582 |
| 5 | -0.0158 | 0.72 | 0.04 | 0.24 | 0.536 |
| 6 | -0.0582 | 0.75 | 0.04 | 0.21 | 0.524 |
| 7 | -0.0021 | 0.69 | 0.01 | 0.30 | 0.466 |
| 8 | +0.0076 | 0.69 | 0.02 | 0.29 | 0.434 |
| 9 | +0.0222 | 0.71 | 0.01 | 0.28 | 0.392 |
| 10 | +0.0049 | 0.70 | 0.01 | 0.28 | 0.431 |
| 11 | +0.0065 | 0.65 | 0.01 | 0.34 | 0.510 |
| 12 | -0.0020 | 0.61 | 0.00 | 0.38 | 0.488 |
| 13 | +0.0306 | 0.58 | 0.00 | 0.42 | 0.510 |
| 14 | +0.0310 | 0.62 | 0.00 | 0.38 | 0.428 |
| 15 | +0.0685 | 0.68 | 0.01 | 0.31 | 0.431 |
| 16 | +0.0163 | 0.64 | 0.01 | 0.35 | 0.344 |
| 17 | +0.0015 | 0.61 | 0.00 | 0.39 | 0.309 |
| 18 | +0.0339 | 0.65 | 0.01 | 0.34 | 0.311 |
| 19 | +0.0289 | 0.62 | 0.01 | 0.37 | 0.329 |
| 20 | +0.0473 | 0.64 | 0.00 | 0.36 | 0.274 |

constants: {"HIDDEN": 32, "LR": 0.002, "EPOCHS_PER_DAY": 8, "ENT_W": 0.05, "CHOOSER_SEED": 7, "TRAIN_SEED": 93006, "SEALED_SEED": 93005, "TOOL_COST": 0.02, "COST": {"0": 0.25, "1": 1.0}, "P_THANKS": 0.3}
h1_chooser.py sha256: 29b76a2a81002310b044e0babfb8b3ddd48cb0d29e6f84a7a594a37937f10ec8
p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
