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


GETTING YOUR FILES: run git fetch -q origin claude/project-thread-p68q5v and read each named file with git show origin/claude/project-thread-p68q5v:<path>. Never check out or merge that branch.


YOUR TASK: restart and finish the BUILD half of exp 241b (the mouth, stage A v2), the one follow-up to 241's registered FAIL. CPU only.
Read first: handoff/kit/briefs/241b-mouthA2.txt (the registered brief; follow it exactly) and handoff/kit/briefs/241b-stylesheet.txt (its sha256 must be 16bdf0cf0403bce26886ea345f1ea44242e54537380f0ab3b8c7ed40f2dad8ef; check it and stop if it differs). In this worktree read artifacts/claude-mouth241-20260922/PASSMARKS.md and RESULTS.md.
State: the first 241b builder stopped before sealing (account limit). It left unsealed code: scripts/claude_mouth241b_*.py (13 files), claude_loop241b_agent.py, claude_confirm241b.py, claude_fix172b241b_benchv3.py and artifacts/claude-mouth241b-20260922/say_forms.json. claude_mouth241b_test.py gives 29/29 in the director's check. No PASSMARKS, no seal, no sweep yet.
Rules for the old files: they are read-only. Reuse them by import. If one must change, copy it to a new file with the suffix _r (for example claude_mouth241b_say_r.py), change the copy, and list every copy with a one-line reason in PASSMARKS.
Order:
(1) Inventory: for each brief item a to g and each new scorer version, say which file does it and whether its tests cover it. Build what is missing.
(2) Dev pilot on the 241 sweep and pairs (dev material now): the 42 old M1 misses fixed or not, M2 a/b/c, M3 suites vs 228, S1 identity check on every saved row, M5 render median/p99 and the D6 suite wall vs 228 (check uptime first; stop and report if the wall is still over +5%, with the per-line cost).
(3) PASSMARKS.md with 241b's registered marks and S1, numbered predictions P241b.n, every predicted move; the style sheet copied verbatim into section 6. Seal (shasum -a 256 > SEAL.sha256.txt). Append the ledger lines.
(4) Generate the FRESH sweep (seed SEED241B, about 1,200 replies, at least 30 AMBIGUOUS) and the FRESH 120 M4 pairs, and seal them into SEAL2.sha256.txt.
(5) Run the registered M2, M3, M5, S1 and the sleep smoke. Stop there. Never grade or judge the sweep or pairs yourself; the director launches fresh graders and a fresh judge.
Keep every registered run under 25 minutes. Report: marks so far with integer counts, the paths and sha256 of the sweep, pairs and pairs key, every move, miss and deviation.
PUSH: artifacts/claude-mouth241b-20260922 scripts/claude_mouth241b_* scripts/claude_loop241b_* scripts/claude_confirm241b* scripts/claude_fix172b241b_* artifacts/fable-predictions-ledger.md
