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


YOUR TASK: run the director's held-out probe for exp 255b. You run dialogs and save transcripts; you change no code and judge nothing.
Arms: 138m (scripts/claude_loop138m_agent.py + artifacts/claude-merge138m-20260922/loop138m-config.json) and 255b (scripts/claude_loop255b_agent.py + artifacts/claude-fixedtext255b-20260923/loop255b-config.json). Load and drive them exactly the way scripts/claude_255b_* drives the verifier probes (fresh daemon per dialog, notebook triples recorded after every turn). First verify: shasum -a 256 -c artifacts/claude-fixedtext255b-20260923/SEAL.sha256.txt from the worktree root (all OK, or stop).
Run each dialog below on each arm, fresh notebook each dialog. Turns are separated by " | ".
D1: Ana's boss is Tobin. | whos anas boss tho | who is ana's bos
D2: My name is Corla. | whats my nmae? | Do u know what im called
D3: How many turns have we had? | Have you slept? | How many facts do you know?
D4: Did you ask me to clarify anything? | How many questions have you answered? | Tell me about yesterday.
D5: Pim's city is Oslo. | where Pim live at | Where does Pim live?
D6: Who talked to you besides me? | whats ur name | Tobin's dog is Rufus. | rufus belongs to who
D7: Kell's teacher is Mara. | Mara teaches who? | who's kell's teachr
D8: Have you stored any web rows? | Hello! | How many times have you slept?
Save artifacts/claude-probe255b-director-20260923/transcripts.jsonl: one line per turn with arm, dialog, turn index, user text, reply, and the sorted stored triples after the turn. Also a transcripts.md side by side.
Report: the number of turns whose reply differs between arms, and the number of turns whose stored triples differ (list both by dialog and turn). No judging.
PUSH: artifacts/claude-probe255b-director-20260923
