# Brain-1 results (in progress)

## Haiku reference arm (does not decide; Batches, default sampling)
Same 192 pools, tests written after seeing the start state.

| test writer | pick rate (%) | solvable (%) | AUROC | tests that hold on the reference |
|---|---|---|---|---|
| Haiku, Probe-2 prompt | 44.3 | 65.4 | 0.759 | 74.5% |
| Haiku, with the checklist | **49.5** | 73.1 | **0.838** | 81.0% |

shown: with the relation checklist first, Haiku's tests pick a winning try 5.2 points more often and separate winning
from losing tries better (AUROC .76 -> .84). Effective sample ~48 tasks, one sample of Haiku's sampling.
The decision arm (K2 on the M3, BASE vs CHECK) has not run yet.
