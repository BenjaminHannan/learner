COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $1.50 for this whole task. Label: rent-333b-creative. This is a re-queue of rent-333-creative, which ended HOST-FAIL with nothing run (origin/builder-outbox:artifacts/claude-cre333-20260924/RESULTS-rent.md); the 4-rental count starts fresh. Re-run the offer search before every create (a `success: false` usually means the offer was just taken). No reader needed.

YOUR TASK: rent-333b-creative, the REGISTERED run of exp 333 (creative v1), which e2e-333-creative could not run on Windows. Marks: artifacts/claude-cre333-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-creativepanel333-20260924 is TEST-ONLY. Run once. If artifacts/claude-cre333-20260924/run already exists on origin/builder-outbox, stop with DUPLICATE.
1. On the rental: sha256sum -c SEAL.sha256.txt from inside the panel folder: all OK. BEFORE running write artifacts/claude-cre333-20260924/SEAL-code-rent.sha256.txt = sha256sum of scripts/claude_cre333_agent.py scripts/claude_cre333_run.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py.
2. Each its own process (P = --panel artifacts/claude-creativepanel333-20260924, O = --out artifacts/claude-cre333-20260924/run; write them in full):
   python -B scripts/claude_cre333_run.py P --arm B O
   python -B scripts/claude_cre333_run.py P --arm P --gen-model BASE O
   python -B scripts/claude_cre333_run.py P --arm T --gen-model BASE O
   python -B scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --score artifacts/claude-cre333-20260924/run
3. Copy run/ back to the Mac, check, destroy, ledger line.
4. RESULTS-rent-b.md (do not overwrite RESULTS-rent.md): the printed summary with P333.1 and P333.2 PASS/FAIL against their bars (the rest are judged later by the thread), GPU, hours, dollars, model commit hash, wall time per arm. Do NOT open judge_creative.jsonl or quote replies.
PUSH: artifacts/claude-cre333-20260924/RESULTS-rent-b.md artifacts/claude-cre333-20260924/SEAL-code-rent.sha256.txt artifacts/claude-cre333-20260924/run artifacts/fable-predictions-ledger.md
