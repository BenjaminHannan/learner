COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation. Follow the setup section of origin/main:design/v3/30-modes/330-rent-kit.md for installing packages and fetching plain MiniCPM5-1B (BASE = the printed snapshot path; record its commit hash; never download any other model).
GPU: rent
BUDGET: $1.00 for this whole task, re-rents included (the Director releases it). Label: rent-tgt5.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $3.00: rent nothing, stop with CREDIT-STOP. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.90 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid). Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-tgt5-20260926/gpu or a live instance is labelled rent-tgt5.

YOUR TASK: tgt5, the registered run of tgt-5 (does sleep make the model match answers to their own targets; one GPU run). The creative thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch.
READ FIRST (origin/main): artifacts/claude-tgt5-20260926/PASSMARKS-tgt5.md and the docstring of scripts/claude_tgt5.py.
1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_blurt4.py scripts/claude_blurt5s.py scripts/claude_tgt5.py scripts/claude_cre333b_agent.py artifacts/claude-blurt1-dev-20260925/puzzles.jsonl artifacts/claude-tgt5-20260926/PASSMARKS-tgt5.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_tgt5.py --selftest --model BASE` prints "selftest ok", else stop.
3. One process, with a log:
   python -B scripts/claude_tgt5.py --model BASE --out gpu --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 9 --pair-seed 795
   Expect about 15-25 minutes on a 5090 (blurt-5s took 17.8 min with far more sampling).
4. Copy gpu/tgt5_summary.json, gpu/pairs.jsonl, gpu/contrasts.json and the log back as artifacts/claude-tgt5-20260926/gpu/ (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu.md in artifacts/claude-tgt5-20260926/: the whole tgt5_summary.json, then the PASS and proved-wrong clauses from PASSMARKS-tgt5.md with the numbers, GPU name, wall minutes, dollars, model commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-tgt5-20260926/gpu artifacts/claude-tgt5-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
