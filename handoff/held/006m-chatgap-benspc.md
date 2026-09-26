COMMON RULES (the Fix-sleep thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti 16 GB; one job at a time). NO RENTALS. $0.
LOWDISK-OK: yes (runs on BensPC; copies back only small JSON/JSONL files to the Mac, never model weights)
TIME CAP: 2 hours in total. If reached: stop by exact PID, copy back what exists (chatgap_rows.jsonl is appended after every puzzle), report "partial".

YOUR TASK: 006m-chatgap, a DIAGNOSIS (report only, nothing registered, nothing trained). Question: why does sleep's puzzle skill (0.2c: 74 -> 192 right guesses) not show when a puzzle is typed as a chat message (0 of 40 before and after)? Read the docstring of scripts/claude_chatgap_diag.py. Run it ONCE.
DUPLICATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-chatgap-20260926/chatgap_summary.json.
SETUP: reuse the 0.2c tree C:/Users/benja/lis301/work/e2e02c/tree (it holds the trained adapter at artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt and its sidecar adapter02c.json). Do NOT change anything already in that tree: add ONLY scripts/claude_chatgap_diag.py from origin/main (`git show origin/main:scripts/claude_chatgap_diag.py > scripts/claude_chatgap_diag.py`). If the adapter or its sidecar is missing, stop with NO-ADAPTER. Python, env, BASE and READER319 exactly as origin/main:handoff/queue/006k-02c-benspc.md SETUP says (PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1; native Windows paths; nohup+disown and wait ~100 s after launch). Check free VRAM first: nothing else of ours on the GPU unless it is a small capped job leaving >= 8 GB free.
1. From the tree root: `python -B scripts/claude_chatgap_diag.py --selftest` prints "selftest ok", else stop.
2. One process, with a log:
   python -B scripts/claude_twinb_wrap.py scripts/claude_chatgap_diag.py --arm claude_e2e02c:build_02c --model READER319 --gen-model BASE --adapter artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt --out W/chatgap
   (W = C:/Users/benja/lis301/work/e2e02c). Expect 30-60 minutes. A "refusing to load" error (sidecar, sha256 or base mismatch): stop and report it in full; do not work around it.
3. Copy W/chatgap/chatgap_summary.json, W/chatgap/chatgap_rows.jsonl and the log back as artifacts/claude-chatgap-20260926/chatgap_summary.json, chatgap_rows.jsonl, log.txt (force-add; artifacts/ is git-ignored). The rows hold the model's replies to code-made puzzles (no TEST-ONLY item); they may be pushed.
4. RESULTS.md in artifacts/claude-chatgap-20260926/: the summary JSON in full, GPU, wall minutes, commit hash, every deviation.
Never push weights.
PUSH: artifacts/claude-chatgap-20260926
