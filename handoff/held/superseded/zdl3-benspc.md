COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, no secrets, report in your final reply: verdict first, integer counts, every deviation).
GPU: yes (BensPC RTX 5070 Ti; one job at a time). NO RENTALS.
TIME CAP: 5 hours in total. If the cap is reached, stop by exact PID, copy back what exists (dl3_results.json is rewritten after every arm-seed), report which arm-seeds finished.
WHEN TO RUN (Director): only if rent-zdl3 ended with CREDIT-STOP or never started, and BensPC is free. Move this file from handoff/held/ to handoff/queue/ as zdl3-benspc.md.
DUPLICATE GATE, first: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-dl3-20260926/gpu, or a rent-dl3 instance is live.

YOUR TASK: dl-3, the registered run, on BensPC instead of a rental (same code, same command; the hardware is the only difference, and it is reported). The Fix-sleep thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved.
READ FIRST (origin/main): artifacts/claude-dl3-20260926/PASSMARKS.md and the docstring of scripts/claude_dl3_replay.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B (thinking off; the copy already on BensPC, no new download). Run every command through scripts/claude_winnl_wrap.py if it exists on origin/main (Linux line endings on Windows).
1. `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_dl1_nights.py scripts/claude_dl3_replay.py scripts/claude_winnl_wrap.py artifacts/claude-dl3-20260926/PASSMARKS.md` into a fresh folder, keeping the paths.
2. Check: `python -B scripts/claude_dl3_replay.py --selftest` prints "selftest ok", else stop.
3. One process, with a log: `python -B scripts/claude_dl3_replay.py --model BASE --out gpu`. If it has not printed "[dl3] S s4 night 1" after 80 minutes, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/dl3_results.json, gpu/replay_pool.json and the log back as artifacts/claude-dl3-20260926/gpu/dl3_results.json, gpu/replay_pool.json and gpu/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-benspc.md in artifacts/claude-dl3-20260926/: the whole "marks" block, each mark F1-F5, the verdict and proved-wrong clause with integer counts, pool_size, GPU name, wall minutes, commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-dl3-20260926/gpu artifacts/claude-dl3-20260926/RESULTS-benspc.md artifacts/fable-predictions-ledger.md
