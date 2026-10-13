# H-2 results, model seed 201
checkpoint: /mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt
sealed sessions by person: {'easygoing': 183, 'tidy': 217}

## H-2: HELPER-REACT (HELPER-TOOL + reaction counts and thanks in the value head)

| Arm | all | easygoing | tidy |
|---|---|---|---|
| NONE | 3.0350 | 3.1038 | 2.9770 |
| EAGER-TOOL | 3.1057 | 2.4118 | 3.6909 |
| HELPER-TOOL | 2.9138 | 2.7599 | 3.0436 |
| HELPER-REACT | 2.9241 | 2.7525 | 3.0688 |

HELPER-REACT - HELPER-TOOL: +0.0103 [-0.0769, +0.0967] (10,000 resamples, seed 0)

H2-1: PROVED WRONG (on this seed)  (pass: HELPER-REACT - HELPER-TOOL <= -0.05 and CI upper < 0; wrong: diff >= 0 on either seed)
H2-3: neither pass nor wrong  offer rate after thanks 37.9% (n 240) vs after plain 32.9% (n 574), gap +4.99 points  (pass: |gap| <= 3 points; wrong: |gap| > 5 points)
H-2 passes on this seed: False (H-2 passes only if so on both seeds)

| Extras rate in the next round | after removed | after left |
|---|---|---|
| HELPER-REACT | 56.4% (n 78) | 73.7% (n 76) |
| HELPER-TOOL | 47.7% (n 86) | 45.3% (n 64) |

h1_chooser.py sha256: 9579fc73bd1d66e17f8ae7273a1c6aec52120f2f99f18fd0472bb8579ee1311b
p1_sessions.py sha256: 64b77011fcaf1a31c5a273b8b0a2edaa581722f88fd2a1a2ceb332a80d267da6
