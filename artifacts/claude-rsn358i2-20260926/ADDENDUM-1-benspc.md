# rsn-358i2 addendum 1: run on BensPC (2026-09-26 17:15 UTC, before any 358i2 run)

**Why:** the Director reported that BensPC is free (17:09 UTC), and the Thread manager recommended the $0 BensPC copy over a rental (17:08-17:13 UTC). Ben's rental card stays as the fallback if BensPC fails.

**What changes:** the machine only. The code, seal, marks V0/M1/M2/M3, proved-wrong clause, seeds, steps, tests and plain reference (358i's own plain tests.json) are unchanged.

**What it means:**
- BensPC runs torch 2.11.0 (handoff/memory/benspc-gpu-ops.md:15). The cache bug does not occur on that version: CPU check at 14dc0c013 on 2.14, and the Thread manager's CPU check on 2.11.
- So Stage 0 there is report only. It is expected to show 0/12 on both lines, and it does NOT stop the job. (PASSMARKS' Stage 0 stop rule was written for the torch 2.8 rental.)
- The cache_enabled=False flag is harmless on 2.11.
- This run therefore tests the core question: does 358i's loop close the grid gap when its layers actually train? It does not test the fix on CUDA 2.8. That comes from 000-check-358t, if its rental was reachable, or from any later rental run of the same seal.
- Machine and torch version differ from 358i's plain reference, which was trained on a torch 2.8 rental. Plain is unaffected by the bug, and the audit's logs show plain learning at the same speed on both machines. This is disclosed as a deviation.
