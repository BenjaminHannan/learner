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


YOUR TASK: builder for exp 282 (casual greetings and closings). CPU only.
Read: the "282" section of design/v3/30-modes/280-282-chat-fixes.md (git show origin/main:design/v3/30-modes/280-282-chat-fixes.md): the one change, marks and panel spec. Also handoff/kit/briefs/260-openers.txt (how 260 was built, run and scored; copy its structure), artifacts/claude-openers260-20260922/PASSMARKS.md and RESULTS.md, and artifacts/claude-chatweak-20260923/WEAKSPOTS.md + dialogs.json (dev material).
Base: 260 (scripts/claude_loop260_agent.py + its config). One change: one outermost mixin scripts/claude_fix282_small.py in scripts/claude_loop282_agent.py (SrcGuardMixin228 stays where 260 has it). Artifacts: artifacts/claude-small282-20260923/. Ledger lines P282.n appended to artifacts/fable-predictions-ledger.md. New files only.
Order: (1) reproduce the probe's failure on 260; (2) write 40+ dev dialogs in your own wording (never modelled on any panel); (3) build and pilot on dev, the frozen suites (fable_suitediff218 --only rt136,rt143,sessions152,bench against 260's rows) and the 138m verifier probes; (4) PASSMARKS.md with numbered predictions and every predicted move by id; seal (shasum -a 256 > SEAL.sha256.txt); append the ledger; (5) only then wait for artifacts/claude-smallpanel282-20260923/SEAL.sha256.txt (poll every 2 min, up to 120 min), check it OK from the worktree root, and run the panel ONCE on both arms (260 and 282), plus any extra registered run the note names.
Scoring: mechanical counts per category only (right, wrong, abstain, writes). Anything the note says the director grades (truth of claims, grammar), leave ungraded and list the changed replies' file path.
Finish with RESULTS.md (result first, integer counts, categories only, never quote panel items) and your final reply.
PUSH: artifacts/claude-small282-20260923 scripts/claude_fix282_small.py scripts/claude_loop282_agent.py scripts/claude_small282_* artifacts/fable-predictions-ledger.md
