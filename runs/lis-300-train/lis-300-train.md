COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the listener spec: design/v3/60-listener/frame-spec.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open or read items of any TEST-ONLY panel. You may RUN artifacts/claude-lispanel300-20260923 exactly once, in step 6, and only see scores. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main` and `git archive origin/builder-outbox <path>`.
GPU: yes

YOUR TASK: builder for lis-300. Fine-tune our own listener (openbmb/MiniCPM5-1B, Apache 2.0; Ben chose it on 2026-09-23 at 11:01 UTC, which is his yes to download it), pick the confidence threshold on dev, then run the sealed blind panel ONCE. Artifacts go in artifacts/claude-lis300-20260923/. The listener thread (Opus) wrote and CPU-smoke-tested all code. Import it and run it; never edit it. If something breaks, stop and report the exact error. Do not patch the code.

READ FIRST: artifacts/claude-lis300-20260923/PASSMARKS.md (marks, threshold rule), design/v3/60-listener/frame-spec.md, and scripts/claude_lis300_{common,compiler,data,train,read,score,agree}.py.

0. GPU. GPU: yes. Use BensPC (RTX 5070 Ti, free) if it has a working CUDA torch env; check with `python -c "import torch;print(torch.cuda.is_available())"` in <= 10 min. You need torch, transformers >= 5.6, peft, safetensors and huggingface_hub; installing those with pip in a NEW venv is fine. If BensPC is not usable, rent ONE vast.ai RTX 4090/5090 on demand under the rental rules in handoff/queue/269-resume.md:
   - read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it;
   - STOP if another instance is running;
   - ceiling $3.00 and 3 h, enforced by a watchdog;
   - destroy at the end and confirm the instance list is empty;
   - append a ledger line.
   Check `uptime` and `df` first. Weights never go into git.
1. DATA. On the GPU machine, get the repo at origin/main plus origin/builder-outbox:artifacts/claude-own-o0b-20260923 and origin/builder-outbox:artifacts/claude-own-o0a2-20260923. Then run:
   python scripts/claude_lis300_data.py --o0b <o0b dir> --opus artifacts/claude-lis300-20260923/data --agree artifacts/claude-lis300-20260923/data/agreed_ids.txt --o0a2 <o0a2 dir> --out <work>/data
   First check `shasum -a 256 -c artifacts/claude-lis300-20260923/SEAL.sha256.txt` from the repo root: it must be all OK. Record the printed counts.
2. MODEL. Download openbmb/MiniCPM5-1B from Hugging Face with huggingface_hub.snapshot_download (about 2.1 GB). Record the commit hash and the sha256 of the safetensors file.
3. TRAIN. Run:
   python scripts/claude_lis300_train.py --model <model dir> --data <work>/data --out <work>/run --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 256 --max-minutes 150 --merge
   If it runs out of memory, use --batch 8 once and report it. Keep train_log.jsonl and summary.json.
4. DEV + THRESHOLD. Make <work>/dev_rows.jsonl from <work>/data/dev.jsonl (fields id, turn, prev_reply). Then run:
   python scripts/claude_lis300_read.py --model <work>/run/merged --rows <work>/dev_rows.jsonl --out <work>/dev_pred.jsonl
   Then run claude_lis300_score.py --gold <work>/data/dev.jsonl --pred <work>/dev_pred.jsonl --sweep. Apply the PASSMARKS threshold rule exactly: T is the smallest grid value with 0 wrong-save turns on the whole dev set, else 0.995. Write T to THRESHOLD.txt along with the sweep table. Also report the dev numbers for each src (o0b_l2, opus_dev, o0a2) at T.
5. SEAL. Run sha256 over THRESHOLD.txt, the merged model's safetensors, and the dev sweep output. Put the hashes in SEAL-run.sha256.txt BEFORE opening the panel.
6. PANEL, run ONCE. Check `shasum -a 256 -c artifacts/claude-lispanel300-20260923/SEAL-key.sha256.txt` (must be all OK). Then run the reader on panel.jsonl, and score it against the key file that seal names, at T and also at T = 0 (the latter is report only). Never print or quote panel turns. Report by category only.
7. RESULTS.md, result first:
   - each P300.n with integer counts, PASS/FAIL;
   - wrong facts per saved fact and per turn;
   - recall by family;
   - device, median/p90/max read ms;
   - training minutes and tok/s;
   - dollars spent.
   Append ledger lines P300.1 to P300.6 (cat >> artifacts/fable-predictions-ledger.md).
8. KEEP THE MODEL. Copy <work>/run/merged to the Mac at ~/premonition-models/lis300-merged/ (make the folder) and record its sha256 in RESULTS.md. The chat page will load it from there later. Also keep it on BensPC if trained there. Never push weights.
PUSH: artifacts/claude-lis300-20260923/{RESULTS.md,THRESHOLD.txt,SEAL-run.sha256.txt,dev_sweep.txt,panel_score.json,panel_score_T0.json,train_summary.json,train_log.jsonl} artifacts/fable-predictions-ledger.md
