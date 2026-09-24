# rsn-296b pass marks (fixed before any run; 2026-09-24)

Arm: plain, seeds 1 and 2 (the loop arm is not run). The code is 296's plus scripts/claude_rsn296b_run.py. Checked answers only, i.e. after the fact-check.
Panels are the same as 296: reasonpanel296 items-v2 (fresh, 298) and reasonpanel294 items-v3 (transfer, 300). Both are TEST-ONLY and reported at category level. The diagnosis uses scripts/claude_rsn296_diag.py (--n 200, generated episodes only).

| mark | what (each seed) | pass |
|---|---|---|
| P296b.1 | invented answers, each panel | ≤ 2 |
| P296b.2 | diagnosis: counts 1–7 right, and comparing right | each ≥ 160/200 |
| P296b.3 | fresh panel counting + comparing | ≥ 296 same seed + 12, i.e. ≥ 40/60 for both seeds (296: 28 and 28) |
| P296b.4 | fresh panel total | ≥ 228/298 |
| P296b.5 | fresh code-doable, and transfer total | ≥ 168/178, and ≥ 228/300 (296 got 238) |

PASS = all five marks on both seeds.
**What proves the idea wrong:** P296b.2 fails on both seeds. Being told the answer then does not teach this 30M net to count or compare, and the next question is architecture, not practice.
Predictions:
- P296b.1 pass.
- P296b.2 uncertain (the tiny CPU check says it may fail).
- P296b.3 and P296b.4 follow P296b.2.
- P296b.5 likely pass.
