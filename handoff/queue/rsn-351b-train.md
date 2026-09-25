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

RENTAL RULES:
- Search offers with reliability >= 0.98 (vastai search offers 'gpu_name=RTX_5090 reliability>=0.98 rentable=true' -o dph), preferring at least 16 CPU cores (use a host with >= 32 cores if one is within $0.10/h of the cheapest; the practice generator is CPU-heavy). 4090 with the same filter if no 5090.
- Before renting: `vastai show instances`; if an instance labelled fair351b is live and healthy, exit and report DUPLICATE.
- Label every instance fair351b (NOT rsn-351..., so rsn-351's guard never counts it). Never touch an instance with any other label (another job, e.g. rent-336, may be live at the same time).
- MONEY (Ben 2026-09-23 21:51 UTC: "don't use gpu rentals above 4$"): $4 is the COMBINED limit for this whole task, re-rents included. Keep a running total of dph x hours for every instance you create. If the total would pass $3.80, destroy everything and stop with BUDGET-STOP. A separate guard task (rsn-351b-guard, which watches the label fair351b) also watches this.
- If a new instance is not "running" within 6 min (or create returns success: False), destroy it by exact id and try the next offer on a different host, up to 4 rentals in total. If a running instance goes offline or shows no log progress for 10 min, destroy it and count it. After 4 failures stop with HOST-FAIL. Never 2 fair351b instances at once.
- Read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Destroy the instance at the end and confirm it is gone. Append a ledger line.

YOUR TASK: builder for rsn-351b (rsn-296's plain 30M arm with ONE change: learning rate 1e-4 instead of 3e-4, via the existing --lr flag). The sleep research thread (Opus) wrote and sealed everything; run it, never edit code. If something breaks, stop and report; do not patch. Artifacts go in artifacts/claude-rsn351b-20260925/.
READ FIRST (on origin/main): artifacts/claude-rsn351b-20260925/PASSMARKS.md and the docstrings of scripts/claude_rsn296_run.py and scripts/claude_rsn294_run.py.
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. Run the eval commands below exactly once per checkpoint; they write category-level counts only.

0. Rent as above. New venv with torch (CUDA) and numpy only. Check `nproc`, `nvidia-smi`, `df -h`.
1. CODE. git archive / clone of origin/main. From the repo root, `sha256sum -c` on artifacts/claude-rsn351b-20260925/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt: every line OK, else stop. `python scripts/claude_rsn296_gen.py` prints "selftest ok".
2. TRAIN both seeds at once (--workers 8 each; defaults otherwise):
   python scripts/claude_rsn296_run.py train --arm plain --lr 1e-4 --seed 1 --out W/plain30lr-s1 --workers 8
   python scripts/claude_rsn296_run.py train --arm plain --lr 1e-4 --seed 2 --out W/plain30lr-s2 --workers 8
   If after 10 minutes the copy-phase "min" values project a total over 150 minutes wall or over $3.40, stop, destroy, report TOO-SLOW.
3. SEAL: sha256 of the 4 checkpoints into artifacts/claude-rsn351b-20260925/SEAL-run.sha256.txt BEFORE step 4.
4. EVAL once per checkpoint (R in plain30lr-s1, plain30lr-s2; C in copy_only.pt, final.pt):
   python scripts/claude_rsn296_run.py dev  --ckpt W/R/C --out W/R/dev-<copy|final>.json
   python scripts/claude_rsn296_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/R/panel296-<copy|final>.json
   python scripts/claude_rsn296_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel294-<copy|final>.json
   Copy every train_log.jsonl, train_summary.json, dev-*.json and panel*.json into artifacts/claude-rsn351b-20260925/runs/<R>/ BEFORE destroying the instance.
5. RESULTS.md, verdict first: per run minutes, copy loss first/last, practice reward means per 1,000 steps, dev totals, panel totals and per-category checked-right counts (copy-only and final), W1-W3 with integer counts, raw and checked counts, dollars. Append ledger lines W1-W3 (cat >> artifacts/fable-predictions-ledger.md).
6. Copy checkpoints to the Mac at ~/premonition-models/rsn351b/<run>/ with sha256 in RESULTS.md. Never push weights. Results first.
PUSH: artifacts/claude-rsn351b-20260925/RESULTS.md artifacts/claude-rsn351b-20260925/SEAL-run.sha256.txt artifacts/claude-rsn351b-20260925/runs artifacts/fable-predictions-ledger.md
