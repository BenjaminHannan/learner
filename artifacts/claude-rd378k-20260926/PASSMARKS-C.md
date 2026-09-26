# rd-378k addendum C (2026-09-26 17:35 UTC): the labeller, fixed for long dialogs, and the gate measured again

Written after the label gate's first result (VERIFY-gate.md: PASS on both rows) and before any training grade is used.
PASSMARKS.md, PASSMARKS-B.md stay as sealed; this file adds to them.

## What was found (shown, from gate/labels.jsonl and the rd-371b judge input; Thread manager asked for it by kind)
The teacher's answer was unusable for 10 of the 39 gate dialogs, and all 10 are overheard: 0 of 23 chat dialogs failed,
10 of 16 overheard dialogs failed (same median length, 14 turns). An overheard dialog asks for a grade on every turn at
once; a chat dialog on about 7. So the first gate mostly measured chat notes (23 of 29 usable dialogs), and training on
version-1 grades would drop most overheard dialogs: the writer would learn mostly from chats with an assistant.

## The one change to the labeller
scripts/claude_rd378k_teacher2.py: at most 7 graded turns per call (the dialog up to the window's last turn; only the
window's turns carry notes). Same prompt words, verdicts, checks and output format. Failed calls keep the teacher's raw
answer for reading. All training grades for rd-378g and rd-378k come from this labeller.

## The gate again, with the labeller that will be used (same 39 dialogs, sha256(id) % 3 == 0; same bars)
- overall: agreement >= 85% and kappa >= 0.5;
- untrue notes: teacher "ok" on <= 15% of judge-unsupported notes;
- coverage (new): usable dialogs >= 90% of the picked ones in EACH kind (chat, overheard).
Report only: both rows per kind. If any row fails, nothing trains on teacher grades; the two-pass teacher of addendum B
is measured on the sha256(id) % 3 == 1 dialogs with this labeller and these rows.
