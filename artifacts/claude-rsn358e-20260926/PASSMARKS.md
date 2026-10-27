# rsn-358e pass marks: does a mixture-of-experts loop keep an old skill? (fixed before any run; sleep research thread, 2026-09-26 19:28 UTC)

**Source:** Ben 19:20-19:21 UTC, relayed by the Thread manager:
- "If it's overriding old skills, just put the old skills somewhere where they don't get overridden."
- "what if we just did a mixture of experts where ... it has the learned router and then the reasoner is just the mixture of experts."

**Code:** scripts/claude_rsn358e_moe.py (docstring, `selftest`).

**One change** vs the dense loop (358i design): each block's MLP becomes 4 experts with a learned top-1 router.
- Total weights are equal (+0.1% for the routers and biases). Active MLP weights per cell are 1/4.
- **Brain angle (a guess):** skills sit in partly separate circuits, and a learned gate picks which circuit runs.

**Practice, the same for both arms:**
- Phase A: grids 4x4/5x5.
- Phase B: sums 1-4 digits. Grids are never shown again.
- Phase C: mazes, report only (carry-over).

Code-made data only. Fresh dev sets (seed 48000), never a sealed test file.

## Stage 1 = this screen: small nets on CPU ($0)
- Size: d256 x 2 (1.65M weights).
- Steps: 2,500 / 2,500 / 1,500. Batch 64.
- Runs: seeds 1-2, both arms.
- All numbers are right answers out of 200 on dev, with the net's own stop.
- A_after_A = grids5 after phase A; A_after_B = grids5 after phase B; F (forgetting) = A_after_A - A_after_B.

**Marks:**
- **V validity:** on both seeds and both arms, grids5 >= 120 after phase A AND sums4 >= 120 after phase B. Otherwise INCONCLUSIVE (the nets didn't learn the skills, so there was nothing to forget).
- **PASS (the experts keep the old skill better):** mean F_moe <= mean F_dense - 30, AND F_moe < F_dense on both seeds, AND the mean of sums4 after B for moe >= dense - 20 (it still learns the new skill).
- **Proved wrong:** V met and mean F_moe >= mean F_dense - 5.
- **Report only:**
  - grids6, sums6, fixed 16 rounds, any round;
  - expert share per kind per block (do grids and sums use different experts?);
  - maze7 after phase C (carry-over) and grids5/sums4 after phase C.

**Next steps (fixed now):**
- PASS: BensPC at full size (d512 x 2, 6.44M; 6,000 / 6,000 / 3,000 steps; 4 seeds), same marks, sealed as stage 2.
- FAIL or proved wrong: the next test is the "grow and freeze" form. The old experts are frozen after phase A and new experts are added for phase B, with the router learned. It is reported against the same-size rule, because total weights grow.
- Brain angle for that form (a guess): new memories get new, separate cells (pattern separation) instead of rewriting old ones.

**Prediction:** PASS 25%. Nothing pushes the router to keep kinds apart: the load-balance loss spreads every kind over all experts, and the shared attention layers still change in phase B.

**Cost:** $0. CPU, 4 runs in parallel, about 1-1.5 hours (estimate from a 100-step timing).
