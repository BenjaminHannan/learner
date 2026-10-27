COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
GPU: no (Mac CPU; opencode network calls only; $0 beyond Ben's opencode subscription, which Ben offered at 18:47 UTC 09-26).

YOUR TASK: probe GLM 5.3 Flash through the Mac's opencode, then write one shared helper (director, 2026-09-26 18:55 UTC). Never read, print, copy or commit any opencode config, auth file or key. Rent nothing.
1. `/usr/local/bin/opencode models | grep -i glm` (model names only). The watcher's rungo already uses `opencode-go/glm-5.3-flash`; confirm that id.
2. `/usr/local/bin/opencode session --help` and `/usr/local/bin/opencode run --help` (flags only). Find how to list and delete a session, and whether `run` has a flag that skips saving one.
3. One call: in a fresh empty temp dir, `/usr/local/bin/opencode run --model opencode-go/glm-5.3-flash "Reply with the word ok" < /dev/null`. Record the output (first 200 chars), wall time, and exit code. Then delete that session (step 2's command) and confirm it is gone.
4. Parallel: 2, 4, then 8 of the same call at once (each in its own temp dir). Record success count, errors (first line of each), and wall time per level. Stop raising at the first level with any error. Delete every session made.
5. If steps 3-4 work, write scripts/claude_glm_opencode.py: `call(text, model="opencode-go/glm-5.3-flash", timeout=300) -> str`, the same prompt-in, text-out shape as `call()` in scripts/claude_lis320_glm.py but with no key argument. It runs one `opencode run` in a private temp dir with stdin /dev/null, returns stdout text stripped of any opencode chrome, retries up to 3 times on nonzero exit, always deletes its session afterwards, and never touches config or auth files. Add `--selftest`, which makes one "Reply with the word ok" call and prints `selftest ok` when the reply contains "ok". Run the selftest.
Write artifacts/claude-glm-opencode-20260926/REPORT.md with 1-5 (numbers, commands used, errors verbatim, the helper's sha256).
PUSH: artifacts/claude-glm-opencode-20260926/REPORT.md scripts/claude_glm_opencode.py
DISK: 0
