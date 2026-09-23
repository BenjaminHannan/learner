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


YOUR TASK: builder for exp 280b, the one follow-up to 280's registered FAIL. CPU only.
Read: the "280b" section of design/v3/30-modes/280-282-chat-fixes.md (git show origin/main:...), and in this worktree artifacts/claude-capab280-20260923/PASSMARKS.md, RESULTS.md and scripts/claude_*280*.py (read-only; import them).
Base: 280 (scripts/claude_loop280_agent.py + its config). One change: one outermost mixin scripts/claude_fix280b_general.py in scripts/claude_loop280b_agent.py. Artifacts: artifacts/claude-capab280b-20260923/. Ledger P280b.n (append only). New files only.
Order: (1) write 60+ dev turns in your own wording (general ability questions, "can you X" turns, near-misses about people's abilities, controls); never model them on any panel; (2) build and pilot on dev, the frozen suites vs 280's rows and the verifier probes; (3) PASSMARKS with numbered predictions and every predicted move; seal; ledger; (4) then wait for artifacts/claude-capabilpanel280b-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min), check it OK, and run it ONCE per arm (280 and 280b); re-run capabilpanel280 once on 280b (report only).
Process rules learned from 280: before sealing, run your panel runner and scorer end to end on a mock panel in the exact schema the spec describes (dialog_id, turn_index, last turn scored). After the seal, never change any sealed file. If a sealed script breaks, stop and report it; do not fix it and continue.
Scoring: mechanical counts per category. Leave the truth check of claims to the director and list the reply file paths.
PUSH: artifacts/claude-capab280b-20260923 scripts/claude_fix280b_general.py scripts/claude_loop280b_agent.py scripts/claude_capab280b_* artifacts/fable-predictions-ledger.md
