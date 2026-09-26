# rsn-358e next step if moe-grow fails: a small grids replay in phase B (DRAFT, 2026-09-26 20:26 UTC; not sealed, not run)

Written before dense and moe have finished phase A and before the 358e verdict, at the Thread manager's request (20:25 UTC). It is sealed only after the 358e verdict is registered, and only if moe-grow fails.

**Why:** moe-grow froze every old weight, yet grids5 fell from 187 / 188 to 40 / 70 after phase B. The suggested reading is that the router's new rows learned only from sums, so nothing told the router to keep grids cells on the old experts. The report-only diagnostic (scripts/claude_rsn358e_diag.py) tests that reading directly.
**Brain angle:** interleaved replay. In complementary-learning-systems theory the hippocampus replays old experiences while the cortex learns new ones, which prevents catastrophic interference. That this helps networks is established; whether it helps this router is untested.

**One change vs moe-grow:** in phase B, 1 step in 10 (steps 10, 20, ..., 2,500; 250 steps, fixed now) uses a grids batch drawn from the same phase-A grids training pool (never the dev sets) instead of a sums batch. The replay count, 250 batches, is fixed before the run. Everything else is the same: code, seeds 1-2, steps, freeze and grow, dev sets.

**Mark (fixed now from the after-A numbers, 187 / 188):**
- **PASS:** grids5 after B >= 150 of 200 on both seeds (keeps at least 80% of the after-A score), AND sums4 after B >= 120 on both seeds (it still learns the new kind).
- **Proved wrong:** grids5 after B <= 100 on both seeds, meaning even replay loses about half the old skill.
- Anything between is a FAIL that is not proved wrong.

**Report only:** dense with the same replay (the fair control), expert_share and separation S. A moe-grow pass shows only that replay keeps the old skill in the frozen-experts net. No "experts beat dense" claim is made from this test; that would need its own graded mark in a later test.

**Cost:** $0, CPU, about 1 h for 2 seeds of each arm.

_Edited 20:27 UTC (before sealing) after the Thread manager's 20:27 notes: dense-replay stays report only with no experts-vs-dense claim; replay pool and count stated._
