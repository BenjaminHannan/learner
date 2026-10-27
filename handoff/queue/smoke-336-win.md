COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time).
TIME CAP: 20 minutes in total, and it must end by 20:00 ET.

YOUR TASK: smoke-336-win, REPORT ONLY. Can BensPC (Windows) run the joined month-end agent now that scripts/winshim/resource.py stands in for the Unix-only `resource` module? The answer decides whether Sunday's registered run 336 stays on BensPC. Never edit any code; if something breaks, report the exact error and traceback.

CODE AND MODELS: build the combined tree exactly as design/v3/30-modes/330-rent-kit.md section A says (builder-outbox, then main on top, self122_head.pt copied in), and copy it to BensPC. READER = C:/Users/benja/lis301/work/run/merged (model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890). BASE = the cached openbmb/MiniCPM5-1B snapshot (snapshot_download(..., local_files_only=True)). Use the lis-301 venv (C:/Users/benja/lis300/venv). Set PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.

1. From the tree root: `python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-smoke336win-20260924/run --arm claude_chat338_run:build_P --name smoke --model READER --gen-model BASE --lives e2e-dev-01` (one DEV life, 3 days, 2 sleeps, 2 restarts; the DEV bank is dev data).
2. RESULTS.md: PASS if it wrote arm_smoke.jsonl with one row per turn of that life and exited 0, else FAIL with the exact error and traceback. Also: rows written, median and slowest ms per turn, GPU name, wall time.
PUSH: artifacts/claude-smoke336win-20260924
