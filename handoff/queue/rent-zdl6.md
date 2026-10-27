COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). ONLY the Fix-sleep thread or the Director may stop or destroy claude-fixsleep-dl6. Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $0.80 for this whole task, re-rents included, from the Fix-sleep thread's $2 (Ben, 12:59 UTC 09-26) (standing caps: <=$4 per job, $30 total; the Director keeps the ledger and may lower this). Label: claude-fixsleep-dl6.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $1.50: rent nothing, stop with CREDIT-STOP (vast auto-refills, per Ben via the Director; the gate only guards the cap). Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.75 kill running commands by exact PID, copy back what exists (dl6_results.json is rewritten after every arm-seed), destroy, stop with BUDGET-STOP. Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch the run detached (nohup/setsid) so it survives SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl6-20260926/gpu or a live instance is labelled claude-fixsleep-dl6.


YOUR TASK: dl-6, the registered run (seven copy-practice nights at 3 epochs vs 1 epoch per night, on MiniCPM5-1B; one GPU run). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-dl6-20260926/PASSMARKS.md and the docstring of scripts/claude_dl6_light.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the same model files as dl-2, revision 87179e5c1f455ef22e6223592d2d61351b525bfc, no new download). No other packages.

1. On the rental: `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py scripts/claude_dl3_replay.py scripts/claude_dl6_light.py artifacts/claude-dl6-20260926/PASSMARKS.md`, extract keeping the paths.
2. Check: `python -B scripts/claude_dl6_light.py --selftest` prints "selftest ok", else stop.
3. One process, with a log, launched detached:
   python -B scripts/claude_dl6_light.py --model BASE --out gpu
   Expect roughly 55-65 minutes (dl-2's same-size run took 67 min on a 5090; the L arm trains a third as long). If it has not printed "[dl6] S s10 night 1" after 40 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl6_results.json and the log back as artifacts/claude-dl6-20260926/gpu/dl6_results.json and gpu/log.txt (force-add; artifacts/ is git-ignored). dl6_results.json is rewritten after every arm-seed, so copy it back on any stop.
5. RESULTS-gpu.md in artifacts/claude-dl6-20260926/: the whole "marks" block of dl6_results.json, then each mark F1-F5 (L arm), the verdict and the proved-wrong clause with integer counts, GPU name, wall minutes, dollars, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl6-20260926/gpu artifacts/claude-dl6-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
