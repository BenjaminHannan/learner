COMMON RULES (the benchmarks thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time). NO RENTALS, whatever fails (the vast.ai account is out of credit).
TIME CAP: 7 hours in total. If the cap is reached, stop, copy back what exists, report which commands finished.

YOUR TASK: bench-bm390w, THE REGISTERED RUN bm-390, second attempt on BensPC. The first attempt (001-bench-bm390) stopped at its smoke test: the sealed turn log and notebook check their own writes byte for byte, and Windows writes "\n" as "\r\n" (origin/builder-outbox:artifacts/claude-bm390-20260925/RESULTS-benspc.md). This attempt runs every command through scripts/claude_winnl_wrap.py, which makes Windows write text files with Linux line endings. Nothing sealed changes; the one difference is registered in artifacts/claude-bm390-20260925/AMEND-winnl.md. Read it, PASSMARKS.md and design/v3/30-modes/390-public-bench-plan.md. Run ONCE.
DUPLICATE GUARD, before anything else: stop with DUPLICATE if artifacts/claude-bm390-20260925/run or RESULTS-rent.md exists on origin/builder-outbox, or if origin/builder-outbox has no runs/rent-bm390/rent-bm390.exit (the refused rental task must have ended first). The benchmark files are public test sets: the scripts download and read them; you never open, print or quote a question, an answer or a reply (count rows only). Nothing is trained. Edit no file.

SETUP (Windows, as the first attempt, which set up everything below):
- Tree: design/v3/30-modes/330-rent-kit.md section A (git archive origin/builder-outbox, then origin/main on top, self122_head.pt copied in, sha256 5ca02173...), copied to BensPC as a NEW folder C:/Users/benja/lis301/work/bm390/tree2 (leave the first attempt's tree as it is).
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe. Env for every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1.
- READER = C:/Users/benja/lis301/work/run/merged (model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890). BASE = C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc.
- Q2DIR and L12DIR = the two paths in RESULTS-benspc.md (already downloaded; download nothing). If either is missing, that rival is NOT RUN.
- MiniLM and pyarrow were set up by the first attempt; check only: the route122 check from the tree root prints a route, and `python -c "import pyarrow"` works. Install nothing.
- DATA = C:/Users/benja/lis301/work/bm390/data2 (a NEW folder). OUT = artifacts/claude-bm390-20260925/run (inside the tree).
- W = `python -B scripts/claude_winnl_wrap.py` (every command below starts with it). Its first printed line must be: winnl: Windows text-mode writes use Linux line endings (newline=''). If it prints anything else, stop with WINNL-FAIL.

STEPS
1. From the tree root: `sha256sum -c` (or the same check in Python) of artifacts/claude-bm390-20260925/SEAL-code.sha256.txt (8 OK), artifacts/claude-bm390-20260925/SEAL-winnl.sha256.txt (3 OK) and artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt (229 OK). Any mismatch: stop with SEAL-MISMATCH, report the failing lines.
2. Sleep's base checkpoint: `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/bm390/r44b`, then copy r44b/base-seed4102.pt to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in the tree. Report the JSON line and the .pt sha256.
3. `python -B scripts/claude_bm390.py fetch --data DATA` must print one line starting {"fetch": "OK" with locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300, mmlu300_sha256 1a44e3041355e7fcc1e4d2b188dec0f2362a2ceb9820f62acd957b29909e3850, gsm8k300_sha256 073acc01184dc13caa732adf33fb9d69e049153549d8364401f4320ca0bc555b. Report it verbatim. Anything else: stop, report the exact error.
   Load check, each separately: `python -c "import torch; from transformers import AutoModelForCausalLM as M; m=M.from_pretrained(r'Q2DIR', dtype=torch.bfloat16).to('cuda'); print(type(m).__name__, sum(p.numel() for p in m.parameters()))"` and the same with L12DIR (expected Qwen3_5ForCausalLM 1881825088; Lfm2ForCausalLM 1170340608).
4. SMOKE on made-up data (fictional people, not a benchmark). This is the Windows check the Director asked for:
   SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=C:/Users/benja/lis301/work/bm390/smoke2/sleep_P.jsonl W scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo --data artifacts/claude-bm390-20260925/smoke --arm agent:claude_e2e330c:build_330c --name P --also-bare --model READER --gen-model BASE --out C:/Users/benja/lis301/work/bm390/smoke2
   W scripts/claude_bm390.py locomo --data artifacts/claude-bm390-20260925/smoke --arm plain:BASE --name T --out C:/Users/benja/lis301/work/bm390/smoke2
   Both exit 0 and print "wrote locomo_... rows=5"; the smoke sleep log has 2 rows, both checkpoint_exists true. Also count "\r\n" in every file under smoke2 (a byte count only): it must be 0. If anything fails: stop with SMOKE-FAIL, report the exact error and full traceback, run nothing on the real data. Report the smoke wall time.
5. Registered arms. Each command is its own process, launched ONCE (check the process list before any retry). Two lanes:
   Lane 1, in this order:
     P:   SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=artifacts/claude-bm390-20260925/run/sleep_P.jsonl W scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo --data DATA --arm agent:claude_e2e330c:build_330c --name P --also-bare --model READER --gen-model BASE --out OUT
     Pm:  W scripts/claude_bm390.py general --task mmlu --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT
     Pg:  W scripts/claude_bm390.py general --task gsm8k --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT
   Lane 2, in this order (plain models, LoCoMo first):
     T:   W scripts/claude_bm390.py locomo --data DATA --arm plain:BASE --name T --out OUT
     Rb:  W scripts/claude_bm390.py locomo --data DATA --arm bm25:BASE --name Rb --out OUT
     C:   W scripts/claude_bm390.py locomo --data DATA --arm closed:BASE --name C --out OUT
     Q2:  W scripts/claude_bm390.py locomo --data DATA --arm plain:Q2DIR --name Q2 --out OUT
     L12: W scripts/claude_bm390.py locomo --data DATA --arm plain:L12DIR --name L12 --out OUT
     Tm, Tg: W scripts/claude_bm390.py general --task mmlu|gsm8k --data DATA --arm plain:BASE --name T --out OUT
     Q2m, Q2g, L12m, L12g: the same general commands with plain:Q2DIR --name Q2 and plain:L12DIR --name L12
   Start lane 1. Once P has printed its first "[bm390] conv-" line, start lane 2 at the same time if nvidia-smi shows at least 8 GB of GPU memory free; otherwise run lane 2 after lane 1. If P stops with SLEEP-NOT-LEARNING or STATE-RESET-FAILED: stop lane 1, let lane 2 finish, copy back what exists, report. A lane-2 command that fails does not stop the others; report its traceback. At the time cap, stop what is still running (exact PID) and copy back what finished.
6. Copy run/ back to the Mac; check sizes and sha256 match BensPC. Leave the models on BensPC.
7. RESULTS-benspc2.md (a NEW file) in artifacts/claude-bm390-20260925/, counts only: the three seal results; step 2's JSON line and sha256; the fetch line; the load-check lines (or errors); the smoke result, its "\r\n" byte count and wall time; for each command its first printed line (the winnl line), last printed "wrote ..." line, exit code, start and end time (UTC); the row count of every run/*.jsonl file; the count of "\r\n" in every run/ file; for sleep_P.jsonl: rows, rows with checkpoint_exists true, rows with attempted true; lane 2 parallel or after; GPU; any traceback in full. Quote no question, answer or reply.
PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc2.md artifacts/claude-bm390-20260925/run
