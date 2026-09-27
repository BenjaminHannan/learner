# 0.2d gates, ADDENDUM-52: the notes slot is G (rd-378g's note writer). Written Sun Sep 27 23:24:04 UTC 2026, before any check run

Acting for Month-end (stopped) on this one slot only, from the Thread manager's prompt
(reviews/chat-prompt-build-notes-2026-09-27.md; Ben's "Yes" at 22:55:09 UTC). Additive only. No other slot, gate or
row changes. One environment probe ran before this file: `python -B scripts/claude_e2e02d.py selftest` in the cloud
session between 23:03 and 23:15 UTC (20/20), to see whether it runs without torch. It is re-run below as part of W3.

## What changes
- ADDENDUM-20's notes slot is G, the rd-378g note writer, verified PASS G1-G5 at commit 9d7a51c0f
  (artifacts/claude-rd378g-20260926/RESULTS.md, RESULTS-G5.md). G was trained only on GLM and Luna notes, never on
  anything Claude wrote.
  - Base: openbmb/MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc.
  - G's adapter (artifacts/claude-rd378g-20260926/vast/SEAL-run.sha256.txt). The only copy is on Ben's Mac at
    /Users/ben-hannan/premonition-models/rd378g-vast-adapter, which matches SEAL-run (vast/COLLECT.txt):
    - adapter_model.safetensors b1c69db46666e6dc68f41de760f6541a9174c4fbb92a26040b0edb208b064998
    - adapter_config.json ae8df4275c6cfe1b782ee55d4469113d19a02eeea5dd86fadcec7cfbd3ebbb03
    - README.md 8443ad44b3ceac7a87bd9c33eb48bb592cbedf787347ec071fd651a84d3a5e20
    - chat_template.jinja 7451a05cf1e28a79d97d7c0bc951028c0b1915119bf9046acd06a0e3d931f47c
    - tokenizer.json 3e065a558a034185fe299917b398685c1facd0169a9eea1e629eb30c171fed81
    - tokenizer_config.json bd4a5446624eb938cd57c97b0be1914372a433df17efaac052aabed57ac3b26b
  - Merged G (the model that wrote every scored note): model.safetensors
    a0fb1c9bd663b00b1470d515ae0c38a8dd3ed7d1cfdead70325137312300d1ed. It stayed on rd-378g's rental and was destroyed
    with it, so it is rebuilt from the base and the adapter (see "Where it runs").
- Code: scripts/claude_e2e02d_g.py (new file).
  - It imports scripts/claude_e2e02d.py and replaces only the note step. claude_e2e02d.py is not edited; its sha256 at
    this commit is 4870333c7ad562f5635b09b7b92629f6fd26cb30b9de5e0f3779891de33a3929. scripts/claude_e2e336_run.py is not
    edited either.
  - Slot constants: NOTES02D (G's merged model dir; E2E02D_NOTES moves it on a given machine but cannot fill an empty
    slot) and NOTES_SHA02D = a0fb1c9b... (checked before loading, fail closed).
  - Harness arm: `--arm claude_e2e02d_g:build_02d_g` (output arm_claude_e2e02d_g_build_02d_g.jsonl).
  - `claude_e2e02d_g.py merge` rebuilds G the way rd-378g's trainer merged it: base in bf16 on CUDA (fp32 elsewhere),
    peft merge_and_unload, save_pretrained(safe_serialization=True), the base's tokenizer. It checks the six adapter
    files first.
- Before: the store's note rows are N0 text ("owner relation value") built from the reader's saved facts.
- After: the store's note rows are G's notes.
  - G writes them on every user turn from the inputs rd-378g used: kind "chat", the date line (the build's said_at,
    D15), the earlier turns of this session (the user's turns and the talker's replies, oldest first; the prompt keeps
    the last 6) and the new turn.
  - It is one greedy call of claude_rd378_write.NoteWriter. That file and claude_rd378_common.py are the files
    rd-378g sealed (artifacts/claude-rd378g-20260926/SEAL.sha256.txt).
  - Each note row points at the raw user turn it was written on (turn_ids = [that turn]), as store v4 expects.
  - If G's output does not parse on a turn, no note is stored for that turn, and the turn is counted.
- N0 leaves the path. It stays only as the fallback if the slot is ever emptied (NOTES02D = ""), as ADDENDUM-20 fixed.
- Unchanged: the reader, the fact book (still fed by the reader's saved facts), the W input, the reasoner, the
  talker, and recall returning raw user turns only. The memory row and every bar are unchanged.

## Disclosure (rd-378g ADDENDUM-K, "What each result means"; every use of G carries it)
- G is in the build only as a search aid: "trained on ungraded GLM and Luna notes; G's unsupported share 49.2% vs R's
  50.9% on fresh dialogs" (R = the rd-378 writer).
- G5 PASS means "no less true than the rd-378 writer". It does not mean G's notes are true: the blind judges called
  about half of each writer's notes unsupported. No G note is offered as true.
- Notes stay search pointers to the raw lines. Store v4 answers from raw lines only.
- Search with G's notes (rd-378g G1, LoCoMo 5-9 practice): an evidence line reached the top 10 for 577 of 772
  questions, against 489 with no notes and 585 with R's notes.

## Hand-written parts the new file adds, and how it differs from the setup G was scored in
- N1: a note row's text is G's note text plus its "when" in brackets. This is exactly how rd-378g's scored store
  indexed notes (claude_rd378L_recall.py:108-109). A report-only rd-378g row without it scored 581 of 772
  (vast/notes_confirm_whenoff.json), so N1 is not where the gain comes from.
- N2: a note row points at the turn it was written on, as the prompt asks. rd-378g's scored store pointed each note
  at the turns its cites name (offsets 0 to -6 in the same session). In a chat, an offset of -1 is usually the talker's
  reply, which the store does not hold. The report counts how many notes cite an earlier turn.
- The date line: the build's said_at comes from a "today is ..." line (D15). rd-378g's LoCoMo test used the session
  dates. The earlier turns reach G with the talker's replies as "Assistant:" lines, the same shape as the chat dialogs
  G5 used.

## Checks (fixed before any run)
- W1, same path.
  - On one machine and one dtype, run the new file's note step (claude_e2e02d_g.writer_for + write_notes, through
    artifacts/claude-e2e02dg-20260927/checks.py w1) and scripts/claude_rd378_write.py over all 43 dialogs in
    artifacts/claude-rd378g-20260926/g5/dialogs.jsonl (504 user turns).
  - PASS: identical notes (text, cites, when) on 504 of 504 turns.
  - This is a wiring check, so a mismatch means fix the wiring and run again. Every attempt is reported.
  - What would prove the wiring wrong: a turn that still differs on the same card and dtype after a second CLI run
    matches the first. If W1 fails, the box script runs the CLI a second time to tell run-to-run noise from wiring.
- W2, pointers.
  - Every note row the new build stores points at the raw user turn it was written on, that turn's heard row holds
    the turn's text, and recall returns only heard rows.
  - Checked in the new selftest with a stub writer (no model).
  - Checked again with real G on the 14 chat dialogs (99 user turns) through the whole 0.2d-G turn path
    (checks.py w2).
    - The stand-ins: a stub reader that saves nothing, the dialog's own replies replayed as the talker's, and a no-op
      solver.
    - Fresh state per dialog, and said_at preset to the dialog's date.
    - Recall is store v4 in bm25 mode, k=10, with every note row and every user turn as a query. bm25 is used
      because no MiniLM is downloaded, and v4's pointer step is the same in both modes.
  - PASS: all note rows and all heard rows are right, and 0 non-heard rows come back from recall.
- W2b (added; the direct evidence for "the build's note step writes exactly the notes G was scored on").
  - In the same w2 run, the notes the build's turn path writes, and the note row texts (N1), equal
    claude_rd378_write.py's notes on the same turns.
  - PASS: 99 of 99 chat user turns.
- W3, nothing else moved.
  - claude_e2e02d.py's own selftest still passes, with the file unchanged (sha256 above).
  - The new file's selftest passes (stub reader, talker, solver and writer; no model loaded). It runs 0.2d and
    0.2d-G side by side on the same turns and requires the same replies, the same talker input on every turn, the same
    fact book, the same heard rows, and the same per-turn log except for time.
- The merge, report only: whether the rebuilt model.safetensors equals a0fb1c9b... If it does not, NOTES_SHA02D is
  not changed in this task. The checks then run on the rebuilt model with its own sha named, and the report says so.
- Report only:
  - how often the notes match the rental's notes (artifacts/claude-rd378g-20260926/vast/g5/notes_G.jsonl; a
    different card can shift a few);
  - notes per turn and unparsed turns;
  - notes that cite an earlier turn (N2);
  - writer time per turn (median and p90) on the machine used;
  - the build's time per turn with and without the writer, on 8 turns (2 chat dialogs x 4 user turns). This uses
    claude_e2e02d's own log "ms", a stub reader (lis-320's weights are not on the rental), and the base MiniCPM5-1B
    loaded as the talker. That is a stand-in for LFM2.5-1.2B, because no model download other than MiniCPM5-1B is
    allowed.
- This proves the wiring only. Whether G helps the whole build is judged later by the build's own memory row, after
  the seal.

## Where it runs
- One vast rental job (Ben's standing rule; cap $4; this job's money stop $2).
  - It is started from Ben's Mac by the BASH-ONLY queue job handoff/queue/rent-e2e02dg-1.md, because G's adapter is
    only on the Mac. The Mac reads the adapter and sends a copy; it never moves or deletes it.
  - The job files are in artifacts/claude-e2e02dg-20260927/kit/ (mac.sh on the Mac, box.sh on the rental).
- The card: an RTX 5090 first, because rd-378g's rental was one and a same-card merge and notes are the most likely to
  repeat bit for bit. Any card with at least 16 GB and compute capability 8.0 is used only if no 5090 is offered.
- The stack is rd-378g's rental's: torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0, bf16 on CUDA.
- No model download other than MiniCPM5-1B.
- The instance is destroyed only after a checked copy-back (every file against the rental's manifest); otherwise it
  is stopped.
- The G5 dialogs are test input only. Nothing is trained.
- Results: artifacts/claude-e2e02dg-20260927/RESULTS.md.
