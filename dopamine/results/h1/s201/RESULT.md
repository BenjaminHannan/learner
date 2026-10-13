# H-1 learned help chooser, model seed 201

checkpoint: /mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt
sealed sessions: 400 (easygoing 183, tidy 217), mean requests 3.035, training days 20

| Arm | all | easygoing | tidy |
|---|---|---|---|
| NONE | 3.0350 | 3.1038 | 2.9770 |
| EAGER-TOOL | 3.1057 | 2.4118 | 3.6909 |
| HELPER-TOOL | 2.9138 | 2.7599 | 3.0436 |
| CHOOSER | 2.9786 | 2.9392 | 3.0118 |
| ORACLE | 1.6150 | 1.6339 | 1.5991 |

Mean effort = person actions per session + 0.02 per tool call (lower is better).

| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |
|---|---|---|
| CHOOSER-HELPER-TOOL | +0.0648 | [-0.0256, +0.1566] |
| CHOOSER-EAGER-TOOL | -0.1271 | [-0.2542, -0.0027] |

H1-1: PROVED WRONG (on this seed)  (pass: CHOOSER - HELPER-TOOL <= -0.10 and CI upper < 0; wrong: diff >= 0 on either seed)
H1-2: PASS  (pass: CHOOSER - EAGER-TOOL <= -0.05 and CI upper < 0)
H1-3: PROVED WRONG (on this seed)  offer rate after thanks 3.3% (n 240) vs after plain 8.4% (n 574), gap -5.03 points  (pass: |gap| <= 3 points; wrong: |gap| > 5 points)
H1-4: meets 90%  147 of 147 shown extras used the tool (100.0%)
H1-1..3 all pass on this seed: False (H-1 passes only if so on both seeds)

| CHOOSER action shares (sealed, rounds with a candidate) | rounds | quiet | own answer | tool |
|---|---|---|---|---|
| all | 1214 | 0.879 | 0.000 | 0.121 |
| easygoing | 568 | 0.879 | 0.000 | 0.121 |
| tidy | 646 | 0.879 | 0.000 | 0.121 |
| position 1 | 400 | 0.772 | 0.000 | 0.228 |
| position 2 | 400 | 0.900 | 0.000 | 0.100 |
| position 3 | 276 | 0.964 | 0.000 | 0.036 |
| position 4 | 138 | 0.957 | 0.000 | 0.043 |

| Arm | extras/session | tool calls/session | wanted share | accepted share |
|---|---|---|---|---|
| EAGER-TOOL | 3.035 | 3.035 | 0.392 | 0.392 |
| HELPER-TOOL | 1.222 | 1.222 | 0.468 | 0.468 |
| CHOOSER | 0.367 | 0.367 | 0.510 | 0.510 |

ORACLE saving per session: 1.4200

| Training day | reward/round | quiet | own | tool | entropy |
|---|---|---|---|---|---|
| 1 | -0.3672 | 0.36 | 0.32 | 0.32 | 0.945 |
| 2 | +0.0049 | 0.31 | 0.14 | 0.55 | 0.498 |
| 3 | -0.0702 | 0.72 | 0.12 | 0.16 | 0.517 |
| 4 | -0.0131 | 0.77 | 0.07 | 0.16 | 0.464 |
| 5 | -0.0217 | 0.80 | 0.02 | 0.18 | 0.389 |
| 6 | -0.0147 | 0.84 | 0.04 | 0.13 | 0.324 |
| 7 | -0.0180 | 0.84 | 0.04 | 0.12 | 0.322 |
| 8 | -0.0123 | 0.83 | 0.03 | 0.14 | 0.333 |
| 9 | -0.0100 | 0.83 | 0.03 | 0.14 | 0.307 |
| 10 | +0.0007 | 0.80 | 0.01 | 0.19 | 0.307 |
| 11 | +0.0099 | 0.84 | 0.02 | 0.14 | 0.322 |
| 12 | -0.0223 | 0.81 | 0.01 | 0.18 | 0.285 |
| 13 | -0.0116 | 0.73 | 0.02 | 0.25 | 0.285 |
| 14 | +0.0209 | 0.79 | 0.01 | 0.20 | 0.223 |
| 15 | +0.0196 | 0.87 | 0.01 | 0.12 | 0.250 |
| 16 | +0.0190 | 0.90 | 0.00 | 0.10 | 0.245 |
| 17 | +0.0190 | 0.87 | 0.01 | 0.12 | 0.227 |
| 18 | +0.0042 | 0.83 | 0.01 | 0.16 | 0.258 |
| 19 | +0.0009 | 0.81 | 0.01 | 0.18 | 0.246 |
| 20 | +0.0388 | 0.79 | 0.02 | 0.19 | 0.242 |

constants: {"HIDDEN": 32, "LR": 0.002, "EPOCHS_PER_DAY": 8, "ENT_W": 0.05, "CHOOSER_SEED": 7, "TRAIN_SEED": 93006, "SEALED_SEED": 93005, "TOOL_COST": 0.02, "COST": {"0": 0.25, "1": 1.0}, "P_THANKS": 0.3}
h1_chooser.py sha256: 29b76a2a81002310b044e0babfb8b3ddd48cb0d29e6f84a7a594a37937f10ec8
p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
