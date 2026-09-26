COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.

YOUR TASK: STOP (not destroy) the Director's reader depot (director, 2026-09-26 19:05 UTC; the Director created it; the Thread manager asked to cut spend; stopping ends the GPU charge and keeps the disk for a small storage fee).
1. Report where the readers live on the Mac: `shasum -a 256 ~/premonition-models/lis319f-merged/model.safetensors` (expected 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b) and the path of lis319-merged/model.safetensors. Stop the depot either way.
2. vast (key only via $(cat ~/.config/vastai/vast_api_key), never printed): find the ONE instance labelled exactly claude-director-depot (expected id 52755827). `vastai stop instance <id>`; confirm its status is stopped/exited, NOT destroyed. Record start time, dph, hours, cost so far, and the storage cost per hour and per day while stopped (from `vastai show instance <id> --raw`). Touch no other instance.
Write artifacts/claude-stop-depot-20260926/REPORT.md and append a ledger line with `cat >> artifacts/fable-predictions-ledger.md`: "- 2026-09-26 <time> UTC depot 52755827 STOPPED (disk kept); <h> h x $<dph> = $<cost>; storage $<x>/day."
PUSH: artifacts/claude-stop-depot-20260926/REPORT.md artifacts/fable-predictions-ledger.md
DISK: 0
