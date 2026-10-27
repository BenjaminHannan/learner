# rd-378L addendum D: the machine changes, nothing else (registered 2026-09-26 ~13:45 UTC, before rd-378L ran)

Thread "Trustworthy notes" (problem #3, notes), which took rd-378L over from "Fix: reading facts from chat" at 13:33 UTC.
Written before any note was written over LoCoMo and before any score. 007g never ran.

## Why
Ben, 13:30 UTC: "none of them should be waiting for benspc btw, they should all be using vast.ai if they're tests are
queued. Benspc's gpu should not be the blocker". 007g sat behind 007b on BensPC, so it moves to a vast.ai rental
(handoff/queue/rent-rd378L.md replaces handoff/queue/007g-rd-378L-notes-search.md).

## What stays the same
The script (scripts/claude_rd378L_recall.py, SEAL-C hash 6b9398c0...), the data (LoCoMo conversations 0-4,
locomo10.json sha256 79fa87e9...), the writer command, the score command, the marks L1-L3, the proved-wrong clause, the
outputs, and the privacy rule (no LoCoMo question, answer, turn or note text is printed or pushed).

## What changes
1. Where it runs: a rented Linux RTX 5090 (or 4090) instead of BensPC's RTX 5070 Ti.
2. How the writer gets there. The registered writer is the rd-378 merged model, model.safetensors sha256
   dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510. On the rental it is rebuilt from its own LoRA
   adapter (BensPC C:/Users/benja/rd378/tree/WORK/nrun/adapter, from the same training run) on the same base
   (openbmb/MiniCPM5-1B commit 87179e5c) by scripts/claude_rd378L_rebuild.py, with BensPC's versions (torch 2.11.0
   cu128, transformers 5.17.0, peft 0.21.0). The rebuild is used only if its model.safetensors hashes to dbcc8db5...;
   otherwise the Mac's copy (~/premonition-models/rd378-notes-merged/, same hash) is copied to the rental and must hash
   the same. No other writer may be used. If neither route gives that hash, the job stops with WRITER-FAIL.
3. Where the LoCoMo-derived files live: dialogs.jsonl, notes.jsonl and notes_recall_per_question.jsonl are copied
   from the rental to the Mac at ~/rd378L-private/ (outside git) and never pushed; the rental's copies go with it.

## Known difference, accepted before the run
Same weights, but greedy decoding on another GPU and software build can pick a different token where two are almost
tied, so a few notes may differ from what BensPC would have written. Store A has no notes and store B uses this one
notes file, so the A-vs-B comparison is unaffected; the GPU and versions are reported, not corrected.

## Seal
SEAL-D.sha256.txt covers the recall script (unchanged), PASSMARKS, B, C and D, the rebuild script and the writer
code. The rental runs the exact commit that added SEAL-D.sha256.txt.
