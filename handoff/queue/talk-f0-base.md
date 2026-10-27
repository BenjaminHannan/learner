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


YOUR TASK: baseline run of the conversation benchmark convbench-f0 on the main base 292 (step F0 of design/v3/30-modes/talk-fluency-plan.md). CPU only. No agent code changes.
Read: design/v3/30-modes/talk-fluency-plan.md (git show origin/main:...) and, in this worktree, scripts/claude_loop292_agent.py (build_agent292, DEFAULT_CONFIG292), read-only. Never use git log.
Wait for artifacts/claude-convbench-f0-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min) and check it OK from the worktree root. Write one new runner scripts/claude_convf0_run.py that runs each dialog once, in order, with a fresh agent per dialog, and records for every turn: dialog_id, turn_index, reply, notebook events, and stored triples. Accept a text key named `user_text` or `user`, and stop with an error on empty text. Run on 292 once. Write artifacts/claude-convf0-20260923/run/base292.jsonl.
Then compute mechanical figures only, with a new scorer scripts/claude_convf0_score.py:
- turns;
- share of turns whose reply is a clarify or not-understood line (list the exact marker strings you used);
- count and share of the single most common reply;
- number of distinct replies;
- mean reply length in words;
- replies starting with "Saved:" or "Updated:";
- right, wrong and abstain on ask turns (exact value match);
- saves that match the teach gold.
Write artifacts/claude-convf0-20260923/RESULTS.md (result first, integer counts, never quote benchmark user turns; quoting the agent's replies is fine).
PUSH: artifacts/claude-convf0-20260923 scripts/claude_convf0_*
