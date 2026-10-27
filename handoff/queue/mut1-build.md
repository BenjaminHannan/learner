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

EXP mut-1: do our tests catch broken sleep/listen code? (director, 2026-09-24 03:55 UTC). CPU only. Report-only mutation test on the 274 base (scripts/claude_loop274_agent.py, verified PASS).
Build 4 mutants, each a NEW file scripts/claude_mut1_<k>.py that wraps 274 with ONE deliberate break (never edit 274 or frozen files):
 k1 swap step order back (sleep_due before inbox);
 k2 drop the inbox branch from step() (listening tick never chosen by step);
 k3 sleep never due (sleep_due always False);
 k4 listening tick replaced by the thinking tick.
Run against each mutant AND the unmutated 274: scripts/claude_loop274_test.py (its M1, M2, M4), the sleep smoke fable_sleepsmoke206.py, and the 292t/273 90-turn panel scorer used by 274 (M3). Seal first: artifacts/claude-mut1-20260924/PASSMARKS.md + SEAL.sha256.txt.
Marks: K0 unmutated 274 passes every suite (same numbers as 274's results). K1 each mutant is caught (at least one suite FAILS) - 4/4. Report which suites catch which mutant (a table). A mutant no suite catches = a test gap: report it, don't fix it.
Before running, check ~/.cache/huggingface/hub has the MiniLM snapshot; if missing, stop and report MISSING-CACHE (don't download).
PUSH: scripts/claude_mut1_k1.py scripts/claude_mut1_k2.py scripts/claude_mut1_k3.py scripts/claude_mut1_k4.py artifacts/claude-mut1-20260924/PASSMARKS.md artifacts/claude-mut1-20260924/SEAL.sha256.txt artifacts/claude-mut1-20260924/RESULTS.md artifacts/claude-mut1-20260924/results.json
