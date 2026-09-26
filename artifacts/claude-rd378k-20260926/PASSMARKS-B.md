# rd-378k addendum B (2026-09-26 16:55 UTC): untrue-note gate row, and the writer 4b starts from

Written before any teacher label exists (the rd378k-teacher job is held in the Mac queue, not started) and before any
rd-378k training. PASSMARKS.md stays as sealed; this file adds to it.

## B1: label gate row for the untrue notes (Thread manager, 16:53 UTC)
The notes that matter most are the ones the blind judges call "unsupported": a teacher that calls them "ok" puts untrue
notes into training. So the gate needs BOTH rows, from the same `agree` output:
- overall: agreement >= 85% and kappa >= 0.5 (as sealed);
- untrue notes: judges_unsupported_teacher_ok <= 15% of judges_unsupported.
If either row fails, nothing is trained on the teacher's grades: the two-pass teacher (a note is kept only if two
independent teacher passes both say "ok") is measured on the sha256(id) % 3 == 1 dialogs by both rows.

## B2: the writer 4b starts from (Thread manager ruling, 16:53 UTC, after Ben's "Retrain first" for the reader, 16:46)
Ben's 16:39 rule covers models that are already trained, if they could join a build. The rd-378 writer learned from
Opus-written dialogs and notes (artifacts/claude-rd378-20260925/data/README.md), so it stays out of every build.
Order, one change at a time:
1. rd-378g: a writer trained from the plain 1B on GLM-written notes over GLM-written chats, with its own sealed marks
   (artifacts/claude-rd378g-20260926/PASSMARKS.md) and its own verdict against the rd-378 writer on real chats.
2. Only if rd-378g passes: rd-378k runs as sealed, with A = the rd-378g writer instead of the rd-378 writer. The
   drafts come from A over GLM practice chats that A never trained on. K5's A is the rd-378g writer's notes over
   conversations 5-9 (from rd-378g's run, kept on the Mac). The rd-378 writer's panel notes are a report-only third set
   (a third unnamed letter, two judge runs, counted with the same scorer functions), never part of a mark.
If rd-378g fails, rd-378k does not run until a Claude-free writer passes.
