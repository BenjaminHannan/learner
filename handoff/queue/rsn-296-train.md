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
- Search offers with reliability >= 0.98 (vastai search offers 'gpu_name=RTX_5090 reliability>=0.98 rentable=true' -o dph), preferring at least 16 CPU cores and more is better (the practice generator is CPU-heavy: use a host with >= 32 cores if one is within $0.10/h of the cheapest). 4090 with the same filter if no 5090.
- Before renting: `vastai show instances`; if an instance labelled rsn-296 is live and healthy, exit and report DUPLICATE.
- Label every instance rsn-296. Check credit first: stop and report LOW-CREDIT if it is under $4.
- MONEY (Ben 2026-09-23 21:51 UTC: "don't use gpu rentals above 4$"): $4 is the COMBINED limit for this whole task, re-rents included. Keep a running total of dph x hours for every instance you create. If the total would pass $3.80, destroy everything and stop with BUDGET-STOP. A separate guard task (rsn-296-guard) also watches this.
- If a new instance is not "running" within 6 min (or create returns success: False), destroy it by exact id and try the next offer on a different host, up to 4 rentals in total. If a running instance goes offline or shows no log progress for 10 min, destroy it and count it. After 4 failures stop with HOST-FAIL. Never 2 instances at once.
- Read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Destroy the instance at the end and confirm it is gone. Append a ledger line.

YOUR TASK: builder for rsn-296 (varied "sleep school" practice; rsn-294's arms and training with ONE change: the practice generator). The reasoning thread (Opus) wrote and sealed all code; import and run it, never edit it. If something breaks, stop and report; do not patch. Artifacts go in artifacts/claude-rsn296-20260924/.
READ FIRST (on origin/main): artifacts/claude-rsn296-20260924/PASSMARKS.md, design/v3/30-modes/296-sleep-school-practice.md, and the docstrings of scripts/claude_rsn296_gen.py and scripts/claude_rsn294_run.py.
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. You run the eval commands below exactly once per checkpoint; they write category-level counts only.

0. Rent as above. On the GPU machine: a NEW venv with torch (CUDA build) and numpy only. Check `nproc`, `nvidia-smi`, `df -h`.
1. CODE. Tarball of origin/main (git archive) or git clone. From the repo root, `sha256sum -c` on artifacts/claude-rsn296-20260924/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt: every line OK, else stop. Run `python scripts/claude_rsn296_gen.py` (prints "selftest ok"; takes about 30 s).
2. PILOT (timing only). For each arm: `python scripts/claude_rsn296_run.py train --arm <arm> --seed 9 --out /tmp/pilot-<arm> --copy-steps 100 --rl-steps 50 --workers 6`, run from the repo root. Estimate a full run as 60 x copy-phase minutes + 120 x practice-phase minutes (from its train_log.jsonl "min" values). If the four full runs, 2 at a time, would take over 150 minutes, OR the estimated dollars would pass $3.50, stop, destroy the instance and report TOO-SLOW with the timings.
3. TRAIN (4 runs, 2 at a time, --workers 6 each, from the repo root; defaults otherwise, change nothing):
   python scripts/claude_rsn296_run.py train --arm plain --seed 1 --out W/plain-s1
   python scripts/claude_rsn296_run.py train --arm loop  --seed 1 --out W/loop-s1
   then
   python scripts/claude_rsn296_run.py train --arm plain --seed 2 --out W/plain-s2
   python scripts/claude_rsn296_run.py train --arm loop  --seed 2 --out W/loop-s2
4. SEAL. sha256 of all 8 checkpoints into artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt BEFORE step 5.
5. EVAL, ONCE per checkpoint. For each run R and C in copy_only.pt, final.pt:
   python scripts/claude_rsn296_run.py dev  --ckpt W/R/C --out W/R/dev-<copy|final>.json
   python scripts/claude_rsn296_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/R/panel296-<copy|final>.json
   python scripts/claude_rsn296_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel294-<copy|final>.json
   Copy every train_log.jsonl, train_summary.json, dev-*.json and panel*.json into artifacts/claude-rsn296-20260924/runs/<R>/.
6. RESULTS.md, verdict first: per run minutes, first/last copy loss, first/last practice reward, panel totals (copy-only and final, both panels). Every mark P296.1-P296.4 for both plain seeds with integer counts and PASS/FAIL (code-arm numbers are in PASSMARKS.md; 294 plain final right on reasonpanel294 was 184 for seed 1 and 189 for seed 2). Loop numbers reported the same way, no marks. Dollars spent. Append ledger lines P296.1-P296.4 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE CHECKPOINTS: copy them to the Mac at ~/premonition-models/rsn296/<run>/ (one directory per run) and record sha256 in RESULTS.md. Never push weights. Destroy the instance BEFORE a slow copy if the $3.80 total is near: copy checkpoints first only if time allows; results come first.
PUSH: artifacts/claude-rsn296-20260924/RESULTS.md artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt artifacts/claude-rsn296-20260924/runs artifacts/fable-predictions-ledger.md
