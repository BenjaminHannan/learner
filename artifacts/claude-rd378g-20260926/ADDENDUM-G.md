# rd-378g addendum G (2026-09-27 00:24:29 UTC): the lost batches are written at opencode reasoning effort "low", and the grades go through the same low route

Written before any of rd378g-writemore's output has been seen. The thread has only the peek's counts from 20:36 UTC
(0 failed calls, 0 batch lines). ADDENDUM-A to F stay as sealed; this file adds to them.

- Why: see rd-378k addendum I (artifacts/claude-rd378k-20260926/PASSMARKS-I.md). A call at the default effort takes
  88 s to over 300 s; at low it takes 5-15 s. The route is scripts/claude_glm_low_run.py.
- writemore: 000-peek-rd378oc2 stops it by exact PID if fewer than 18 of its 21 batches are done ("batch N ok" plus
  "skipped after 3 tries" lines). If 18 or more are done, it runs on, and this addendum changes only the grading. A
  stopped writemore leaves no output, because it writes its file only at the end.
- rd378g-writelow runs only if writemore was stopped. It is claude_rd378g_writemore_oc.py, unchanged, run through
  claude_glm_low_run.py, with the same --have glm/notes_w1.jsonl (sha256 87a51358...) and the same batches 18-20 and
  22-39. Its output goes to glm2L/, a new folder, so nothing can mix with a partial glm2/. Everything else is as in
  addenda D and F:
  - batches that fail the code checks stay skipped;
  - route-lost batches may be written again under an addendum;
  - fewer than 120 dialogs in total means stop and report.
- A difference, disclosed. The 90 kept dialogs (kg-001..090) were written through OpenRouter at temperature 0.9, at
  OpenRouter's reasoning default. The new ones are written through opencode at effort low, with no temperature set.
  The writer's route is not a measured quantity. Before any row trains, every note is graded by the gated route.
- Grades (rd378g-label3) come from claude_rd378k_teacher3oc.py run through claude_glm_low_run.py, and only after
  gate3low passes. This replaces "after a gate3oc PASS" in addendum C.
