COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $1.00 for this whole task. Label: rent-333bc-creative. No reader needed. Re-run the offer search before every create (a `success: false` usually means the offer was just taken).

YOUR TASK: rent-333bc-creative, the REGISTERED runs of 333b and 333c (marks: artifacts/claude-cre333-20260924/PASSMARKS-333b.md and PASSMARKS-333c.md; read both and VERIFY-333.md first). The panel artifacts/claude-creativepanel333-20260924 is TEST-ONLY. Run once. If artifacts/claude-cre333-20260924/run-b already exists on origin/builder-outbox, stop with DUPLICATE.
1. On the rental: `sha256sum -c SEAL.sha256.txt` from inside the panel folder: all OK. `python -B scripts/claude_cre333b_test.py` must print "333b/c tests: 2/2 OK ...". BEFORE running write artifacts/claude-cre333-20260924/SEAL-code-333bc.sha256.txt = sha256sum of scripts/claude_cre333_agent.py scripts/claude_cre333_run.py scripts/claude_cre333b_agent.py scripts/claude_cre333b_wrap.py scripts/claude_e2e336_twin.py scripts/claude_e2e336_twinb.py.
2. Each its own process (PANEL = artifacts/claude-creativepanel333-20260924, D = artifacts/claude-cre333-20260924; write them in full). The first printed line of each must start with "cre333b:" or "cre333c:"; if not, stop and report.
   python -B scripts/claude_cre333b_wrap.py b scripts/claude_cre333_run.py --panel PANEL --arm P --gen-model BASE --out D/run-b
   python -B scripts/claude_cre333b_wrap.py b scripts/claude_cre333_run.py --panel PANEL --arm T --gen-model BASE --out D/run-b
   python -B scripts/claude_cre333b_wrap.py c scripts/claude_cre333_run.py --panel PANEL --arm P --gen-model BASE --out D/run-c
3. `cp D/run/arm_B.jsonl D/run-b/` and `cp D/run/arm_B.jsonl D/run-b/arm_T.jsonl D/run-c/` (arm_B is 333's registered B from origin/builder-outbox, unchanged: check its sha256 before and after). Then
   python -B scripts/claude_cre333_run.py --panel PANEL --score D/run-b
   python -B scripts/claude_cre333_run.py --panel PANEL --score D/run-c
4. Mechanical counts you MAY do (never quote a reply): in each arm_P.jsonl and in run-b/arm_T.jsonl, rows whose reply contains "<think" (expected 0).
5. Copy run-b/ and run-c/ back to the Mac, check, destroy, ledger line.
6. RESULTS-333bc.md in D: both printed summaries, P333.1 and P333.2 PASS/FAIL against their bars for each, the step-4 counts, GPU, hours, dollars, model commit hash, wall time per step. Do NOT open judge_creative.jsonl or quote replies.
PUSH: artifacts/claude-cre333-20260924/RESULTS-333bc.md artifacts/claude-cre333-20260924/SEAL-code-333bc.sha256.txt artifacts/claude-cre333-20260924/run-b artifacts/claude-cre333-20260924/run-c artifacts/fable-predictions-ledger.md
