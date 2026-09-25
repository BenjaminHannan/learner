COMMON RULES (the grammar thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time). NO RENTALS, whatever fails.
TIME CAP: 1.5 hours in total (the same run took ~20 minutes on a rented 5090). If the cap is reached, stop, copy back what exists, report which commands finished.

YOUR TASK: gram-364-benspc, THE REGISTERED RUN of gram-364 (fill-in finisher v2). Marks: artifacts/claude-gram364-20260925/PASSMARKS.md (do not edit it). One arm on bank H (artifacts/claude-gram364-bankH-20260925, sealed test data: the runner reads it; you never open, print or quote its turns, truth or any reply). Run ONCE.
DUPLICATE GUARD, before anything else: stop with DUPLICATE if artifacts/claude-gram364-20260925/run or RESULTS-benspc.md exists on origin/builder-outbox.

SETUP (Windows, exactly as bench-bm390x, handoff/queue/001-bench-bm390x.md SETUP):
- Tree: design/v3/30-modes/330-rent-kit.md section A (git archive origin/builder-outbox, then origin/main on top, self122_head.pt copied in, sha256 5ca02173...), copied to BensPC as a NEW folder C:/Users/benja/lis301/work/gram364/tree.
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe. Env for every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1.
- READER = C:/Users/benja/lis301/work/run/merged (model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890). BASE = C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc. Download nothing, install nothing.
- W = `python -B scripts/claude_winnl2_wrap.py`. Its first printed line must be: winnl2: Windows text-mode writes use Linux line endings (newline=''). Otherwise stop with WINNL-FAIL.
- RUN = artifacts/claude-gram364-20260925/run (inside the tree; create it; gram364_parts.jsonl must not exist before step 4).

STEPS (from the tree root)
1. Seals: `sha256sum -c` (or the same check in Python) of artifacts/claude-gram364-bankH-20260925/SEAL.sha256.txt run from inside that folder (4 OK) and artifacts/claude-gram364-20260925/SEAL-code.sha256.txt from the tree root (9 OK). Any mismatch: stop with SEAL-MISMATCH.
2. Tests, each must print exactly: `python -B scripts/claude_gram364_test.py` "gram364 tests: 45/45 OK"; `python -B scripts/claude_gram360_test.py` "gram360 tests: 16/16 OK"; `python -B scripts/claude_chat338b_test.py` "338b tests: 3/3 OK"; `python -B scripts/claude_cre333d_test.py` "333d tests: 2/2 OK"; `python -B scripts/claude_vary330c_test.py` "vary330c tests: 2/2 OK". W CHECK: `W scripts/claude_winnl2_test.py probe` prints "ok": true and "crlf": 0. Any other output: stop, report it.
3. Sleep's base checkpoint (the agent includes sleep): `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/gram364/r44c`, then copy r44c/base-seed4102.pt to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in the tree. Report the JSON line and the .pt sha256.
4. The arm (first printed lines: the winnl2 line, then "twinb: the plain twin is Twin336b (enable_thinking=False)"):
   GRAM360_LOG=artifacts/claude-gram364-20260925/run/gram364_parts.jsonl W scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank artifacts/claude-gram364-bankH-20260925 --arm claude_e2e364:build_364 --name P364 --model READER --gen-model BASE --out artifacts/claude-gram364-20260925/run
5. `W scripts/claude_e2e336_score.py --bank artifacts/claude-gram364-bankH-20260925 --runs artifacts/claude-gram364-20260925/run/arm_P364.jsonl --out artifacts/claude-gram364-20260925/score`
6. `W scripts/claude_gram364_check.py --bank artifacts/claude-gram364-bankH-20260925 --run artifacts/claude-gram364-20260925/run/arm_P364.jsonl --log artifacts/claude-gram364-20260925/run/gram364_parts.jsonl --out artifacts/claude-gram364-20260925/check`
7. Count "\r\n" in every file under run/, score/ and check/ (a byte count only; expected 0). Copy run/, score/ and check/ back to the Mac; check sizes and sha256 match BensPC.
8. RESULTS-benspc.md (a NEW file) in artifacts/claude-gram364-20260925/, counts only: the seal results; each test line and the W CHECK line; step 3's JSON line and sha256; the arm's first two printed lines, last "wrote ..." line, exit code, start and end time (UTC); the scorer's printed line; the checker's last printed line (its WORDS/ASK lines as counts only); the "\r\n" counts; GPU; any traceback in full. Do not quote any reply or turn text. Do not open any check/*.jsonl file.
PUSH: artifacts/claude-gram364-20260925/RESULTS-benspc.md artifacts/claude-gram364-20260925/run artifacts/claude-gram364-20260925/score artifacts/claude-gram364-20260925/check
