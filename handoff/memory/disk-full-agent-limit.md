---
name: disk-full-agent-limit
description: 2026-09-22 overnight agents filled the Mac disk (opencode.db 28→32 GB + 5 GB swap); all launches failed; kill agents by exact PID only
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T10:47:08.374Z
---

On 2026-09-22 ~05:50 the Mac disk hit 0 free. opencode.db grew 28 → 32 GB overnight (~2 GB/h with ~8 Muse agents), and swap reached 5.1/6 GB at load 40–200. Every `opencode run` then failed with rc=1 "Failed to execute statement". Claude deleted only its own scratch and file copies; Ben's opencode.db was left for him.

**Why:** free disk space, not the budget, was the real cap on agent width. Also, a `ps | grep 146 | kill` hit the merge agent 134, because its task text mentioned "146".

**How to apply:** check `df -h /` before every launch wave, and don't launch below ~5 GB free. NO agent cap (Ben 2026-09-22). Instead, rungo2 titles each run and deletes its opencode session when it ends, and diskguard.sh prunes stale sessions and runs incremental_vacuum. The DB was 30 GB of `event` rows from agent sessions; `opencode session delete <id>` removes them cleanly. Kill agents by the exact PID from `ps -p <pid> -o command=`, after confirming the task name, never by a loose grep. Related: [[mimo-skill]], [[director-role]].

**2026-09-22 09:54 follow-up:** "Failed to execute statement" also comes from DB LOCKS, not only a full disk. My diskguard's `PRAGMA wal_checkpoint(TRUNCATE)` (with .timeout 20000) held the writer lock while waiting for readers, and 2 live agents crashed. Now reclaim uses PASSIVE + `incremental_vacuum(256)` while agents run, and TRUNCATE only when idle. rungo2 treats a crashed run as done when its reply is > 300 bytes; use rungo3, which retries on that error.

**2026-09-22 13:46 follow-up (snapshots):** opencode also keeps a git "undo snapshot" store, ~/.local/share/opencode/snapshot/<project>/<worktree> (11 GB for this worktree). Every agent step runs `git add` over the whole worktree, about 50% CPU per agent, and at 9 agents the load was 30 on 10 cores. Fix, scoped to my headless runs only: `export OPENCODE_CONFIG_CONTENT='{"snapshot": false}'` in the launcher. This merges over the global config; check with `opencode debug config | grep '"snapshot"'`, never printing the rest (it holds keys). The global config is untouched. Deleting the existing store needs Ben's OK.
