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
- Before renting: `vastai show instances`; if an instance labelled rsn-296b is live and healthy, exit and report DUPLICATE.
- Label every instance rsn-296b. Check credit first: stop and report LOW-CREDIT if it is under $4.
- MONEY (Ben 2026-09-23 21:51 UTC: "don't use gpu rentals above 4$"): $4 is the COMBINED limit for this whole task, re-rents included. Keep a running total of dph x hours for every instance you create. If the total would pass $3.80, destroy everything and stop with BUDGET-STOP. A separate guard task (rsn-296b-guard) also watches this.
- If a new instance is not "running" within 6 min (or create returns success: False), destroy it by exact id and try the next offer on a different host, up to 4 rentals in total. If a running instance goes offline or shows no log progress for 10 min, destroy it and count it. After 4 failures stop with HOST-FAIL. Never 2 instances at once.
- Read the key only as $(cat ~/.config/vastai/vast_api_key) and never print it. Destroy the instance at the end and confirm it is gone. Append a ledger line.

YOUR TASK: builder for rsn-296b (296 with ONE change: "told the answer after a miss" in practice; plain arm only). The reasoning thread (Opus) wrote and sealed all code; import and run it, never edit it. If something breaks, stop and report; do not patch. Artifacts go in artifacts/claude-rsn296b-20260924/.
READ FIRST (on origin/main): artifacts/claude-rsn296b-20260924/PASSMARKS.md, design/v3/30-modes/296b-told-after-miss.md, and the docstrings of scripts/claude_rsn296b_run.py and scripts/claude_rsn296_diag.py.
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. You run the eval commands below exactly once per checkpoint; they write category-level counts only.

LESSON FROM rsn-296 (it lost every result file): COPY ALL RESULT FILES BACK TO THE MAC (scp -r W/ and the run logs) AND CHECK THEY ARRIVED BEFORE YOU DESTROY THE INSTANCE. Results first, checkpoints second.

0. Rent as above. Use the image's CUDA torch if it works (python -c "import torch;print(torch.cuda.is_available())"), else a new venv with torch (CUDA) and numpy. Check `nproc`, `nvidia-smi`, `df -h`.
1. CODE. Tarball of origin/main (git archive) or git clone. From the repo root, `sha256sum -c` on artifacts/claude-rsn296b-20260924/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt: every line OK, else stop.
2. PILOT (timing only): `python scripts/claude_rsn296b_run.py train --arm plain --seed 9 --out /tmp/pilot --copy-steps 100 --rl-steps 50 --workers 6`. Estimate a full run as 60 x copy minutes + 120 x practice minutes. If the two runs in parallel would take over 90 minutes or the dollars would pass $3.00, stop, destroy and report TOO-SLOW.
3. TRAIN, both at once, --workers 6 each, from the repo root, run under setsid/nohup so an ssh drop cannot kill them (defaults otherwise):
   python scripts/claude_rsn296b_run.py train --arm plain --seed 1 --out W/plain-s1
   python scripts/claude_rsn296b_run.py train --arm plain --seed 2 --out W/plain-s2
4. SEAL. sha256 of the 4 checkpoints into artifacts/claude-rsn296b-20260924/SEAL-run.sha256.txt BEFORE step 5.
5. EVAL, ONCE per checkpoint. For R in plain-s1 plain-s2 and C in copy_only.pt final.pt:
   python scripts/claude_rsn296b_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/R/panel296-<copy|final>.json
   python scripts/claude_rsn296b_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel294-<copy|final>.json
   and for C = final.pt only:
   python scripts/claude_rsn296_diag.py --device cuda --n 200 --ckpt W/R/final.pt --out W/R/diag-final.json > W/R/diag-final.txt
6. COPY BACK (see LESSON): every train_log.jsonl, train_summary.json, panel*.json, diag-final.* into artifacts/claude-rsn296b-20260924/runs/<R>/ on the Mac, and the 4 checkpoints to ~/premonition-models/rsn296b/<R>/. List the copied files, check the checkpoint sha256 against the seal, THEN destroy the instance and confirm it is gone.
7. RESULTS.md, verdict first: per run minutes, first/last copy loss, first/last practice reward; every mark P296b.1-P296b.5 for both seeds with integer counts and PASS/FAIL, computed from the CHECKED fields (checked_right, checked_answered_without_fact) in the JSON files. The 296 same-seed counting+comparing on the fresh panel was 28 (s1) and 28 (s2). Every miss and deviation.
PUSH: artifacts/claude-rsn296b-20260924/RESULTS.md artifacts/claude-rsn296b-20260924/SEAL-run.sha256.txt artifacts/claude-rsn296b-20260924/runs artifacts/fable-predictions-ledger.md
