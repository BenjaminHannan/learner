COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). RERUN of rent-zdl4: that rental was destroyed at ~13:29 UTC by a Mac agent that took it for its own, before the anchor arm started; nothing of it is used. Same sealed code, same command, from scratch. ONLY the Fix-sleep thread or the Director may stop or destroy claude-fixsleep-dl4b. Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $1.20 for this whole task, re-rents included, from the Fix-sleep thread's $2 (Ben, 12:59 UTC 09-26) (standing caps: <=$4 per job, $30 total; the Director keeps the ledger and may lower this). Label: claude-fixsleep-dl4b.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $1.50: rent nothing, stop with CREDIT-STOP (vast auto-refills, per Ben via the Director; the gate only guards the $1.20 cap). Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $1.10 kill running commands by exact PID, copy back what exists (dl4_results.json is rewritten after every arm-seed), destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl4-20260926/gpu or a live instance is labelled rent-dl4, rent-dl4b or claude-fixsleep-dl4b.

YOUR TASK: dl-4, the registered run (seven copy-practice nights with vs without a KL anchor to the base on general text, on MiniCPM5-1B; one GPU run). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-dl4-20260926/PASSMARKS.md and the docstring of scripts/claude_dl4_anchor.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the same model files as dl-2, no new download). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py scripts/claude_dl3_replay.py scripts/claude_dl4_anchor.py artifacts/claude-dl4-20260926/PASSMARKS.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_dl4_anchor.py --selftest` prints "selftest ok", else stop.
3. One process, with a log:
   python -B scripts/claude_dl4_anchor.py --model BASE --out gpu
   Expect roughly 85-105 minutes (dl-3 took 81 min on a 5090; the anchor adds one extra forward pass per anchor item). If it has not printed "[dl4] S s6 night 1" after 45 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl4_results.json, gpu/anchor_pool.json and the log back as artifacts/claude-dl4-20260926/gpu/dl4_results.json, gpu/anchor_pool.json and gpu/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu.md in artifacts/claude-dl4-20260926/: the whole "marks" block of dl4_results.json, then each mark F1-F5 (K arm), the verdict and the proved-wrong clause with integer counts, pool_size, GPU name, wall minutes, dollars, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl4-20260926/gpu artifacts/claude-dl4-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
