# TTT-1 results (Kaggle 2x T4, benhannanjfkldsfds/ttt1-patterns, commit e919e7c91, 02:03Z-05:15Z Oct 26, free)

Pre-registration: PREREG-ttt1.md + addendum 1. 100 ARC-AGI-1 evaluation tasks; K2-Horizon-3.7B, thinking off, greedy decoding. Raw rows are in results_ttt1/.

| arm | solved (of 100) | answer loss (mean per token) |
|---|---|---|
| B base | 2 | 1.102 |
| T practise on this puzzle's demos (48 LoRA steps) | 4 | 0.582 |
| C same practice on another puzzle's demos | 1 | 1.328 |

- **T1 FAIL, not wrong (shown):** T solves 3 more than C (4 vs 1, McNemar p = 0.25). The mark was +5 with p < 0.05. Solved tasks: T 0607ce86, 19bb5feb, 2072aba6, 332efdb3; B 332efdb3, 3b4c2228; C 332efdb3.
- **T1b PASS (shown):** T's loss on the true answer is lower than C's on 90 of 100 tasks (sign test p = 3e-17) and lower than B's on 93 of 100. The mean loss nearly halves (1.10 -> 0.58). Practice on another puzzle makes it worse than no practice (C higher than B on 69 of 100, p = 0.0002). So the gain comes from this puzzle's own rule, not from format practice.
- **Reading (suggested):** the model learns much of each puzzle's rule in 48 steps, but a whole grid has to be right cell for cell. At 0.58 nats per token, a 100-cell answer is still unlikely under greedy decoding. Untested: whether more passes, color augmentation and voting over the 8 symmetries turn the lower loss into solves (addendum 1's "next").
- Cost: 90 s per task for T on a T4 (B 16 s). The Mac speed is not measured.
- Caveats: one seed; the loss also rewards learning the output's surface style (grid size, palette), which is part of the puzzle's pattern but not the whole rule.
