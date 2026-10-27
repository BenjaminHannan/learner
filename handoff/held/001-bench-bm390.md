COMMON RULES (the benchmarks thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time). Ben asked for tonight's GPU work on his PC: NO RENTALS, whatever fails.
TIME CAP: 7 hours in total. If the cap is reached, stop, copy back what exists, report which commands finished.

YOUR TASK: bench-bm390, THE REGISTERED RUN bm-390: Premonition 0.1 against plain same-size models on public benchmarks (LoCoMo, MMLU-Redux, GSM8K). Marks: artifacts/claude-bm390-20260925/PASSMARKS.md; plan: design/v3/30-modes/390-public-bench-plan.md. Read both. Run ONCE. If artifacts/claude-bm390-20260925/run already exists on origin/builder-outbox, stop with DUPLICATE. The benchmark files are public test sets: the scripts download and read them; you never open, print or quote a question, an answer or a reply (count rows only). Nothing is trained.

SETUP (Windows, as benspc-336b / smoke-336-win):
- Tree: design/v3/30-modes/330-rent-kit.md section A (git archive origin/builder-outbox, then origin/main on top, self122_head.pt copied in, sha256 5ca02173...), copied to BensPC as a NEW folder C:/Users/benja/lis301/work/bm390/tree. scripts/claude_bm390.py and scripts/claude_sleepcheck_wrap.py put scripts/winshim on the path themselves on Windows.
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe. Env for every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 (except the one download command in step 3).
- READER = C:/Users/benja/lis301/work/run/merged (model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890). BASE = C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc.
- MiniLM (the self122 router's model) must be at C:/Users/benja/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2 (from benspc-336b / 000-cache-pin). If missing, copy the Mac's pinned snapshot exactly as handoff/held/benspc-336b.md says (copy, never move; delete nothing). Check from the tree root: `python -B -c "import sys; sys.path[:0]=['scripts','scripts/winshim']; import fable_self122 as S; print(S.route122('what is your name?'))"` prints a route, no error.
- pyarrow (reads the public data files): `python -c "import pyarrow"`; only if that fails, `python -m pip install pyarrow` into the same venv. Install or upgrade nothing else.
- DATA = C:/Users/benja/lis301/work/bm390/data. OUT = artifacts/claude-bm390-20260925/run (inside the tree).

STEPS
1. From the tree root BEFORE anything else: check artifacts/claude-bm390-20260925/SEAL-code.sha256.txt and artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt (sha256sum -c, or the same check in Python): every line OK. Any mismatch: stop with SEAL-MISMATCH, report the failing lines.
2. Sleep's base checkpoint (not in git): `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/bm390/r44` (about 30 s), then copy r44/base-seed4102.pt to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in the tree. Do not write into that runs folder directly. Report the printed JSON line and the .pt sha256.
3. Data and the two rival models (Ben approved both rivals at 02:12 UTC 2026-09-25; these are the ONLY downloads allowed):
   `python -B scripts/claude_bm390.py fetch --data DATA` must print one line starting {"fetch": "OK" with locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300. Report that JSON line verbatim (counts and hashes only). Any DATA-MISMATCH or network error: stop, report the exact error.
   With HF_HUB_OFFLINE=0 for this one command: `python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3.5-2B', revision='15852e8c16360a2fea060d615a32b45270f8a8fc')); print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'))"`. Q2DIR and L12DIR = the two printed paths (about 7 GB in all).
   Load check, each separately: `python -c "import torch; from transformers import AutoModelForCausalLM as M; m=M.from_pretrained(r'Q2DIR', dtype=torch.bfloat16).to('cuda'); print(type(m).__name__, sum(p.numel() for p in m.parameters()))"` and the same with L12DIR. A rival whose load check fails is NOT RUN: skip its commands below, report the exact error. Do not upgrade transformers or anything else for it.
4. SMOKE on made-up data (fictional people, not a benchmark):
   SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=C:/Users/benja/lis301/work/bm390/smoke/sleep_P.jsonl python -B scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo --data artifacts/claude-bm390-20260925/smoke --arm agent:claude_e2e330c:build_330c --name P --also-bare --model READER --gen-model BASE --out C:/Users/benja/lis301/work/bm390/smoke
   python -B scripts/claude_bm390.py locomo --data artifacts/claude-bm390-20260925/smoke --arm plain:BASE --name T --out C:/Users/benja/lis301/work/bm390/smoke
   Both must exit 0 and print "wrote locomo_... rows=5"; the smoke sleep log must have 2 rows, both with checkpoint_exists true. If not: stop with SMOKE-FAIL, report the exact error and full traceback, run nothing on the real data. Report the smoke's wall time.
5. Registered arms. Each command is its own process, launched ONCE (check the process list before any retry; in 336 a retry started a duplicate). Two lanes:
   Lane 1, in this order:
     P:   SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=artifacts/claude-bm390-20260925/run/sleep_P.jsonl python -B scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo --data DATA --arm agent:claude_e2e330c:build_330c --name P --also-bare --model READER --gen-model BASE --out OUT
     Pm:  python -B scripts/claude_bm390.py general --task mmlu --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT
     Pg:  python -B scripts/claude_bm390.py general --task gsm8k --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT
   Lane 2, in this order (plain models; each loads its model once):
     T:   python -B scripts/claude_bm390.py locomo --data DATA --arm plain:BASE --name T --out OUT
     Rb:  python -B scripts/claude_bm390.py locomo --data DATA --arm bm25:BASE --name Rb --out OUT
     C:   python -B scripts/claude_bm390.py locomo --data DATA --arm closed:BASE --name C --out OUT
     Tm:  python -B scripts/claude_bm390.py general --task mmlu --data DATA --arm plain:BASE --name T --out OUT
     Tg:  python -B scripts/claude_bm390.py general --task gsm8k --data DATA --arm plain:BASE --name T --out OUT
     Q2:  python -B scripts/claude_bm390.py locomo --data DATA --arm plain:Q2DIR --name Q2 --out OUT
     Q2m: python -B scripts/claude_bm390.py general --task mmlu --data DATA --arm plain:Q2DIR --name Q2 --out OUT
     Q2g: python -B scripts/claude_bm390.py general --task gsm8k --data DATA --arm plain:Q2DIR --name Q2 --out OUT
     L12, L12m, L12g: the same three commands with plain:L12DIR and --name L12.
   Start lane 1. Once P has printed its first "[bm390] conv-" line, start lane 2 at the same time if nvidia-smi shows at least 8 GB of GPU memory free; otherwise run lane 2 after lane 1. If P stops with SLEEP-NOT-LEARNING or STATE-RESET-FAILED: stop lane 1, let lane 2 finish, copy back what exists, report. A lane-2 command that fails does not stop the others; report its traceback.
6. Copy run/ back to the Mac; check sizes and sha256 match BensPC. Leave the downloaded models on BensPC.
7. RESULTS-benspc.md in artifacts/claude-bm390-20260925/, counts only: seal results (both); step 2's JSON line and sha256; step 3's fetch line, the two model paths and load-check lines (or errors); the smoke result; for each command, its last printed "wrote ..." line, exit code and wall time; the row count of every run/*.jsonl file; for sleep_P.jsonl: rows, rows with checkpoint_exists true, rows with attempted true; lane 2 parallel or after; GPU; any traceback in full. Quote no question, answer or reply.
PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc.md artifacts/claude-bm390-20260925/run
