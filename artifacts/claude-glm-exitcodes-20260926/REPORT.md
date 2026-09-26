# GLM exit-code count (read-only) — 2026-09-26

Director task 20:32 UTC. Touch-no-process, edit-nothing run. All counts are
integers from each job's own log/jsonl. No prompt or reply text is quoted.
Snapshot time for running jobs: 2026-09-26 20:36–20:37 UTC (counts move while
jobs run). Reference: `artifacts/claude-lis320-20260926/pilot3/glm.log`
holds 62 lines = 2 ok + 30 unparsed + 30 `call failed` lines, of which
27 are `exit 1: > build · glm-5.3-flash` and 3 are `exit 124: TIMEOUT`
(not 30 exit-1 as the brief states).

Failure kinds: A = `exit 1` with `> build` stderr; B = timeout
(`exit 124` / TIMEOUT); C = other.

## 1. claude-madeup-g406-mac — FINISHED

- Logs: `artifacts/claude-g406-20260926/run/glm.jsonl` (80 rows),
  `run/glm.log` (3 summary lines), `run/verdict.json`, `run/RESULTS.md`.
- Calls made so far: 80. Returned text (parsed, ok=true): 23.
  Unparsed (ok=false, failed calls and unparseable replies not
  distinguished in this log): 57.
- Failures by kind: A 0 recorded, B 0 recorded, C unknown —
  the log records no per-call exit codes, stderr, or timeouts.
  `glm.log` last line: stopped=`failed` (max-failed reached).
- First 10 exit codes: NOT RECORDED in this job's log. Saying so
  per instructions; no codes listed rather than invented.
- Still running: no. Queue shows `.done` + `.pushed`; no dedicated PIDs.

## 2. rd378k-gate3oc — RUNNING (PIDs 49571, 49540, 50350, 50352, 54057)

- Logs (all under the job's tmp dir
  `/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate3oc-tmp/artifacts/claude-rd378k-20260926/`):
  `gate3oc-logs/step4-label.log` (1 line: 1 ok),
  `gate3oc-logs/step3-selftest.txt` (2 lines: teacher3 selftest 1/1 ok,
  teacher3oc selftest 1/1 ok),
  `gate3oc-logs/step3b-leakcheck.txt` (1 JSON line: exit 0),
  `gate3oc-logs/step3-check.txt` (no call), output dir `gate3oc/` empty
  (0 files).
- Calls made so far: 4 recorded call outcomes. Returned text: 4.
  Failed: 0. Kinds: A 0, B 0, C 0.
- First 10 exit codes: only 1 numeric exit is recorded
  (leakcheck `exit: 0`, first in order). The 3 other ok lines carry no
  numeric exit code. Remaining 6 of the first 10 have not happened yet.
- Still running: yes (PIDs above; 54057 is the in-flight GLM call).

## 3. rd378g-writemore — RUNNING (PIDs 49522, 49465, 50341, 50343, 52643)

- Current run: tmp dir `.../T/opencode/rd378g-writemore/`;
  `writemore-write.log` is 0 bytes; output dir `glm2/` does not exist yet.
- Calls made so far (current run log): 0 recorded outcomes.
  Returned text: 0. Failed: 0. Kinds: A 0, B 0, C 0.
  One GLM call is in flight (PID 52643), outcome pending.
- Prior-steps log in worktree
  (`artifacts/claude-rd378g-20260926/teacher-log.txt`, 723 lines, earlier
  teacher steps, not this writemore run): 555 per-try failures, all kind C
  (`HTTPError HTTP Error 402: Payment Required`); A 0, B 0; 0 lines
  containing `exit` or `> build`.
- First 10 exit codes: NOT RECORDED in this job's logs. Saying so.
- Still running: yes (PIDs above; 52643 is the in-flight GLM call).

## 4. k1h-glm2 — RUNNING (PIDs 46743, 46711, 47255, 47257, 47258)

- Chats phase (prior, worktree
  `artifacts/claude-k1h-20260926/glm-v1/chats-log.txt`): 14 lines,
  14 `done`, 0 `ERROR` lines. Calls 14, returned text 14, failed 0.
  No exit codes recorded.
- Answer phase (current, tmp `/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/k1h-glm2.pp0OOR/O/answers.jsonl`):
  116 rows at snapshot; 116 nonempty answers; 0 failed; 0 `error` rows.
  Failed rows, when they occur, record only an error type name
  (e.g. `RuntimeError`), never a numeric exit code or stderr.
- Failures by kind: A 0, B 0, C 0 in both phases so far.
- First 10 exit codes: NOT RECORDED in this job's logs. Saying so.
- Still running: yes (PIDs above; 47258 is the answer driver).

## 5. y1t-topup-mac — NO SUCH JOB / NO LOG FOUND

- No queue file, no tmp dir, no artifact dir, and no PIDs exist under the
  name `y1t-topup-mac` (searched queue, `/T/opencode`, `/T`, artifacts,
  and `ps`). Nothing to count; miss reported, not hidden.
- Closest finished job, `y1t-glm-mac` (queue `.done` + `.pushed`;
  logs `artifacts/claude-y1t-20260926/glm/glm_0.log` … `glm_3.log`,
  2468 lines total): ok 645, unparsed 376, per-try failures 1447, all
  kind C (`HTTPError HTTP Error 402: Payment Required`); A 0, B 0;
  0 lines contain `exit`, `> build`, or `timeout`.
- First 10 exit codes: NOT RECORDED in these logs. Saying so.
- Still running: no (finished; no dedicated PIDs).

## Deviations and notes

- `y1t-topup-mac` does not exist as a job/log; reported via the finished
  `y1t-glm-mac` logs instead. That substitution is explicit, not silent.
- Reference correction: lis-320 pilot3 is 27 exit-1+build plus 3
  exit-124 timeouts (30 failed of 32 calls), not 30 exit-1.
- No per-call exit-code list exists for any of the 5 jobs except one
  entry (gate3oc leakcheck `exit: 0`); everywhere else the logs record
  ok/unparsed or HTTP errors without numeric exits. First-10 code lists
  are therefore reported as not recorded rather than inferred, except
  where stated.
- Machine: `uptime` 1-min load ~115 at snapshot (shared Mac, heavy);
  disk 51 GB free (above the 3 GB stop line). No heavy steps were run
  (read-only counts via `/usr/bin/python3`).
- TEST-ONLY panels were not opened, item content was not read, no tuning
  or quoting occurred, and no GLM call was made by this task.
