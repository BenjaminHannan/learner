COMMON RULES (the director, Claude, wrote this task on 2026-09-24). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
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
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. You run the eval commands below exactly once per checkpoint; they write category-level counts only. New files only. Get the code for the GPU machine with `git archive origin/main`.
GPU: yes (BensPC; Ben 02:12 UTC 09-25: tonight's GPU jobs run on his PC. One job at a time. Free, no rental: never rent for this task.)

YOUR TASK: builder for rsn-353 ON BENSPC (re-run; the rental run on 2026-09-25 ended with NO RESULT: host died, credit ran out, see runs/rsn-353-train/ on origin/builder-outbox). Same sealed code, same pass marks: rsn-296's LOOP arm with ONE change (no per-pass step embedding). The sleep research thread (Opus) wrote and sealed all code; import and run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn353-20260925/.
READ FIRST (on origin/main): artifacts/claude-rsn353-20260925/PASSMARKS.md, design/v3/30-modes/353-loop-no-step-embedding.md, the docstrings of scripts/claude_rsn353_run.py and scripts/claude_rsn294_run.py, and the rental builder's report runs/rsn-353-train/rsn-353-train.go1.reply.md on origin/builder-outbox (one loop run needed ~14 GB of GPU memory; two at once ran out of memory on a 32 GB card).
Registered deviations for this re-run (no change to the code or marks): --workers 0 (Windows), one run at a time (BensPC has 16 GB).

1. SEAL. After git fetch, `git archive origin/main` into a temp dir and from its root run `shasum -a 256 -c` on artifacts/claude-rsn353-20260925/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt. Every line OK, else stop.
2. CODE on BensPC (`ssh benspc`): copy `git archive origin/main scripts artifacts/claude-rsn353-20260925 artifacts/claude-reasonpanel296-20260924 artifacts/claude-reasonpanel294-20260923` to BensPC and extract, keeping the paths. Same venv as rsn-355. Run `python -B scripts/claude_rsn296_gen.py` ("selftest ok").
3. PILOT (timing only): `python -B scripts/claude_rsn353_run.py train --arm loop --seed 9 --out pilot-353 --copy-steps 100 --rl-steps 50 --workers 0`. If it runs out of GPU memory, stop and report OOM (do not change the batch). Estimate one full run as 60 x copy-phase minutes + 120 x practice-phase minutes. If the estimate for 2 runs one after the other is over 8 hours, stop and report TOO-SLOW with the timings.
4. SEED 1, then evaluate it BEFORE seed 2 (so a crash can't lose it):
   python -B scripts/claude_rsn353_run.py train --arm loop --seed 1 --out W/loop-s1 --workers 0
   sha256 of W/loop-s1/copy_only.pt and final.pt into artifacts/claude-rsn353-20260925/SEAL-run.sha256.txt, then for C in copy_only.pt, final.pt, ONCE each:
   python -B scripts/claude_rsn353_run.py dev  --ckpt W/loop-s1/C --out W/loop-s1/dev-<copy|final>.json
   python -B scripts/claude_rsn353_run.py eval --ckpt W/loop-s1/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/loop-s1/panel296-<copy|final>.json
   python -B scripts/claude_rsn353_run.py eval --ckpt W/loop-s1/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/loop-s1/panel294-<copy|final>.json
   Copy train_log.jsonl, train_summary.json, dev-*.json and panel*.json to the Mac into artifacts/claude-rsn353-20260925/runs/loop-s1/.
5. SEED 2: the same with --seed 2 and W/loop-s2 (append its sha256 lines to SEAL-run.sha256.txt before its evals).
6. RESULTS.md, verdict first: marks L1-L4 for both seeds with integer counts and PASS/FAIL using PASSMARKS.md (L1 = action_ce on the last copy line of train_log.jsonl), and whether the "proved wrong" clause triggered. Per run: minutes, copy action_ce every 1,000 steps, practice reward means per 1,000 steps, panel totals and per-category checked-right counts (copy-only and final, both panels), raw and checked counts, dev at 6/12/20 passes. State both deviations. Append ledger lines L1-L4 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE CHECKPOINTS on BensPC (e.g. C:/Users/benja/premonition-models/rsn353/<run>/) and record their sha256 in RESULTS.md. Never push weights. Do not copy them to the Mac.
PUSH: artifacts/claude-rsn353-20260925/RESULTS.md artifacts/claude-rsn353-20260925/SEAL-run.sha256.txt artifacts/claude-rsn353-20260925/runs artifacts/fable-predictions-ledger.md
