# Baseline v2 length-generalisation read — Fable's predictions

Written 2026-09-20 ~13:45 local, BEFORE any scorer exists and before any baseline-v2 checkpoint has been scored on any panel other than its four
fit cells (dev 512/512 ×4, sealed confirm 512/512 ×4, 3/3 seeds, arm I1-H1). Known: the baseline practised 1–3 hops, 6 people, steps mode,
line positions. System S (dispatcher v3 + operators) clears all 25 development cells (≥ 59/64). My record so far: 7 hits / 7 misses.

Panels: the 25 v3 dispatcher development cells × 64 (excluded from baseline training by construction). Mark per cell: 58/64 answers.
This is a DEVELOPMENT read, not confirmation.

| id | forecast | p | falsified by |
|---|---|---|---|
| P47 | every practised-length cell (1–3 hops, 6 people, practised terminal) clears 58/64 in ≥ 2/3 seeds | 0.85 | ≤ 1 seed |
| P48 | at least one cell with ≥ 5 hops clears 58/64 in ≥ 2/3 seeds | 0.15 | none does |
| P49 | all 25 cells clear in ≥ 1 seed (baseline matches System S on development) | 0.05 | no seed clears all |
| P50 | mean answers on cells with ≥ 5 hops is below 32/64 in ≥ 2/3 seeds | 0.65 | ≥ 2 seeds at or above 32 |
