# GLM 5.3 Flash via opencode — probe report 2026-09-26

Worktree: `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
All commands run from there. GPU: none used (Mac CPU; opencode network calls only; $0 spent).

## 0. Pre-checks

- `uptime`: load averages 133.35 116.31 84.69 (high but proceeded; all calls succeeded).
- `df -g /`: 460G total, 12G used, 55G available at start (54G at end). Above the 3 GB stop line throughout.
- At most 4 parallel processes used for shell plumbing; opencode concurrency per task levels only (2/4/8).
- No opencode config, auth file or key was read, printed, copied or committed at any point.
- No TEST-ONLY panels involved. No rentals. No secrets. Fictional names only (none needed).

## 1. Model id

Command: `/usr/local/bin/opencode models | grep -i glm` (opencode 1.18.32). Output, 4 lines:

```
opencode-go/glm-5.1
opencode-go/glm-5.2
opencode-go/glm-5.3
opencode-go/glm-5.3-flash
```

`opencode-go/glm-5.3-flash` confirmed present — same id as the watcher's rungo.

## 2. Session flags

- `/usr/local/bin/opencode session --help` → subcommands `session list` and `session delete <sessionID>` only.
- `session list` flags: `-n/--max-count` (limit to N most recent), `--format table|json` (default table).
- `session delete` takes one required positional: the session ID.
- `/usr/local/bin/opencode run --help` full flag list: `--command, -c/--continue, -s/--session,
  --fork, --share, -m/--model, --agent, --format (default|json), -f/--file, --title,
  --attach, -p/--password, -u/--username, --dir, --port, --variant, --thinking,
  -i/--interactive, --auto` (+ global `--print-logs, --log-level, --pure`).
- Finding: **no flag skips saving a session**. Every `run` creates one; deletion is manual.
- Scoping discovery: `session list` run from a plain temp dir returns a shared bucket of
  unscoped sessions; run from this git worktree it returns the worktree bucket (11 sessions,
  all other agents' `mimo:`-titled sessions, never touched). Session objects carry
  `projectId: "global"` plus a `directory` field. All probe sessions were identified by their
  temp-dir paths and deleted by explicit ID only.

## 3. Single call

Command (fresh empty temp dir): `/usr/local/bin/opencode run --model opencode-go/glm-5.3-flash
"Reply with the word ok" < /dev/null`

- Exit code: 0. Wall time: 41 s.
- stdout (3 bytes, first 200 chars): `ok\n` (repr: `'ok\n'`, OUTLEN=3).
- stderr first line: empty ANSI reset only (opencode chrome on stderr, not stdout).
- Session `ses_f20efc4ceffeBRM3bzFBWSKuAy` created, deleted via
  `opencode session delete <id>` (exit 0, "Session ... deleted"), confirmed gone
  (temp-dir `session list --format json` returned empty; worktree bucket unchanged at 11).

## 4. Parallel levels (same call, each in its own temp dir)

| Level | Success | Errors | Wall time |
|-------|---------|--------|-----------|
| 2     | 2/2     | 0      | 42 s      |
| 4     | 4/4     | 0      | 6 s       |
| 8     | 8/8     | 0      | 99 s      |

- Every run exited 0 with stdout `ok` (3 bytes). No error output beyond the ANSI line;
  there were no first-error-lines to quote because there were no errors.
- No level had any error, so all three levels ran; stopped at 8 per task (no higher level requested).
- Cleanup: every session deleted and confirmed via empty bucket list —
  level 2: 2 deleted; level 4: 4 deleted; level 8: 8 deleted.
- One operational error during level-4 cleanup (zsh passed 4 IDs as a single argument),
  recovered immediately, verbatim:

```
Error:  Session not found: ses_f20edf45affeZhTHzQjAFLtUJA ses_f20edf456ffe4WsE2Y4D0SVwRS ses_f20edf41fffeAzkPURmVTJLyec ses_f20edf44dffeM6wz6gELYcb03u
```

  All 4 were then deleted one ID per line (4/4 "deleted" confirmations, bucket empty).
- Worktree bucket observed at 11 → 10 → 11 across the run from other agents' concurrent
  activity; none of those sessions were listed for deletion or touched.

Totals: 15 probe calls (1+2+4+8), 15 successes, 0 failures; 15 probe sessions created,
15 deleted, 0 remaining.

## 5. Helper `scripts/claude_glm_opencode.py`

- `call(text, model="opencode-go/glm-5.3-flash", timeout=300) -> str`: prompt in, text out,
  no key argument (auth is the Mac's existing opencode setup, never read/modified).
- Runs one `opencode run --model <model> <text>` in a private temp dir with stdin /dev/null;
  strips ANSI/chrome from stdout; retries up to 3 times on nonzero exit (or empty reply);
  snapshots session IDs before/after each try and deletes only sessions it created
  (parallel-safe); raises RuntimeError after 3 failed tries.
- Reference shape: `scripts/claude_lis320_glm.py` does not exist in this worktree; the
  `call(key, model, text, temperature, tries=4) -> (text, usage)` shape was taken from git
  history (commit 9390fb15d) read-only.
- `--selftest`: one "Reply with the word ok" call; prints `selftest ok` when the reply
  contains "ok". Result: `selftest ok`, exit 0, wall 6 s (interpreter: /usr/local/bin/python3,
  stdlib only). Its session was auto-deleted (bucket empty afterwards).
- sha256: `3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2`
  (4081 bytes).

## Deviations / notes

1. The brief `.../scratchpad/briefs/OPUS-RULES.txt` does not exist (that scratchpad dir is
   empty); proceeded under the key points stated in the task itself (additive-only, no config
   access, append-only ledger untouched, integer counts, report-in-final-reply).
2. PUSH not executed: this shell denies `git push*` by policy, so `REPORT.md` and
   `claude_glm_opencode.py` are written in place, uncommitted, ready for the director.
   Nothing else in the repo was created, edited or deleted.
3. `rm -rf /tmp/...` is denied by shell policy; temp dirs were removed without `-f` where
   needed (level-8 dirs); no repo files affected.
