# rd-378g addendum I, DRAFT (2026-09-27 03:50:37 UTC; NOT sealed): the missing practice batches are written by GPT-6 Luna, and every grade comes from the Luna grader

DRAFT for the Thread manager's review. It becomes ADDENDUM-I.md, with SEAL-ADD-I, together with rd-378k addendum K
(artifacts/claude-rd378k-20260926/DRAFT-PASSMARKS-K.md, which gives the reason and the helper). It is written before any
Luna call, and before any output of 005-rd378g-writelow has landed. ADDENDUM-A to H stay as sealed; this file adds to
them.

- Kept: the 90 GLM dialogs kg-001..090 (glm/notes_w1.jsonl, sha256 87a51358fa2b...). This follows the Thread manager's
  recorded reading of Ben's ruling: data already written by GLM is kept. The file was written by rd378g-teacher before
  OpenRouter's 402s at about 18:30 UTC, so none of it was written after the 00:57 UTC limit. The error-text scan
  requested at 03:48 UTC runs on it anyway: a dialog whose text matches (case-insensitive) "usage limit",
  "limit exceeded", "rate limit" or "quota" is dropped. The scan reports counts only.
- Not kept: anything from 005-rd378g-writelow. Its agent is stuck behind the same limit, and its output has not
  landed. Keeping it would add a third writer setting (GLM at effort low) for at most a few batches. This replaces
  addendum H's writelow2.
- The one change for writing: claude_rd378g_writemore_oc.py runs unchanged, with each call going through the Luna
  helper via scripts/claude_luna_run.py. Unchanged: the WRITE prompt, area, speaker letters, check_batch, the repeat
  check against every first turn already written, and to_rows.
- Step 1, format pilot: Luna writes batch 18 alone into pilot-luna/. It never trains anything.
  - Pass: "batch 18 ok" within its 3 tries, and 0 "call failed" lines.
  - Otherwise: stop, and the Thread manager gets the counts.
- Step 2, writeluna: batches 18-20 and 22-39, with --have glm/notes_w1.jsonl and output to glm2N/.
  - Batches that fail the code checks 3 times stay skipped.
  - Route-lost batches (every try "call failed") may be written again under an addendum.
  - Fewer than 120 dialogs in total after that means stop and report.
- Grades: rd378g-label3 grades every kept dialog, GLM-written and Luna-written. It uses teacher3 through the Luna route,
  and runs only after gate3luna passes.
- Disclosed:
  - The training set mixes two writers: 90 GLM dialogs and up to 126 Luna dialogs.
  - Ben's words "rewrite all the training data" could also mean rewriting the 90 with Luna. This keeps them, as
    recorded.
  - The writer's route is not a measured quantity.
  - The G1/G2 marks (PASSMARKS, addenda A and B) do not change.
