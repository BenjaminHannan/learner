# Salvage k1h-glm — REPORT (counts only, no content quoted)

Date (UTC): 2026-09-26. Worktree: card-experiment-handoff-7c5b27.
Task header time: 2026-09-26 20:20 UTC. Session clock at start: 2026-09-26 20:06:51 UTC.

## Verdict: EMPTY (0 chats, 0 answers recovered; 1 log file preserved)

The stopped k1h-glm job's output folder was found at
`/private/tmp/k1h-glm-iLDhRG` (cwd recorded by the 000-stop-k1h report).
Its output dir `O/` is empty: 0 files, 0 chats.jsonl lines, 0 answers.jsonl lines.
One log file `chats-log.txt` (14 lines, 499 bytes) was preserved into this folder.
No `answers.jsonl`, no `answer-log.txt` exists there. Nothing was read or quoted.

## Duplicate guard

- 2026-09-26 20:06:51 UTC: `git fetch -q origin main builder-outbox` exit 0.
- `git ls-tree -r --name-only origin/main -- artifacts/claude-k1h-20260926/glm-v1`: 0 lines.
- `git ls-tree -r --name-only origin/builder-outbox -- artifacts/claude-k1h-20260926/glm-v1`: 0 lines.
- Guard result: PASS (not a duplicate).

## 1. Process wait

- Check 2026-09-26 20:07:04 UTC: `ps -axo pid,etime,command` filtered for
  `claude_k1h_glm.py` excluding the wrapper matched 0 processes (filtered_exit 1).
- Unfiltered grep matched only this salvage task's own `opencode run` wrapper
  (PID 36288), whose `--title` embeds the task text including the script name.
  That is not the k1h-glm job (no python process, no `scripts/claude_k1h_glm.py`
  in its command beyond the title text).
- Re-check 2026-09-26 20:16:40 UTC: same, only the own wrapper (PID 36288).
- Action: no process killed, nothing else touched. Wait time needed: 0 minutes
  (no live job process at first check). No 20-minute kill path taken.

## 2. Output-folder search (counts, sizes, sha256 only)

Search roots: /tmp, /private/tmp, /private/var/folders, worktree
(card-experiment-handoff-7c5b27). Criterion: file named `chats.jsonl` or
`answers.jsonl` modified after 2026-09-26 19:39 UTC whose folder or a parent
folder up to 3 levels also holds `scripts/claude_k1h_glm.py`. Also looked for
`chats-log.txt` and `answer-log.txt` in the same folder.

- Full-name searches (no time filter, all depths reachable):
  - /private/var/folders for `chats.jsonl`/`answers.jsonl`: 0 paths.
  - /private/tmp for `chats.jsonl`/`answers.jsonl`: 0 paths.
  - worktree for `chats.jsonl`/`answers.jsonl`/`chats-log.txt`/`answer-log.txt`: 0 paths.
  - all worktrees + main repo (maxdepth 4) for `chats.jsonl`/`answers.jsonl`: 0 paths.
  - /private/var/folders + /private/tmp for `chats-log.txt`/`answer-log.txt`: 1 path (below).
- Source folder found: `/private/tmp/k1h-glm-iLDhRG`
  - Holds `scripts/claude_k1h_glm.py` (11374 bytes per origin/main; local copy
    present at 15:39 EDT). Qualifies as the job tree.
  - `O/` (output dir): 0 entries besides `.`/`..`; size 64 bytes (dir);
    mtime 2026-09-26 15:40:07 EDT (19:40:07 UTC).
  - `chats.jsonl` in source tree: 0 files.
  - `answers.jsonl` in source tree: 0 files.
  - `answer-log.txt` in source tree: 0 files.
  - `chats-log.txt`: 1 file:
    - path: /private/tmp/k1h-glm-iLDhRG/chats-log.txt
    - size: 499 bytes
    - lines (`wc -l`): 14
    - mtime: 2026-09-26 16:04:41 EDT (20:04:41 UTC; after the 19:39 UTC cutoff)
    - sha256: e7372a49c1a603c7647251127abf6977b25ee27c4ff2c5ae17fb78ccda5313cd
- Folder count holding candidates: 1 (`/private/tmp/k1h-glm-iLDhRG`).
  Result: NOT ambiguous (single folder; zero jsonl candidates, one log candidate).
- The `artifacts/claude-k1e-20260926/train/items.jsonl` (70445 bytes) inside the
  source tree is job INPUT (`--existing`), not output; not copied per task
  (only the 4 named output files qualify).

## 3. Copy record

Destination: `artifacts/claude-k1h-20260926/glm-v1/` (artifacts/ is git-ignored;
force-add used).

| file | copied | src bytes | dst bytes | src lines | sha256 match |
| --- | --- | --- | --- | --- | --- |
| chats.jsonl | no (0 exist) | 0 | 0 | 0 | n/a |
| answers.jsonl | no (0 exist) | 0 | 0 | 0 | n/a |
| chats-log.txt | yes | 499 | 499 | 14 | yes (e7372a49c1a603c7647251127abf6977b25ee27c4ff2c5ae17fb78ccda5313cd) |
| answer-log.txt | no (0 exist) | 0 | 0 | 0 | n/a |

- Copy time: 2026-09-26 20:17:22 UTC (`cp -p`).
- .jsonl parse stats: 0 files, so lines-total 0, lines-parse-as-JSON 0,
  lines-that-don't 0. answers.jsonl non-empty-`answer` count: n/a (no file).
- No chat, answer, transcript, or key material was opened, printed, or quoted
  at any step (counts, sizes, sha256 only).

## 4. Session count

- `opencode session list -n 1000 | wc -l` at 2026-09-26 20:17:25 UTC: 9 (count only).

## 5. Times (from `date -u`)

- fetch + start: 2026-09-26 20:06:51 UTC
- first ps check: 2026-09-26 20:07:04 UTC
- re-check ps + searches: 2026-09-26 20:16:30 UTC, 20:16:40 UTC
- source stat: 2026-09-26 20:17:20 UTC
- copy verify: 2026-09-26 20:17:22 UTC
- session count: 2026-09-26 20:17:25 UTC

## 6. Every deviation

1. Naive `ps ... | grep claude_k1h_glm.py` matches this salvage task's own
   wrapper (PID 36288) because the task text is in its `--title`. Filtered
   check (excluding the wrapper) yields 0 job processes. No kill performed.
2. At ~20:07-20:12 UTC a second tree holding `scripts/claude_k1h_glm.py` was
   observed at `/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.oSZKfdQy6j`;
   a name search inside it found 0 target files; by ~20:13 UTC the directory
   no longer existed (removed externally). Nothing was copied from it.
3. A temporary script copy I made via `git show origin/main:...` to /tmp for
   output-path inspection was deleted immediately after use and excluded from
   all candidate counts.
4. Zero `chats.jsonl`/`answers.jsonl` exist in any searched root regardless of
   mtime, so the post-cutoff time filter changes nothing; kept rows = 0.
5. Prior art agrees: origin/main commit `5c1da5817` notes the earlier 000-stop-k1h
   salvage found the output folder empty (0 chats, 0 answers); k1h ADDENDUM-2
   (`7f0d11c51`) notes the first launch made 0 chats/0 answers.
6. Constraints kept: additive only; fictional names only (none introduced);
   no secrets; nothing written to repo-root notebook/; no opencode config, auth,
   or key file was read or printed; GPU: no (Mac CPU; file copies only; no GLM
   call; sole opencode call is the session-count above).
7. Task header timestamp (20:20 UTC) is later than this session's clock
   (20:06-20:17 UTC); treated as header metadata, not a blocker.
