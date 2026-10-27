# rd-378g addendum D (2026-09-26 19:39 UTC): the lost writing batches, written again through opencode

Written after rd378g-teacher landed and before any of its notes or dialog texts has been read (only counts: dialogs,
batches, error lines). PASSMARKS.md and addenda A-C stay as sealed; this file adds to them.

## What came back (rd378g-teacher, COMMIT 854f21660; origin/builder-outbox runs/rd378g-teacher)
90 dialogs (45 chat, 45 overheard; kg-001..kg-090) from 15 of 40 batches; glm/notes_w1.jsonl sha256
87a51358fa2bdedaaf0edafeb273074ed648350c5d759f130fcee5fe475b482a. 555 log lines "HTTP Error 402: Payment Required".
Batches 7, 8, 11 and 14 failed the script's own code checks three times (cites / "when" not in a cited turn / speakers
alternate): they stay skipped, as the sealed run would have left them. Batches 18-20 and 22-39 (21 batches) were lost
to the 402s. Grading got 0 usable answers, so glm/judge_w1.jsonl does not exist (addendum B's v1-vs-v3 row is dropped).

## The step (addendum C, C2)
scripts/claude_rd378g_writemore_oc.py writes batches 18-20 and 22-39 again with the same per-batch step as
claude_rd378g_teacher.writenotes (same prompt, area, speaker letters, code checks, repeat check against every first turn
already written, row format), each call through the Director's opencode helper (no temperature setting; the sealed run
asked for 0.9). Output glm2/notes_w1.jsonl = the 90 dialogs unchanged, then the new ones (kg-091 on). It replaces
glm/notes_w1.jsonl everywhere addenda B and C name it (glm3/notes_w1.jsonl is copied from glm2/).
If the total is under 120 dialogs, nothing trains and the Thread manager gets the counts. From 120 up, G trains on what
came back; the total and the per-route split (OpenRouter 90, opencode the rest) are reported.
