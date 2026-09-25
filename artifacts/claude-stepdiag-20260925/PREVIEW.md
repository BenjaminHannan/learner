# CPU previews for road-map R2 and R4 (sleep research thread, 2026-09-25; dev only, not registered)

Small models (width 256), copy phase only (3,000 steps, batch 64, lr 3e-4), seed 2, 296's generator.
Practice never includes three-step. Dev = 200 generated items per kind (seed 777), not a panel.
Numbers are raw right / checked right (after the fact-check) of 200.

## R2: shared chain-step input (rsn-355's change), plain net, 03:35 UTC
| input | one-step | two-step | three-step (never practised) |
|---|---|---|---|
| old (one slot per step) | 200 / 200 | 141 / 91 | 0 / 0 |
| shared chain-step input | 199 / 199 | 137 / 83 | **64 / 13** |

- Suggested (1 seed, small, copy only): the shared input lets the net answer some three-step questions it
  never practised (64 of 200 raw), where the old input gets none. One- and two-step barely change.
- Most of those answers fail the fact-check (13 checked): the check needs every row of the chain cited, and
  the support head has never had to cite a third row. The registered rsn-355 scores checked answers, so
  its H1 (≥ 6/30 checked) may miss even if the net finds the right answer. Watch raw vs checked there.
