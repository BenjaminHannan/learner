# Stage 0 on CPU: the autocast cache blocks the loop's layer gradients on torch 2.8.0 (2026-09-26 17:01 UTC)

Ran `python -B scripts/claude_stage0_autocast_grad.py` on the real 358i Net code, CPU bf16 autocast, one training step on 8 grids5 items (the Thread manager's audit suspect, /mnt/project-files/thread-manager/loop-training-audit-2026-09-26.md §5).

| torch | loop, 3 no-grad + 2 graded, cache on | same, cache off | loop, 0 no-grad | plain |
|---|---|---|---|---|
| 2.8.0+cpu | **8/12 block weight matrices get no gradient** | 0/12 | 0/12 | 0/48 |
| 2.14.0 | 0/12 | 0/12 | 0/12 | 0/48 |

The 8 matrices are all four Linear weights in both blocks (qkv, out, two MLP). The other 4 are position-bias tables, which autocast doesn't cast. SHOWN on CPU. The CUDA path and the rental's actual torch version are not yet checked. The rent kit records image pytorch/pytorch:2.8.0 (handoff/memory/compute-availability.md:16), and BensPC runs 2.11.

If the rentals ran 2.8, the loop's layers learned only on steps with zero no-grad rounds, 15.3% of steps (358a:291-292). That fits the audit's table: the loop learned about 7x slower on rentals than 358a on BensPC, while plain was unchanged.
