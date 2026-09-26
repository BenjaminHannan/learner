# rd-378k label gate 2 = FAIL (recount by the Trustworthy notes thread, 2026-09-26 18:31 UTC)

Source: origin/builder-outbox runs/rd378k-gate2b (COMMIT 5f938199b; seals SEAL-ADD-C 2 OK, SEAL-ADD-D 2 OK, SEAL 15 OK
plus the one allowed trainer line). Files copied here (gate2/); checked, no key text in any of them.
Recounted from gate2/labels.jsonl against artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl (blind judges'
verdicts, used only to measure the teacher):

| Row (PASSMARKS-B B1, PASSMARKS-C) | Bar | Got | Verdict |
|---|---|---|---|
| overall, ok vs not ok | agreement >= 85% and kappa >= 0.5 | 471 of 555 (84.9%), kappa 0.699 | FAIL |
| untrue notes | teacher "ok" on <= 15% of judge-unsupported notes | 35 of 252 (13.9%) | PASS |
| coverage, chat | usable >= 90% | 22 of 23 | PASS |
| coverage, overheard | usable >= 90% | 11 of 16 | FAIL |

Usable dialogs 33 of 39. Teacher counts: ok 296, unsupported 210, bad_cite 36, bad_form 11, bad_when 2. Calls 74, failed
calls 27. Measured teacher cost $0.0324. Wall time 533 s.
Cause, shown by code on gate2/failures.jsonl: 25 of the 27 failed calls left out turns with no notes and 2 also graded
context turns; the parser of claude_rd378k_teacher3.py accepts all 27 and rejects 0. Next: PASSMARKS-E.md.
