# PASSMARKS — Experiment 103: Fable-Edit-SCALE follow-ups (2026-09-22)

One-change follow-ups to the registered FAIL of exp 92. Sealed before any run.

| Mark | Bar (pass =) |
|---|---|
| A1 | S4-clean shared-notebook arm: wrong == 0 (report correct/wrong/miss and n) |
| B1 | English arm with re-ordered patterns on S1–S3: wrong <= 3 total (report per split) |
| B2 | S2-fresh (200 NEW 4-hop cases) English arm: wrong <= 4 of 200 (report correct/wrong/miss) |
| B3 | Notebook arm on S2-fresh: 200/200 correct, 0 wrong (control) |

Rules: every split reported, never averaged. Exp-92 FAIL stands (never re-run into a pass).
S2-fresh: 200 4-hop cases from MQuAKE items not used in any exp-92 split, seed 10300,
zero overlap proved by case id.
