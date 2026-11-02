# Brain-1 results: INCONCLUSIVE (pick rate up 5.2 points, but not through better-bound tests)

## Haiku reference arm (does not decide; Batches, default sampling)
Same 192 pools, tests written after seeing the start state.

| test writer | pick rate (%) | solvable (%) | AUROC | tests that hold on the reference |
|---|---|---|---|---|
| Haiku, Probe-2 prompt | 44.3 | 65.4 | 0.759 | 74.5% |
| Haiku, with the checklist | **49.5** | 73.1 | **0.838** | 81.0% |

shown: with the relation checklist first, Haiku's tests pick a winning try 5.2 points more often and separate winning
from losing tries better (AUROC .76 -> .84). Effective sample ~48 tasks, one sample of Haiku's sampling.

## Decision arm: K2 untuned on MLX (M3, 13:46Z Oct 27, ~37 min, peak 14.1 GB)

| K2 test writer | pick rate (%) | solvable (%) | AUROC | tests holding on the reference | tests per sample | empty samples | all-tie pools |
|---|---|---|---|---|---|---|---|
| BASE (Probe-3 MLX control) | 37.5 | | 0.663 | 57.6% | 1.94 | 49 | 15.1% |
| CHECK (checklist first) | **42.7** | 63.1 | **0.782** | 60.1% | 3.22 | 3 | 6.8% |

P1 (CHECK >= BASE + 4 = 41.5) ok. P2 (reference agreement >= BASE + 8 points) FAIL (+2.5). Not <= BASE + 1.
Verdict per prereg: INCONCLUSIVE.

shown: the checklist raises K2's pick rate by 5.2 points and AUROC by .12. shown: the mechanism the prereg named
(more correct, better-bound tests) barely moved (+2.5 points). suggested: the gain comes from K2 writing more tests
per sample and almost never an empty set, so fewer pools tie, rather than from each test being more right.
Haiku's arm did move in the predicted way (74.5% -> 81.0% correct tests).
