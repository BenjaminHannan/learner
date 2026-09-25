COMMON RULES (the creative research thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: yes (BensPC. One job at a time, after whatever the director has queued ahead of it. Free, no rental: never rent for this task.)

YOUR TASK: blurt4-loop, the registered run of blurt-4 (hindsight hits; one GPU run). The creative thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. No TEST-ONLY panel is involved (the test puzzles are made inside the run and never printed).
READ FIRST (origin/main): artifacts/claude-blurt4-20260925/PASSMARKS-blurt4.md and the docstring of scripts/claude_blurt4.py.
Needs: torch with CUDA, transformers (the text-predict benchmark venv on BensPC, as in blurt3r-loop; launch detached so the process survives SSH closing, e.g. the scheduled-task method that worked for blurt3r), plain MiniCPM5-1B (already on BensPC, thinking off; no download). No other packages.

1. Copy `git archive origin/main scripts/claude_blurt1.py scripts/claude_blurt2.py scripts/claude_blurt4.py scripts/claude_cre333b_agent.py artifacts/claude-blurt1-dev-20260925/puzzles.jsonl artifacts/claude-blurt4-20260925/PASSMARKS-blurt4.md` to BensPC and extract, keeping the paths. BASE = the local MiniCPM5-1B folder.
2. Check: `python -B scripts/claude_blurt4.py --selftest` prints "selftest ok"; and `python -B scripts/claude_blurt1.py make --out pzcheck --n 60 --seed 1`, then compare pzcheck/puzzles.jsonl with artifacts/claude-blurt1-dev-20260925/puzzles.jsonl (identical after normalising line endings), else stop.
3. One process, with a log:
   python -B scripts/claude_blurt4.py --model BASE --out gpu-4 --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 8 --test-seed 783 --n-test 80
   If it has not reached the "[b4] practice:" line after 3 hours, stop it and report TOO-SLOW with the last log lines. (blurt3r took 31 min in total; this one trains 6 adapters instead of 4, expect about 45 min.)
4. Copy gpu-4/blurt4_summary.json and the log back to the Mac as artifacts/claude-blurt4-20260925/gpu-4/blurt4_summary.json and gpu-4/log.txt (force-add; artifacts/ is git-ignored).
5. RESULTS-gpu-4.md in artifacts/claude-blurt4-20260925/: the whole blurt4_summary.json, then H1 and H2 from PASSMARKS-blurt4.md with integer counts and PASS / FAIL / INCONCLUSIVE, GPU name, wall minutes, model commit hash. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-blurt4-20260925/gpu-4 artifacts/claude-blurt4-20260925/RESULTS-gpu-4.md artifacts/fable-predictions-ledger.md
