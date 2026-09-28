# Final Sol blind recount

Audit UTC: 2026-09-28T05:52:39Z. Recounted only the attached brief, original marks, sealed panels/checks, and raw outputs. Earlier results, gate/status/recount files, and the user verdict were excluded.

**Practice gate: FAIL.** The pilot qualified all six kinds. All patch-versus-control gaps pass, but every arm fails the absolute grids gate on verification. The registered maze race is ineligible.

Selected verification scores (right of 300): sums and grids require 285; other kinds require 270.

| Seed | Arm | Sums | Grids | Sorting | Reversing | Counting | Brackets |
|---|---|---:|---:|---:|---:|---:|---:|
| 927401 | patch | 300 of 300 | 278 of 300 | 297 of 300 | 289 of 300 | 298 of 300 | 300 of 300 |
| 927401 | loop | 300 of 300 | 274 of 300 | 293 of 300 | 295 of 300 | 298 of 300 | 300 of 300 |
| 927401 | loop_meta | 300 of 300 | 282 of 300 | 297 of 300 | 292 of 300 | 298 of 300 | 300 of 300 |
| 927401 | plain | 295 of 300 | 164 of 300 | 297 of 300 | 299 of 300 | 299 of 300 | 300 of 300 |
| 927402 | patch | 300 of 300 | 272 of 300 | 296 of 300 | 293 of 300 | 298 of 300 | 300 of 300 |
| 927402 | loop | 298 of 300 | 272 of 300 | 298 of 300 | 292 of 300 | 299 of 300 | 300 of 300 |
| 927402 | loop_meta | 300 of 300 | 260 of 300 | 298 of 300 | 291 of 300 | 297 of 300 | 300 of 300 |
| 927402 | plain | 292 of 300 | 160 of 300 | 300 of 300 | 297 of 300 | 299 of 300 | 300 of 300 |

Pilot dev: sums 300 of 300, grids 287 of 300, sorting 300 of 300, reversing 296 of 300, counting 300 of 300, brackets 300 of 300.

Patch minus control (answers of 300; each difference must be at least −9):
- 927401 vs loop: sums +0, grids +4, sorting +4, reversing -6, counting +0, brackets +0.
- 927401 vs loop_meta: sums +0, grids -4, sorting +0, reversing -3, counting +0, brackets +0.
- 927402 vs loop: sums +2, grids +0, sorting -2, reversing +1, counting -1, brackets +0.
- 927402 vs loop_meta: sums +0, grids +12, sorting -2, reversing +2, counting +1, brackets +0.

Identity: both panels have 300 unique inputs per kind with no dev/verify overlap; all 17 expected raw files have 1,800 rows. Each raw input and fingerprint matches its sealed panel; independent and original checkers agree with every stored right flag.

Checks: patch 1,652,767 coefficients, including 4,096 persistent A/B values; loop 1,645,726; plain 1,646,693; reference 1,646,750. The patch is 0.428% larger than its own loop, within 2%. Independent CPU model instantiation reproduced the counts; no training or inference was run. Construction and both trained-patch checks each have 20 of 20 finite, nonzero matrix gradients.

Patch grids, selected versus fixed-48 diagnostic: 927401 278/288 of 300; 927402 272/280 of 300. The diagnostic does not alter the selected-answer gate.

Maze raw inventory: 0 race/maze scoring files in this experiment folder. Maze learning, retention after support/sleep, and any causal effect of wider practice remain **untested** here. Absence from this folder does not prove no external computation.

Key SHA-256: candidate seal `645657e0e378eea2ed56eb8d8943eaa931feb1720fcadbe9b6cab51af78c6bbd`; qualified seal `d6154c909c8add111db9548c9718547f174ab536cb7c80f7b993586c7f52e7a9`; panels `4a95366a1d5f0acadb7ac8a58e3e7e67785447ed7dfb42a90a73759548a97c28`; qualification raw `ab5da0859964ae99f9881d48640ec5736090b6fe1c3fadc8dcfa70c3dbaeb1fb`. All arm raw hashes, generator/code hashes, checkpoint hashes, and gradient names/norms are in the JSON.

Discrepancies: none in checked seals, panels, raw outputs, or check inventories. Grid scores are gate failures, not recount mismatches.
