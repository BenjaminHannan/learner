COMMON RULES (the director, Claude, wrote this task on 2026-09-22). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.


GETTING YOUR FILES: run git fetch -q origin main and read each named file with git show origin/main:<path>. Never check out or merge that branch.


YOUR TASK: independent judge for F1's M4 (naturalness, talking line). You judge; you build nothing. CPU only, GPU: no.
Read ONLY artifacts/claude-gradef1-20260923/pairs.jsonl (13 pairs; each row is {"pair_id", "X", "Y"}: two replies a chat assistant could give at the same point in a conversation) and handoff/kit/briefs/241b-stylesheet.txt (sha256 16bdf0cf0403bce26886ea345f1ea44242e54537380f0ab3b8c7ed40f2dad8ef; stop if it differs), via git show origin/main:<path>. Never open anything under artifacts/claude-f1-20260923, any key file or any script: you must not know which reply comes from which system.
For each pair: which reply would a careful person rather receive in a friendly conversation (X, Y or tie), and do X and Y say different facts (meaning_change true/false)? Read every pair yourself.
Write artifacts/claude-judgef1-20260923/m4-judgments.jsonl: {"pair_id", "pick": "X"|"Y"|"tie", "meaning_change": bool, "note": short reason}, one line per pair, 13 lines.
Report: counts of X, Y, tie and meaning_change true, with the ids of every meaning_change.
PUSH: artifacts/claude-judgef1-20260923/m4-judgments.jsonl
