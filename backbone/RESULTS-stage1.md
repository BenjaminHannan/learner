# Stage 1 results (2026-10-23; numbers copied from the box logs' [result] lines, one seed)

Village `validation` = 8,675 questions held out by names, templates, styles and rule families. Dev = 4,000 sampled
from train shards 380-399. Sealed `test` never built or read.

| Arm | Steps | Dev | Validation |
|---|---:|---:|---:|
| D, premonition v1 FULL (REPORT-V1, 95k visits) | 12,000 | 80.1% | 44.7% |
| Qwen3.8-27B, untrained, instruction + 3-shot (dev n=1,000) | 0 | 45.8% | 39.3% |
| A: Qwen3.5-0.8B + LoRA | 537 | 81.65% | 67.46% |
| B: A + borrowed middle block looped 3x | 418 | 82.15% | 67.57% |
| B scored with 1 loop (lesion) | 418 | 72.90% | 59.88% |
| A at 418 steps (equal-steps check) | 418 | pending | pending |
| A2: Qwen3.5-2B + LoRA | budget | pending | pending |

Both 0.8B arms hit their time budget, so steps were cut once at step 20 (RUNLOG.md). Train rows seen: ~8,600 (A),
~6,700 (B) of 86,238.

Marks (PREREG-stage1.md):
- P1 (A validation >= 55.0%): **PASS**, 67.46%.
- P2 (A dev - validation <= 25 points): **PASS**, 14.2 points (D: 35.4).
- P3 (B >= A + 2.0 AND 1-loop lesion drops >= 3.0): **FAIL**. Lesion half holds (-7.7 points), but B beats A by only
  0.1 points (and A had more steps; the equal-steps A is pending). Not the "wrong if" either (B > A; lesion moves B).
  Reading (suggested): B uses its loop, but three passes of the borrowed block buy no more than one pass plus more steps.
- P4: pending A2.
- Untrained 27B is below D: the model knows English but not this task's answer conventions. Borrowing needs training.
