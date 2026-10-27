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
- Before renting: `vastai show instances`; if an instance labelled rsn-357r is live and healthy, exit and report DUPLICATE.
- Label every instance rsn-357r. Never touch an instance with any other label (another job, e.g. rent-336, may be live at the same time).
- MONEY (Ben 2026-09-23 21:51 UTC: "don't use gpu rentals above 4$"): $4 is the COMBINED limit for this whole task, re-rents included. Keep a running total of dph x hours for every instance you create. If the total would pass $3.80, destroy everything and stop with BUDGET-STOP. A separate guard task (rsn-357r-guard) also watches this.
- If a new instance is not "running" within 6 min (or create returns success: False), destroy it by exact id and try the next offer on a different host, up to 4 rentals in total. If a running instance goes offline or shows no log progress for 10 min, destroy it and count it. After 4 failures stop with HOST-FAIL. Never 2 rsn-357r instances at once.
- Read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Destroy the instance at the end and confirm it is gone. Append a ledger line.

YOUR TASK: builder for rsn-357 ON A RENTAL (practise three-step, test four-step; plain and loop arms). The BensPC version (handoff/held/007-rsn-357-train.md) is held; this replaces it. Same sealed code and pass marks. The sleep research thread (Opus) wrote and sealed all code; import and run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn357-20260925/.
READ FIRST (on origin/main): artifacts/claude-rsn357-20260925/PASSMARKS.md, design/v3/30-modes/357-practise-three-test-four.md, the docstrings of scripts/claude_rsn357_run.py and scripts/claude_rsn357_four.py, and origin/builder-outbox:artifacts/claude-rsn353-20260925/RESULTS.md (one loop run needs ~14 GB of GPU memory; two loop runs at once ran out of memory on a 32 GB 5090).
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. You run the eval commands below exactly once per checkpoint; they write category-level counts only.

0. Rent as above. On the GPU machine: a NEW venv with torch (CUDA build) and numpy only. Check `nproc`, `nvidia-smi`, `df -h`.
1. SEAL. Tarball of origin/main (git archive). From the repo root, `sha256sum -c` on artifacts/claude-rsn357-20260925/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt: every line OK, else stop. Run `python scripts/claude_rsn296_gen.py` ("selftest ok").
2. PILOT (timing only): `python scripts/claude_rsn357_run.py train --arm loop --seed 9 --out /tmp/pilot-357 --copy-steps 100 --rl-steps 50 --workers 8`. Estimate one run as 60 x copy-phase minutes + 120 x practice-phase minutes. Runs go ONE AT A TIME (loop memory). If the 4-run total estimate is over 300 minutes OR the estimated dollars would pass $3.40, stop, destroy the instance and report TOO-SLOW with the timings. If the pilot runs out of GPU memory, stop and report OOM (do not change the batch).
3. TRAIN, one at a time, and after EACH run immediately do steps 4-5 for that run and copy its files off the instance (a dead host must not lose finished runs):
   python scripts/claude_rsn357_run.py train --arm loop  --seed 1 --out W/loop-s1  --workers 8
   python scripts/claude_rsn357_run.py train --arm plain --seed 1 --out W/plain-s1 --workers 8
   python scripts/claude_rsn357_run.py train --arm loop  --seed 2 --out W/loop-s2  --workers 8
   python scripts/claude_rsn357_run.py train --arm plain --seed 2 --out W/plain-s2 --workers 8
   If money runs short, drop runs from the end of this list and report which.
4. SEAL each run's copy_only.pt and final.pt (sha256 appended to artifacts/claude-rsn357-20260925/SEAL-run.sha256.txt) BEFORE its evals.
5. EVAL, ONCE per checkpoint. For run R and C in copy_only.pt, final.pt:
   python scripts/claude_rsn357_run.py dev  --ckpt W/R/C --out W/R/dev-<copy|final>.json
   python scripts/claude_rsn357_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/R/panel296-<copy|final>.json
   python scripts/claude_rsn357_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel294-<copy|final>.json
   python scripts/claude_rsn357_four.py --ckpt W/R/C --out W/R/four-<copy|final>.json
   Copy train_log.jsonl, train_summary.json, dev-*.json, panel*.json and four-*.json into artifacts/claude-rsn357-20260925/runs/<R>/ on the Mac.
6. RESULTS.md, verdict first, PER ARM: marks F1-F4 for both seeds with integer counts and PASS/FAIL using PASSMARKS.md, and whether the "proved wrong" clause triggered. Per run: minutes, copy action_ce every 1,000 steps, practice reward means per 1,000 steps, panel totals and per-category checked-right counts (copy-only and final, both panels), raw and checked counts, four-step raw and checked (loop: at every round count), dev. Dollars spent. Append ledger lines F1-F4 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE CHECKPOINTS: copy them to the Mac at ~/premonition-models/rsn357/<run>/ only if `df -g /` shows at least 8 GB free after the copy; otherwise leave them and say so. Record sha256 in RESULTS.md. Never push weights. Destroy the instance at the end and confirm it is gone.
PUSH: artifacts/claude-rsn357-20260925/RESULTS.md artifacts/claude-rsn357-20260925/SEAL-run.sha256.txt artifacts/claude-rsn357-20260925/runs artifacts/fable-predictions-ledger.md
