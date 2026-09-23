COMMON RULES (the director, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the plan: design/v3/50-own-model/01-own-ear-mouth-plan.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
GPU: rent

YOUR TASK: builder for own-M1. Fine-tune the conversational mouth, then measure it on dev ONCE. Artifacts go in artifacts/claude-own-m1-20260923/. The own-model thread (Opus) wrote all the code, smoke-tested it on CPU and sealed it (SEAL-code.sha256.txt). Import and run it; never edit it. If something breaks, stop and report; do not patch it.
READ FIRST: artifacts/claude-own-m1-20260923/PASSMARKS.md and scripts/claude_own_m1_{common,data,speak}.py (on origin/main).
INDEPENDENCE: never open any TEST-ONLY panel, any artifacts/claude-*panel* folder, artifacts/claude-own-bench-20260923, or ANY convbench-f0 file.

0. GPU: rent. Rent ONE vast.ai RTX 5090 (4090 if no 5090 is available) on demand, following the rental rules in handoff/queue:
   - read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it;
   - check the ledger first: stop if the rental total would pass $30;
   - this task's ceiling is $4.00 and 3 h, enforced by a watchdog;
   - destroy the instance at the end and confirm your instance is gone;
   - append a ledger line.
   Check `uptime` and `df` first. Weights never go into git. On the GPU machine, put torch, transformers >= 5.6, peft, safetensors and huggingface_hub in a NEW venv.
1. CODE + DATA. Get the repo at origin/main, and the M0 data from origin/builder-outbox:artifacts/claude-own-m0-20260923. From the repo root:
   - run `shasum -a 256 -c artifacts/claude-own-m1-20260923/SEAL-code.sha256.txt` (sha256sum -c on Linux); every line must be OK, otherwise stop;
   - run python scripts/claude_own_m1_data.py --m0 <m0 dir> --out <work>/data and record the printed counts.
2. MODEL. huggingface_hub.snapshot_download("openbmb/MiniCPM5-1B") (Ben chose it 2026-09-23 11:01 UTC). Record the commit hash.
3. TRAIN. python scripts/claude_lis300_train.py --model <model dir> --data <work>/data --out <work>/run --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 256 --max-minutes 120 --merge
   If it runs out of memory, use --batch 8 once and report it.
4. SEAL. Put sha256 of the merged safetensors and <work>/data/counts.json in artifacts/claude-own-m1-20260923/SEAL-run.sha256.txt BEFORE step 5.
5. MEASURE ONCE. python scripts/claude_own_m1_speak.py --model <work>/run/merged --data <work>/data/dev.jsonl --out <work>/dev_out.jsonl
   Then recount Pm1.3 yourself: re-run slot_check on every non-null reply's winning raw text (the last non-empty raw); the count of failures must be 0.
   Also quote 20 random dev_out rows (dev material, fictional names): the record status, user_turn and filled reply.
6. RESULTS.md, verdict first: every Pm1.n with integer counts and PASS/FAIL, fallbacks per status, speak ms, training minutes, tok/s, dollars. Append ledger lines Pm1.1 to Pm1.5 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE MODEL. Copy <work>/run/merged to the Mac at ~/premonition-models/own-m1-mouth/ and record its sha256 in RESULTS.md. Never push weights.
PUSH: artifacts/claude-own-m1-20260923/RESULTS.md artifacts/claude-own-m1-20260923/SEAL-run.sha256.txt artifacts/claude-own-m1-20260923/dev_summary.json artifacts/claude-own-m1-20260923/dev_out_sample.jsonl artifacts/claude-own-m1-20260923/train_summary.json artifacts/claude-own-m1-20260923/train_log.jsonl artifacts/fable-predictions-ledger.md
