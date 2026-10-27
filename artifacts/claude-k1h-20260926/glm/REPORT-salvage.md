# salvage-k1h-glm2 REPORT

Verdict: COPIED

Job salvaged: k1h-glm2 (launched 2026-09-26 20:22 UTC).
Salvage run: 2026-09-27 04:44:42 UTC to 2026-09-27 04:45:41 UTC (`date -u`).
Copy moment (`date -u -r` on copies): 2026-09-27T04:45:16Z for all 5 copied files.
No chat and no answer is quoted in this file; counts only.
Script parsing printed counts only; no chat/answer text was opened for reading beyond field counts.

## Step 0 — DUPLICATE GUARD: 0 duplicates, continue

- `git fetch -q origin main builder-outbox` exit: 0.
- `git ls-tree origin/main --name-only -- artifacts/claude-k1h-20260926/glm`: 0 lines.
- `git ls-tree origin/builder-outbox --name-only -- artifacts/claude-k1h-20260926/glm`: 0 lines.
- Parent `artifacts/claude-k1h-20260926/` on origin/main: 13 entries (no `glm`).
- Parent `artifacts/claude-k1h-20260926/` on origin/builder-outbox: 3 entries (`glm-gate`, `glm-peek`, `glm-v1`; no exact `glm`).
- origin/main commit at fetch: a0b9ebd3930fe360f5aee43de2bfa22750fad1c2.
- origin/builder-outbox commit at fetch: 847aa4da9f44106d337bd686d6d0d47ed88dd461.
- Result: 0 duplicates found; not DUPLICATE.

## Step 1 — process scan (`ps -axo pid,ppid,etime,command` filtered to `k1h-glm2` or `claude_k1h_glm`): 4 lines, 0 python

- Matching line count: 4.
- Python lines containing `claude_k1h_glm`: 0.
- Step mapping for python (answer with one `--items` = step 4, chats = step 5, answer with `O/chats.jsonl` = step 6): 0 in step 4, 0 in step 5, 0 in step 6.
- No process was signaled, stopped, or otherwise touched.
- Copying was done while no python writer was running, so verdict is COPIED (not COPIED-WHILE-RUNNING).

| PID | PPID | ELAPSED | COMMAND first 160 chars |
|-----|------|---------|--------------------------|
| 19907 | 19905 | 00:43 | `bash /Users/ben-hannan/premonition-watch/rungo5.sh /Users/ben-hannan/premonition-watch/queue/000-salvage-k1h-glm2.md opencode/muse-spark-1.3-contributor-free` (157 chars, full) |
| 19940 | 19907 | 00:43 | `/usr/local/bin/opencode run --model opencode/muse-spark-1.3-contributor-free --auto --dir /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/c` (160-char cut) |
| 46711 | 46709 | 08:22:48 | `bash /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/handoff/kit/mimo/rungo4.sh /Users/ben-hannan/premonitio` (160-char cut) |
| 46743 | 46711 | 08:22:47 | `/usr/local/bin/opencode run --model opencode-go/muse-spark-1.3-contributor --auto --dir /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/car` (160-char cut) |

Notes: PID 19907/19940 are this salvage job; PID 46711/46743 are the stalled k1h-glm2 job's watcher wrappers. Elapsed values as printed at 2026-09-27 04:45:13 UTC.

## Step 2 — tmp folder: 1 match, exact path used

- Primary `<tmp>` `/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/k1h-glm2.pp0OOR`: exists = 1.
- Glob `k1h-glm2.*` under same `T/` folder: 1 match (the same path).
- Fallback search: not needed; count of fallback candidates = 0.
- Result: not NO-TMP.
- Nothing in the job folder was deleted, changed, or written.

## Step 3 — copy: 5 files, 5/5 sha256 match

Source `<tmp>` listing counts: `O/` file count = 2; `<tmp>/*log*.txt` file count = 3; `answer2-log.txt` count = 0.

Copies into worktree:

- `<tmp>/O/answers.jsonl` -> `artifacts/claude-k1h-20260926/glm/answers.jsonl`
- `<tmp>/O/chats.jsonl` -> `artifacts/claude-k1h-20260926/glm/chats.jsonl`
- `<tmp>/answer1-log.txt` -> `artifacts/claude-k1h-20260926/glm/logs/answer1-log.txt`
- `<tmp>/chats-log.txt` -> `artifacts/claude-k1h-20260926/glm/logs/chats-log.txt`
- `<tmp>/chats-log-attempt1.txt` -> `artifacts/claude-k1h-20260926/glm/logs/chats-log-attempt1.txt`

sha256 (source and copy identical, 5/5 match):

- answers.jsonl: 348b645b1e87be405b31d7684bbb0d7e57976a716e79b57414374dd32aac944c
- chats.jsonl: 49c74254ea797454d98967b4b3123f23f51498ae8e70089ff978191db76ee8a2
- logs/answer1-log.txt: 4fd8416f3cba077690027f54f3a9b54ca42749256080a921bf03d9c6a2d7d789
- logs/chats-log.txt: e71e9ce0eb98495a2d59303699f72091defe12947d9c257c09e6dc2f349e7545
- logs/chats-log-attempt1.txt: b4057e81bf0d04494335686e0669c96603492117725bbfc8bdb1890790556c88

Sizes (bytes): answers.jsonl = 133121; chats.jsonl = 212058; answer1-log.txt = 754; chats-log.txt = 1603; chats-log-attempt1.txt = 906.

## Step 4 — counts

All counts from a script that printed counts only (no chat/answer text).

- answers.jsonl lines: 240.
- answers.jsonl with non-empty `answer`: 240.
- answers.jsonl with empty `answer`: 0.
- answers.jsonl `error` kinds among empty: 0 kinds.
- answers.jsonl distinct `item_id`: 240.
- answers.jsonl `item_id` starting with `kh-`: 0.
- answers.jsonl bad-JSON lines: 0.
- chats.jsonl lines: 593.
- chats.jsonl distinct `item_id`: 593.
- chats.jsonl bad-JSON lines: 0.
- `\r\n` byte count in answers.jsonl: 0 (expected 0).
- `\r\n` byte count in chats.jsonl: 0 (expected 0).

Logs (line count; lines containing `chats call`; last-line classification counts only):

- logs/answer1-log.txt: lines = 13; `chats call` lines = 0; last line is-JSON = 1; last-line JSON key count = 7; last line starts with `[k1h-glm]` = 0; last-line length chars = 117.
- logs/chats-log.txt: lines = 37; `chats call` lines = 36; last line is-JSON = 1; last-line JSON key count = 5; last line starts with `[k1h-glm]` = 0; last-line length chars = 289.
- logs/chats-log-attempt1.txt: lines = 25; `chats call` lines = 25; last line is-JSON = 0; last-line JSON key count = 0; last line starts with `[k1h-glm]` = 1; last-line length chars = 36.

Modification times (UTC, `date -u -r`):

- Source `<tmp>/O/answers.jsonl`: 2026-09-26T21:01:09Z.
- Source `<tmp>/O/chats.jsonl`: 2026-09-27T01:58:50Z.
- Source `<tmp>/answer1-log.txt`: 2026-09-26T21:01:09Z.
- Source `<tmp>/chats-log.txt`: 2026-09-27T01:58:50Z.
- Source `<tmp>/chats-log-attempt1.txt`: 2026-09-26T22:46:58Z.
- Copies in worktree (all 5): 2026-09-27T04:45:16Z.

## Every deviation

1. `answer2-log.txt` (original job step 6) is absent from `<tmp>`: count 0. Step 6 output was never produced.
2. Extra file `chats-log-attempt1.txt` present in `<tmp>` (count 1) and copied as-is; its last line is not JSON (is-JSON = 0) and starts with `[k1h-glm]` (starts-tag = 1), unlike the other two logs.
3. `chats.jsonl` has 593 lines, not ~650 named in the original task; `answers.jsonl` has 240 lines with 0 `kh-` item_ids, consistent with step 6 never running.
4. `artifacts/` is git-ignored, so copies were force-added (staged with `git add -f`); the watcher pushes `artifacts/claude-k1h-20260926/glm`.
5. No GLM call and no opencode command were run by this salvage; GPU count = 0.
6. Run 1 ended without a `.done`/`.exit` marker after writing this report, so the wrapper launched `go2` (this run)
   with the RESUME NOTICE; steps 0-4 were re-run and reproduced every count with 0 discrepancies.
7. `shasum -a 256 -c` from the repo root cannot read 24/25, 2/2 and 3/4 seal entries because this worktree branch is
   behind origin/main and does not contain those files; the 31 sealed entries were instead verified by hashing
   `git show origin/main:<path>` = 31 OK, 0 mismatch. Deviation from the literal instruction, content unchanged.
8. Filtering `ps` on the command text alone also matches this salvage's own opencode command line (the task text
   contains `python` and `claude_k1h_glm`); python counts above use the executable name, so the step 4/5/6 counts
   are 0/0/0 rather than the 2 false positives a text-only filter reports.
9. The parent job's watcher wrappers (PID 46711 / 46743, elapsed 08:34) are still alive but stalled at the Go usage
   limit; they were not signaled, and no `claude_k1h_glm` python is writing.

## Resume (go2) — re-verified; verdict unchanged: COPIED

Run 1 (queue `000-salvage-k1h-glm2.go1`, muse-spark free) did steps 0-4 and wrote this file, then ended without a
`.done`/`.exit` marker, so the wrapper fell through to `go2` (free `opencode/mimo-v2.6-flash`, this run) with the
RESUME NOTICE. Work continued from the first unfinished step: independent re-verification, then the local commit and push.
No file in the job's folder was opened beyond field counts, changed, or signaled.

- Resume start: 2026-09-27 04:46:26 UTC (`date -u`); this section written 2026-09-27 04:57:26 UTC (`date -u`).
- Step 0 re-run: `git fetch -q origin main builder-outbox` exit 0; `artifacts/claude-k1h-20260926/glm` entries on
  origin/main = 0 and on origin/builder-outbox = 0 → 0 duplicates, not DUPLICATE.
- Step 1 re-run at 2026-09-27 04:56:29 UTC: filtered lines = 4; python lines (executable-name filter) = 0, so
  step 4 = 0, step 5 = 0, step 6 = 0. No process was signaled, stopped, or touched.
  (A naive `command ~ "python"` match returns 2 because both opencode command lines carry the task text, which
  contains the words `python` and `claude_k1h_glm`; the executable-name filter is the correct one.)

| PID | PPID | ELAPSED | COMMAND first 160 chars |
|-----|------|---------|--------------------------|
| 19907 | 19905 | 11:59 | `bash /Users/ben-hannan/premonition-watch/rungo5.sh /Users/ben-hannan/premonition-watch/queue/000-salvage-k1h-glm2.md opencode/muse-spark` (157 chars, full) |
| 20416 | 19907 | 10:12 | `/usr/local/bin/opencode run --model opencode/mimo-v2.6-flash-free --auto --dir /Users/ben-hannan/Desktop/projects/beautiful-model/.claud` (160-char cut) |
| 46711 | 46709 | 08:34:04 | `bash /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/handoff/kit/mimo/rungo4.sh /Use` (160-char cut) |
| 46743 | 46711 | 08:34:03 | `/usr/local/bin/opencode run --model opencode-go/muse-spark-1.3-contributor --auto --dir /Users/ben-hannan/Desktop/projects/beautiful-model/` (160-char cut) |

- Step 2 re-run: folders named `k1h-glm2.*` under `T/` = 1 (the same `<tmp>` path) → not NO-TMP.
- Step 3 re-run (source sha256 recomputed and compared to the 5 copies): 5/5 identical; source mtimes unchanged
  (`2026-09-26T21:01:09Z`, `2026-09-27T01:58:50Z`, `2026-09-26T21:01:09Z`, `2026-09-27T01:58:50Z`,
  `2026-09-26T22:46:58Z`); `<tmp>` inventory unchanged (`O/` files = 2, `*log*.txt` = 3, `answer2-log.txt` = 0).
- Step 4 re-run by a second, independently written counts script: answers 240 lines / 240 non-empty / 0 empty /
  0 error kinds / 240 distinct `item_id` / 0 `kh-` / 0 bad-JSON; chats 593 lines / 593 distinct `item_id` / 0 bad-JSON;
  `\r\n` = 0 in both; logs 13 lines (0 `chats call`), 37 (36), 25 (25) with the same last-line classifications as above.
  Discrepancies against the run-1 numbers: 0.
- Seals: 0 seal entries cover `artifacts/claude-k1h-20260926/glm/` (SEAL-k1h, SEAL-addendum1, SEAL-addendum2 each
  contain 0 `glm/` paths). `shasum -a 256 -c` from the repo root against the seal files as this branch has them reports
  `No such file or directory` for 24/25, 2/2 and 3/4 entries, because this worktree branch is behind origin/main and does
  not contain those sealed files at all (1/25, 0/2, 1/4 are present and OK). Re-verified by hashing
  `git show origin/main:<path>` for every seal entry: 25/25, 2/2 and 4/4 match = 31 OK, 0 mismatch, 0 missing.
  No sealed file was written, moved or edited by this salvage (only `artifacts/claude-k1h-20260926/glm/` is new).

## PUSH

- Line in the queue file: `PUSH: artifacts/claude-k1h-20260926/glm` (1 line).
- The 6 files are staged with `git add -f` (artifacts/ is git-ignored) and committed on this branch; this agent runs no
  `git push`. `premonition-watch/watcher.sh` `publish()` copies that path out of the worktree into the outbox clone and
  pushes it to origin/builder-outbox as `builder results: 000-salvage-k1h-glm2` when this run writes its `.exit`
  marker (same path as the earlier `000-peek-k1h-glm2` publish).
- Files to be pushed: 6 (2 `.jsonl`, 3 logs, 1 report); largest = 212058 bytes, all under the watcher's 5 MB limit.
