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

YOUR TASK: builder for exp 264, the question-answering checker. Read design/v3/30-modes/264-qa-checker.md (the one change, exact prompts and save rule) and handoff/kit/briefs/261-earcheck.txt (BensPC, llama-server, ear, arms). In this worktree read artifacts/claude-earcheck261b-20260923/PASSMARKS.md + RESULTS.md and scripts/claude_earcheck261_*.py + scripts/claude_earcheck261b_*.py (read-only; import, never edit). New files only: scripts/claude_earcheck264_*.py, artifacts/claude-earcheck264-20260923/, ledger lines P264.n.
GPU: yes

YOUR TASK: builder for exp 270, ear line. The one change: a text normaliser in front of the ear on 263's base (263 = 260 + comma guard; see artifacts/claude-comma263-20260923/ and scripts/claude_loop263_agent.py, import never edit). Only when a turn has no capital letters at all (or no apostrophes where a possessive "Xs <relation>" pattern is present), restore name capitals and possessive apostrophes with a rule-based pass (an English common-word list plus names already in the notebook; words that are common English stay lowercase), then hand the fixed text to the unchanged ear. Clean turns must pass through byte-identical.
Dev only before the seal: your own 60+ casual turns and 20+ traps (no panels). Report every rewrite. PASSMARKS.md with P270.n, seal, ledger.
Registered test: artifacts/claude-typepanel270-20260923/ (blind writer). Never open before your seal; poll up to 120 min; check seal; run each arm ONCE.
Arms: A (263 + normaliser), A263 (263 exactly). Marks, arm A: M1 casual exact TEACH >= 30/40 and >= A263+20; M2 casual_q ASK >= 12/15; M3 lower_trap wrong saves <= 1; M4 clean 30/30 byte-identical replies to A263; M5 0 new wrong saves vs A263 overall; M6 median added time <= 20 ms.
Compute as 263 did (the ear on BensPC); stop anything you start by exact PID; never touch pythonw 13036.
PUSH: artifacts/claude-type270-20260923 scripts/claude_type270_*.py artifacts/fable-predictions-ledger.md
