# Wave 1 r4: not started

**Verdict: INCONCLUSIVE.** The r3 harness checks its source manifest before loading the model. Six files in the requested branch do not match the recorded r3 hashes: sleepmlx/worker.py, sleepmlx/served.py, sleepmlx/replay_monitor.py, sleepmlx/day_adapter.py, sleepmlx/mac_gateway.py, sleepmlx/recipe.py. The exact r3 source was not available in this worktree. The integrity check was not bypassed; no model was loaded, and neither the rehearsal-ON nor matched MPS OFF arm was run. The machine-readable results record the expected and actual hashes.

| Block | Fact answer | Learned after own block | Kept after block 3 |
| --- | --- | --- | --- |
| 1 | Copperfern | Not measured | Not measured |
| 1 | Moonhaven | Not measured | Not measured |
| 1 | Sunwillow | Not measured | Not measured |
| 2 | Mistbrook | Not measured | Not measured |
| 2 | Pinecrest | Not measured | Not measured |
| 2 | Starmeadow | Not measured | Not measured |

| Checkpoint | General hits |
| --- | --- |
| Baseline | Not measured |
| After block 1 | Not measured |
| After block 2 | Not measured |
| After block 3 | Not measured |

No test time elapsed; HARM cannot be scored. At the resource check, available memory was 10.68 GiB, pressure level 1, and free disk was 1.86 GiB. Disk free had fallen below the 4 GiB start requirement and the 2 GiB abort threshold, independently preventing a safe run. Two other agents were running unit tests on the Mac, according to the task. The historical control learned 3 earlier facts and kept 0; its baseline general score was 6/8. The control used CPU/BF16, while the planned run uses MPS/FP16, so device differences could contribute to any future difference.

**For Ben**

- **Shown:** The older test learned three facts and later kept none.
- **Shown:** This new test did not start because some of its computer instructions did not match the saved fingerprints.
- **Shown:** Free disk space fell below the safety limit before the test could start.
- **Untested:** Whether re-studying helps on the Mac GPU, and whether it changes answers to general questions.
- **Suggested:** Restore the exact six source files from the r3 run before trying again.
