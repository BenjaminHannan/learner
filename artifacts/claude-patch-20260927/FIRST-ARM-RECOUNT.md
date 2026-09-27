# First trained arm: independent recount

UTC: 2026-09-27 23:51:03 UTC

**Shown:** patch-927401 selected verification misses the grid mark: 278 of 300 versus 285 required. The other five kinds meet their selected marks.

Raw audit: **consistent**. All dev/verify inputs must match the sealed panels exactly, once each; selected and fixed-depth counts, mean rounds, cap hits, and timing aggregates were compared with result.json.

| Kind | Dev selected | Verify selected | Mark | Verify 4 | Verify 8 | Verify 16 | Verify 32 | Verify 48 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sums | 300 of 300 | 300 of 300 | 285 of 300 | 298 of 300 | 300 of 300 | 300 of 300 | 300 of 300 | 300 of 300 |
| grids | 281 of 300 | 278 of 300 | 285 of 300 | 168 of 300 | 261 of 300 | 285 of 300 | 288 of 300 | 288 of 300 |
| sorting | 293 of 300 | 297 of 300 | 270 of 300 | 288 of 300 | 296 of 300 | 298 of 300 | 298 of 300 | 298 of 300 |
| reversing | 291 of 300 | 289 of 300 | 270 of 300 | 283 of 300 | 287 of 300 | 288 of 300 | 288 of 300 | 288 of 300 |
| counting | 297 of 300 | 298 of 300 | 270 of 300 | 298 of 300 | 298 of 300 | 298 of 300 | 298 of 300 | 298 of 300 |
| brackets | 300 of 300 | 300 of 300 | 270 of 300 | 300 of 300 | 300 of 300 | 300 of 300 | 300 of 300 | 300 of 300 |

**Shown from saved records:** 20 of 20 expected matrix gradients have finite positive norms. Three stress patterns record 48 finite rounds at maximum A/B factor norm; largest recorded absolute hidden value 2.547309637. Recomputed operator bounds are at most 0.249999970. Zero-patch maximum difference is 0.0.

**Shown from CPU tensor inventory:** 1,648,671 ordinary coefficients plus 4,096 persistent patch coefficients = 1,652,767; tensor shapes and checkpoint digest match trained-checks.json. All saved tensors are finite fp32.

**Untested:** Paired gaps to loop/loop_meta and the full eight-arm gate remain unknown. Only this arm was audited; live training was not changed.

Fixed-depth results are diagnostic; they do not replace selected-prediction marks. Recorded gradient/stability/zero-patch checks were audited without repeating model computations. Per-round stop probabilities were unavailable.
