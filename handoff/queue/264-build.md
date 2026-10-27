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
GPU: yes

YOUR TASK: builder for exp 264, the question-answering checker. Read design/v3/30-modes/264-qa-checker.md (the one change, exact prompts and save rule) and handoff/kit/briefs/261-earcheck.txt (BensPC, llama-server, ear, arms). In this worktree read artifacts/claude-earcheck261b-20260923/PASSMARKS.md + RESULTS.md and scripts/claude_earcheck261_*.py + scripts/claude_earcheck261b_*.py (read-only; import, never edit). New files only: scripts/claude_earcheck264_*.py, artifacts/claude-earcheck264-20260923/, ledger lines P264.n.
Arms: A (registered: 261b's A with the YES/NO checker replaced by the QA checker), A261b (261b's A exactly), A_brake, B (138i + 228). All scored with 261b's scorer (Ruling 1 included), in a new wrapper that also reports wrong saves per saved fact and per turn.
Before the seal (dev only, never any panel): (1) reproduce 261b's dev numbers from its sealed files; (2) run the QA checker on 261's dev + 261b's dev; report holds, false holds and wrong saves let through, by tag. Also write 30+ own dev turns with wrong-relation traps and stale values, and report on them. Debug the prompt wording on dev only; log every change. (3) Measure latency; the three questions may be sent one after another. (4) PASSMARKS.md with numbered predictions P264.n, seal, append ledger lines.
Registered test: artifacts/claude-earpanel264-20260923/ (written in parallel by a blind writer). Never open it before your seal. After your seal, poll for its SEAL.sha256.txt every 2 min for up to 120 min, check it OK from the repo root, run the strict schema check, then run every arm ONCE. Never run earpanel257/261/261b.
Marks, arm A: M1 no_save saves <= 1; M2 wrong saves <= 1; M3 exact TEACH recall >= 85% and >= B+30; M3b held back <= 12% of gold TEACH; M4 ASK >= 90%; M5 median per turn <= 800 ms (report p90/max); M6 every A frame byte-identical in A_brake. Also report (no bars): per-fact and per-turn wrong-save rates for every arm, per family, per tag (R1-R17), and each held or wrong frame by category only.
Compute: BensPC via ssh benspc exactly as 261/261b did (the llama-server launch that worked in 261b: detached via Win32_Process). Stop it by exact PID at the end and confirm with nvidia-smi. Never touch pythonw 13036. Check Mac load before Mac-side arms. Waves under 30 min.
RESULTS.md laid out like 261b's (result first, integer counts, categories only, never quote panel items), then your final reply.
PUSH: artifacts/claude-earcheck264-20260923 scripts/claude_earcheck264_*.py artifacts/fable-predictions-ledger.md
