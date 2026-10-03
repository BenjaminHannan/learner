# vast ledger, two-doors test (thread "more information into the model")

| box | offer | GPU | $/h | arms | created (UTC) | destroyed (UTC) | copy-back checked | cost |
|---|---|---|---|---|---|---|---|---|
| 54052833 | 43861052 | RTX 3090 (Utah) | 0.151 | A, B | 19:14 | 19:16 | nothing to copy (pip PEP 668 fail at start) | ~$0.01 |
| 54052838 | 52714981 | RTX 3090 (California) | 0.156 | W, BW | 19:14 | 19:16 | nothing to copy (pip PEP 668 fail at start) | ~$0.01 |
| 54052840 | 51737580 | RTX 3090 (US) | 0.156 | C | 19:14 | 19:16 | nothing to copy (pip PEP 668 fail at start) | ~$0.01 |
| 54053228 | 50484118 | RTX 3090 (California) | 0.139 | A, B | 19:17 | 21:44 (stopped 21:37) | yes: 12/12 JSON files per arm read back and parsed | ~$0.37 (hung 1.5 h on a wait-loop bug: pgrep matched its own job script) |
| 54053230 | 49476168 | RTX 3090 (Utah) | 0.144 | W, BW | 19:17 | 21:44 (stopped 21:37) | yes: 12/12 JSON files per arm read back and parsed | ~$0.38 (hung 1.5 h on a wait-loop bug: pgrep matched its own job script) |
| 54053231 | 44133030 | RTX 3090 (US) | 0.164 | C | 19:17 | 21:44 (stopped 21:37) | yes: 12/12 JSON files per arm read back and parsed | ~$0.43 (hung 1.5 h on a wait-loop bug: pgrep matched its own job script) |
| 54067360 | 37955906 | RTX 3090 (BC, Canada) | 0.150 | B | 21:39 | | | |
| 54067364 | 43703592 | RTX 3090 (California) | 0.169 | BW | 21:39 | | | |
