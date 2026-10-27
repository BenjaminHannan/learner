# y1r addendum 3: who wrote the practice chats (Answering-from-memory thread, 2026-09-27 11:14 UTC, before any y1r run on real data; sealed in SEAL-y1r-add3.sha256.txt)

**What changed upstream, not here:** y1r trains on exactly the items y1t's data gate passes (PLAN.md; ADDENDUM-1 point
2; y1t ADDENDUM-3 rule 5). Those items are glm2's (artifacts/claude-y1t-20260926/gate/GATE-RESULT.md, GATE-PASS,
64cf3b193). By y1t's ADDENDUM-5 (sealed 03:53 UTC, after Ben's 03:47 UTC words "just have luna rewrite all the
training data"), GPT-6 Luna wrote 315 of the 2,400 dialogs and GLM 5.3 Flash wrote the other 2,085. So PLAN.md's line
"GLM 5.3 Flash wrote every word" no longer holds for y1r's data; the correct line is "GLM 5.3 Flash wrote 2,085
dialogs and GPT-6 Luna wrote 315". No Claude-written text is in it.

**What does not change:** the one change, the recipe, the run order (ADDENDUM-1), the items file (the gate result's
glm2/items/items_train.jsonl, sha256 47e2e295...79e4, and items_dev.jsonl, c0288f2c...07e4), the marks, the
predictions and the control row. There is still one run.

**Added, report only:** how many training and dev pairs come from Luna's dialogs. There is no split of LoCoMo results
by writer, because the retriever is trained on all pairs together.
