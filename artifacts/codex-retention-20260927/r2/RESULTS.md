# R2 mastered-snapshot retention results

**PASS under the sealed [R2 PASSMARKS](PASSMARKS.md).** Both preregistered seeds mastered grids and sums at **200/200** on their independent held-out panels. After sum training, the latest mutable model scored **0/200** on grids on each seed, losing all 200 previously correct items. Routing the caller's known grid task ID to its complete frozen grid snapshot kept **200/200**, with zero previously correct items lost and all required bitwise and restart checks passing. R2 does not change R1's separate **INCONCLUSIVE** verdict.

## Shown

The 1,646,750-parameter existing small dense loop trained for exactly **6,000 grids steps, then 2,500 sums steps**, batch 64, no replay. Each seed used fresh 200-item grids5 and sums4 panels. The primary count is exact correctness at the model's own stop; fixed16 and any48 are report-only.

| Seed / held-out seed | Evaluation point and serving model | Grids5 own stop / fixed16 / any48 | Sums4 own stop / fixed16 / any48 |
| --- | --- | ---: | ---: |
| 31 / 92031 | After grids, current and frozen grid model | 200 / 200 / 200 | 0 / 0 / 0 (current only) |
| 31 / 92031 | After sums, latest mutable model | 0 / 0 / 0 | 200 / 200 / 200 |
| 31 / 92031 | After sums, task-routed frozen snapshots | 200 / 200 / 200 | 200 / 200 / 200 |
| 32 / 92032 | After grids, current and frozen grid model | 200 / 200 / 200 | 0 / 0 / 0 (current only) |
| 32 / 92032 | After sums, latest mutable model | 0 / 0 / 0 | 200 / 200 / 200 |
| 32 / 92032 | After sums, task-routed frozen snapshots | 200 / 200 / 200 | 200 / 200 / 200 |

On **each** seed, the mutable control lost **200** previously correct grid items and gained **0**; the routed snapshot lost **0** and gained **0**. Each saved grid tensor and the state hash were unchanged after sum training. Predicted tokens and stop probabilities at **all 48 rounds** on the fixed first 16 grid items were bit-identical before/after B and after reload; all 200 per-item own-stop outcomes agreed exactly. Serialization/reload preserved A and B outputs. Alternating grid/sum/grid requests returned identical outputs and stop probabilities, and an unknown task ID was rejected. These are complete-model snapshots; the B learner was a fully trainable clone of A. The comparison used the same training trajectory for both serving paths.

Seed 31 rejected 0 training/final-panel input collisions in grids and 3 in sums; seed 32 rejected 0 and 2. Replacement retained puzzle size. Neither panel selected a checkpoint or training duration.

| Seed | Device / Torch | UTC start–end | Wall time | Phase A training time | Phase B training time | Two checkpoint bytes | Two-model parameters |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 31 | MPS / 2.14.0 | 2026-09-27 04:13:40–04:26:02 | 742.1 s | 578.6 s | 152.0 s | 13,198,245 | 3,293,500 |
| 32 | MPS / 2.14.0 | 2026-09-27 04:26:22–04:38:16 | 713.9 s | 556.3 s | 146.7 s | 13,198,245 | 3,293,500 |

Each grid checkpoint is **6,599,145 bytes**; each sum checkpoint is **6,599,100 bytes**. Both runs used software HEAD and PASSMARKS commit `57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7` on MacBook-Pro. R2's measured phase-A training time was **321.6 s** and **310.6 s** longer than R1 seeds 29 and 30 respectively (R1 times 257.0 s and 245.7 s); those are cross-seed operational comparisons, not paired causal estimates. Full provenance, scores, checks, training logs, and checkpoints are in [seed31](seed31/result.json) and [seed32](seed32/result.json), with their own `RUN-NOTE.md` files.

## Suggested by the observations

When the caller supplies the correct task identity, a complete frozen snapshot can preserve a mastered grid skill through training a new sum skill. The paired latest-model control reproduced catastrophic forgetting in both mastered trajectories. This supports the scoped, task-aware serving mechanism tested here.

## Untested

The route does not learn task identity, select a model from an ambiguous input, retain both skills in one fixed-size network, cover other puzzle families, or establish language-model retention. Storage and serving capacity grow by one complete model per skill. R2 supplies no evidence about task-agnostic or equal-total-size continual learning.
