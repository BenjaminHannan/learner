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

EXP 273: listen before sleep, on the 292t base (director, 2026-09-23 18:58 UTC). ONE change. CPU only (GPU: no).
Problem (confirmed): scripts/fable_agent_loop.py step() (lines ~292-301) checks sleep_due() BEFORE the inbox, so a user message waiting in the inbox is delayed by a whole sleep tick. Ben's design says listening comes first.
The change: a NEW file scripts/claude_loop273_agent.py providing build_agent273(cfg) and Loop273Daemon, built exactly like 292t (import scripts/claude_loop292t_agent.py from origin/builder-outbox read-only), with the loop's step() order changed ONLY to: inbox -> sleep_due -> work_queue -> thinking. Do it by a subclass or a method wrapper installed on the built loop object; never edit fable_agent_loop.py or any 292t file. The listener line will also wrap 292t's READER stage; do not touch reader/ear stages, so the two changes don't collide.
Before running anything, write artifacts/claude-loop273-20260923/PASSMARKS.md and SEAL.sha256.txt (sha256 of the new script, the test script and PASSMARKS). Pass marks (all must hold):
 M1 order test: a new script scripts/claude_loop273_test.py builds a loop with sleep_due() forced True AND one user message in the inbox; the first step() must be a listening tick. Run 20 such seeded cases: 20/20 listening first (292t: expect 0/20, report the number).
 M2 no starvation: with sleep due and a stream of 1 user message per tick for 10 ticks and then an empty inbox, sleep runs within 3 ticks of the inbox emptying, in 20/20 cases.
 M3 no behaviour change on the verified 292t panel: rerun the 292t panel (same script and gold that the talking line used; find it on origin/builder-outbox under artifacts/*292t*) with 273; every score identical to 292t's recorded one (90/90, 0 overlaps, 0 wrong). Any change = FAIL.
 M4 0 new wrong saves anywhere in M3.
What would prove it wrong: any M3 score change, or M2 starvation.
Report 292t's own M1/M2 numbers for comparison. Verdict PASS only if M1-M4 all hold.
PUSH: scripts/claude_loop273_agent.py scripts/claude_loop273_test.py artifacts/claude-loop273-20260923/PASSMARKS.md artifacts/claude-loop273-20260923/SEAL.sha256.txt artifacts/claude-loop273-20260923/RESULTS.md artifacts/claude-loop273-20260923/results.json
