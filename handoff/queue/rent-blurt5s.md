COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation. Follow the setup section of origin/main:design/v3/30-modes/330-rent-kit.md for installing packages and fetching plain MiniCPM5-1B (BASE = the printed snapshot path; record its commit hash; never download any other model).
GPU: rent
BUDGET: $3.00 for this whole task, re-rents included (Ben 19:13 UTC 2026-09-25: "you can use vast btw"; the Director releases it). Label: rent-blurt5s.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $5.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $2.70 kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-blurt5s-20260925/gpu-5s or a live instance is labelled rent-blurt5s.

YOUR TASK: blurt5s, the registered run of blurt-5s (own lucky hits vs exact-solver answers; one GPU run). The creative thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-blurt5s-20260925/PASSMARKS-blurt5s.md and the docstring of scripts/claude_blurt5s.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_blurt5s.py scripts/claude_cre333b_agent.py artifacts/claude-blurt1-dev-20260925/puzzles.jsonl artifacts/claude-blurt5s-20260925/PASSMARKS-blurt5s.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_blurt5s.py --selftest` prints "selftest ok"; and `python -B scripts/claude_blurt1.py make --out pzcheck --n 60 --seed 1`, then pzcheck/puzzles.jsonl must be identical to artifacts/claude-blurt1-dev-20260925/puzzles.jsonl, else stop.
3. One process, with a log:
   python -B scripts/claude_blurt5s.py --model BASE --out gpu-5s --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 9 --test-seed 785 --n-test 240
   Expect roughly 1-2.5 hours (about 4x the sampling of blurt-3r, which took 31 min on a 5070 Ti). If it has not printed "[b5s] practice" after 2 hours, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu-5s/blurt5s_summary.json and the log back as artifacts/claude-blurt5s-20260925/gpu-5s/blurt5s_summary.json and gpu-5s/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu-5s.md in artifacts/claude-blurt5s-20260925/: the whole blurt5s_summary.json, then S1 and the proved-wrong clause from PASSMARKS-blurt5s.md with integer counts, GPU name, wall minutes, dollars, model commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-blurt5s-20260925/gpu-5s artifacts/claude-blurt5s-20260925/RESULTS-gpu-5s.md artifacts/fable-predictions-ledger.md
