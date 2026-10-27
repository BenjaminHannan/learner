# rd-378g addendum I (2026-09-27 03:55:09 UTC): the missing practice batches are written by GPT-6 Luna, and every grade comes from the Luna grader

Sealed from DRAFT-ADDENDUM-I.md (dc71c074a) after the Thread manager's review (03:53 UTC). The review added one thing:
a writer field on every row. The reason and the helper are in rd-378k addendum K
(artifacts/claude-rd378k-20260926/PASSMARKS-K.md). This is written before any Luna writing call and before any output
of 005-rd378g-writelow has been seen. ADDENDUM-A to H stay as sealed; this file adds to them.

- Kept: the 90 GLM dialogs kg-001..090 (glm/notes_w1.jsonl, sha256 87a51358fa2b...).
  - This follows the Thread manager's recorded reading of Ben's ruling: data already written by GLM is kept.
  - They were written before OpenRouter's 402s at about 18:30 UTC, so none were written after the 00:57 UTC limit.
  - The error-text scan (scripts/claude_rd378g_tagwriter.py, counts only) ran on them at 03:55 UTC: 90 dialogs, 0
    dropped.
- Not kept: anything from 005-rd378g-writelow. Its agent is stuck behind the GLM limit, and 000-stop-rd378low stops it.
  This replaces addendum H's writelow2.
- The one change for writing: claude_rd378g_writemore_oc.py runs unchanged, with each call going through the Luna
  helper via scripts/claude_luna_run.py. Unchanged: the WRITE prompt, area, speaker letters, check_batch, the repeat
  check against every first turn already written, and to_rows. A Luna route failure prints "call failed"; a batch
  whose every try failed that way is route-lost (addendum F).
- Step 1, format pilot: Luna writes batch 18 alone into pilot-luna/. It never trains anything.
  - Pass: "batch 18 ok" within its 3 tries, and 0 "call failed" lines.
  - Otherwise: stop, and the Thread manager gets the counts.
- Step 2, writeluna: batches 18-20 and 22-39, with --have glm/notes_w1.jsonl and output to glm2N/notes_w1.jsonl.
  - Batches that fail the code checks 3 times stay skipped.
  - Route-lost batches may be written again under an addendum.
- Step 3, writer tag: claude_rd378g_tagwriter.py tag --have glm/notes_w1.jsonl --in glm2N/notes_w1.jsonl
  --out glm2N/notes_w1_tagged.jsonl.
  - Every row gets "writer": GLM for the 90 kept ids, Luna for the rest.
  - Any dialog with error text is dropped, with counts by writer.
  - Everything after this reads notes_w1_tagged.jsonl: the grades, the rows and the retrain.
  - Fewer than 120 dialogs in it means stop and report.
- Grades: rd378g-label3 grades every kept dialog, GLM-written and Luna-written. It uses teacher3 through the Luna route,
  and runs only after gate3luna passes.
- Report only: grade counts (ok / unsupported / other verdicts, missed) split by writer.
- Disclosed:
  - The training set mixes two writers: 90 GLM dialogs and up to 126 Luna dialogs.
  - Ben's words "rewrite all the training data" could also mean rewriting the 90 with Luna. This keeps them, as the
    Thread manager recorded.
  - The G1/G2 marks (PASSMARKS, addenda A and B) do not change.
  - G1/G2 test one writer model trained on the mixed set, so they cannot be split by the training data's writer.
