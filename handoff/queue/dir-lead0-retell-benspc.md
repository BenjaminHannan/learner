GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, NO rental, whatever fails). If C:\Users\benja\GPU-BUSY.txt names any job other than this file's name without .md, stop with BUSY and run nothing. Additive only, no secrets, download nothing, install nothing.
Owner: Director helper "Lead 0" (Claude, 2026-09-28). Read-only check, no training. Pass marks sealed before the run: artifacts/claude-dir-lead0-20260928/PASSMARKS.md (PASS = 95 of 100 or more exact on BOTH grid seeds).
WHERE: you run on the Mac; BensPC (Windows) is reached with `ssh benspc`. Every BensPC command runs on BensPC. Stream the tree with `git archive origin/main scripts | ssh benspc "tar -x -C <folder>"`; copy results back with scp.
SETUP: Python C:/Users/benja/lis300/venv/Scripts/python.exe. Env: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1.
  L12DIR = C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b (used by the y1v and k1f jobs). If it does not exist, stop with MODEL-MISSING and download nothing.
STEPS (from the tree root):
1. `python -B scripts/claude_dir_lead0_retell.py selftest` must print "lead0 selftest 3/3 ok". Else stop.
2. `python -B scripts/claude_dir_lead0_retell.py run --model L12DIR --out run_lead0 --seeds 1,2 --n 100 > log.txt` (four arms of 100 chats, minutes). Log must show four lines "lead0 seedS_R|N x of 100". Do not retry more than once on out-of-memory.
3. Copy back run_lead0/ (seed1_R.jsonl, seed1_N.jsonl, seed2_R.jsonl, seed2_N.jsonl, summary.json) and log.txt to artifacts/claude-dir-lead0-20260928/run/ on the Mac. These files are DEV-free code-made data; nothing here is a sealed panel.
4. Write artifacts/claude-dir-lead0-20260928/RESULTS.md (NEW file): GPU name, versions, model path, exit code, wall minutes, then a table with integer counts: for seed 1 and 2, arm R: exact x of 100, has grid, solves puzzle, cut off, by size; arm N the same. Verdict per PASSMARKS.md wording (PASS or FAIL), nothing else. Then list up to 5 miss replies verbatim to show the failure mode.
PUSH: artifacts/claude-dir-lead0-20260928/run artifacts/claude-dir-lead0-20260928/RESULTS.md
