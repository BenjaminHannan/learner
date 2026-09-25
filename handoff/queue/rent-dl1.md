COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $3.00 for this whole task, re-rents included (Ben 19:38 UTC 2026-09-25: threads share $7 of rentals until ~23:40 UTC; the Director keeps the ledger). Label: rent-dl1.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $4.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $2.70 kill running commands by exact PID, copy back what exists (dl1_results.json is rewritten after every arm), destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl1-20260925/gpu or a live instance is labelled rent-dl1.

YOUR TASK: dl-1, the registered run (three night learning rules on MiniCPM5-1B; one GPU run). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-dl1-20260925/PASSMARKS.md and the docstring of scripts/claude_dl1_nights.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the same model files as blurt-4/5s, no new download). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py artifacts/claude-dl1-20260925/PASSMARKS.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_dl1_nights.py --selftest` prints "selftest ok", else stop.
3. One process, with a log:
   python -B scripts/claude_dl1_nights.py --model BASE --out gpu
   Expect roughly 1.5-3 hours (about 6x blurt-3r's sampling, which took 31 min on a 5070 Ti). If it has not printed "[dl1] S s0 night 1" after 75 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl1_results.json and the log back as artifacts/claude-dl1-20260925/gpu/dl1_results.json and gpu/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu.md in artifacts/claude-dl1-20260925/: the whole "marks" block of dl1_results.json, then each mark R1-R5, the verdict and the proved-wrong clause with integer counts, GPU name, wall minutes, dollars, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl1-20260925/gpu artifacts/claude-dl1-20260925/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
