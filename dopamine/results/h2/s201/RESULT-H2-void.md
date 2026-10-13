# H-2 results, model seed 201
checkpoint: /mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt
sealed sessions by person: {'easygoing': 183, 'tidy': 217}

## H-2: HELPER-REACT (HELPER-TOOL + reaction counts and thanks in the value head)

| Arm | all | easygoing | tidy |
|---|---|---|---|
| NONE | 3.0350 | 3.1038 | 2.9770 |
| EAGER-TOOL | 3.1057 | 2.4118 | 3.6909 |
| HELPER-TOOL | 2.9138 | 2.7599 | 3.0436 |
| HELPER-REACT | 3.0350 | 3.1038 | 2.9770 |

HELPER-REACT - HELPER-TOOL: +0.1212 [+0.0299, +0.2135] (10,000 resamples, seed 0)

H2-1: PROVED WRONG (on this seed)  (pass: HELPER-REACT - HELPER-TOOL <= -0.05 and CI upper < 0; wrong: diff >= 0 on either seed)
H2-3: PASS  offer rate after thanks 0.0% (n 240) vs after plain 0.0% (n 574), gap +0.00 points  (pass: |gap| <= 3 points; wrong: |gap| > 5 points)
H-2 passes on this seed: False (H-2 passes only if so on both seeds)

| Extras rate in the next round | after removed | after left |
|---|---|---|
| HELPER-REACT | - (n 0) | - (n 0) |
| HELPER-TOOL | 47.7% (n 86) | 45.3% (n 64) |

h1_chooser.py sha256: 18b668be68d902cd11e89a4bf0c11c272cac4e497c63f459be446a67d09d6cc6
p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
