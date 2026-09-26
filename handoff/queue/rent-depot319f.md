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



GPU: rent
DISK: 0
BUDGET: $0 (rents nothing; uploads to the existing claude-director-depot, instance 52755827)
YOUR TASK: add the lis-319f reader to the depot (director, 15:20 UTC 09-26; Reading facts: lis-319f passed). Never stop, destroy or change anything else on any instance; key only via $(cat ~/.config/vastai/vast_api_key), never printed.
1. On the Mac: `shasum -a 256 ~/premonition-models/lis319f-merged/model.safetensors` must equal 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b, else stop with SRC-MISMATCH.
2. Confirm instance 52755827 is running and labelled claude-director-depot. `rsync -a --partial -e "ssh -p 35826" ~/premonition-models/lis319f-merged/ root@ssh3.vast.ai:/root/reader319f/` (retry on drop, up to 3 h). Never touch /root/reader319.
3. On the depot `sha256sum /root/reader319f/model.safetensors` must equal 970ef0ac...; report it, the file list, and transfer time.
Write artifacts/claude-depot319f-20260926/REPORT.md. Append a ledger line.
PUSH: artifacts/claude-depot319f-20260926/REPORT.md
