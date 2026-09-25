# rsn-354 pass marks (fixed before any run; 2026-09-25)

One change from rsn-351 (3x) and from 296 / 351b (1x): 12,000 practice steps instead of 6,000.
Scoring as in 350/351: checked right, 294's sealed scorer, TEST-ONLY panels at category level only.
"1x" = the better 1x arm on dev (B or C, see design/v3/30-modes/354-more-practice-both-sizes.md).

| mark | what (each seed) | pass |
|---|---|---|
| P1 | fresh panel296 v2 total, 3x (A) vs 1x, same seed, same run | A ≥ 1x + 10 |
| P2 | practice gain (final − copy-only total on panel296), 3x vs 1x | A's gain ≥ 1x's gain (report) |
| P3 | invented answers (checked), each panel, every arm | ≤ 2 |
| P4 | fresh three-step, never practised | report (every run so far: 0/30) |
| P5 | fresh panel296 v2 total, A vs rsn-351 same seed (221 / 218) | report: did more practice help the 3x? |

Verdict: **PASS = P1 and P3 on both seeds.** A PASS sends the frozen recipes to the fresh blind panel
(plan 352 step S3); it is not by itself "the 3x beats the 1x".

**Proved wrong ("the 3x just needs more practice"):** A ≤ rsn-351 + 2 on both seeds (s1 ≤ 223, s2 ≤ 220).

Predictions: P5 likely small gain (351's reward was flat over its last 2,000 steps on s1, still rising on
s2); P1 unlikely but possible; P4 0/30.
