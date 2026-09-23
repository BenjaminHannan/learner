COMMON RULES (the director, Claude, wrote this task on 2026-09-22). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read handoff/kit/briefs/OPUS-RULES.txt (git show origin/main:handoff/kit/briefs/OPUS-RULES.txt). It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: the director works from GitHub. Run: git fetch -q origin main. Read each file named below that is not in your worktree with: git show origin/main:<path>. Never check out, merge or push main.

YOUR TASK: diagnosis only (reasoning line). No fix, no sealed experiment, no panel. CPU only. You may create new scratch/dev files and new scripts only.
Found by the director on 2026-09-23 with dialogs in his own wording (fictional names), on BOTH 138n and the 221 arm: after "Kim Varro's spouse is Dana Holt." then "Dana Holt's spouse is Ravi Stone.", the question "Whose spouse is Dana Holt?" (also "Who is married to Dana Holt?", "Whose wife/husband is Dana Holt?") gets "Dana Holt's spouse is Ravi Stone." That is a wrong answer (gold: Kim Varro), from stage loop138-nhop. The same thing happens with author/founder chains ("What has Dana Holt written?" gives "Dana Holt's author is Ravi Stone."). Base to study: 138n = scripts/claude_loop138n_agent.py + artifacts/claude-merge138n-20260922/loop138n-config.json.
Do: (1) reproduce it with 30+ dialogs of your own (spouse, author, founder, boss, mother, friend; chain vs no chain; 1 and 2 subjects); record the stage for every reply; (2) find in code why loop138-nhop answers a backwards question with a forward fact about the value (file:line); (3) say which relations are affected (symmetric ones like spouse vs one-way ones), and whether a stored fact could be misreported or only the reply is wrong; (4) propose ONE change that fixes it, with pass marks and the result that would prove it wrong. Do not build it.
Output: artifacts/claude-nhopdiag-20260923/DIAG.md (+ your dev dialogs and the raw replies JSON). Final reply: the cause (file:line), counts, and the proposed one change.
PUSH: artifacts/claude-nhopdiag-20260923
