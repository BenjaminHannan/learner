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


RESUME CONTEXT (director, 2026-09-22 20:50): the previous builder for this exact task was killed at about 20:40 by an app restart (not by any task problem), right after it wrote artifacts/claude-earcheck261-20260922/theta.json (20:39). Nothing is sealed yet in that folder. Your scripts are scripts/claude_earcheck261_*.py. The panel folder artifacts/claude-earpanel261-20260922/ IS sealed (verified 2/2 OK at 20:12), so the 60-minute panel wait will end at once after your own seal. The previous builder's llama-server (PID 13444, started 20:17, port 8081, Qwen3.8-27B) is still running on BensPC: check it with a /health request and reuse it; if it is unhealthy, stop exactly PID 13444 and start a fresh one. The ear model files on BensPC are unchanged.

YOUR TASK: the builder for exp 261 (the ear with an entailment checker).
Read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/261-earcheck.txt and follow it exactly. It is your whole task. The shared panel schema is in /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/earpanel261-spec.txt (read the spec only; never open the panel folder before your own seal).
Help for the BensPC side (read-only references; never edit them):
- 257's code: scripts/claude_smolear257_*.py (infer, table, tau, score, armb, panel, devset). Its artifacts: artifacts/claude-smolear257-20260922/ (PASSMARKS.md, RESULTS.md, dev/, run/). These show exactly how 257 ran the v4.1 ear on BensPC over ssh (ssh benspc), how it read predictions back, and how it scored. Reuse by import or by calling them; put all new code in new files.
- The earpanel257 panel is TEST-ONLY. You may run it only once, at the very end, report-only, exactly as the brief says.
- If llama-server does not start, or the model file is missing, or VRAM spills and a lower -ngl does not fix it, stop and report. Do not download or install anything.
- Waiting for the panel: poll for artifacts/claude-earpanel261-20260922/SEAL.sha256.txt every 2 minutes with a bash sleep loop, up to 60 minutes after your own seal.
- Before your final reply, stop llama-server by its exact PID and confirm with nvidia-smi that the GPU memory is released.
