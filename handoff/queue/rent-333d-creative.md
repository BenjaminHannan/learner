COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $0.60 for this whole task. Label: rent-333d-creative. No reader needed. Re-run the offer search before every create (a `success: false` usually means the offer was just taken).

YOUR TASK: rent-333d-creative, the REGISTERED run of 333d (marks: artifacts/claude-cre333-20260924/PASSMARKS-333d.md; read it and VERIFY-333.md first). The panel artifacts/claude-creativepanel333-20260924 is TEST-ONLY. Run once. If artifacts/claude-cre333-20260924/run-d already exists on origin/builder-outbox, stop with DUPLICATE.
1. On the rental: `sha256sum -c SEAL.sha256.txt` from inside the panel folder: all OK. `python -B scripts/claude_cre333d_test.py` must print "333d tests: 2/2 OK". BEFORE running write artifacts/claude-cre333-20260924/SEAL-code-333d.sha256.txt = sha256sum of scripts/claude_cre333_agent.py scripts/claude_cre333_run.py scripts/claude_cre333b_agent.py scripts/claude_cre333d_agent.py scripts/claude_cre333d_wrap.py scripts/claude_chat338_agent.py.
2. One process (PANEL = artifacts/claude-creativepanel333-20260924, D = artifacts/claude-cre333-20260924; write them in full). Its first printed line must start with "cre333d:"; if not, stop and report.
   python -B scripts/claude_cre333d_wrap.py scripts/claude_cre333_run.py --panel PANEL --arm P --gen-model BASE --out D/run-d
3. `cp D/run/arm_B.jsonl D/run-b/arm_T.jsonl D/run-d/` (333's registered B and 333b's twin b T from origin/builder-outbox, unchanged: check both sha256 before and after), then
   python -B scripts/claude_cre333_run.py --panel PANEL --score D/run-d
4. Mechanical count you MAY do (never quote a reply): rows in run-d/arm_P.jsonl whose reply contains "<think" (expected 0).
5. Copy run-d/ back to the Mac, check, destroy, ledger line.
6. RESULTS-333d.md in D: the printed summary, P333.1 and P333.2 PASS/FAIL against their bars, the step-4 count, GPU, hours, dollars, model commit hash, wall time. Do NOT open judge_creative.jsonl or quote replies.
PUSH: artifacts/claude-cre333-20260924/RESULTS-333d.md artifacts/claude-cre333-20260924/SEAL-code-333d.sha256.txt artifacts/claude-cre333-20260924/run-d artifacts/fable-predictions-ledger.md
