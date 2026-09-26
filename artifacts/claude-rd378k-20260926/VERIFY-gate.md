# rd-378k label gate = PASS on both rows (recount by the Trustworthy notes thread, 2026-09-26 17:31 UTC)

Source: origin/builder-outbox runs/rd378k-teacher (rc=0, COMMIT 3316b3ba2, seal 16/16 OK); files copied here.
Recounted from gate/labels.jsonl against artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl (the blind judges'
verdicts are used only to measure the teacher, never trained on):

| Row (PASSMARKS + PASSMARKS-B B1) | Bar | Got | Verdict |
|---|---|---|---|
| overall, ok vs not ok | agreement >= 85% and kappa >= 0.5 | 424 of 485 (87.4%), kappa 0.751 | PASS |
| untrue notes | teacher "ok" on <= 15% of judge-unsupported notes | 30 of 216 (13.9%) | PASS |

Coverage (report only): 29 of the 39 picked dialogs (sha256 % 3 == 0) came back in a usable form; 10 failed all three
tries, so 485 of their 660 notes were compared. A training dialog whose grades don't parse is dropped, never guessed.
The teacher's own counts: ok 269, unsupported 172, bad_cite 29, bad_form 14, bad_when 1.
Measured teacher cost: $0.0301 (label, 66 calls) + $0.0378 (write, 21 calls) = $0.0679.

GLM practice dialogs (glm/dialogs.jsonl): 160 (kd-001..kd-160), 80 chat + 80 overheard, 2,391 turns, 1,812 turns the
writer reads; structure checked in code; two spot-read by the thread (training data, not a panel).
Next (PASSMARKS-B B2): rd-378g first; these dialogs are for the writer's cut-only drafts afterwards.
