COMMON RULES (the notebook thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/talk-f0-base.md: read its first 14 lines and follow them in full (additive only, fictional names, never the repo-root notebook/, uv run python, report format, getting files with git show origin/main:<path> and git show origin/builder-outbox:<path>).
GPU: no (Mac CPU only).
TIME CAP: 180 minutes in total. macOS has no `timeout`, so run long steps in the background and kill their exact PID if they overrun.
DISK: check `df -g /` first and stop if free disk is under 8 GB. Every notebook and workload lives under /tmp/nb321run/ (never inside the repo). Delete /tmp/nb321run/ at the end. Never push a notebook, a workload or anything over 5 MB.

YOUR TASK: the registered nb-321 scale run, plus cold-open timing for the month-end restart test. No code changes. Run only sealed files.
- Before anything else, check both seals from the worktree root with `shasum -a 256 -c`:
  - artifacts/claude-nb320-20260923/SEAL.sha256.txt
  - artifacts/claude-nb321-20260923/SEAL.sha256.txt
  - Take the files from origin/builder-outbox.
  - If either seal fails, stop and report.
- Read:
  - artifacts/claude-nb321-20260923/PASSMARKS.md (the marks: M1-M7);
  - artifacts/claude-nb321-20260923/RESULTS-build.md;
  - artifacts/claude-nb320-20260923/RESULTS.md and results.json. Use exactly the workload commands, seeds and probe seeds that nb-320 recorded.

RUN (the sealed nb-320 runner scripts/claude_nb320_scale.py, unchanged).
- Compact arm: add `--factory claude_nb321_store:open_compact`. The runner takes module:attr with scripts/ on the path.
- Baseline arm: no --factory.
- A. Registered sizes, each through write, then open x3 (in fresh processes), then probe, for BOTH arms in the same session so machine load is comparable:
  - 20,000 and 100,000, both arms.
  - 1,000,000: compact arm only. The baseline did not finish in nb-320.
  - Same caps as nb-320: stop a size after 90 minutes of writing or 8 GB of memory, and report it as DID NOT FINISH.
- B. Crash (30 kills) and tamper (20 copies) at 20,000 with the compact factory.
- C. M2 lossless check: at 20,000 and 100,000, call export_events on the compact notebook. Compare its sha256 with the baseline arm's events.jsonl from the same workload.
- D. REPORT-ONLY cold-open ladder for the month-end 3-day restart test:
  - Both arms, sizes 500 / 2,000 / 5,000 ops. Build the workloads with scripts/claude_nb320_workload.py at those --n values, seed 3200.
  - Cold open x5 each in fresh processes: report the median and max seconds.
  - Also report open time right after a SIGKILL during a write, 5 times, 5,000 ops, both arms.
- Log `uptime` before every timing step. The Mac is busy, so every timing is noisy; say so.

DIRECTOR RULINGS, fixed before the run:
- M1 counts every file in the notebook dir, as the runner measures. The build keeps a full events.jsonl copy beside store.db (RESULTS-build.md T5: 582 bytes per FACT write for the dir, against 441 for the baseline). So M1 is expected to FAIL. Report the dir total AND the store.db-only bytes per FACT write, but only the dir total scores M1.
- The baseline's 1M reference for M1 is its 100k value (467.1 bytes per FACT write). Its bytes per fact were flat from 20k to 100k.
- M4 memory reference: the baseline's 100k peak RSS scaled linearly to 1M (5.93 GB). Report the scaling as an assumption.
- Every other mark exactly as PASSMARKS.md.

OUTPUT: artifacts/claude-nb321-20260923/RESULTS-run.md and results-run.json:
- verdict first;
- a marks table M1-M7 with integer counts and PASS/FAIL each;
- a table per size for both arms;
- the section D ladder;
- every wrong or different probe listed;
- deviations;
- what this means / doesn't mean in plain words.
Append the P321.1 outcome to artifacts/fable-predictions-ledger.md (cat >>).

PUSH: artifacts/claude-nb321-20260923/RESULTS-run.md artifacts/claude-nb321-20260923/results-run.json artifacts/fable-predictions-ledger.md
