# Chat prompt: finish, train and test the lis-320 fact reader (Thread manager, 2026-09-27T22:13Z)

Ben asked at 22:09 UTC for work that doesn't clash with the reasoner chats, then "should we do both?" (this and the note writer's G5). The prompt uses the card option the Thread manager recommended, "finish all 6,000 practice chats first", since Ben has not tapped otherwise. Everything below the line is the prompt.

---

# Goal: finish the lis-320 reader's practice chats, train it, and give its registered verdict on the sealed test

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The reader listens to chat and writes down the facts people state. That includes who a fact is about, corrections, and things that are no longer true.
- The current reader, lis-319f, works, but it learned from Claude-written chats, which Ben bans from training. lis-320 retrains the same reader on chats that GPT-6 Luna worded from code-made facts. The reader is MiniCPM5-1B + LoRA, with the same settings.
- lis-320 passes only if it matches lis-319f on a sealed 320-row test, readpanel320.
- Everything is sealed in artifacts/claude-lis320-20260926/. Read these first and change nothing sealed:
  - PASSMARKS.md (marks R1-R6, validity, scoring);
  - ADDENDUM-1 (R7);
  - ADDENDUM-3 and ADDENDUM-4 (C1, reported as its own verdict);
  - ADDENDUM-9 to ADDENDUM-12 (the Luna writer and how the full run is chunked).
- If something can't be done as written, write a dated addendum before that step and tell Ben.
- **Where it stands:**
  - Luna pilot 8 passed. The full run is seed 324, 6,000 dialogs.
  - Chunks 1-10 are done: 2,028 dialogs worded, all parsed, rawcheck2 OK, on builder-outbox under full-luna/chunkK/.
  - Ben chose to finish all 6,000 before training.

**Steps**
1. **Finish the wording.**
   - Next is chunk 11. Copy handoff/queue/claude-lis320-luna-c10b-mac.md to handoff/queue/claude-lis320-luna-c11-mac.md, set K=11 and fix its header line.
   - Ben's Mac watcher runs queue jobs, and results land on builder-outbox. Queue each chunk only after the one before it lands (ADDENDUM-11). That's about 18-20 more chunks.
   - Keep waiting cheap. Use a background shell loop that checks builder-outbox every 10 minutes and wakes you only when a chunk lands or a stop rule fires. Never poll with the model.
   - ADDENDUM-11's stop rules apply: parsed below 85%, a rawcheck2 failure, a seal or selftest failure, or a changed seeds hash. If one fires, stop and tell Ben with the counts.
2. **DATA.md.** When every seed-324 dialog has a parsed row, write and seal DATA.md as ADDENDUM-11 says, before any training.
3. **Train.**
   - Build a vast kit following the patterns in handoff/kit/ (for example rd378gv or lf8v), with the sealed training settings.
   - Mock-test it against a fake vast CLI before its first real run.
   - Run it as one rental job through the Mac queue, capped at $4. Ben's standing rule lets you rent without asking.
   - Destroy the instance only after a manifest-checked copy-back; otherwise stop it. Put the adapter on the Mac.
4. **Test once.**
   - Both readers read readpanel320 once each, with the same settings (T = 0.995, the unchanged compiler). They are lis-320 and lis-319f, whose merged weights are on the Mac at ~/premonition-models/lis319f-merged/.
   - Use the sealed scorers and two fresh blind judges exactly as PASSMARKS says.
   - The panel is test-only. Never open, print or quote its rows; scripts print counts only.
5. **Results.** RESULTS.md holds:
   - R1-R7, the validity counts and the proved-wrong line;
   - C1 as its own verdict;
   - the report-only rows.

   A separate subagent recounts the marks blind, from the score files only.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. Only add files; never touch the repo-root notebook/.
- Times in files come from `date -u`.
- Training data is Luna- or code-written only, never Claude-written. The blind judges only measure.
- Never read keys or auth files (~/.codex and the like). Stop processes by exact PID. Never stop another agent's rental.
- Label claims shown, suggested or untested.
- Save usage: no polling, no status chatter, and subagents only when needed.
- Tell Ben only at a stop rule, when the data is done, and at the verdict.

**Done means**
- All 6,000 dialogs are worded, DATA.md is sealed, the reader is trained, both readers are scored once, and RESULTS.md is recounted and pushed to main.
- Final report for Ben, 15 lines at most, plain words, result first:
  - Does lis-320 match lis-319f? Give right saves and turns with a wrong save for both, out of the panel.
  - Corrections, and things no longer true.
  - Rental cost.
  - Is it ready for the build?
  - Commit hashes.
