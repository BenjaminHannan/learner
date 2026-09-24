COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the listener spec: design/v3/60-listener/frame-spec.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open or read items of any TEST-ONLY panel. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main` and `git archive origin/builder-outbox <path>`.
GPU: yes

YOUR TASK: lis-302-gpu, REPORT ONLY (no registered marks, no training, no panel). Two GPU measurements on BensPC for the listener thread, over lis-301's DEV readings (dev only; never any panel). Artifacts go in artifacts/claude-lis302-20260924/. The listener thread wrote the code. Run it and never edit it. If something breaks, stop and report the exact error.
Files: scripts/claude_lis302_tokprobs.py, artifacts/claude-lis302-20260924/checks.json (753 checker queries, already built), scripts/claude_earcheck261_checker.py (sealed exp-261 client, unchanged). Dev inputs are on origin/builder-outbox: artifacts/claude-lis301-20260923/dev/dev_rows.jsonl and dev_pred.jsonl.
1. TOKEN PROBS (about 5 min). Use the lis-301 merged reader on BensPC (C:/Users/benja/lis301/work/run/merged; check its safetensors sha256 = b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890) and the lis-301 venv:
   python scripts/claude_lis302_tokprobs.py --model <merged> --rows dev_rows.jsonl --pred dev_pred.jsonl --out artifacts/claude-lis302-20260924/tokprobs.jsonl
   Then free the GPU (the process exits).
2. EXP-261 CHECKER PASS. Check `curl -s http://127.0.0.1:8081/health` on BensPC. If llama-server is not already up, start it yourself exactly as in handoff/kit/briefs/261-earcheck.txt line 44 (C:\llama-b10679\llama-server.exe, model C:\Users\benja\.lmstudio\models\Qwen3.8-27B\Qwen3.8-27B-UD-IQ4_XS.gguf, --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 --cache-type-k q8_0 --cache-type-v q8_0 --parallel 1 -t 6), wait for /health ok, and record its PID. If the GGUF or exe is missing, skip this step and report it. Then run:
   python scripts/claude_earcheck261_checker.py --url http://127.0.0.1:8081 --in artifacts/claude-lis302-20260924/checks.json --out artifacts/claude-lis302-20260924/pyes.json
   Watch for VRAM spill (see the brief, line 48). If you started llama-server, stop it afterwards by its exact PID only.
3. RESULTS-gpu.md: counts only. Include:
   - rows done;
   - how many rows have check_minp differing from the recorded minimum conf by more than 0.01 (dev_pred's conf list; report the count);
   - the checker summary (n, fallbacks, median/p90/max ms);
   - the device;
   - whether you started or reused llama-server.
   Never print dev turns in bulk (a few examples in RESULTS-gpu.md are fine).
PUSH: artifacts/claude-lis302-20260924/tokprobs.jsonl artifacts/claude-lis302-20260924/pyes.json artifacts/claude-lis302-20260924/RESULTS-gpu.md
