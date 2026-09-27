# Chat prompt: put the new note writer into the 0.2d build (Thread manager, 2026-09-27T22:57Z)

rd-378g passed G1-G5 at 9d7a51c0f (RESULTS-G5.md). The Thread manager asked Ben at 22:43 UTC whether to write the prompt
that puts the new writer into the build; Ben answered "Yes" at 22:55:09 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWE3btCiBcqaS22Yi9oEYGmA).
ADDENDUM-20 of the 0.2d gates already names this slot, and rd-378g ADDENDUM-K fixed the offer's wording. Everything below
the line is the prompt.

---

# Goal: put the new note writer (rd-378g's G) into the 0.2d build as its notes slot, and show that the build's note step writes exactly the notes G was scored on

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The 0.2d build (scripts/claude_e2e02d.py, an unsealed draft) hears every user turn. Today its notes are a code stand-in called N0: each fact the reader saves is joined into "owner relation value" and stored as a note. Notes are only search pointers. Recall always returns the raw user turns, and answers come from those lines.
- design/v3/30-modes/02d-gates-ADDENDUM-20.md says the notes slot goes to the retrained note writer once it has a verified PASS. It now has one. rd-378g (G, trained only on GLM and Luna data, never on anything Claude wrote) passed G1-G5: artifacts/claude-rd378g-20260926/RESULTS.md and RESULTS-G5.md (9d7a51c0f). With G's notes, search found 577 of 772 LoCoMo questions, against 489 with no notes and 585 for the old Claude-trained writer. The judges called 49.2% of G's notes unsupported and 50.9% of the old writer's.
- The Month-end thread that owns the build is stopped. You act for it on this one slot only. Don't change any other slot, gate or row.
- Other chats are running (the lis-320 reader, the thinker-as-reader test, the relation-net and patch tests). Don't edit their files or touch their jobs.

**Read first**
- scripts/claude_e2e02d.py: the header (N0, F1, the notebook), `turn()`, and the selftest.
- design/v3/30-modes/02d-gates-ADDENDUM-20.md, -23 (store v4) and -51 (the newest addendum).
- artifacts/claude-rd378g-20260926/ADDENDUM-K.md, "What each result means": the exact wording any use of G must carry.
- scripts/claude_rd378_write.py (NoteWriter), scripts/claude_rd378_common.py (build_nprompt, parse_notes), scripts/claude_ep382_store_v4.py.
- artifacts/claude-rd378g-20260926/vast/COLLECT.txt and vast/SEAL-run.sha256.txt: where G lives and its hashes.

**Where G is**
- G's adapter is only on Ben's Mac, at /Users/ben-hannan/premonition-models/rd378g-vast-adapter (it matches SEAL-run; adapter_model.safetensors sha256 b1c69db4...). The base is MiniCPM5-1B, and its download is already approved. The merged model on the rental had sha256 a0fb1c9b... Rebuild it from base + adapter and report whether your merge matches.
- Copy the adapter; never move or delete it. Ben's Mac runs bash-only jobs from main's handoff/queue/ (see handoff/HANDOFF.md and the kit in handoff/kit/rd378gv for how the rental got Mac files).

**The one change**
- Before: the store's note rows are N0 text built from the reader's saved facts. After: the store's note rows are G's notes. G writes them on every user turn, from the same inputs rd-378g used (kind "chat", the date line, the earlier turns and the new turn), and each points at the raw turn it was written on (turn_ids), as store v4 expects.
- Everything else stays as it is: the reader, the fact book (still fed by the reader's saved facts), the W input, the reasoner, the talker, and recall returning raw turns only.
- If G's output doesn't parse on a turn, store no note for that turn and count it.
- scripts/claude_e2e02d.py is pinned by other seals (artifacts/claude-c1dev-20260927/SEAL*.sha256.txt), so don't edit it or scripts/claude_e2e336_run.py. Put the change in a new file, scripts/claude_e2e02d_g.py, that imports claude_e2e02d and replaces only the note step, with its own slot constant for G's path (NOTES02D) and its own arm name for the harness.
- Write design/v3/30-modes/02d-gates-ADDENDUM-52.md: the notes slot is G (hashes, merged sha, commit 9d7a51c0f), N0 leaves the path and stays only as the fallback if the slot is ever emptied, and the disclosure reads exactly as ADDENDUM-K asks: "trained on ungraded GLM and Luna notes; G's unsupported share 49.2% vs R's 50.9% on fresh dialogs", "no less true than the rd-378 writer", never "trustworthy". Update the new file's header to match.

**Checks (write them into ADDENDUM-52 and commit it before running any)**
- W1, same path: on one machine and one dtype, run the new file's note step and scripts/claude_rd378_write.py over all 43 dialogs in artifacts/claude-rd378g-20260926/g5/dialogs.jsonl (504 user turns). PASS: identical notes (text, cites, when) on 504 of 504 turns. This is a wiring check, so a mismatch means fix the wiring and run again. Report every attempt.
- W2, pointers: every note row the new build stores points at the raw user turn it was written on, and recall returns only heard rows. Check this in the new selftest with a stub writer, and again with real G on the 14 chat dialogs.
- W3, nothing else moved: claude_e2e02d.py's own selftest still passes unchanged, and so does the new file's selftest (stub reader, talker, solver and writer; no model loaded).
- Report only: how often your notes match the rental's notes (artifacts/claude-rd378g-20260926/vast/g5/notes_G.jsonl; a different card can shift a few); notes per turn; unparsed turns; writer time per turn (median and p90) on the machine used; and the build's time per turn with and without the writer, on a few turns.
- This proves the wiring only. Whether G helps the whole build is judged later by the build's own memory row, after the seal.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. New files only: scripts/claude_e2e02d_g.py, design/v3/30-modes/02d-gates-ADDENDUM-52.md and artifacts/claude-e2e02dg-YYYYMMDD/. Never touch the repo-root notebook/.
- Times in files come from `date -u`.
- Compute: Ben's Mac through the queue, or BensPC, both $0. Otherwise at most one rental job, capped at $4. Ben's standing rule lets you rent. Destroy an instance only after a checked copy-back, otherwise stop it. Never stop another agent's rental. No new model downloads other than MiniCPM5-1B.
- The G5 dialogs are test input only: never train on them. No training in this task at all.
- Never read keys or auth files. Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.

**Done means**
- ADDENDUM-52, the new build file and the check results (artifacts/claude-e2e02dg-YYYYMMDD/RESULTS.md) all pushed to main.
- Final report for Ben, 12 lines at most, plain words, result first:
  - Is the new note writer in the build, and does the build write the same notes it was scored on?
  - How much slower is a turn with it?
  - Anything that didn't match, and why.
  - The single next step.
  - Commit hashes.
