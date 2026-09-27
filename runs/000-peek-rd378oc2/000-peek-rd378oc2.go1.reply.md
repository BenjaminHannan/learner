Stopping the two Mac jobs by exact PID — checking duplicate gate and process chains.
Both jobs found running — mapping full process chains and in-flight calls.
Process chains mapped — counting log progress for both jobs.
Counts are in (gate3oc 6/38, writemore 6/21) — both under threshold, stopping them now.
Both jobs stopped cleanly — cleaning up their leftover opencode sessions.
Sessions deleted — writing the final report.
STOPPED both (no DUPLICATE; no LEFT-RUNNING; neither NOT-RUNNING).

- rd378k-gate3oc: STOPPED. Dialogs done 6 of 38 (ok 5 + unparsed 1; "call failed" lines 8; log 14 lines). Chain: launcher 49465→no; gate3oc chain was launcher 49540 (04:03:05) > agent 49571 (04:03:05) > uv 50350 (04:01:41, PPID 1) > python 50352 (04:01:41) > opencode child 94896 (00:55). Cwd .../T/opencode/rd378k-gate3oc-tmp. In-flight tags: 1 (glm11-5af0d108fcac4c798d7d300f10f367ef).
- rd378g-writemore: STOPPED (batches done 6 ≤ 17). Batches done 6 of 21 (batch-ok 1 + skipped-after-3-tries 5; batch-try 16; "call failed" 14; log 36 lines). Chain: launcher 49465 (04:03:05) > agent 49522 (04:03:05) > uv 50341 (04:01:42, PPID 1) > python 50343 (04:01:42) > opencode child 95005 (00:20). Cwd .../T/opencode/rd378g-writemore. In-flight tags: 1 (glm11-3d20e7d4ea5443f69d938473cee02f96).
- PIDs killed (SIGTERM, exact PIDs, agent→uv→python→child): 49571, 50350, 50352, 94896, 49522, 50341, 50343, 95005 = 8 killed. After 10 s wait all 8 gone; kill -9 count 0. Launchers/watcher/other jobs/BensPC untouched (launchers exited on their own after agents died).
- Session cleanup: glm11-5af0… found 1, left 0; glm11-3d20… found 1, left 0. Nothing else deleted; both cwds existed.
- REPORT.md written to artifacts/claude-peek-rd378oc2-20260927/REPORT.md (70 lines, counts only, no log text). No GPU, no new opencode call, no rental. Disk 43 GB free. PUSH path ready for the watcher.
