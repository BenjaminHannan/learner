COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). ONLY the Fix-sleep thread or the Director may stop or destroy claude-fixsleep-dl7. Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $1.00 for this whole task, re-rents included, beyond the Fix-sleep thread's $2; HELD until Ben says yes to this figure (via the Thread manager); the Director releases it to handoff/queue/ only then (standing caps: <=$4 per job, $30 total; the Director keeps the ledger and may lower this). Label: claude-fixsleep-dl7.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $1.50: rent nothing, stop with CREDIT-STOP (vast auto-refills, per Ben via the Director; the gate only guards the cap). Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.95 kill running commands by exact PID, copy back what exists (dl7_results.json is rewritten after every arm-seed), destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl7-20260926/gpu or a live instance is labelled claude-fixsleep-dl7.


YOUR TASK: dl-7, the registered run (seven copy-practice nights without vs with a KL anchor on the base's shaky short facts, on MiniCPM5-1B; one GPU run). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-dl7-20260926/PASSMARKS.md and the docstring of scripts/claude_dl7_fragile.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the same model files as dl-2, revision 87179e5c1f455ef22e6223592d2d61351b525bfc, no new download). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py scripts/claude_dl3_replay.py scripts/claude_dl4_anchor.py scripts/claude_dl7_fragile.py artifacts/claude-dl7-20260926/PASSMARKS.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_dl7_fragile.py --selftest` prints "selftest ok", else stop.
3. One process, with a log, launched detached:
   python -B scripts/claude_dl7_fragile.py --model BASE --out gpu
   Expect roughly 85-95 minutes (dl-4's same-shape run took 85 min on a 5090; the pool step adds a few minutes). If it has not printed "[dl7] S s12 night 1" after 45 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl7_results.json, gpu/fragile_pool.json and the log back as artifacts/claude-dl7-20260926/gpu/dl7_results.json, gpu/fragile_pool.json and gpu/log.txt (force-add; artifacts/ is git-ignored). dl7_results.json is rewritten after every arm-seed, so copy it back on any stop.
5. RESULTS-gpu.md in artifacts/claude-dl7-20260926/: the whole "marks" block of dl7_results.json, then each mark F1-F5 (F arm), the verdict and the proved-wrong clause with integer counts, GPU name, wall minutes, dollars, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl7-20260926/gpu artifacts/claude-dl7-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
