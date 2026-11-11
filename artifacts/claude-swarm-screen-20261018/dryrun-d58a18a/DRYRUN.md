# DRYRUN at d58a18ada (after review round 2, items 1-5), 2026-10-18, CPU, T = 120 s

**A DRY RUN: tiny preset (d = 32), tiny visits (60 / 24), CPU, T = 120 s (coordinator, round 2: a procedural
setting that changes no bar). Every number and verdict is meaningless and nothing was tuned on it.**

- `DRYRUN=1 PIN=d58a18ada… WORKERS=3 OUT=…/dryrun-d58a18a bash scripts/premonition_swarm_box.sh`, with the tiny data
  cache deleted first so the build starts from scratch. Exit 0 after 1,760 s; 33 steps, all rc 0. HEAD == PIN, and all 18
  manifest files check OK.
- C0: T = 120 s (override); ratio S0m4/D1 = 1.14; stop_and_ask False; money_stop False.
- Train seconds 120.01-120.28 (≤ +0.25%, inside M5's ±2%). Steps in T: D1 402-424, S0 369-386, S1 322-337.
- Every mark of both cards was COMPUTED. No VOID, so the verdict path past VOID ran this time:
  - MARKS-S0: INSUFFICIENT (far_deep has 62 items < 100). MARKS-S0-minitems1: **FAIL (M3 USAGE-COLLAPSE)**.
  - MARKS-S1: INSUFFICIENT. MARKS-S1-minitems1: **KILL-COMM**.
  These are tiny-model artifacts with no meaning for the screen.
