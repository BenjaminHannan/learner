COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
GPU: no (Mac CPU; about 20 GLM calls through opencode).

YOUR TASK: GLM helper v1.1 (director, 2026-09-26 20:05 UTC). The 000-glm-throughput report found that scripts/claude_glm_opencode.py (sha 3b597086) never deletes its sessions: it lists and deletes with cwd = its temp dir, but opencode files new sessions under the enclosing git worktree project, so its before/after diff is always empty (150 calls left 150 sessions).
Never read or print opencode config, auth or key files.
1. Do NOT edit scripts/claude_glm_opencode.py (owners sealed against it). Create a NEW file scripts/claude_glm_opencode_v11.py with the same interface: call(text, model=MODEL, timeout=300) -> str, and --selftest.
2. Fix: each call must delete exactly the session it created and no other, even when 16 calls run in parallel from other processes. Prefer taking the created session id from the run itself (check `opencode run --help` for a JSON or session-id output option, or a --title option you can set to a unique uuid and then find by that title). Only if neither exists, fall back to listing sessions in the project where they are actually filed and matching a unique uuid title; never a plain before/after diff (under parallel load it would delete other callers' sessions). Reply text must be the same as v1 returns (strip chrome only).
3. Test: selftest; then 16 calls in parallel (fictional prompts). Report session count (`session list -n 1000`) before and after: after must equal before. Report the sha256 of the new file.
3b. Two-process test: start two separate python processes at the same moment, each making 4 calls; each records the session ids it created. After both finish, show that each process deleted only its own ids and that, mid-run, the other's live sessions were still present (list between calls). Name the mechanism used (id from run output, or unique title) in the report.
3c. Report v1 as measured in 000-glm-throughput: its cleanup deleted nothing (empty diff), so it never cross-deleted, but it leaks one session per call.
4. Put a docstring line: "v1.1 (2026-09-26): deletes exactly its own session; v1 sha 3b597086 leaked sessions".
Write artifacts/claude-glm-helper-v11-20260926/REPORT.md.
PUSH: scripts/claude_glm_opencode_v11.py artifacts/claude-glm-helper-v11-20260926/REPORT.md
DISK: 0
