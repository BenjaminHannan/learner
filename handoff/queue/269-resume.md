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


GETTING YOUR FILES: git fetch -q origin main, then read each named file with git show origin/main:<path>.

YOUR TASK: resume exp 269's registered run ON A RENTED vast.ai GPU. BensPC is offline, and Ben said on 2026-09-23 09:24 UTC "you can just use cloud gpus for now". Do NOT change any sealed file.
0. RENTAL RULES (hard): read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Use the REST recipe in runs/rentcheck (builder-outbox). First GET /users/current/ and list /instances/: stop if any instance is already running. Check artifacts/*ledger* and the rental notes; the $30 total cap stands, and this job's hard ceiling is $2.00 and 3 hours. ON-DEMAND only: one GPU with 24 GB or more (e.g. RTX 4090/5090/3090), with the lowest price that has good reliability. Start a watchdog that destroys the instance at 3 hours no matter what. Verify copy-back BEFORE destroying; destroy at the end and confirm GET /instances/ is empty. Append a ledger line (date, instance type, hours, dollars).
1. Check seals from the repo root: artifacts/claude-ear269-20260923/SEAL.sha256.txt (15 OK) and artifacts/claude-ourpanel269-20260923/SEAL.sha256.txt (2 OK). Stop if either fails.
2. Weights: the ear checkpoint and Qwen GGUF used by 265/269 must come from the Mac (look where the 261b/265 scripts point; check the sha against the one the sealed files record). If the ear checkpoint is not on the Mac, stop and report BLOCKED (do not retrain anything). The Qwen GGUF may be fetched on the rental from the same Hugging Face repo and file as before (not a new model); verify its sha256 matches the one recorded. Never upload any file from notebook/.
3. Run llama-server on the rental with the same flags as 265/269, then the three unrun arms (A, A265, A261b) ONCE each on ourpanel269 with the sealed 269 scripts. Do not re-run arm B. Score with the sealed scorer (marks M1-M8 as sealed). Record that the hardware differs from BensPC, and report latency as information only.
4. Write RESULTS-resume.md (new file) in the same folder: verdict first, marks table, every move/miss, deviations, dollars spent.
PUSH: artifacts/claude-ear269-20260923 artifacts/fable-predictions-ledger.md
