COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $3.50 for this whole task. Label: rent-339-style. Needs READER.

YOUR TASK: rent-339-style, the REGISTERED run of exp 339 (learns how the user likes to be talked to), which e2e-339-style could not run on Windows. Marks: artifacts/claude-style339-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-stylepanel339-20260924 is TEST-ONLY. Run once. If artifacts/claude-style339-20260924/run already exists on origin/builder-outbox, stop with DUPLICATE.
1. On the rental: sha256sum -c SEAL.sha256.txt from inside the panel folder: all OK. BEFORE running write artifacts/claude-style339-20260924/SEAL-code-rent.sha256.txt = sha256sum of scripts/claude_style339_agent.py scripts/claude_style339_run.py scripts/claude_chat338_agent.py scripts/claude_chat338_run.py scripts/claude_cre333_agent.py scripts/claude_e2e330_arms.py scripts/claude_lis_stackb.py scripts/claude_lis_e2e_armsb.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py scripts/claude_age334_agent.py.
2. Each its own process, through the 336 harness (PANEL = artifacts/claude-stylepanel339-20260924, OUT = artifacts/claude-style339-20260924/run; write them in full):
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_chat338_run:build_P --name B --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_style339_run:build_P --name P --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm twin --name T --model BASE
   python -B scripts/claude_style339_run.py --panel PANEL --score OUT
3. P339.4 on the readable DEV bank:
   python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-style339-20260924/dev --arm claude_style339_run:build_P --name P339 --model READER --gen-model BASE
   then count the rows of dev/arm_P339.jsonl whose reply starts with one of the ACK339 acknowledgements in scripts/claude_style339_agent.py (print the count only).
4. Copy run/ and dev/ back to the Mac, check, destroy, ledger line.
5. RESULTS-rent.md: the step 2 summary with P339.1 and P339.2 PASS/FAIL, the step 3 count with P339.4 PASS/FAIL, GPU, hours, dollars, model commit hash, wall time per arm. Do NOT open judge_*.jsonl or quote any panel reply.
PUSH: artifacts/claude-style339-20260924/RESULTS-rent.md artifacts/claude-style339-20260924/SEAL-code-rent.sha256.txt artifacts/claude-style339-20260924/run artifacts/claude-style339-20260924/dev artifacts/fable-predictions-ledger.md
