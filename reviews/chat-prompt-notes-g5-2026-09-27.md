# Chat prompt: finish the note writer's last mark (rd-378g G5) (Thread manager, 2026-09-27T22:12Z)

Ben asked at 22:09 UTC for work that doesn't clash with the reasoner chats, then "should we do both?" (this and the reader). Everything below the line is the prompt.

---

# Goal: run rd-378g's last mark (G5, are the new writer's notes as true as the old writer's?) and give its registered verdict

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The build writes short notes about what people say, and the notes help it find the right chat lines later. The old note writer (R) learned from Claude-written notes, which Ben bans from training. The new writer (G) learned only from GLM- and Luna-written notes, with no grader.
- G already passed marks G1-G4: search help 577 of 772 against R's 585. See artifacts/claude-rd378g-20260926/RESULTS.md.
- The last mark, G5, asks whether G's notes are no less true than R's. Both writers' notes on the 43 G5 dialogs are already written: vast/g5/notes_G.jsonl and notes_R.jsonl, 504 lines each. Nothing needs training or renting.
- Everything is sealed in artifacts/claude-rd378g-20260926/: PASSMARKS.md and ADDENDUM-K.md (G5's rule, bar, proved-wrong line and wording). Read both first and change nothing sealed. If something can't be done as written, write a dated addendum before doing the step, and tell Ben.

**Steps**
1. Run `python -B scripts/claude_rd378g_g5.py selftest`.
2. Run `make` exactly as ADDENDUM-K says (seed 37805):
   - dialogs from artifacts/claude-rd378g-20260926/g5/dialogs.jsonl with `--rem 2`;
   - `--g` and `--r` pointing at the two vast/g5 notes files;
   - `--out` to a scratch folder outside the repo, so no judge can find map.json there.
3. Two fresh blind judges: two new subagents that have seen none of this work.
   - Each gets its own empty folder holding only items.jsonl and a copy of artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md.
   - Neither ever sees map.json, the repo, any other notes file, or which writer wrote which note.
   - Each writes one row per turn in the format the score step reads, {"dialog", "t", "verdicts": ["ok" or "unsupported", ...]}. The selftest in the script shows the format.
4. Run `score` with the map and both judge files. It prints counts only.
5. Commit the G5 folder (items, map, both judge files, the score output) and write RESULTS-G5.md as a new file. Don't edit RESULTS.md. Include:
   - G's and R's unsupported shares side by side;
   - G5 against its bar (G's share at most R's + 5 points) and the proved-wrong line (G's share at least R's + 15 points);
   - the report-only rows ADDENDUM-K lists;
   - the overall rd-378g verdict, which is PASS only if G1-G5 all pass.
6. A separate subagent does a blind recount of the shares from the map and the two judge files only.

**Wording rule (sealed)**
- A pass means "no less true than the rd-378 writer", never "trustworthy".
- Always give R's share next to G's. About half of R's notes were judged unsupported before, so matching R is a low bar.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. Only add files.
- Times in files come from `date -u`.
- Never print or quote dialog or note text; scripts and reports give counts only.
- The judges only measure. Their verdicts never train, tune or filter anything.
- $0: no rentals or downloads. Never touch secrets. Stop processes by exact PID.
- Label claims shown, suggested or untested.

**Done means**
- G5 has been judged, scored and recounted. RESULTS-G5.md has the verdict, and everything is pushed to main.
- Final report for Ben, 8 lines at most, plain words, result first:
  - G's and R's unsupported shares;
  - the G5 verdict and the overall rd-378g verdict;
  - what it means for the build, in one line;
  - commit hashes.
