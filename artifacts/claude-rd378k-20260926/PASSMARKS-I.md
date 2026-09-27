# rd-378k addendum I (2026-09-27 00:24:29 UTC): the gate runs again at opencode reasoning effort "low"; gate3oc is stopped and never read

Written before any of gate3oc's output has been seen. The thread has only the peek's counts from 20:36 UTC (0 failed
calls, 1 dialog done). It has not seen a label, grade count, agreement line or teacher log. PASSMARKS.md and addenda B-H
stay as sealed; this file adds to them.

## Why: time, and the gate must certify the route that grades the training data
- gate3oc has run since about 20:27 UTC, one process, at opencode's default reasoning effort. At that effort a GLM 5.3
  Flash call took 88 s, 112 s and 263 s-class, and one of four timed out at 300 s (lis-320 ocdiag). With
  "--variant low", 4 of 4 replies parsed in 5-15 s with 0-9 reasoning tokens (ocdiag3, a5a07655c). lis-320 pilot 4
  ran 60 low calls in 3.1 min.
- The grades that would train the writer (rd378g-label3) come to about 1,000 calls: about 200 dialogs, 2-3 windows
  each, two passes. At about 2.5 min a call over this thread's 2 processes that is about 20 hours on the default
  effort, against about 2 hours at low. So training grades will come from the low route. Addendum F's rule is that
  the gate measures the route that grades training data, so a default-route PASS would certify a route that will not
  be used.
- The Thread manager asked (00:20 UTC) whether a restart on low finishes sooner (obvious fix first). This decision is
  the thread's own.

## The one change: reasoning effort low
Every call goes through scripts/claude_glm_low_run.py. It binds claude_glm_opencode to
scripts/claude_glm_opencode_low.py, which is the reading thread's call_low (scripts/claude_lis320_glm_oclow.py): helper
v1.1's call with "--variant low" on the `opencode run` line. These stay as in addenda E and F: the model, prompt words,
verdict words, windows, parser, the two passes, the 38 dialogs and every bar. Addendum H's route-loss rule applies
unchanged.
Risk, disclosed now: with less thinking the model may grade worse than at the default effort. This gate measures
exactly that; it is not assumed away.

## gate3oc
000-peek-rd378oc2 stops it by exact PID. Whether it is stopped or finishes before the stop lands, nothing of it is read:
not its labels, agreement lines, grade counts or teacher log. The one exception is the peek's counts (dialog lines
done, failed-call lines, elapsed time). It has no verdict.

## The gate: gate3low, on the same 38 dialogs (sha256(id) % 3 == 1: 23 chat, 15 overheard)
- overall: agreement >= 85% and kappa >= 0.5 (claude_rd378k_teacher.py agree on gate3low/labels.jsonl);
- untrue notes: teacher "ok" on <= 15% of judge-unsupported notes;
- coverage: usable dialogs chat >= 21 of 23 and overheard >= 14 of 15.
Report only: pass A's agree line, failed calls, missed_unknown_turns, wall time.
Proved wrong (the low route does not grade like the blind judges): agreement below 85% or the untrue row above 15%,
with no route loss.

## After
- PASS: every training grade for rd-378g and rd-378k comes from claude_rd378k_teacher3oc.py run through
  claude_glm_low_run.py, exactly this route.
- A row fails and a route loss is present (addendum H): there is no verdict. The route is fixed, then the same 38
  dialogs run again under a new addendum.
- A row fails and no route loss is present: this is a registered FAIL of the low route. GLM grading on that route
  stops, and no grade from it trains anything. The default route was never gated, because gate3oc was stopped unread.
  Gating it later would be a second route tried on the same 38 dialogs. It could run only under its own sealed
  addendum, after the Thread manager has reviewed it, and would be reported as a second try.
