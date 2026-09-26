# rd-378k addendum F (2026-09-26 19:04 UTC): if gate3 was hit by OpenRouter's 402s, the same gate through opencode

Written before gate3's output has landed and before any gate3 grade, agreement line or label file has been read.
PASSMARKS.md and addenda B-E stay as sealed; this file adds to them.

## Why
The OpenRouter account ran out of funds at about 18:29-18:33 UTC (lis320-full-mac got 60 "402 Payment Required"
failures from then; outbox b1895b05c). gate3 (addendum E) started at about 18:32 UTC on the same account. A 402 call
comes back empty and is counted as a failed call (claude_rd378k_teacher.py lines 85-98), so a hit run measures the
account, not the grader. Agreed with the Thread manager (19:00 UTC): if gate3's log shows even one 402, gate3 does not
count (no verdict either way). Ben (18:47 UTC) offered GLM 5.3 Flash through his opencode subscription.

## When this runs
Only if origin/builder-outbox:artifacts/claude-rd378k-20260926/gate3/teacher-log.txt contains at least one line with
"402". From gate3 the thread reads only that count, the failed-call count and the usable dialogs per kind; its labels,
its grade counts and its agreement lines are never read or used. If the log has no 402, this addendum does not apply.

## The one change: the route
scripts/claude_rd378k_teacher3oc.py runs claude_rd378k_teacher3 unchanged (same prompt and verdict words, windows of at
most 7 graded turns, tolerant parser, two passes) with each teacher call sent through scripts/claude_glm_opencode.py
(the Director's shared helper, sha256 3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2; model
opencode-go/glm-5.3-flash). The route sets no temperature and runs through opencode's own agent; this gate measures the
route as it is, and it is the route that would grade training data. So this run is also the route check.

## The gate (same 38 dialogs, sha256(id) % 3 == 1: 23 chat, 15 overheard; same rows and bars as addendum E)
- overall: agreement >= 85% and kappa >= 0.5 (claude_rd378k_teacher.py agree on labels.jsonl);
- untrue notes: teacher "ok" on <= 15% of judge-unsupported notes;
- coverage: usable dialogs chat >= 21 of 23 and overheard >= 14 of 15 (summed over the four parts).
Report only: the same agree line on labels_passA.jsonl, failed calls, missed_unknown_turns, wall time.
Proved wrong (this route does not grade like the blind judges): agreement below 85% or the untrue row above 15%.

## After
PASS: all training grades for rd-378g and rd-378k come from claude_rd378k_teacher3oc.py through this route.
Any row fails: GLM grading stops (the Thread manager's 18:32 rule: labeller v3 is the last version), no grade trains
anything, and the Thread manager gets the counts.
