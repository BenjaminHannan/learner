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


YOUR TASK: builder for exp 282b, the one follow-up to 282's registered FAIL (small talk by vocabulary, not word order). CPU only.
Never use git log or older versions of any file. Never open artifacts/claude-smallpanel282-20260923/ or any other panel, and never read 282's run/ panel files.
Read: the section "282 ruling and the 282b follow-up" of design/v3/30-modes/280-282-chat-fixes.md (git show origin/main:...), and in this worktree artifacts/claude-small282-20260923/PASSMARKS.md and scripts/claude_*282*.py (read-only; import them), plus artifacts/claude-chatweak-20260923/WEAKSPOTS.md (dev material).
Base: 282 (scripts/claude_loop282_agent.py + its config). One change: one outermost mixin scripts/claude_fix282b_vocab.py in scripts/claude_loop282b_agent.py; the vocabulary is a sealed list inside that file. Artifacts: artifacts/claude-small282b-20260923/. Ledger P282b.n (append only). New files only.
Order: (1) write 60+ dev turns in your own wording (greetings and closings with slang, typos in filler words, extra words and emoji; mixed turns; controls); (2) build and pilot on dev, the frozen suites vs 282's rows (fable_suitediff218 --only rt136,rt143,sessions152,bench) and the verifier probes; (3) PASSMARKS with numbered predictions and every predicted move. M1's denominator is the PANEL WRITER'S greeting and closing categories, never your matcher. Before sealing, run your panel runner and scorer end to end on a mock panel in exactly this schema: one row per turn {dialog_id, turn_index, user_text, category, gold}, categories greeting / closing / mixed / control; the runner must also accept a key named `user` for the text and must stop with an error if any turn text is empty; seal; ledger; (4) then wait for artifacts/claude-smallpanel282b-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min), check it OK, run it ONCE per arm (282 and 282b), and run smalltalkpanel234 once per arm as M3. After the seal never change a sealed file; if a sealed script breaks, stop and report.
Scoring: mechanical counts per category, 282 beside 282b; list the changed replies' file path.
Finish with RESULTS.md (result first, integer counts, categories only, never quote panel items) and your final reply.
PUSH: artifacts/claude-small282b-20260923 scripts/claude_fix282b_vocab.py scripts/claude_loop282b_agent.py scripts/claude_small282b_* scripts/claude_282b_* scripts/claude_282_runall.sh scripts/claude_282_panelrun.sh artifacts/fable-predictions-ledger.md
