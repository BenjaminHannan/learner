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


YOUR TASK: blind writer for the talking line's conversation benchmark convbench-f0 (step F0 of design/v3/30-modes/talk-fluency-plan.md). You write dialogs only; you never read or run any code.
Read ONLY design/v3/30-modes/talk-fluency-plan.md (git show origin/main:...). Never use git log. Do not open scripts/ or any artifacts folder.
Write artifacts/claude-convbench-f0-20260923/: dialogs.jsonl with 40 multi-turn dialogs of 6 to 10 user turns each (one line per turn, exactly these keys: dialog_id, turn_index, user_text, kind, gold). The dialogs should read like a real person chatting casually with an assistant that keeps a notebook of facts about people: greetings, telling it facts about friends, family, pets, jobs and places in everyday wording, asking about those facts later in varied wording, a correction or two, small talk, thanks and goodbye. kind is one of teach / ask / correct / smalltalk / other. gold = the stored triple Subject|relation|Object for teach turns, the exact expected value for ask turns, "smalltalk", or "none". Also write README.md with counts per kind. Fictional names only, freshly invented, never Ana, Kim, Mira, Tomas or any name in the plan.
Seal from the worktree root: shasum -a 256 artifacts/claude-convbench-f0-20260923/dialogs.jsonl artifacts/claude-convbench-f0-20260923/README.md > artifacts/claude-convbench-f0-20260923/SEAL.sha256.txt. Never change the files after sealing.
Report: counts per kind, dialogs, and the seal file's contents. Never quote items.
PUSH: artifacts/claude-convbench-f0-20260923
