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

YOUR TASK: builder for exp 269, the one follow-up to 265's registered FAIL. Read design/v3/30-modes/265-our-ask.md and artifacts/claude-ear265-20260923/RESULTS.md + PASSMARKS.md and scripts/claude_ear265_*.py (import, never edit).
The one change: on 265's arm A, add a text-level group-owner check that runs on the raw turn BEFORE the ear frame and the brake are used. If the turn states something owned or shared by we/us/our/ours (not "I/my", not a named person), reply with 265's fixed ask-whose line and save nothing from that turn; mixed turns (group fact + named/first-person fact) still save the non-group frames. Everything else is 265's arm A exactly.
Dev only before the seal: 265's dev set plus 40+ of your own new turns (owner word mid-sentence, "at ours", plural pronoun as subject of a non-ownership verb like "we think Ana is ..."). Report false asks. Then PASSMARKS.md with P269.n, seal, ledger lines.
Registered test: artifacts/claude-ourpanel269-20260923/ (blind writer, parallel). Never open it before your seal; poll for its SEAL up to 120 min; check it; run every arm ONCE. Never run ourpanel265.
Arms: A (265 A + the check), A265 (265 A exactly), A261b, B. Marks = 265's M1-M5, same bars; M6 false asks: asks on non_owner_we + first_person + named turns <= 1 in total; M7 gold facts lost on non_owner_we vs A265 <= 1; M8 0 new wrong saves vs A265 across all families. Dev must include 30+ of your own non-owner we/us/our turns.
Compute as 265 did (BensPC, detached llama-server, stop by exact PID, nvidia-smi idle, never touch pythonw 13036).
PUSH: artifacts/claude-ear269-20260923 scripts/claude_ear269_*.py artifacts/fable-predictions-ledger.md
