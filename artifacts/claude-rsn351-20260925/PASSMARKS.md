# rsn-351 pass marks (fixed before any run; 2026-09-25)

One change from rsn-350: lr 1e-4 instead of 3e-4. Scoring as in 350 (checked right, 294's sealed
scorer, TEST-ONLY panels at category level only).

| mark | what (each seed) | pass |
|---|---|---|
| Y1 | fresh panel296 v2 total vs the 30M (296) | ≥ 296 same seed + 10 (s1 ≥ 235, s2 ≥ 227) |
| Y2 | fresh panel296 v2 total vs rsn-350 | ≥ 350 same seed + 10 (s1 ≥ 221, s2 ≥ 219) |
| Y3 | fresh three-step, never practised | ≥ 6/30 on at least one seed (report) |
| Y4 | invented answers (checked), each panel | ≤ 2 |

Verdict: **PASS = Y1 and Y4 on both seeds** (size helps when trained slower). Y2 alone answers "was the
learning rate the problem"; Y3 is reported.

**Proved wrong ("the fast learning rate explains 350's drop"):** Y2 fails on both seeds (within +9 of 350).

Predictions: Y2 uncertain; Y1 unlikely (would need +24 and +18 over 350); Y3 likely 0/30 (never practised).
