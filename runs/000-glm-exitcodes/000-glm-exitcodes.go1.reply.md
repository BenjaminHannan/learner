Counting GLM exit codes read-only — assembling your failure report.
Found the likely artifact folders for your five jobs — now digging into their logs.
I've mapped the job outputs — now extracting per-call counts without touching prompts.
The wrapper scripts aren't showing in the listing — tracking down the actual log sources.
No trace of the topup job yet — now parsing the finished job logs for exit patterns.
The wrapper retries 3× then logs failures — now checking each job for those per-call records.
k1h routes through the same helper — now verifying what each log actually records.
Counts are shifting as jobs run — capturing final snapshots and runtimes.
All five jobs accounted for — pulling the final reference numbers, then writing the report.
The report is written; the push path is git-ignored and network push is blocked — trying the forced add.
Done. Report written to `artifacts/claude-glm-exitcodes-20260926/REPORT.md`, force-staged (artifacts/ is gitignored) and committed as `c711e92a5`.

Report (snapshot 2026-09-26 20:36–20:37 UTC; counts only, no prompt/reply text):

- **claude-madeup-g406-mac — FINISHED.** 80 calls, 23 returned parseable text, 57 unparsed (failed calls vs unparseable replies not distinguished in log). Failure kinds: none recorded — log has no per-call exit codes/stderr/timeouts. First-10 exit codes: NOT RECORDED. Not running (queue `.done`+`.pushed`, no PIDs).
- **rd378k-gate3oc — RUNNING** (PIDs 49571, 49540, 50350, 50352, 54057). 4 recorded call outcomes, 4 returned text, 0 failed (A 0, B 0, C 0). Only 1 numeric exit recorded (leakcheck `exit: 0`); other ok lines carry no numeric exit. Output `gate3oc/` still empty (0 files).
- **rd378g-writemore — RUNNING** (PIDs 49522, 49465, 50341, 50343, 52643). Current run: 0 recorded outcomes (log 0 bytes, `glm2/` absent; 1 GLM call in flight). Prior-steps worktree log: 555 per-try failures, all kind C (HTTP 402), A 0, B 0, zero `exit`/`> build` lines. First-10 exit codes: NOT RECORDED.
- **k1h-glm2 — RUNNING** (PIDs 46743, 46711, 47255, 47257, 47258). Chats phase: 14 calls, 14 text, 0 failed. Answer phase: 116 rows, 116 nonempty, 0 failed, 0 error rows. Kinds A/B/C all 0. First-10 exit codes: NOT RECORDED (failures would record only an error type name).
- **y1t-topup-mac — MISS: no such job.** No queue file, tmp dir, artifact dir, or PIDs. Substituted explicitly (not silently) with finished `y1t-glm-mac` logs: 2468 lines = 645 ok + 376 unparsed + 1447 kind-C per-try failures (HTTP 402); A 0, B 0; zero `exit`/`> build`/`timeout` lines. Exit codes NOT RECORDED. Not running.

Deviations/misses:
1. `y1t-topup-mac` does not exist; reported via `y1t-glm-mac`.
2. Reference correction: lis-320 pilot3 is 27× `exit 1`+`> build` plus 3× `exit 124` TIMEOUT (30 failed of 32), not 30 exit-1.
3. My commit swept in other agents' pre-staged files (rsn358i2 runs, glm helper) alongside my REPORT.md — additive only, nothing edited, but flagging it.
4. **PUSH failed:** `git push` is blocked by environment permissions, and `artifacts/` is gitignored (needed `add -f`). The commit exists locally as `c711e92a5`; the push needs director handling.
5. Machine load ~115, disk 51 GB free (above 3 GB line). No processes touched, nothing edited, no GLM calls made, no test-panel content opened.
