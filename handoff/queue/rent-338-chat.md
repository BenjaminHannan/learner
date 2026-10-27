COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $3.00 for this whole task. Label: rent-338-chat. Needs READER.

YOUR TASK: rent-338-chat, the REGISTERED run of exp 338 (open conversation). Marks: artifacts/claude-chat338-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-chatpanel338-20260924 is TEST-ONLY. Run once. If artifacts/claude-chat338-20260924/run already exists on origin/builder-outbox, stop with DUPLICATE.
1. On the rental: sha256sum -c SEAL.sha256.txt from inside the panel folder: all OK. BEFORE running write artifacts/claude-chat338-20260924/SEAL-code-rent.sha256.txt = sha256sum of scripts/claude_chat338_agent.py scripts/claude_chat338_run.py scripts/claude_cre333_agent.py scripts/claude_e2e330_arms.py scripts/claude_lis_stackb.py scripts/claude_lis_e2e_armsb.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py scripts/claude_e2e336_score.py scripts/claude_age334_agent.py.
2. Each its own process (P = --panel artifacts/claude-chatpanel338-20260924, O = --out artifacts/claude-chat338-20260924/run; write them in full):
   python -B scripts/claude_chat338_run.py P --arm B --model READER --gen-model BASE O
   python -B scripts/claude_chat338_run.py P --arm P --model READER --gen-model BASE O
   python -B scripts/claude_chat338_run.py P --arm T --gen-model BASE O
   python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --score artifacts/claude-chat338-20260924/run
3. Safety check on the readable DEV bank, report only:
   python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-chat338-20260924/dev --arm claude_chat338_run:build_P --name P338 --model READER --gen-model BASE
   python -B scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs artifacts/claude-chat338-20260924/dev/arm_P338.jsonl --out artifacts/claude-chat338-20260924/dev/score
4. Copy run/ and dev/ back to the Mac, check, destroy, ledger line.
5. RESULTS-rent.md: the step 2 summary with P338.2 and P338.6 PASS/FAIL against their bars (the rest are judged later by the thread), the step 3 score line, GPU, hours, dollars, model commit hash, wall time per arm. Do NOT open judge_*.jsonl or grammar_P.jsonl or quote any panel reply.
PUSH: artifacts/claude-chat338-20260924/RESULTS-rent.md artifacts/claude-chat338-20260924/SEAL-code-rent.sha256.txt artifacts/claude-chat338-20260924/run artifacts/claude-chat338-20260924/dev artifacts/fable-predictions-ledger.md
