Stopping the orphan job and saving its rows — counts and hashes only, no chat text.
No live job process — now hunting its output files.
Surface checks came up empty — digging deeper for the job folder.
The script exists on origin/main but not locally — widening the search to temp areas.
Those temp dirs are empty — scanning for recently modified outputs.
No matching outputs in the usual spots — inspecting the job script to find where it writes.
A candidate folder just vanished — checking what happened.
Zero recoverable outputs found — verifying context before writing the report.
Found the job folder with its log but no rows — preserving what exists.
Report written — committing and pushing the preserved files.
Verdict: EMPTY — 0 chats, 0 answers recovered; 1 log file preserved. Commit ce8643109 created locally; PUSH BLOCKED (git push denied by tool permissions).

Counts:
- chats.jsonl files found: 0
- answers.jsonl files found: 0
- chats-log.txt files found: 1 (499 bytes, 14 lines, sha256 e7372a49…5313cd, mtime 20:04:41 UTC)
- answer-log.txt files found: 0
- O/ output dir entries: 0
- .jsonl lines total: 0; parse-as-JSON: 0; non-JSON: 0; non-empty "answer": 0 (n/a, no file)
- Copy sha256 match: 1 of 1 (yes)
- `opencode session list -n 1000 | wc -l`: 9
- k1h-glm processes killed: 0 (none running; 0 survivors)
- Candidate folders: 1 (/private/tmp/k1h-glm-iLDhRG) → not AMBIGUOUS
- Duplicate guard: 0 paths on origin/main, 0 on origin/builder-outbox → PASS

Deviations:
1. Naive ps grep matches only this task's own wrapper (PID 36288, title embeds task text); filtered check = 0 job processes. No kill.
2. A second tree with scripts/claude_k1h_glm.py (/private/var/.../T/tmp.oSZKfdQy6j) seen ~20:07–20:12 UTC with 0 target files, gone by ~20:13 UTC. Nothing copied from it.
3. Temp copy of the script via git show to /tmp made then deleted; excluded from counts.
4. Zero chats.jsonl/answers.jsonl exist in any searched root regardless of mtime; cutoff filter changes nothing.
5. Agrees with prior art: origin/main 5c1da5817 (earlier salvage found output empty) and 7f0d11c51 (first launch 0 chats/0 answers).
6. Constraints kept: additive only, no secrets, no notebook/ writes, no config/auth/key reads, no GLM call (sole opencode call = session count).
7. Header timestamp 20:20 UTC vs session clock 20:06–20:18 UTC; treated as metadata.
8. PUSH not done: `git push` denied by environment permissions. Pushed files await push: artifacts/claude-k1h-20260926/glm-v1/chats-log.txt + REPORT.md in commit ce8643109 on claude/card-experiment-handoff-7c5b27.
