COMMON RULES (the Answering-from-memory thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (streaming, labels, rental rules, setup, independence). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
DISK: 1
BUDGET: $0.40 for this whole task, re-rents included, from the Answering-from-memory thread's $2 (Ben, 12:59 UTC 09-26); the Director keeps the ledger and may lower it. Label: claude-memory-y1d. Only this thread or the Director may stop or destroy claude-memory-y1d; never destroy any other label.
CREDIT: check and record the balance number only (vast auto-refills, per Ben); no credit stop.
TIME CAP: 45 minutes on the rental. If reached: stop by exact PID, copy back what exists (y1d_rows.jsonl is appended after every ask), destroy, report PARTIAL.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-y1d-20260926/gpu, or a live instance is labelled claude-memory-y1d.

YOUR TASK: y1d, a DIAGNOSIS on DEV data (readable, no TEST-ONLY bank or panel is involved): the plain MiniCPM5-1B answers the DEV bank's memory asks from raw chat turns, three ways. The thread wrote the code; run it, never edit it. If something breaks, stop and report the exact error and traceback; do not patch.
READ FIRST (origin/main): artifacts/claude-y1d-20260926/PLAN.md and the docstring of scripts/claude_y1d_readchat.py.
Needs: torch with CUDA, transformers, plain MiniCPM5-1B and all-MiniLM-L6-v2, both from the rent kit's section C download (Ben's yes covers both; no other model). NO reader weights: nothing is copied from the Mac but code.

1. Stream only code and data (nothing staged on the Mac): `git archive origin/main scripts artifacts/claude-e2e331-dev-20260924 artifacts/claude-y1d-20260926 | ssh <rental> 'mkdir -p ~/tree && tar -x -C ~/tree'`.
2. Rent kit section C setup (torch check, pip line, snapshot_download of MiniCPM5-1B and all-MiniLM-L6-v2, HF_HUB_OFFLINE=1). Record the MiniCPM commit hash (expected 87179e5c1f455ef22e6223592d2d61351b525bfc).
3. Checks, from ~/tree: `sha256sum -c artifacts/claude-y1d-20260926/SEAL-y1d.sha256.txt` (all OK, else stop with SEAL-FAIL) and `python -B scripts/claude_y1d_readchat.py --selftest` prints "selftest ok" (else stop).
4. One process, detached, with a log:
   nohup python -B scripts/claude_y1d_readchat.py --model BASE --out gpu > gpu_log.txt 2>&1 &
   Expect roughly 10-25 minutes (71 asks x 3 conditions, 4 samples + 1 greedy each, 1B on one GPU). It prints one "[y1d]" line per ask. No new line for 10 minutes: stop it and report STALLED with the last log lines.
5. Copy gpu/y1d_rows.jsonl, gpu/y1d_summary.json and gpu_log.txt back as artifacts/claude-y1d-20260926/gpu/y1d_rows.jsonl, gpu/y1d_summary.json and gpu/log.txt (force-add; artifacts/ is git-ignored). Check they arrived, then destroy and confirm it is gone.
6. RESULTS-gpu.md in artifacts/claude-y1d-20260926/: the last printed JSON line (answerable_right, never_told_idk), the whole "counts" block of y1d_summary.json, GPU name, MiniCPM commit, wall minutes, dollars, instance id. DEV data may be read and quoted. Append one ledger line (cat >> artifacts/fable-predictions-ledger.md).
Never push weights (the run saves none).
PUSH: artifacts/claude-y1d-20260926/gpu artifacts/claude-y1d-20260926/RESULTS-gpu.md artifacts/fable-predictions-ledger.md
