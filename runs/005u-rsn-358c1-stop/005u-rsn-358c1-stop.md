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
GPU: yes (BensPC; $0, no rental). Evaluation only, no training, small (~6.4M-weight nets, 4,200 puzzles per seed). If the GPU has under 4 GB free, run it on BensPC's CPU instead (same commands; slower but fine).

YOUR TASK: builder for rsn-358c1 (evaluation only; the sleep research thread wrote and sealed the code and marks; run it, never edit it). Artifacts go in artifacts/claude-rsn358c-20260926/.
READ FIRST (on origin/main): artifacts/claude-rsn358c-20260926/PASSMARKS-c1.md and the docstring of scripts/claude_rsn358c1_stop.py.
PRECONDITION: rsn-358a (005t) has finished and its checkpoints exist at C:/Users/benja/premonition-models/rsn358a/{loop-s1,plain-s1,loop-s2,plain-s2}/final.pt (or in 005t's working dir W/). If any is missing, stop and report NOT-READY with what exists. Check each final.pt's sha256 against artifacts/claude-rsn358a-20260925/SEAL-run.sha256.txt (on origin/builder-outbox or main): mismatch -> stop. KNOWN TYPO: plain-s2's recorded hash has 65 characters (blind recount). For plain-s2 only, accept the checkpoint if deleting exactly one character from the recorded string gives its real sha256; write the real hash in RESULTS-c1.md as a deviation. Any other mismatch -> stop.
This task never opens artifacts/claude-rsn358a-20260925/tests/ (TEST-ONLY). The script makes its own fresh puzzles.
1. SEAL: from a `git archive origin/main scripts artifacts/claude-rsn358c-20260926 artifacts/claude-rsn358a-20260925` extract, run `sha256sum -c artifacts/claude-rsn358c-20260926/SEAL-c1.sha256.txt`: every line OK, else stop. Run `python -B scripts/claude_rsn358c1_stop.py smoke` ("smoke ok").
2. RUN, once per seed (same venv as 005t):
   python -B scripts/claude_rsn358c1_stop.py --ckpt <loop-s1>/final.pt --plain <plain-s1>/final.pt --out artifacts/claude-rsn358c-20260926/runs/stop358c1-s1.json
   python -B scripts/claude_rsn358c1_stop.py --ckpt <loop-s2>/final.pt --plain <plain-s2>/final.pt --out artifacts/claude-rsn358c-20260926/runs/stop358c1-s2.json
   Keep the printed lines in artifacts/claude-rsn358c-20260926/runs/stop358c1-s<N>.log.
3. RESULTS-c1.md, verdict first: for each seed and family: budget, fixed_budget_right, v2_right, answer_cell_right, plain_right, mean rounds (v2, answer-cell), check_any_round; then marks V, K1-K4 with integer counts and PASS / FAIL / NOT NEEDED / INCONCLUSIVE exactly as PASSMARKS-c1.md; whether "proved wrong" triggered. Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
PUSH: artifacts/claude-rsn358c-20260926/RESULTS-c1.md artifacts/claude-rsn358c-20260926/runs artifacts/fable-predictions-ledger.md
