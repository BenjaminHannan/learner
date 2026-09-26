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
GPU: yes (BensPC; $0, no rental). 4 trainings of ~6.4M-weight nets (358a took 26-33 min each alone on the 5070 Ti) + 4 evals. DEADLINE: results are wanted before 07:30 UTC (03:30 Ben's time).

YOUR TASK: builder for rsn-358d (loop reasoner vs plain twin, same as rsn-358a with ONE change: many more 4-number practice puzzles). The sleep research thread wrote and sealed all code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358d-20260926/.
READ FIRST (on origin/main): artifacts/claude-rsn358d-20260926/PASSMARKS.md, artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md, and the docstring of scripts/claude_rsn358d_run.py. Its commands and arguments are the same as scripts/claude_rsn358a_run.py (see 358a's RESULTS.md on origin/builder-outbox for how 358a was run; reuse the same venv).
INDEPENDENCE: artifacts/claude-rsn358a-20260925/tests/ is TEST-ONLY: never open or print an item; the eval command writes counts only. Run each eval exactly once per checkpoint.
0. On BensPC: `git archive origin/main scripts artifacts/claude-rsn358d-20260926 artifacts/claude-rsn358a-20260925` and extract, keeping paths. Check nvidia-smi and free disk. If another job is on the GPU and free GPU memory is under 6 GB, wait for it; never touch another process.
1. SEAL: `sha256sum -c artifacts/claude-rsn358d-20260926/SEAL-code.sha256.txt` (on Windows compute each hash with Get-FileHash and compare every line; all must match, else stop). Run `python -B scripts/claude_rsn358a_envs.py selftest` and `python -B scripts/claude_rsn358d_run.py pool` (expect "pool 75972 four-number puzzles over 1520 hands; 300 held-out hands excluded; target-24 puzzles in pool: 1062"; anything else -> stop).
2. TRAIN (two at a time is fine if nvidia-smi shows room; the pool takes ~40 s to build at start):
   python -B scripts/claude_rsn358d_run.py train --arm loop  --seed 3 --out W/loop-s3
   python -B scripts/claude_rsn358d_run.py train --arm plain --seed 3 --out W/plain-s3
   python -B scripts/claude_rsn358d_run.py train --arm loop  --seed 4 --out W/loop-s4
   python -B scripts/claude_rsn358d_run.py train --arm plain --seed 4 --out W/plain-s4
   TOO-SLOW: if the pilot-free estimate (first 5,000 steps' minutes x 12) puts the last run's end after 07:00 UTC, still finish seed 3 (both arms) and report TOO-SLOW for seed 4.
3. SEAL each final.pt (sha256, exactly 64 hex characters, appended to artifacts/claude-rsn358d-20260926/SEAL-run.sha256.txt) BEFORE its eval.
4. EVAL once per checkpoint: python -B scripts/claude_rsn358d_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358a-20260925/tests --out W/R/tests.json
   Copy train_log.jsonl, train_summary.json, tests.json into artifacts/claude-rsn358d-20260926/runs/<R>/.
5. RESULTS.md, verdict first: G0-G3 for both seeds with integer counts and PASS / FAIL / INCONCLUSIVE per PASSMARKS-v2.md; proved-wrong clause; per-seed table of every test (plain, loop own stop, loop - plain); loop right at 1/2/4/8/12/16/24/32/48 rounds and any round; numbers4/numbers5 for both arms called out; minutes per run; every deviation. Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
6. Keep checkpoints on BensPC at C:/Users/benja/premonition-models/rsn358d/<run>/ (never push weights).
PUSH: artifacts/claude-rsn358d-20260926/RESULTS.md artifacts/claude-rsn358d-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358d-20260926/runs artifacts/fable-predictions-ledger.md
