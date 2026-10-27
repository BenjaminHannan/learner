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
GPU: yes (BensPC; $0, no rental). 2 trainings of a ~6.4M-weight net (expect ~1 h each alone on the 5070 Ti; 8 rounds with gradient per step) + 2 evals. May run alongside another BensPC job only if nvidia-smi shows at least 6 GB free; never touch another process.

YOUR TASK: builder for rsn-358f (the 358a loop trained as a looped flow, vs 358a's plain twin). The sleep research thread wrote and sealed all code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358f-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358f-20260926/PASSMARKS.md and the docstring of scripts/claude_rsn358f_flow.py.
INDEPENDENCE: artifacts/claude-rsn358a-20260925/tests/ is TEST-ONLY: never open or print an item; eval writes counts only. Run each eval exactly once per checkpoint.
0. On BensPC: `git archive origin/main scripts artifacts/claude-rsn358f-20260926 artifacts/claude-rsn358a-20260925` and extract, keeping paths; same venv as 358a (005t). Check nvidia-smi and free disk.
1. SEAL: check every line of artifacts/claude-rsn358f-20260926/SEAL-code.sha256.txt (Get-FileHash on Windows); all must match, else stop. Run `python -B scripts/claude_rsn358a_envs.py selftest` ("selftest ok").
2. TRAIN (one at a time, or both at once if nvidia-smi shows room):
   python -B scripts/claude_rsn358f_flow.py train --seed 1 --out W/flow-s1
   python -B scripts/claude_rsn358f_flow.py train --seed 2 --out W/flow-s2
   The first log line must say "6356158 weights"; anything else -> stop.
3. SEAL each final.pt (sha256, exactly 64 hex characters; check the length) appended to artifacts/claude-rsn358f-20260926/SEAL-run.sha256.txt BEFORE its eval.
4. EVAL once per checkpoint: python -B scripts/claude_rsn358f_flow.py eval --ckpt W/flow-sN/final.pt --tests artifacts/claude-rsn358a-20260925/tests --out W/flow-sN/tests.json
   Copy train_log.jsonl, train_summary.json, tests.json into artifacts/claude-rsn358f-20260926/runs/flow-sN/.
5. RESULTS.md, verdict first: G0, F1, F2 per seed with integer counts and PASS / FAIL / INCONCLUSIVE per PASSMARKS.md, using 358a's plain counts from origin/builder-outbox:artifacts/claude-rsn358a-20260925/runs/plain-sN/tests.json (seed N = flow seed N); proved-wrong clause; per-seed table of every test (plain, flow at 32 steps, flow - plain, flow at 16 and 64, 358a loop own stop from runs/loop-sN/tests.json); minutes per run; every deviation. Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
6. Keep checkpoints on BensPC at C:/Users/benja/premonition-models/rsn358f/<run>/ (never push weights).
PUSH: artifacts/claude-rsn358f-20260926/RESULTS.md artifacts/claude-rsn358f-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358f-20260926/runs artifacts/fable-predictions-ledger.md
