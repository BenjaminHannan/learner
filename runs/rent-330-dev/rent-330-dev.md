COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $2.00 for this whole task. Label: rent-330-dev. Needs READER.

YOUR TASK: rent-330-dev, REPORT ONLY (dev data, no registered marks): the dress rehearsal that e2e-330-dev could not run on Windows. Artifacts in artifacts/claude-e2e330-dev-20260924/ (new files only; RESULTS-dev.md already exists, so write RESULTS-rent.md). The DEV bank artifacts/claude-e2e331-dev-20260924 is dev data: fine to read.
1. On the rental, from the tree root: sha256sum -c of artifacts/claude-e2e331-dev-20260924/SEAL.sha256.txt run from inside that folder: all OK.
2. Five arms, one after another, each its own process (write --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-e2e330-dev-20260924/run on each):
   python -B scripts/claude_e2e336_run.py --arm claude_lis_e2e_armsb:build_G --name G --model READER
   python -B scripts/claude_e2e336_run.py --arm claude_e2e330_arms:build_330a --name 330a --model READER
   python -B scripts/claude_e2e336_run.py --arm claude_e2e330_arms:build_330a_cre --name 330a_cre --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --arm claude_chat338_run:build_P --name 330a_chat --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --arm twin --name twin --model BASE
3. python -B scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs artifacts/claude-e2e330-dev-20260924/run/arm_*.jsonl --out artifacts/claude-e2e330-dev-20260924/score
4. Copy run/ and score/ back to the Mac, check, destroy, ledger line.
5. RESULTS-rent.md, counts only: the scorer's printed line for every arm; GPU, hours, dollars; model commit hash; wall time per arm; for arm 330a_chat every new triple the scorer marks owner_value_supported=false as "triple <- nearest truth fact". Dev data may be quoted sparingly.
PUSH: artifacts/claude-e2e330-dev-20260924/RESULTS-rent.md artifacts/claude-e2e330-dev-20260924/run artifacts/claude-e2e330-dev-20260924/score artifacts/fable-predictions-ledger.md
