**Verdict: COPIED** (re-verified and committed locally by the resumed run; not DUPLICATE / not NO-TMP / not COPIED-WHILE-RUNNING).

**Run 1** (queue `go1`) did steps 0–4 and wrote `REPORT-salvage.md`, then ended without `.done`/`.exit`; wrapper fell through to `go2` (this run, free mimo flash) with the RESUME NOTICE. I continued at the first unfinished step: re-verify, then commit. Start `date -u` 04:46:26 UTC, end 04:59:59 UTC (14 min, cap 20).

**Counts (steps 0–4, script-printed, nothing quoted)**
- 0: `artifacts/claude-k1h-20260926/glm` on origin/main = 0, on origin/builder-outbox = 0 → 0 duplicates.
- 1: filtered `ps` lines = 4 (19907/19905, 20416/19907 at 04:56:29 UTC; 46711/46709 08:34:04; 46743/46711 08:34:03, commands cut to 160 chars); python = 0, so step 4/5/6 = 0/0/0; 0 processes signaled.
- 2: `k1h-glm2.*` folders under `T/` = 1 (the given `<tmp>`); fallback candidates = 0.
- 3: copied files = 5 (answers.jsonl, chats.jsonl, 3 `*log*.txt`); sha256 source↔copy = 5/5 match, re-checked at 04:59 UTC; `<tmp>` inventory unchanged (O/ files 2, logs 3, `answer2-log.txt` 0).
- 4: answers.jsonl 240 lines, 240 non-empty, 0 empty, 0 error kinds, 240 distinct `item_id`, 0 `kh-`, 0 bad-JSON; chats.jsonl 593 lines, 593 distinct `item_id`, 0 bad-JSON; `\r\n` = 0 and 0 (expected 0). Logs: answer1 13 lines / 0 `chats call` / last-is-JSON 1; chats-log 37 / 36 / 1; chats-log-attempt1 25 / 25 / last-is-JSON 0 with `[k1h-glm]` tag 1. Source mtimes UTC: 2026-09-26T21:01:09Z, 2026-09-27T01:58:50Z, 2026-09-26T21:01:09Z, 2026-09-27T01:58:50Z, 2026-09-26T22:46:58Z; all 5 copies 2026-09-27T04:45:16Z. Independent second counter reproduced every number: 0 discrepancies.

**Push:** commit `86599f56d` (6 files, 1071 insertions, `git add -f`), worktree tracked changes = 0. I run no `git push`: the queue line `PUSH: artifacts/claude-k1h-20260926/glm` is consumed by `premonition-watch/watcher.sh publish()` on this run's `.exit`, which copies that path to the outbox clone and pushes `builder results: 000-salvage-k1h-glm2` to origin/builder-outbox (same mechanism that published `000-peek-k1h-glm2`).

**Deviations**
1. `answer2-log.txt` = 0 (original step 6 never ran) → 0 `kh-` item_ids; chats 593, not the ~650 named.
2. Extra file `chats-log-attempt1.txt` copied as-is (last line not JSON, starts `[k1h-glm]`).
3. `artifacts/` is git-ignored → force-added (6 files).
4. Run 1 stopped after writing the report (no `.done`/`.exit`); steps 0–4 re-run by this resume, all counts identical.
5. `shasum -a 256 -c` from the repo root reports `No such file or directory` for 24/25, 2/2, 3/4 seal entries — this branch is behind origin/main and lacks those files (present-and-OK: 1/25, 0/2, 1/4). Instead hashed `git show origin/main:<path>` for every entry: 31 OK, 0 mismatch, 0 missing; 0 seal entries cover `glm/`; nothing sealed was written.
6. Text-only `ps` filter yields 2 false "python" hits (the task text inside both opencode command lines contains `python` and `claude_k1h_glm`); used the executable-name filter → 0.
7. No GLM call, no opencode command, no GPU, 0 processes signalled, nothing deleted or changed in the job's folder.
