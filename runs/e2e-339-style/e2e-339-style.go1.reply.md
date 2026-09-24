Registered run of exp 339 — locking in your talk-to-me style without peeking at test turns.
Your file paths don't match — I'll map the workspace to find them.
Required experiment files aren't in this worktree — checking related artifacts and branches.
Confirmed this is a BensPC GPU registered run — checking time window and remote access.
BensPC is reachable — checking GPU status and required code.
GPU is free and prior run files exist — verifying the environment before the registered run.
The 330 rehearsal hit a Windows blocker in this same harness — I'll verify whether it still applies, then stage the registered run.
Staging files are ready (203MB) — setting up the BensPC work area.
Files transferred — extracting the combined tree on BensPC.
Tree verified, model head matches — checking the reader and base model.
Models verified — running the panel seal check and code seal.
Seals pass — launching the first registered arm.
Blocker confirmed identical to the rehearsal — writing up the stopped-run report.
Artifacts are in place (this worktree git-ignores `artifacts/`, same as the prior rehearsal — the watcher collects the PUSH path from disk). Cleaning up staging files.
VERDICT: STOPPED — the e2e-339-style REGISTERED run never started. Zero arms ran, zero scores. The 336 harness fails its MiniLM preflight on BensPC before any life — the identical Windows blocker that stopped the e2e-330-dev rehearsal yesterday. Month-end code untouched everywhere. PUSH: `artifacts/claude-style339-20260924/` (`SEAL-code.sha256.txt` + `RESULTS-run.md`, on disk; `artifacts/` is gitignored in this worktree, same as the 330-dev report, so the watcher collects it from disk).

## Every move (integer counts)

1. Read COMMON RULES (first 13 lines of `handoff/queue/lis-302-gpu.md` via `git show origin/main`), PASSMARKS.md, and `e2e-330-dev.md`. Panel file names listed only (`ls-tree`); no panel turns opened, printed, or quoted.
2. Pre-checks on Mac: `uptime` (load ~91–99, fine), `df -g /` (51 GB free, ≥3 GB OK). ET 07:47 at start, 07:54 at stop — inside the daytime window (end by 20:00 ET, no arm after 18:30 ET). Total ~7 min of ~240-min cap; no turn over 5 min.
3. BensPC: RTX 5070 Ti, 16303 MiB total, 15397 MiB free, 0% util — GPU free, one-job rule kept.
4. Venv `C:/Users/benja/lis300/venv`: Python 3.10.9, torch 2.11.0+cu128, transformers 5.17.0, CUDA True. No pip install needed.
5. Combined tree: fresh `git archive origin/builder-outbox` (454,563,840 B) + `origin/main` on top (982,220,800 B) → `C:/Users/benja/e339style/tree/`. All 11 prescribed scripts present.
6. `self122_head.pt` copied in; sha256 BensPC == Mac `5ca02173…6c8ee25` (match).
7. READER sha256 `b4fd93a2…890` (match). BASE via `snapshot_download(local_files_only=True)`, no download; commit `87179e5c1f455ef22e6223592d2d61351b525bfc`.
8. Panel seal from inside the panel folder (hash check only): 4/4 OK. SEAL-code (11 scripts) written BEFORE running; copied back byte-identical.
9. Arm B (first prescribed command): exit code 1 after 1.55 s, before any life/GPU work. Stopped per rule — arms P, T, scorer, DEV run not attempted. No `run/` output exists on BensPC (verified absent); no `judge_*.jsonl` opened.

## Exact error and traceback

Runner stdout: `MISSING-CACHE: the self122 MiniLM router did not load (ModuleNotFoundError("No module named 'resource'")); restore the Hugging Face snapshot, then rerun. Nothing was run.`

Read-only probe (`import fable_self122; route122(...)`, no edits) ends: `File ".../scripts/fable_reasoner50.py", line 57, in <module> → import resource → ModuleNotFoundError: No module named 'resource'` (Unix-only stdlib, absent on Windows). Full chain in RESULTS-run.md. `import resource` is still at line 57 on `origin/main` — unfixed since yesterday.

## Marks table

| Mark | Bar | Result |
|---|---|---|
| P339.1 exactly-right preference saved | ≥ 32/40 | NO DATA (nothing ran — not an agent FAIL) |
| P339.2 control lives with any save | 0/20 | NO DATA |
| P339.3 day-3 replies follow preference | ≥ 80% (dead if < 60%) | N/A, no replies exist |
| P339.4 DEV-bank saves | 0 | NO DATA (DEV run not attempted) |

## What it means / doesn't mean (plain high-school English)

The test never started, so this says nothing about whether the style agent is good or bad — it's a broken starting gate on the Windows machine, not a grade on the agent. Every ingredient (339/338 code, reader, base model, panel seal, code seal) checked out fine. It doesn't mean the twin is broken either (skips the failing check, never attempted). Behind this crash, yesterday's rehearsal also found the MiniLM snapshot missing from BensPC's cache — still untested today and needs the month-end thread's call, since only READER and BASE may be downloaded.

## Deviations

- No `sha256sum` on Windows: panel SEAL verified with an equivalent Python/hashlib check (4/4 OK). No panel content touched.
- New directory + 2 new files only; zero edits/deletes anywhere.
