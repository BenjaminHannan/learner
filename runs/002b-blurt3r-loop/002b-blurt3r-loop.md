COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: yes (BensPC; Ben 02:12 UTC 09-25: tonight's GPU jobs run on his PC. One job at a time, after whatever the director has queued ahead of it. Free, no rental: never rent for this task.)

YOUR TASK: blurt3r-loop, the registered replication of blurt-3 (one GPU run). The creative thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (the test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-blurt2-20260925/PASSMARKS-blurt3.md (section "Replication blurt-3r") and the docstring of scripts/claude_blurt2.py.
Needs: torch with CUDA, transformers (the text-predict benchmark venv on BensPC, as in blurt2-loop; launch detached so the process survives SSH closing), plain MiniCPM5-1B (already on BensPC, thinking off; no download). No other packages.

1. Copy `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_cre333b_agent.py artifacts/claude-blurt1-dev-20260925/puzzles.jsonl artifacts/claude-blurt2-20260925/PASSMARKS-blurt3.md` to BensPC and extract, keeping the paths. BASE = the local MiniCPM5-1B folder.
2. Check: `python -B scripts/claude_blurt1.py make --out pzcheck --n 60 --seed 1`, then compare pzcheck/puzzles.jsonl with artifacts/claude-blurt1-dev-20260925/puzzles.jsonl byte for byte (fc /b on Windows). Must be identical after normalising line endings (the blurt2-loop run found CRLF only), else stop.
3. One process, with a log (it prints progress lines):
   python -B scripts/claude_blurt2.py loop --model BASE --out gpu-3r --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 6 --test-seed 781 --n-test 80 --luck
   If it has not reached the "[loop] practice:" line after 3 hours, stop it and report TOO-SLOW with the last log lines.
4. Copy gpu-3r/loop_summary.json, gpu-3r/wins/wins.jsonl and the log back to the Mac as artifacts/claude-blurt2-20260925/gpu-3r/loop_summary.json, gpu-3r/wins.jsonl, gpu-3r/log_loop.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu-3r.md in artifacts/claude-blurt2-20260925/: the whole loop_summary.json, then U1 and U2 from PASSMARKS-blurt3.md (section "Replication blurt-3r") with integer counts and PASS / FAIL / INCONCLUSIVE, GPU name, wall minutes, model commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-blurt2-20260925/gpu-3r artifacts/claude-blurt2-20260925/RESULTS-gpu-3r.md artifacts/fable-predictions-ledger.md
