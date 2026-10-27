COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $1.50 for this whole task, re-rents included (standing caps: <=$4 per job, $30 total; the Director keeps the ledger and may lower this). Label: rent-dl3.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $3.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $1.35 kill running commands by exact PID, copy back what exists (dl3_results.json is rewritten after every arm-seed), destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl3-20260926/gpu or a live instance is labelled rent-dl3.

YOUR TASK: dl-3, the registered run (seven copy-practice nights with vs without replay of the base's own general answers, on MiniCPM5-1B; one GPU run). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-dl3-20260926/PASSMARKS.md and the docstring of scripts/claude_dl3_replay.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the same model files as dl-2, no new download). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py scripts/claude_dl3_replay.py artifacts/claude-dl3-20260926/PASSMARKS.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_dl3_replay.py --selftest` prints "selftest ok", else stop.
3. One process, with a log:
   python -B scripts/claude_dl3_replay.py --model BASE --out gpu
   Expect roughly 80-100 minutes (dl-2 did 28 arm-nights in 67 min on a 5090; this is 28 plus a replay pool). If it has not printed "[dl3] S s4 night 1" after 45 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl3_results.json, gpu/replay_pool.json and the log back as artifacts/claude-dl3-20260926/gpu/dl3_results.json, gpu/replay_pool.json and gpu/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu.md in artifacts/claude-dl3-20260926/: the whole "marks" block of dl3_results.json, then each mark F1-F5, the verdict and the proved-wrong clause with integer counts, pool_size, GPU name, wall minutes, dollars, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl3-20260926/gpu artifacts/claude-dl3-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
