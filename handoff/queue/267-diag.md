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


GETTING YOUR FILES: git fetch -q origin main, then read each named file with git show origin/main:<path>.

YOUR TASK: builder for exp 264, the question-answering checker. Read design/v3/30-modes/264-qa-checker.md (the one change, exact prompts and save rule) and handoff/kit/briefs/261-earcheck.txt (BensPC, llama-server, ear, arms). In this worktree read artifacts/claude-earcheck261b-20260923/PASSMARKS.md + RESULTS.md and scripts/claude_earcheck261_*.py + scripts/claude_earcheck261b_*.py (read-only; import, never edit). New files only: scripts/claude_earcheck264_*.py, artifacts/claude-earcheck264-20260923/, ledger lines P264.n.
GPU: yes

YOUR TASK: diagnostic for exp 267, the one follow-up to the registered FAIL of 264. This is a diagnostic, not a registered test: no panel is run and no PASS is possible. Read design/v3/30-modes/264-qa-checker.md, artifacts/claude-earcheck264-20260923/RESULTS.md and the 264 scripts (import, never edit). Never open any earpanel*.
Wait (poll every 2 min, up to 90 min) for artifacts/claude-devset267-20260923/SEAL.sha256.txt on origin/main or builder-outbox. Before you open dev.jsonl, write artifacts/claude-diag267-20260923/PREDICTIONS.md with numbered predictions P267.n for each checker below (held-back % of true facts, wrong saves), then seal it (SEAL-pred.sha256.txt).
Then run the ear once over the 120 turns on BensPC (same setup as 264), and score three checkers on the same ear frames, each alone:
 C1 = 261b's YES/NO checker exactly; C2 = 264's QA checker exactly; C3 = PICK-THE-READING: one Qwen call shows the turn and 4 numbered readings (the ear's frame, plus 3 look-alikes made by swapping the relation for its nearest table neighbour, the subject for the other name in the turn, and the value for "not stated"), and saves only if the model picks the ear's reading. Write C3's prompt once, before opening dev.jsonl, and seal it with the predictions; no tuning after.
Report per checker: TEACH hits, held-back true facts, wrong saves (per saved fact and per turn), ms per turn (median/p90), all by family. Stop llama-server by exact PID and confirm with nvidia-smi. Never touch pythonw 13036.
PUSH: artifacts/claude-diag267-20260923 scripts/claude_diag267_*.py
