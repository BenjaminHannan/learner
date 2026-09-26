Probing GLM 5.3 Flash via opencode — verifying access and concurrency limits.
The brief file is missing — I'll proceed under the task's stated rules and note the deviation in the report.
Reference shape confirmed. Starting opencode probes.
Steps 1–2 confirmed. Running the single-call probe.
Single call works (exit 0, 41s, output "ok"). Finding and deleting its session.
Sessions are per-directory — my session is isolated to the temp dir. Deleting it.
Step 3 complete. Starting parallel level 2.
Level 2: 2/2 ok in 42s. Cleaning sessions, then level 4.
Level 4: 4/4 ok in 6s. Cleaning, then level 8.
All 4 deleted, bucket empty. Verifying worktree sessions untouched, then level 8.
The `rm -rf` tripped a shell policy. Retrying without it.
Level 8: 8/8 ok in 99s. Deleting all 8 sessions.
All sessions cleaned. Checking disk and writing the helper.
Selftest passes. Verifying no leftover sessions and hashing the helper.
All green. Writing the report.
Probe complete. Report for the director:

**1. Model id** — `/usr/local/bin/opencode models | grep -i glm` returns 4 lines (`glm-5.1`, `glm-5.2`, `glm-5.3`, `glm-5.3-flash`). `opencode-go/glm-5.3-flash` confirmed, matching the watcher's rungo.

**2. Session flags** — List: `opencode session list` (`-n/--max-count`, `--format table|json`). Delete: `opencode session delete <sessionID>`. `run` has **no flag that skips saving a session** (full flag list recorded in REPORT.md). Discovery: `session list` from a plain temp dir returns a shared bucket; from this worktree it returns a separate bucket of 11 other-agent sessions, never touched.

**3. Single call** — `opencode run --model opencode-go/glm-5.3-flash "Reply with the word ok" < /dev/null` in a fresh temp dir: exit 0, wall 41s, stdout `ok\n` (3 bytes). Session deleted, confirmed gone (bucket empty).

**4. Parallel** — 2/2 ok in 42s; 4/4 ok in 6s; 8/8 ok in 99s. Zero errors at every level, so all three levels ran. Every run exited 0 with stdout `ok`. All 15 probe sessions deleted, 0 remaining. One operational error in level-4 cleanup (zsh passed 4 IDs as one argument → `Error: Session not found: <4 ids>` verbatim); recovered, all deleted individually.

**5. Helper** — `scripts/claude_glm_opencode.py`: `call(text, model="opencode-go/glm-5.3-flash", timeout=300) -> str`, no key argument. Private temp dir, stdin /dev/null, ANSI/chrome stripped, 3 tries on nonzero exit, snapshot-diff session cleanup (parallel-safe), never touches config/auth. `--selftest` → `selftest ok`, exit 0, 6s. sha256 `3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2` (4081 bytes). Reference `scripts/claude_lis320_glm.py` is absent from this worktree; shape taken read-only from git history (commit 9390fb15d).

Full numbers, commands, and errors verbatim in `artifacts/claude-glm-opencode-20260926/REPORT.md`.

**Deviations:** (a) The brief `scratchpad/briefs/OPUS-RULES.txt` does not exist (empty dir) — proceeded under the task-stated rules. (b) PUSH not executed: this shell denies `git push*`, and `artifacts/` is gitignored (`.gitignore:5`), so REPORT.md exists on disk but is unpushable; `scripts/claude_glm_opencode.py` is written, untracked, ready. Nothing else created, edited, or deleted. Disk 54GB free. $0 spent.
