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

YOUR TASK: builder for exp 266, chain-subject lift for two-step questions (reasoning line). CPU only (no GPU, no BensPC).
Read first (from origin/main): design/v3/30-modes/266-chain-subject-questions.md. It gives the diagnosis, THE ONE CHANGE and the marks. Also read, in this worktree, scripts/claude_loop221c_agent.py (the dry, write-free re-hear pattern you copy), scripts/claude_loop138m_agent.py and artifacts/claude-merge138m-20260922/PASSMARKS.md and RESULTS.md (read-only; import, never edit). You may read origin/builder-outbox:runs/chat-weakspots/chat-weakspots.go1.reply.md as dev material.
Base: 138m = scripts/claude_loop138m_agent.py + artifacts/claude-merge138m-20260922/loop138m-config.json; saved rows in artifacts/claude-merge138m-20260922/run/.
New files only: scripts/claude_fix266_chainlift.py (the one outermost ears stage), scripts/claude_loop266_agent.py (SrcGuardMixin228 first; install_srcguard228() at import), scripts/claude_266_*.py/.sh, artifacts/claude-chain266-20260923/. Ledger lines P266.n in artifacts/fable-predictions-ledger.md (append only).
Order: (1) reproduce the gap on 138m with 40+ dev dialogs in your own wording (fictional names; 2- and 3-link chains; "my" chains; every verb/when form the plain-name readers already answer; broken chains; plain controls; statements containing chains); (2) build; pilot on dev and on M2-M4; (3) PASSMARKS.md with numbered predictions and every predicted move by id, seal (shasum -a 256 > SEAL.sha256.txt, repo-root paths), ledger lines; (4) run M2-M4 once; (5) only then wait for artifacts/claude-chainpanel266-20260923/SEAL.sha256.txt (git fetch origin builder-outbox every 2 min, up to 120 min; copy the folder unchanged from origin/builder-outbox), check it OK from the repo root, run the panel ONCE on both arms (138m and 266) with its sealed score_panel.py; (6) RESULTS.md.
Marks (PASS only if all pass):
- M1 chainpanel266: chain_verb >= 27/30; chain_verb_three >= 5/6; chain_possessive: no item right on 138m is not right on 266; broken_chain 12/12 honest abstain; 0 wrong over all 80; 0 question writes; plain_control 14/14 and statement_control 8/8 byte-identical to 138m. Show 138m's number next to every figure.
- M2 frozen suites vs 138m's saved rows (fable_suitediff218 --only rt136,rt143,sessions152,bench,marks123, as 138m did): moves exactly your predicted list; 0 new WRONG, WRONG-WRITE, junk write or lost OK.
- M3 138m's M6 restart files plus artifacts/claude-verify-20260922/138m/probes.json and probes-supp.json: 0 ghost answers, 0 failed duplicate checks, 0 write changes, every reply change predicted.
- M4 latency: median added time per turn <= +5 ms vs 138m (alternate processes).
What would prove the change wrong: a wrong value on any chain question, any answer where a link is missing, or any reply change on a turn with no chain subject.
Finish with RESULTS.md (result first, integer counts, categories and ids only, never quote panel items) and your final reply.
PUSH: artifacts/claude-chain266-20260923 scripts/claude_fix266_chainlift.py scripts/claude_loop266_agent.py scripts/claude_266_*.py scripts/claude_266_*.sh artifacts/fable-predictions-ledger.md
