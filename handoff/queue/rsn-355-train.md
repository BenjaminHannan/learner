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

YOUR TASK: builder for rsn-355 (296's plain arm with ONE change: a shared "chain step" input instead of one slot per step). The sleep research thread (Opus) wrote and sealed all code; import and run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn355-20260925/.
READ FIRST (on origin/main): artifacts/claude-rsn355-20260925/PASSMARKS.md, design/v3/30-modes/355-shared-step-embedding.md, and the docstrings of scripts/claude_rsn355_run.py and scripts/claude_rsn294_run.py.

1. SEAL. After git fetch, `git archive origin/main` into a temp dir and from its root run `shasum -a 256 -c` on artifacts/claude-rsn355-20260925/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt. Every line OK, else stop.
2. CODE on BensPC (`ssh benspc`): copy `git archive origin/main scripts artifacts/claude-rsn355-20260925 artifacts/claude-reasonpanel296-20260924 artifacts/claude-reasonpanel294-20260923` to BensPC and extract, keeping the paths. Use the lis-301 venv (torch with CUDA + numpy) or a new venv with those two only. Check `nvidia-smi`, free disk, CPU core count. Run `python -B scripts/claude_rsn296_gen.py` (prints "selftest ok").
3. PILOT (timing only): `python -B scripts/claude_rsn355_run.py train --arm plain --seed 9 --out pilot-355 --copy-steps 100 --rl-steps 50 --workers 0`. ALWAYS use --workers 0 on Windows (the loader's worker processes cannot start there; registered deviation). If the pilot fails for any other reason, stop and report. Estimate a full run as 60 x copy-phase minutes + 120 x practice-phase minutes (train_log.jsonl "min"). Then time two copies at once (seeds 8 and 9). Choose 2-at-a-time if its wall estimate is lower. If the total wall estimate is over 8 hours, stop and report TOO-SLOW with the timings.
4. TRAIN (2 runs, defaults otherwise, change nothing else):
   python -B scripts/claude_rsn355_run.py train --arm plain --seed 1 --out W/plain355-s1 --workers 0
   python -B scripts/claude_rsn355_run.py train --arm plain --seed 2 --out W/plain355-s2 --workers 0
5. SEAL. sha256 of all 4 checkpoints (copy_only.pt, final.pt per run) into artifacts/claude-rsn355-20260925/SEAL-run.sha256.txt BEFORE step 6.
6. EVAL, ONCE per checkpoint. For each run R and C in copy_only.pt, final.pt:
   python -B scripts/claude_rsn355_run.py dev  --ckpt W/R/C --out W/R/dev-<copy|final>.json
   python -B scripts/claude_rsn355_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out W/R/panel296-<copy|final>.json
   python -B scripts/claude_rsn355_run.py eval --ckpt W/R/C --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out W/R/panel294-<copy|final>.json
   Copy every train_log.jsonl, train_summary.json, dev-*.json and panel*.json back to the Mac into artifacts/claude-rsn355-20260925/runs/<R>/.
7. RESULTS.md, verdict first: marks H1-H4 for both seeds with integer counts and PASS/FAIL using the numbers in PASSMARKS.md, and whether the "proved wrong" clause triggered. Per run: minutes, first/last copy loss (action_ce), practice reward means per 1,000 steps, panel totals and per-category checked-right counts (copy-only and final, both panels), raw and checked counts, dev value3 at copy and final. State the --workers 0 deviation. Append ledger lines H1-H4 (cat >> artifacts/fable-predictions-ledger.md).
8. KEEP THE CHECKPOINTS on BensPC (e.g. C:/Users/benja/premonition-models/rsn355/<run>/) and record their sha256 in RESULTS.md. Never push weights. Do not copy them to the Mac (its disk is nearly full).
PUSH: artifacts/claude-rsn355-20260925/RESULTS.md artifacts/claude-rsn355-20260925/SEAL-run.sha256.txt artifacts/claude-rsn355-20260925/runs artifacts/fable-predictions-ledger.md
