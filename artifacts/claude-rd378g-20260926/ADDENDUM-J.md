# rd-378g addendum J (2026-09-27 06:44:14 UTC): the Luna writer's pilot failed on time only; one timing check picks the Codex setting, then the same write

ADDENDUM-A to I stay as sealed; this file adds to them. It is written after 007-rd378g-writeluna's pilot result and
before any other Luna writing call.

## What happened (007-rd378g-writeluna, origin/builder-outbox; counts from pilot-log.txt and the job's report)
PILOT-FAIL. Batch 18 was tried 3 times; each try was 3 Luna attempts, and all 9 attempts ended "timeout after 300s"
(the Director's helper has a fixed 300 s limit). Result: 3 "call failed" lines, 0 "batch 18 ok", 0 new dialogs. The
job's agent timed the pilot step at 46 min. So batch 18 failed on the route alone (addendum F: route-lost), not on the
code checks. Addendum I's writing step did not run. The grader job (006-rd378k-gate3luna) is separate and unaffected;
its pilot evidently passed, because its gate step is running.

## The one change: the Codex setting for writing calls
Writing calls go through scripts/claude_luna_run2.py, which binds scripts/claude_luna_effort.py. That is the Director's
helper run line with two knobs:
- a time limit per attempt;
- an optional Codex reasoning effort: `-c model_reasoning_effort="<effort>"`, Codex's documented config override
  (`codex exec --help`, 000-probe-codex).
Model, empty temp dir, read-only sandbox, error-like-reply rule, 3 tries and raise are all as in the helper. These
stay as in addendum I: the WRITE prompt, area, speaker letters, check_batch, the repeat check, to_rows, glm2N/, the
writer tag and the 120 floor. The grader keeps the helper as sealed in rd-378k addendum K.
A writing batch is training input, not a test. The writer's route is not a measured quantity.

## Timing check, which also stands in for addendum I's pilot
scripts/claude_rd378g_lunadiag.py sends batch 18's exact WRITE prompt once per setting, in parallel, one attempt each:
- "low" with 600 s;
- the Codex default (no override) with 1200 s.
It prints counts only: exit, wall time, Codex event counts by type, token usage, reply length, error-like, parsed items,
check_batch's verdict and repeats. Nothing it writes is kept.
A setting passes if all of these hold:
- exit 0;
- the reply is not error-like;
- check_batch says ok;
- 0 first turns repeat.

## Rule, fixed now
- The low setting passes: write with effort low, time limit 600 s.
- Else, the default setting passes: write with the Codex default, time limit 1500 s.
- Neither passes: stop (DIAG-FAIL). No further writing attempt without a new addendum, and the Thread manager gets the
  counts.
The write is addendum I's step 2 unchanged (batches 18-20 and 22-39, --have glm/notes_w1.jsonl, output glm2N/), then
its step 3 (the writer tag).
