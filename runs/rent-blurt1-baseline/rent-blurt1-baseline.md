COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence).
GPU: rent
BUDGET: $0.60 for this whole task. Label: rent-blurt1. No reader needed. Re-run the offer search before every create.

YOUR TASK: rent-blurt1, a DEV measurement (no pass marks; DEV data only, no TEST-ONLY panel). Code: scripts/claude_blurt1.py (read its docstring). If artifacts/claude-blurt1-dev-20260925/run exists on origin/builder-outbox, stop with DUPLICATE.
D = artifacts/claude-blurt1-dev-20260925 (write it in full in every command).
1. On the rental, after setup: `python -B scripts/claude_blurt1.py make --out /tmp/pzcheck --n 60 --seed 1` then `cmp /tmp/pzcheck/puzzles.jsonl D/puzzles.jsonl` must print nothing (same puzzles).
2. Three processes, one after another, each under nohup with a log:
   python -B scripts/claude_blurt1.py puzzle --model BASE --puzzles D/puzzles.jsonl --out D/run/puzzles_t06.jsonl --n 30 --temp 0.6
   python -B scripts/claude_blurt1.py puzzle --model BASE --puzzles D/puzzles.jsonl --out D/run/puzzles_t10.jsonl --n 30 --temp 1.0
   python -B scripts/claude_blurt1.py ideas --model BASE --dev artifacts/claude-cre333e-dev-20260924 --out D/run/ideas_t10.jsonl --n 30 --temp 1.0
3. Copy D/run/ and the three logs (as D/run/log_*.txt) back to the Mac, check, destroy, ledger line.
4. RESULTS-blurt1.md in D: the last printed line of each puzzle process, row counts, GPU, hours, dollars, model commit hash, wall time.
PUSH: artifacts/claude-blurt1-dev-20260925/run artifacts/claude-blurt1-dev-20260925/RESULTS-blurt1.md artifacts/fable-predictions-ledger.md
