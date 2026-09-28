# Few-example ruler: INCONCLUSIVE

Written 2026-09-28 01:47:37 UTC. **Shown: V1 and V2 passed; V3 failed, so the 9×9 holdout was never opened.** The registered stop rule ended the two remaining loop seed-1 streams after 16,384 examples. No architecture wins or design-race verdict follow from this ruler.

Original pass-mark seal: `3acb5d18a`. Execution seal after three pre-maze addenda: `aeb524cd0`. The original 6,000-step plain source runs failed V1. ADDENDUM-3 qualified both architectures with 12,000 matched source batches before any maze score; the source guard below uses a fresh 200/200 panel.

## Validity

| Check | Result | Evidence |
|---|---|---|
| V1 | PASS | Every qualified net ≥190/200 on sums and grids separately. |
| V2 | PASS | Every two-dimensional weight matrix had a nonzero fp32 CPU gradient on sums or grids. |
| V3 | FAIL | No arm can have three dev 9×9 rungs strictly between 10% and 90%, even if the two missing 65,536-example scores were in range. |

| Arm | Seed | 4-digit sums | 5×5 grids | Live matrices | Weights / persistent coefficients | Source minutes |
|---|---:|---:|---:|---:|---:|---:|
| loop | 0 | 200 of 200 | 200 of 200 | 16 of 16 | 1,645,726 / 1,645,726 | 46.2 |
| loop | 1 | 200 of 200 | 200 of 200 | 16 of 16 | 1,645,726 / 1,645,726 | 46.8 |
| plain | 0 | 200 of 200 | 195 of 200 | 51 of 51 | 1,619,965 / 1,619,965 | 16.9 |
| plain | 1 | 200 of 200 | 191 of 200 | 51 of 51 | 1,619,965 / 1,619,965 | 26.2 |

Each qualified source model saw 12,000 × 64 = 768,000 code-made source examples; training minutes are wall time under concurrent CPU load. No maze appeared in source training, tuning, or validation.

| Dev arm | Seed | Intermediate rungs | More rungs possible | Maximum intermediate rungs |
|---|---:|---|---:|---:|
| pre loop | 0 | 4096 | 0 | 1 |
| fresh loop | 0 | none | 0 | 0 |
| pre loop | 1 | 4096 | 1 | 2 |
| fresh loop | 1 | none | 1 | 1 |
| pre plain | 0 | 4096, 16384 | 0 | 2 |
| fresh plain | 0 | 16384 | 0 | 1 |
| pre plain | 1 | 4096, 16384 | 0 | 2 |
| fresh plain | 1 | 16384 | 0 | 1 |

The final two loop seed-1 processes were stopped by exact PIDs 21678 and 21679 with SIGTERM at 2026-09-28 01:37 UTC. Their saved checkpoints were recounted without training. All six completed streams had 65,536 distinct 9×9 layouts and zero overlap with panels or supports; each support had 64 distinct 9×9 layouts. Possible layouts: 7×7 192, 9×9 100,352, 11×11 557,568,000. Panel layouts were all distinct: dev 24/300/300 and untouched holdout 48/300/300 for 7×7/9×9/11×11.

## Dev ladder

Counts below are development scores. ‘not run’ means the registered V3 stop ended the two loop seed-1 streams before 65,536. The 7×7 dev panel has 24 mazes; 9×9 and 11×11 have 300 each.

| Arm | Seed | Examples | 7×7 | 9×9 | 11×11 | Fixed-depth 9×9 | Mean rounds | Cap hits | Stop failure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| pre loop | 0 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 0 | 1 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 31.3 | 53 of 300 | no |
| pre loop | 0 | 4 | 1 of 24 | 1 of 300 | 0 of 300 | 1 of 300 | 24.0 | 111 of 300 | no |
| pre loop | 0 | 16 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 35.3 | 145 of 300 | no |
| pre loop | 0 | 64 | 2 of 24 | 2 of 300 | 0 of 300 | 2 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 0 | 256 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 9.0 | 0 of 300 | no |
| pre loop | 0 | 1024 | 1 of 24 | 2 of 300 | 0 of 300 | 2 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 0 | 4096 | 16 of 24 | 82 of 300 | 44 of 300 | 77 of 300 | 37.3 | 159 of 300 | no |
| pre loop | 0 | 16384 | 24 of 24 | 271 of 300 | 183 of 300 | 269 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 0 | 65536 | 24 of 24 | 300 of 300 | 272 of 300 | 300 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 0 | 1 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 4 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 16 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 64 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 256 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 1024 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 4096 | 1 of 24 | 3 of 300 | 0 of 300 | 3 of 300 | 48.0 | 300 of 300 | no |
| fresh loop | 0 | 16384 | 8 of 24 | 17 of 300 | 6 of 300 | 20 of 300 | 47.9 | 299 of 300 | no |
| fresh loop | 0 | 65536 | 24 of 24 | 283 of 300 | 199 of 300 | 282 of 300 | 20.6 | 39 of 300 | no |
| pre loop | 1 | 0 | — | 0 of 300 | — | 0 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 1 | 1 | — | 0 of 300 | — | 0 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 1 | 4 | — | 0 of 300 | — | 0 of 300 | 5.2 | 0 of 300 | no |
| pre loop | 1 | 16 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| pre loop | 1 | 64 | — | 1 of 300 | — | 1 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 1 | 256 | — | 0 of 300 | — | 0 of 300 | 4.3 | 0 of 300 | no |
| pre loop | 1 | 1024 | — | 5 of 300 | — | 5 of 300 | 8.2 | 10 of 300 | no |
| pre loop | 1 | 4096 | — | 46 of 300 | — | 49 of 300 | 48.0 | 300 of 300 | no |
| pre loop | 1 | 16384 | — | 282 of 300 | — | 274 of 300 | 20.0 | 68 of 300 | no |
| pre loop | 1 | 65536 | — | not run | — | — | — | — | — |
| fresh loop | 1 | 0 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 1 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 4 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 16 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 64 | — | 0 of 300 | — | 0 of 300 | 5.0 | 0 of 300 | no |
| fresh loop | 1 | 256 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 1024 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 4096 | — | 0 of 300 | — | 0 of 300 | 3.0 | 0 of 300 | no |
| fresh loop | 1 | 16384 | — | 0 of 300 | — | 0 of 300 | 4.9 | 0 of 300 | no |
| fresh loop | 1 | 65536 | — | not run | — | — | — | — | — |
| pre plain | 0 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 1 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 4 | 1 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 16 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 64 | 0 of 24 | 2 of 300 | 0 of 300 | 2 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 256 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 1024 | 1 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 4096 | 13 of 24 | 76 of 300 | 18 of 300 | 76 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 16384 | 23 of 24 | 190 of 300 | 20 of 300 | 190 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 0 | 65536 | 24 of 24 | 279 of 300 | 130 of 300 | 279 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 1 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 4 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 16 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 64 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 256 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 1024 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 4096 | 0 of 24 | 2 of 300 | 0 of 300 | 2 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 16384 | 18 of 24 | 144 of 300 | 43 of 300 | 144 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 0 | 65536 | 24 of 24 | 270 of 300 | 127 of 300 | 270 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 1 | 0 of 24 | 7 of 300 | 2 of 300 | 7 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 4 | 0 of 24 | 1 of 300 | 0 of 300 | 1 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 16 | 1 of 24 | 6 of 300 | 1 of 300 | 6 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 64 | 0 of 24 | 1 of 300 | 2 of 300 | 1 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 256 | 2 of 24 | 7 of 300 | 0 of 300 | 7 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 1024 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 4096 | 9 of 24 | 42 of 300 | 16 of 300 | 42 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 16384 | 23 of 24 | 225 of 300 | 58 of 300 | 225 of 300 | 1.0 | 0 of 300 | no |
| pre plain | 1 | 65536 | 23 of 24 | 273 of 300 | 115 of 300 | 273 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 0 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 1 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 4 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 16 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 64 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 256 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 1024 | 0 of 24 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 4096 | 0 of 24 | 1 of 300 | 0 of 300 | 1 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 16384 | 14 of 24 | 149 of 300 | 72 of 300 | 149 of 300 | 1.0 | 0 of 300 | no |
| fresh plain | 1 | 65536 | 24 of 24 | 287 of 300 | 132 of 300 | 287 of 300 | 1.0 | 0 of 300 | no |

## Descriptive dev scores

The registered primary `F_all` requires the unopened holdout, so no primary score exists. These dev values describe the observed runs only. `F_all` uses nine positive rungs; it is unavailable for the two stopped runs.

| Arm | Seed | Dev F_all | Dev F_few | Dev cold | Dev F_few − cold | 65,536 dev | Adaptation job minutes |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre loop | 0 | 24.37 | 0.25 | 0.00 | +0.25 | 300 of 300 | 77.4 |
| fresh loop | 0 | 11.22 | 0.00 | 0.00 | +0.00 | 283 of 300 | 77.4 |
| pre loop | 1 | — | 0.08 | 0.00 | +0.08 | not run | stopped |
| fresh loop | 1 | — | 0.00 | 0.00 | +0.00 | not run | stopped |
| pre plain | 0 | 20.26 | 0.17 | 0.00 | +0.17 | 279 of 300 | 48.6 |
| fresh plain | 0 | 15.41 | 0.00 | 0.00 | +0.00 | 270 of 300 | 49.0 |
| pre plain | 1 | 20.81 | 1.25 | 0.00 | +1.25 | 273 of 300 | 49.2 |
| fresh plain | 1 | 16.19 | 0.00 | 0.00 | +0.00 | 287 of 300 | 49.3 |

## Old kinds and sleep

Every old-kind count is of 200. This retention panel is separate from the fresh V1 source guard above. Each arm's replay allowance was the same 128 stored sums and 128 stored grids; each sleep update used four sums, four grids, and eight of that branch's own mazes. `D = before − after sleep` in percentage points; negative means improvement. The 65,536-example sleep did not run for loop seed 1.

| Arm | Seed | Kind | Before | After 64 | Sleep after 64 | D64 | After 65,536 | Sleep after 65,536 | D65,536 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| pre loop | 0 | sums4 | 200 of 200 | 92 of 200 | 194 of 200 | +3.0 | 0 of 200 | 3 of 200 | +98.5 |
| pre loop | 0 | grids5 | 199 of 200 | 11 of 200 | 176 of 200 | +11.5 | 0 of 200 | 0 of 200 | +99.5 |
| fresh loop | 0 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| fresh loop | 0 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| pre loop | 1 | sums4 | 200 of 200 | 143 of 200 | 187 of 200 | +6.5 | not run | not run | — |
| pre loop | 1 | grids5 | 200 of 200 | 128 of 200 | 178 of 200 | +11.0 | not run | not run | — |
| fresh loop | 1 | sums4 | 0 of 200 | 0 of 200 | 1 of 200 | -0.5 | not run | not run | — |
| fresh loop | 1 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | not run | not run | — |
| pre plain | 0 | sums4 | 200 of 200 | 32 of 200 | 199 of 200 | +0.5 | 0 of 200 | 6 of 200 | +97.0 |
| pre plain | 0 | grids5 | 193 of 200 | 153 of 200 | 159 of 200 | +17.0 | 0 of 200 | 1 of 200 | +96.0 |
| fresh plain | 0 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| fresh plain | 0 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| pre plain | 1 | sums4 | 200 of 200 | 195 of 200 | 188 of 200 | +6.0 | 0 of 200 | 11 of 200 | +94.5 |
| pre plain | 1 | grids5 | 190 of 200 | 155 of 200 | 145 of 200 | +22.5 | 0 of 200 | 0 of 200 | +95.0 |
| fresh plain | 1 | sums4 | 0 of 200 | 0 of 200 | 1 of 200 | -0.5 | 0 of 200 | 0 of 200 | +0.0 |
| fresh plain | 1 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |

| Arm | Seed | Sleep branch | Dev 9×9 after sleep | Updates | Minutes |
|---|---:|---|---:|---:|---:|
| pre loop | 0 | 64 | 31 of 300 | 512 | 2.7 |
| pre loop | 0 | 64k | 300 of 300 | 512 | 4.4 |
| fresh loop | 0 | 64 | 0 of 300 | 512 | 2.7 |
| fresh loop | 0 | 64k | 277 of 300 | 512 | 4.4 |
| pre loop | 1 | 64 | 9 of 300 | 512 | recorded only for completed arms |
| fresh loop | 1 | 64 | 0 of 300 | 512 | recorded only for completed arms |
| pre plain | 0 | 64 | 11 of 300 | 512 | 1.3 |
| pre plain | 0 | 64k | 291 of 300 | 512 | 1.9 |
| fresh plain | 0 | 64 | 0 of 300 | 512 | 1.5 |
| fresh plain | 0 | 64k | 292 of 300 | 512 | 2.0 |
| pre plain | 1 | 64 | 5 of 300 | 512 | 1.1 |
| pre plain | 1 | 64k | 291 of 300 | 512 | 1.0 |
| fresh plain | 1 | 64 | 0 of 300 | 512 | 1.1 |
| fresh plain | 1 | 64k | 290 of 300 | 512 | 1.0 |

**Shown (dev only):** source practice improves maze learning around 4,096–16,384 examples in both architectures; 64 unique examples remain near zero. At 4,096, the practiced loop solved 82/300 versus practiced plain 76/300 in seed 0, and 46/300 versus 42/300 in seed 1. At 16,384, loop solved 271/300 versus plain 190/300 in seed 0, and 282/300 versus 225/300 in seed 1. The loop was ahead at those rungs. These are descriptive development findings, not a valid holdout comparison. After 65,536, seed-0 loop solved 300/300 versus plain 279/300; seed 1's loop stopped before that rung. **Suggested:** the registered ladder is too sparse around the transition to provide three intermediate rungs. **Untested:** whether the same gaps hold on the unopened holdout or whether any of the three designs beats these baselines.

**For Ben:** Practice helped these small nets start solving new mazes sooner in the dev test. Learning began to show clearly around 4,096 different mazes, not 64. The loop was ahead of the same-size plain net at 4,096 and 16,384 in both seeds. But the test's own rule says it must catch at least three middle steps of learning; it caught at most two. We stopped and did not peek at the final exam. The three design chats should read PROTOCOL.md, PASSMARKS.md, RACE-PASSMARKS.md, and ADDENDUM-3.md first; this ruler is not yet ready to judge their claims.

The independent blind recount is in BLIND-RECOUNT.md. Raw JSON is under `runs/`; local checkpoints were retained for audit and are not committed as model weights.
