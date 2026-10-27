COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: yes (BensPC; Ben 02:12 UTC 09-25: tonight's GPU jobs run on his PC. One job at a time, after whatever the director has queued ahead of it. Free, no rental: never rent for this task.)

YOUR TASK: blurt2-loop, the registered creative learning loop (GPU repeat; the same command also runs on the creative thread's CPU). The creative thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (the test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-blurt2-20260925/PASSMARKS-blurt2.md and the docstring of scripts/claude_blurt2.py.
Needs: torch with CUDA, transformers (the benchmark venv on BensPC), plain MiniCPM5-1B (already on BensPC, thinking off; no download). No other packages.

1. Copy `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_cre333b_agent.py artifacts/claude-blurt1-dev-20260925/puzzles.jsonl artifacts/claude-blurt2-20260925/PASSMARKS-blurt2.md` to BensPC and extract, keeping the paths. BASE = the local MiniCPM5-1B folder.
2. Check: `python -B scripts/claude_blurt1.py make --out pzcheck --n 60 --seed 1`, then compare pzcheck/puzzles.jsonl with artifacts/claude-blurt1-dev-20260925/puzzles.jsonl byte for byte (fc /b on Windows). Must be identical, else stop.
3. One process, with a log (it prints progress lines):
   python -B scripts/claude_blurt2.py loop --model BASE --out gpu --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl
   If it has not reached the "[loop] practice:" line after 3 hours, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu/loop_summary.json, gpu/wins/wins.jsonl and the log back to the Mac as artifacts/claude-blurt2-20260925/gpu/loop_summary.json, gpu/wins.jsonl, gpu/log_loop.txt.
5. RESULTS-gpu.md in artifacts/claude-blurt2-20260925/: the whole loop_summary.json, then L1 and L2 from PASSMARKS-blurt2.md with integer counts and PASS / FAIL / INCONCLUSIVE, GPU name, wall minutes, model commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-blurt2-20260925/gpu artifacts/claude-blurt2-20260925/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
