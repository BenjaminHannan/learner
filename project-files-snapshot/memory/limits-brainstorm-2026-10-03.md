---
name: limits-brainstorm-2026-10-03
description: Ben's limits brainstorm (10-03, PR #31): top gap = core barely trained; Ben said "all" = whole model counts, yes to skills curriculum + dense loss
metadata:
  type: project
  modified: 2026-10-03T19:42:06.065Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvM63nbKUDcKdgMgNRz6yzQqv, PR #31 (design/brainstorm/what-holds-premonition-back-2026-10-03.md).
Ranked limits: (1) core pretrained only on TRAIN256 synthetic numeric + 800 warm-up updates + 48 English Qs; (2) only ~4 answer tokens of loss per question, no RL; (3) two narrow doors (PR #30); (4) MoE collapse; (5) fixed 4 loops, op picked at loop 0.

Ben 19:41 UTC answered the three questions with "all". Read as: the whole model incl. the borrowed 1.2B LM counts toward "its size" (compare to 1-2B models); YES to a large generated never-repeating skills curriculum to pretrain the core; YES to testing a dense self-supervised loss for the core after door results.

**Why:** memorizing, not generalizing, is the main failure. **How to apply:** prioritise core pretraining data over shape changes. See [[critical-thinking-reasoner-design]].
