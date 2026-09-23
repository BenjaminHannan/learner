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


GETTING YOUR FILES: run git fetch -q origin main and read each named file with git show origin/main:<path>. Never check out or merge that branch.


YOUR TASK: builder for exp 281b, the one follow-up to 281's registered FAIL (casual typing of called/named questions). CPU only.
Never use git log or older versions of any file. Never open artifacts/claude-calledpanel281-20260923/ (burned) or any other panel.
Read: the section "281 result and the 281b follow-up" of design/v3/30-modes/280-282-chat-fixes.md (git show origin/main:...), and in this worktree artifacts/claude-called281-20260923/PASSMARKS.md and scripts/claude_*281*.py (read-only; import them), plus artifacts/claude-chatweak-20260923/WEAKSPOTS.md (dev material).
Base: 281 (scripts/claude_loop281_agent.py + its config). One change: one outermost mixin scripts/claude_fix281b_casual.py in scripts/claude_loop281b_agent.py. Artifacts: artifacts/claude-called281b-20260923/. Ledger P281b.n (append only). New files only.
Order: (1) show the casual forms fail on 281 with your own dev turns; (2) write 50+ dev dialogs in your own wording (casual and formal called/named questions, never-taught versions, "called" belonging to a name, controls); (3) build and pilot on dev, the frozen suites vs 281's rows (fable_suitediff218 --only rt136,rt143,sessions152,bench) and the verifier probes; (4) PASSMARKS with numbered predictions and every predicted move; before sealing, run your panel runner and scorer end to end on a mock panel in exactly this schema: one row per turn {dialog_id, turn_index, user_text, category, gold}, categories teach_setup / stored_called / nostore_called / ambiguous_called / control_plain; the runner must also accept a key named `user` for the text; seal; ledger; (5) then wait for artifacts/claude-calledpanel281b-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min), check it OK, run it ONCE per arm (281 and 281b). After the seal never change a sealed file; if a sealed script breaks, stop and report.
Scoring: mechanical counts per category, including the teach-fail count on the 281 arm and the M1 denominator the note defines.
Finish with RESULTS.md (result first, integer counts, categories only, never quote panel items) and your final reply.
PUSH: artifacts/claude-called281b-20260923 scripts/claude_fix281b_casual.py scripts/claude_loop281b_agent.py scripts/claude_called281b_* scripts/claude_281b_* artifacts/fable-predictions-ledger.md
