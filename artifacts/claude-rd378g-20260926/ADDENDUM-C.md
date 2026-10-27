# rd-378g addendum C (2026-09-26 19:30 UTC): the grades come through the opencode route

Written before any GLM note or grade for rd-378g has been read (the rd378g-teacher job is still running on the Mac).
PASSMARKS.md and addenda A and B stay as sealed; this file adds to them. Marks G1-G4 and the proved-wrong line are
unchanged.

## C1: which labeller grades the 240 dialogs
OpenRouter ran out of funds at about 18:30 UTC, so the rd-378k gate3 run has no verdict (rd-378k VERIFY-gate3.md) and
the label gate is now measured through Ben's opencode route (rd-378k PASSMARKS-F.md, job rd378k-gate3oc). Addendum B's
B1 is read with "labeller v3" meaning scripts/claude_rd378k_teacher3oc.py (labeller v3 run unchanged through the
Director's opencode helper), and "VERIFY-gate3.md says PASS" meaning VERIFY-gate3oc.md says PASS on all rows. Everything
else in B1 stands (glm3/ copy of notes_w1.jsonl, rows from claude_rd378_data.py, missed = -1 dropped). If gate3oc
fails, G is not trained on GLM grades.

## C2: if the writing step was also hit
If glm/notes_w1.jsonl holds fewer than 180 dialogs (75% of 240) because writing calls failed, no rows are built from it
until the missing batches are written again through the opencode route, under an addendum fixed before that run.
From 180 to 240 dialogs, G trains on what came back, and the count is reported.
