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

GETTING YOUR FILES: git fetch -q origin main; read files with git show origin/main:<path>.
GPU: yes

YOUR TASK: builder for exp 265. Read design/v3/30-modes/265-our-ask.md (the one change) and design/v3/30-modes/our-policy-decision-20260923.md. Reuse 261b exactly as the 264 task describes (read handoff/queue/264-build.md for the BensPC and arm setup), but the only change is the canonicaliser/ask rule. New files: scripts/claude_ear265_*.py, artifacts/claude-ear265-20260923/, ledger lines P265.n.
Arms: A (261b A + the 265 rule), A261b (261b A exactly), B (138i+228).
Dev first (never any panel): 40+ own dev turns across group_owner/mixed/first_person/named. Then PASSMARKS with predictions, seal, ledger. Then wait for artifacts/claude-ourpanel265-20260923/SEAL.sha256.txt (poll every 2 min, up to 120 min), check OK, and run each arm ONCE.
Marks, arm A: M1 group_owner: 0 group-owned facts saved, and >= 27/30 turns ask whose; M2 mixed: >= 12/15 turns exactly right (other fact saved, no group fact); M3 first_person: 0 lost vs A261b; M4 named: 15/15 byte-identical to A261b; M5 0 wrong saves overall besides those A261b already makes. Report per-fact and per-turn wrong saves.
Stop llama-server by exact PID at the end. RESULTS.md (categories only, never quote items), then your final reply.
PUSH: artifacts/claude-ear265-20260923 scripts/claude_ear265_*.py artifacts/fable-predictions-ledger.md
