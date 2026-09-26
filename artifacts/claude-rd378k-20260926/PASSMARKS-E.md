# rd-378k addendum E (2026-09-26 18:31 UTC): gate2 FAIL, the cause, and the sealed fallback measured on fresh dialogs

Written after gate2's result and before any dialog with sha256(id) % 3 == 1 has been graded by the teacher.
PASSMARKS.md and addenda B, C and D stay as sealed; this file adds to them.

## gate2 = FAIL as registered (VERIFY-gate2.md; files in gate2/)
Labeller v2 on the 39 dialogs with sha256(id) % 3 == 0: agreement 471 of 555 (84.9%, bar 85%), kappa 0.699; untrue
notes 35 of 252 (13.9%, bar 15%); coverage chat 22 of 23, overheard 11 of 16 (bar 90% each). Two rows fail. No
training uses labeller v1 or v2 grades.

## Cause (shown, from gate2/failures.jsonl, all 27 failed calls read by code)
The teacher left out turns whose notes list is empty (25 calls) or also graded earlier context turns it was not asked
about (2 calls). A parser that ignores out-of-window turns and lets a note-less turn be left out accepts all 27 and
rejects 0. So the coverage row measured the parser, not the teacher's grades.

## What runs now (the fallback sealed in addenda B and C, plus one parser fix)
scripts/claude_rd378k_teacher3.py:
1. parser fix: verdicts are never changed or guessed. A turn WITH notes must come back with one verdict per note, as
   before. A turn with NO notes may be left out; its "missed" is then unknown (-1), and both row builders
   (claude_rd378_data.py line 56, claude_rd378k_data.py line 93) drop such a turn, so it never teaches "no note here".
2. the two-pass teacher of addenda B and C: pass A as shown, pass B with each turn's notes in reverse order; a note is
   "ok" only if both passes say "ok". Windows of at most 7 graded turns, prompt, verdict words and model as labeller v2.
All training grades for rd-378g and rd-378k come from this labeller, and only if every row below passes.

## The gate (38 dialogs with sha256(id) % 3 == 1: 23 chat, 15 overheard; never graded by any teacher before)
Same rows and bars, counted by claude_rd378k_teacher.py agree on labels.jsonl and by teacher3's per_kind line:
- overall: agreement >= 85% and kappa >= 0.5;
- untrue notes: teacher "ok" on <= 15% of judge-unsupported notes;
- coverage: usable dialogs >= 90% of the picked ones in each kind (chat >= 21 of 23, overheard >= 14 of 15).
Report only: the same agree line on labels_passA.jsonl (pass A alone, so the parser fix and the second pass can be
told apart), missed_unknown_turns, failed calls, cost.
The cause above is proved wrong if overheard coverage is still below 14 of 15 with this parser.

## If any row fails
GLM grades train nothing and the GLM-grader route stops. The Thread manager gets the counts and one next option,
measured on the last unused third (sha256(id) % 3 == 2) with these rows: a larger GLM teacher in the same labeller,
only with the Thread manager's yes on its cost. No hand-written grading rule replaces the teacher (the 16:04 redirect).
Brain mapping: none claimed; this is a fix to the measuring tool, not to the model.
