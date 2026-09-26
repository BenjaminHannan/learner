COMMON RULES (the director, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.
GPU: yes (BensPC; $0, no rental). 4 trainings of ~6.4M-weight nets (358a took 26-33 min each alone on the 5070 Ti) + 4 evals. Two at a time is fine if nvidia-smi shows room; never touch another process.

YOUR TASK: builder for rsn-358g (rsn-358a with ONE change: every grid shows its full symbol set). The sleep research thread wrote and sealed all code and tests; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358g-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358g-20260926/PASSMARKS.md, artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md, the docstring of scripts/claude_rsn358g_run.py (same commands/arguments as scripts/claude_rsn358a_run.py).
INDEPENDENCE: artifacts/claude-rsn358g-20260926/tests/ is TEST-ONLY: never open or print an item; eval writes counts only. Run each eval exactly once per checkpoint.
0. On BensPC: `git archive origin/main scripts artifacts/claude-rsn358g-20260926 artifacts/claude-rsn358a-20260925` and extract, keeping paths; same venv as 358a (005t).
1. SEAL: check every line of artifacts/claude-rsn358g-20260926/SEAL-code.sha256.txt (Get-FileHash on Windows); all must match, else stop. Run `python -B scripts/claude_rsn358a_envs.py selftest` and `python -B scripts/claude_rsn358g_run.py audit` (four lines "300/300 puzzles show every needed symbol"; else stop).
2. TRAIN:
   python -B scripts/claude_rsn358g_run.py train --arm loop  --seed 1 --out W/loop-s1
   python -B scripts/claude_rsn358g_run.py train --arm plain --seed 1 --out W/plain-s1
   python -B scripts/claude_rsn358g_run.py train --arm loop  --seed 2 --out W/loop-s2
   python -B scripts/claude_rsn358g_run.py train --arm plain --seed 2 --out W/plain-s2
3. SEAL each final.pt (sha256, exactly 64 hex characters; check the length) appended to artifacts/claude-rsn358g-20260926/SEAL-run.sha256.txt BEFORE its eval.
4. EVAL once per checkpoint: python -B scripts/claude_rsn358g_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358g-20260926/tests --out W/R/tests.json
   Copy train_log.jsonl, train_summary.json, tests.json into artifacts/claude-rsn358g-20260926/runs/<R>/.
5. RESULTS.md, verdict first: G0-G3 for both seeds with integer counts and PASS / FAIL / INCONCLUSIVE per PASSMARKS-v2.md; proved-wrong clause; per-seed table of every test (plain, loop own stop, loop - plain, and 358a's counts from origin/builder-outbox:artifacts/claude-rsn358a-20260925/runs/*/tests.json beside them); loop right at 1/2/4/8/12/16/24/32/48 rounds and any round; minutes per run; every deviation. Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
6. Keep checkpoints on BensPC at C:/Users/benja/premonition-models/rsn358g/<run>/ (never push weights).
PUSH: artifacts/claude-rsn358g-20260926/RESULTS.md artifacts/claude-rsn358g-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358g-20260926/runs artifacts/fable-predictions-ledger.md
