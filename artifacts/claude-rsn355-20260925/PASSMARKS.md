# rsn-355 pass marks (fixed before any run; 2026-09-25)

One change from 296's plain arm: shared chain-step input (design/v3/30-modes/355-shared-step-embedding.md).
Scoring as in 296: checked right, 294's sealed scorer, TEST-ONLY panels at category level only.
Three-step is never practised (value3 is not in COPY_KINDS or ALL_KINDS).

| mark | what (each seed) | pass |
|---|---|---|
| H1 | fresh panel296 v2, heldout_three_step, checked right | ≥ 6/30 on BOTH seeds (296: 0 / 0) |
| H2 | fresh panel296 v2 total WITHOUT three-step | ≥ 296 same seed − 5 (s1 ≥ 220, s2 ≥ 212) |
| H3 | invented answers (checked), each panel | ≤ 2 |
| H4 | transfer panel294 v3 heldout_three_step (/15), dev value3 (/100) | report |

Verdict: **PASS = H1, H2 and H3 on both seeds.**

**Proved wrong ("the untrained slot is what blocks three-step"):** H1 ≤ 1/30 on both seeds while H2 passes.
Then the plain net cannot chain past what it practised even with a trained input, and the next step is
practising three-step (round 1's C1), not input fixes.

Predictions: H2 likely pass; H1 uncertain (the net has never had to chain three lookups, and 6 layers is
enough depth in principle); H3 likely pass.
