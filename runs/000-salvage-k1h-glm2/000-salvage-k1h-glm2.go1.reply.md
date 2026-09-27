Verdict pending — running duplicate guard and process scan for the stalled job.
No duplicate found and the temp folder exists — now copying the job outputs.
Copies verified with matching hashes — now gathering final counts and timestamps.
COPIED

- Duplicate guard: 0 on origin/main for `artifacts/claude-k1h-20260926/glm`, 0 on origin/builder-outbox; parent on main 13 entries, on outbox 3 entries; fetch exit 0.
- ps filter (`k1h-glm2` or `claude_k1h_glm`): 4 lines, 0 python with `claude_k1h_glm` (0 step-4, 0 step-5, 0 step-6). PIDs: 19907/PPID 19905/00:43 salvage bash; 19940/19907/00:43 salvage opencode; 46711/46709/08:22:48 k1h-glm2 bash; 46743/46711/08:22:47 k1h-glm2 opencode. Nothing signaled.
- Tmp: primary `/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/k1h-glm2.pp0OOR` exists 1; glob `k1h-glm2.*` 1 match; fallback 0. Not NO-TMP. Nothing deleted/changed there.
- Copy: 5 files copied, 5/5 sha256 match. answers.jsonl 133121 B `348b645b…944c`; chats.jsonl 212058 B `49c74254…ee8a2`; answer1-log.txt 754 B `4fd8416f…7d789`; chats-log.txt 1603 B `e71e9ce0…e7545`; chats-log-attempt1.txt 906 B `b4057e81…55c88`.
- answers.jsonl: 240 lines; 240 non-empty answer; 0 empty; 0 error kinds; 240 distinct item_id; 0 starting `kh-`; 0 bad-JSON.
- chats.jsonl: 593 lines; 593 distinct item_id; 0 bad-JSON.
- CRLF bytes: 0 in answers.jsonl, 0 in chats.jsonl.
- logs: answer1-log.txt 13 lines, 0 `chats call`, last is-JSON 1 keys 7 tag 0 len 117; chats-log.txt 37 lines, 36 `chats call`, last is-JSON 1 keys 5 tag 0 len 289; chats-log-attempt1.txt 25 lines, 25 `chats call`, last is-JSON 0 keys 0 tag 1 len 36.
- mtimes UTC src: answers 2026-09-26T21:01:09Z, chats 2026-09-27T01:58:50Z, answer1-log 2026-09-26T21:01:09Z, chats-log 2026-09-27T01:58:50Z, attempt1 2026-09-26T22:46:58Z. Copies: all 5 2026-09-27T04:45:16Z. Salvage 2026-09-27 04:44:42Z–04:46:08Z.
- Report: `artifacts/claude-k1h-20260926/glm/REPORT-salvage.md` written, counts only. Staged 6 files with `git add -f` (1019 insertions); watcher pushes `artifacts/claude-k1h-20260926/glm`.

Deviations:
1. `answer2-log.txt` count 0 in tmp — step 6 never produced output.
2. Extra `chats-log-attempt1.txt` count 1, copied as-is; only log with last-is-JSON 0 / starts-tag 1.
3. chats 593 lines vs ~650 named; answers 0 `kh-` consistent with no step 6.
4. `artifacts/` git-ignored so force-add used.
5. No GLM call, no opencode command, GPU 0, COPY-ONLY obeyed.
