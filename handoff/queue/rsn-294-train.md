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
- Search offers with reliability >= 0.98 (vastai search offers 'gpu_name=RTX_5090 reliability>=0.98 rentable=true' -o dph), preferring at least 16 CPU cores; a 4090 with the same filter if no 5090 is available.
- Before renting: check with `vastai show instances` that no instance labelled rsn-294 is live. If one is running and healthy, exit and report DUPLICATE.
- Label the instance rsn-294. Check the credit balance first: stop and report LOW-CREDIT if it is under $4, or if the ledger total would pass $30. The ceiling for this task is $4 / 3 h, enforced by a watchdog.
- Liveness watchdog: every 60 s, check the instance's actual_status and that the train logs grow. If the instance is offline or shows no log progress for 10 min, destroy it by exact id and rent once more (same filter). If that one fails too, destroy it and stop with HOST-FAIL. Never run 2 instances at once.
- Read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Destroy the instance at the end and confirm it is gone. Append a ledger line.

YOUR TASK: builder for rsn-294 (a learned, brain-style reasoner vs an equal-size plain transformer). The reasoning thread (Opus) wrote all the code, smoke-tested it on CPU and sealed it. Import and run it; never edit it. If something breaks, stop and report; do not patch it. Artifacts go in artifacts/claude-rsn294-20260923/.
READ FIRST (on origin/main): artifacts/claude-rsn294-20260923/PASSMARKS.md and the docstrings of scripts/claude_rsn294_core.py and scripts/claude_rsn294_run.py.
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel294-20260923/ yourself. You run the eval command below on items-v3.jsonl exactly once per checkpoint; it writes category-level counts only.

0. Rent as above. On the GPU machine: a NEW venv with torch (CUDA build) and numpy only. Check `nproc`, `nvidia-smi` and `df -h`.
1. CODE. Clone the repo at origin/main (git clone or tarball of main). From the repo root, run `sha256sum -c` on artifacts/claude-rsn294-20260923/SEAL-code.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt. Every line must be OK, or stop. Run `python scripts/claude_rsn294_core.py` (it must print "selftest ok").
2. PILOT (timing only). For each arm, run `python scripts/claude_rsn294_run.py train --arm <arm> --seed 9 --out /tmp/pilot-<arm> --copy-steps 100 --rl-steps 50 --workers 4` and read the "min" values in its train_log.jsonl. Estimate a full run as 60 x the copy-phase minutes plus 120 x the practice-phase minutes. If the four full runs below (2 arms x 2 seeds), run 2 at a time, would take over 150 minutes, stop, destroy the instance and report TOO-SLOW with the timings.
3. TRAIN (4 runs, 2 at a time, --workers 4 each):
   python scripts/claude_rsn294_run.py train --arm loop  --seed 1 --out W/loop-s1
   python scripts/claude_rsn294_run.py train --arm plain --seed 1 --out W/plain-s1
   then
   python scripts/claude_rsn294_run.py train --arm loop  --seed 2 --out W/loop-s2
   python scripts/claude_rsn294_run.py train --arm plain --seed 2 --out W/plain-s2
   Use the default steps, batch and learning rate. Do not change anything.
4. SEAL. Write the sha256 of all 8 checkpoints (copy_only.pt and final.pt for each run) to artifacts/claude-rsn294-20260923/SEAL-run.sha256.txt BEFORE step 5.
5. DEV + PANEL, ONCE per checkpoint. For each run R and each of copy_only.pt and final.pt (C):
   python scripts/claude_rsn294_run.py dev  --ckpt W/R/C --out W/R/dev-<copy|final>.json
   python scripts/claude_rsn294_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel-<copy|final>.json
   Copy every train_log.jsonl, train_summary.json, dev-*.json and panel-*.json into artifacts/claude-rsn294-20260923/runs/<R>/.
6. RESULTS.md, verdict first. For each run: minutes, first and last copy loss, first and last practice reward, and the panel "total" counts for copy-only and final. Then every mark P294.1 to P294.6 from PASSMARKS.md, with integer counts and PASS/FAIL. The code arm's scores are in artifacts/claude-rsn294-20260923/codearm_scores.json. Add dollars spent. Append ledger lines P294.1 to P294.6 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE CHECKPOINTS: copy W/*/ *.pt to the Mac at ~/premonition-models/rsn294/ and record their sha256 in RESULTS.md. Never push weights.
PUSH: artifacts/claude-rsn294-20260923/RESULTS.md artifacts/claude-rsn294-20260923/SEAL-run.sha256.txt artifacts/claude-rsn294-20260923/runs artifacts/fable-predictions-ledger.md
