# rsn-358e addendum 1: three more arms, a mechanism number, and what the middle band means (2026-09-26 19:37 UTC, before any 358e number was read)

**Why:** the Thread manager's review at 19:31 UTC. The sealed moe arm is the weak version of Ben's idea: a per-cell top-1 router with a load-balance loss spreads every kind over all experts, and the shared attention keeps training in phase B. Ben's own words were "put the old skills somewhere where they don't get overridden".

**Code:** scripts/claude_rsn358e2_arms.py. It imports claude_rsn358e_moe.py unchanged, with the same seeds, data, steps and dev sets. Selftest: every old weight stays frozen, including the router's old rows, and only the new experts move.

| arm | what it is | role |
|---|---|---|
| **moe-grow** | Ben's form. Phase A as moe. Before phase B (and again before C), every trained weight is frozen (old experts, attention, embeddings, head, stop head, norms, and the router's old rows), and 4 new experts per block are added. Only the new experts and the router's new rows learn. | **graded on the same marks as moe** (a second graded test, so the chance of one pass by luck roughly doubles) |
| moe-aux0 | moe with no load-balance loss | report only |
| dense-narrow | dense with MLP width d instead of 4d: the same active weights per cell as moe (0.86M total vs 1.65M) | report only |

**moe-grow size:** 1.65M weights in phase A, about 2.7M in phase B and about 3.7M in phase C (small nets). It breaks the same-size rule, and every row that shows it says so. If it passes, the next question is whether the gain survives at equal total weights, for example with 2+2 experts.

**Mechanism number, fixed now:** separation S per block = 1 - sum over experts of min(share of grids5 cells, share of sums4 cells), measured after phase B at round 8 on the dev sets.
- S = 0 means grids and sums use the experts identically; S = 1 means they share no expert.
- "Different experts" means S >= 0.5 in both blocks. Report only.
- For moe-grow the number is read the same way. S near 1 means the router sends sums to the new experts and grids to the old ones.

**Middle band, fixed now:** mean F_moe between F_dense - 30 and F_dense - 5 is a FAIL that is not proved wrong. It reads as "experts forget somewhat less, but not enough to matter". The same holds for moe-grow.

**Schedule:** CPU has only 4 cores.
- moe-grow seeds 1-2 start now, next to the 4 running runs.
- moe-aux0 and dense-narrow seeds 1-2 start when those 4 finish.
- No stage-1 number has been read yet.

**Prediction for moe-grow:** PASS 45%. It cannot overwrite any old weight. It can still fail if the router sends grids cells to the new experts at test, or if it cannot learn sums through the experts alone (validity mark V).
