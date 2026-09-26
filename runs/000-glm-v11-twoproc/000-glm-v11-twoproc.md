COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
GPU: no (Mac CPU; 8 GLM calls).

YOUR TASK: two-process isolation test for scripts/claude_glm_opencode_v11.py (director, 20:11 UTC 2026-09-26). Check its sha256 is 7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4; do not edit it. Never read or print opencode config, auth or key files.
Start two separate python processes at the same moment. Each makes 4 calls one after another (fictional prompts, "Reply with only the word <word>"), and before each call and after it records `opencode session list -n 1000 --format json` titles that start with glm11- (count and titles only). Mid-run, each process must see the other's live glm11- session at least once, or report that it never overlapped. At the end: 0 glm11- sessions remain, every reply returned, total session count before == after.
Write artifacts/claude-glm-v11-twoproc-20260926/REPORT.md (counts, overlaps seen, pass/fail).
PUSH: artifacts/claude-glm-v11-twoproc-20260926/REPORT.md
DISK: 0
