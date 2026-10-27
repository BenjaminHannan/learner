---
name: exp43e-rank4-sleep-confirmed
description: 2026-09-21 — rank-4 limited sleep update beats plain replay on CardFold, 6/6 seeds incl. fresh-seed confirmation; first sleep mark ever passed
metadata:
  type: project
---

Experiment 43E (scripts/fable_sleepselect43e.py, artifacts/fable-sleepselect43e-20260921/). Registered bases, 100 clean episodes (80 train / 20 held out), 3,000 updates. After every step each block matrix's total change W−W0 is SVD-cut to rank 4.

Fresh accuracy plain → rank-4: 4102 0.505→0.715, 4103 0.650→0.905, 4104 0.435→0.885; fresh seeds 4111 0.210→0.395, 4112 0.480→0.680, 4113 0.630→0.755. Old skills kept. Long inputs still ≤0.05.

Checkpoint rule: held-out exact match (min 1,000 updates, ties→later) is within 0.05 of best-possible but did NOT beat held-out loss by the sealed margin on clean data → loss rule not replaced. Final-update scores give the same verdict.

**Why:** first sleep change to pass a pre-fixed mark and a fresh-seed confirmation; it is automatic arithmetic, fits [[sleep-automatic-mathematical]]. In 43B (noisy, randpos base) rank-4 was also the only arm never below plain ([[exp43-length-gate-and-shared-sleep]]).
**How to apply:** allowed claim is toy-only, 80 episodes, 6/6 seeds. Not shown: low rank is the active ingredient, other ranks, fewer episodes, length. Follow-up 43F tests 20/50 episodes and ranks 1/2/8/16. Baseline remains [[exp42-automatic-sleep-result]].

43F follow-up (2026-09-21, exploration seeds): gain does NOT survive fewer episodes (50: +0.15/−0.15/+0.09; 20: all ≤0.105 fresh). Rank dose at 100 episodes: 1–4 best (0.71–0.92), 8 middle, 16 lower, plain worst → low rank itself matters. Episode wall stands for the transformer; only skills+router ([[exp43g-transport-router-control]]) reached 20-episode learning.
