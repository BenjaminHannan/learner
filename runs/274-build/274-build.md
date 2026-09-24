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

EXP 274: never deaf, step A (director, 2026-09-24 01:55 UTC). CPU only. ONE change, on the 273 base (scripts/claude_loop273_agent.py on origin/builder-outbox, verified PASS).
Problem (director checked): scripts/fable_agent_loop.py:313-319 turn() = submit() + run_until_idle(), and busy() includes sleep_due() (line ~290), so when sleep is due the reply to a turn is only returned after the whole sleep runs. 273 fixed tick order but not this.
The change: a NEW file scripts/claude_loop274_agent.py (build_agent274, Loop274Daemon) built exactly like 273, where turn() runs ticks only while the inbox is non-empty (the listening ticks), returns/writes the reply, and leaves any due sleep for the next idle tick (the daemon's idle loop / next run_until_idle). Never edit frozen files. Do not change WORK vs SLEEP order (pending ruling for Ben). Plus a deaf-seconds meter: for every turn, seconds between the message arriving and its reply being written; logged per turn and summarised (median, max).
Seal first: artifacts/claude-loop274-20260924/PASSMARKS.md + SEAL.sha256.txt. Marks:
 M1 20 seeded cases with sleep due and one message waiting: the reply is returned before any sleep tick runs, 20/20 (273: report its number; expect 0/20).
 M2 sleep still happens: in the same 20 cases the due sleep runs within the next 3 idle ticks, 20/20.
 M3 no behaviour change: the 292t/273 panel (same scorer and gold 273 used) gives identical scores (90/90, 0 overlaps, 0 wrong); any change = FAIL.
 M4 deaf meter on the 20 cases: 274 max deaf seconds < 273 max deaf seconds and 274 median ≤ 2 s. Report both arms.
Proved wrong by: any M3 score change, or sleep never running.
PUSH: scripts/claude_loop274_agent.py scripts/claude_loop274_test.py artifacts/claude-loop274-20260924/PASSMARKS.md artifacts/claude-loop274-20260924/SEAL.sha256.txt artifacts/claude-loop274-20260924/RESULTS.md artifacts/claude-loop274-20260924/results.json
