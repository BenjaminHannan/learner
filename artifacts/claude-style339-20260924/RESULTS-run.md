# e2e-339-style: REGISTERED run of exp 339 (2026-09-24) — STOPPED, nothing ran

No arm ran. The first prescribed command (arm B) exits during the 336 runner's
MiniLM preflight, before any life, any GPU work, or any output file — the same
Windows preflight breakage that stopped the e2e-330-dev rehearsal yesterday.
Per the task's stop rule ("If something breaks, stop and report"), arms P and T,
the scorer, and the P339.4 DEV run were not attempted. Month-end code untouched
(no edits anywhere, on either machine).

## What was verified (integer counts)

- Combined tree on BensPC: fresh `git archive origin/builder-outbox`
  (454,563,840 bytes, 70 MB gzipped) + fresh `git archive origin/main` on top
  (982,220,800 bytes, 133 MB gzipped, main wins), extracted at
  `C:/Users/benja/e339style/tree/`. All 11 prescribed scripts present.
- `self122_head.pt` copied from the Mac repo into the tree; sha256 on BensPC ==
  Mac copy: `5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25`
  (match).
- READER safetensors sha256 on BensPC
  (`C:/Users/benja/lis301/work/run/merged/model.safetensors`):
  `b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890` (match).
- Venv: `C:/Users/benja/lis300/venv/Scripts/python.exe`, Python 3.10.9,
  torch 2.11.0+cu128, transformers 5.17.0, `torch.cuda.is_available()` True.
  No pip install was needed.
- BASE: `snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True)`
  succeeded from cache, no download. Snapshot path:
  `C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc`.
  BASE commit hash: `87179e5c1f455ef22e6223592d2d61351b525bfc`.
- Panel seal on BensPC (step 1, hash verification only, no turns read): 4/4 OK
  (`turns.jsonl` OK, `truth.jsonl` OK, `lives.jsonl` OK, `README.md` OK).
- SEAL-code (step 1, 11 scripts, written BEFORE running): 11/11 hashed, stored in
  `artifacts/claude-style339-20260924/SEAL-code.sha256.txt` (this folder).
- GPU at run time: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total,
  15397 MiB free, 0% utilisation. No other job was running (one-job rule kept).
- Time window: staged and attempted 07:47–07:54 ET, within the daytime cap
  (end by 20:00 ET, no arm after 18:30 ET). Total well under the 240-minute cap;
  no single turn exceeded 5 minutes.

## Arms run: 0 of 3. Scorer: not run. DEV run (P339.4): not attempted

Wall time per arm: B 1.55 s (preflight exit, process then ended, GPU untouched);
P, T: not attempted (stopped per task rule). `artifacts/claude-style339-20260924/run`
does not exist on BensPC (verified absent). No `judge_*.jsonl` exists anywhere;
none opened, no panel reply quoted.

## The breakage (exact error, then underlying traceback)

Prescribed command (from `C:/Users/benja/e339style/tree`, `PYTHONUTF8=1`,
`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, lis-301 venv):

`python -B scripts/claude_e2e336_run.py --bank
artifacts/claude-stylepanel339-20260924 --out
artifacts/claude-style339-20260924/run --arm claude_chat338_run:build_P
--name B --model C:/Users/benja/lis301/work/run/merged --gen-model
openbmb/MiniCPM5-1B`

Exact output (the runner's whole stdout, exit before any life, exit code 1):

`MISSING-CACHE: the self122 MiniLM router did not load
(ModuleNotFoundError("No module named 'resource'")); restore the Hugging Face
snapshot, then rerun. Nothing was run.`

Underlying traceback (same machine, read-only probe
`sys.path.insert(0, "scripts"); import fable_self122;
fable_self122.route122("what is your name?")` — code not edited):

```
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "C:\Users\benja\e339style\tree\scripts\fable_self122.py", line 45, in <module>
    import fable_self105 as S105
  File "C:\Users\benja\e339style\tree\scripts\fable_self105.py", line 58, in <module>
    import fable_self99 as S99
  File "C:\Users\benja\e339style\tree\scripts\fable_self99.py", line 42, in <module>
    import fable_loop90_agent as L90
  File "C:\Users\benja\e339style\tree\scripts\fable_loop90_agent.py", line 45, in <module>
    import fable_bench73_english_arm as B73
  File "C:\Users\benja\e339style\tree\scripts\fable_bench73_english_arm.py", line 58, in <module>
    import fable_bench65_notebook_arm as B65
  File "C:\Users\benja\e339style\tree\scripts\fable_bench65_notebook_arm.py", line 43, in <module>
    from fable_qual56_reasoner import QualifierAwareReasoner
  File "C:\Users\benja\e339style\tree\scripts\fable_qual56_reasoner.py", line 39, in <module>
    import fable_reasoner50 as R50
  File "C:\Users\benja\e339style\tree\scripts\fable_reasoner50.py", line 57, in <module>
    import resource
ModuleNotFoundError: No module named 'resource'
```

`import resource` is a Unix-only stdlib module; it does not exist on Windows
Python 3.10.9. The runner converts this import failure into `MISSING-CACHE` and
exits. This hits every non-twin arm (B, P, and the P339.4 DEV run all go through
the same preflight); the twin arm skips the preflight but was not attempted
(stop rule).

## Marks

| Mark | Bar | Result |
|---|---|---|
| P339.1 feedback lives with exactly the right preference saved | ≥ 32/40 | NO DATA (nothing ran — not a registered FAIL of the agent) |
| P339.2 control lives with any preference saved | 0/20 | NO DATA (nothing ran) |
| P339.3 day-3 replies following the preference | ≥ 80% (proved wrong if < 60%) | N/A (no replies exist) |
| P339.4 preferences saved on the 194-turn DEV bank | 0 | NO DATA (DEV run not attempted) |

## What it means (plain high-school English)

- The registered run never started: zero lives ran, zero replies, zero scores.
  This says nothing about whether the style agent is good or bad.
- The failure is in the test harness's startup check on Windows, not in the
  339 agent: a Mac-only system module is imported by the check, so the check
  crashes before the agent is even built. The 339/338 code, the reader, the
  base model, the panel seal, and the code seal all checked out fine.
- This is the identical blocker that stopped e2e-330-dev yesterday
  (`artifacts/claude-e2e330-dev-20260924/RESULTS-dev.md`): still present on
  `origin/main` today (verified: `import resource` is still at
  `scripts/fable_reasoner50.py` line 57; the preflight is unchanged).

## What it doesn't mean

- It doesn't mean the style preferences, the detector rules, or the panel are
  broken: none of those was exercised.
- It doesn't mean the twin arm is broken: it was not attempted, and it skips
  the failing check by design.
- Behind the import crash, yesterday's rehearsal also found the MiniLM snapshot
  absent from the BensPC cache; that second blocker is still untested today
  (the run dies at the import before reaching the snapshot check) and would
  need staging if the harness is ever fixed — but the task allows downloading
  only READER and BASE, so that staging needs the month-end thread's call.

## Deviations

- Windows has no `sha256sum`; the panel SEAL was verified with an equivalent
  read-only Python/hashlib check (4/4 OK), and SEAL-code with SHA-256 over the
  exact 11 prescribed paths. No panel turns were read, printed, or quoted.
- One new directory + two new files in this folder (`SEAL-code.sha256.txt`,
  `RESULTS-run.md`); nothing else created, edited, or deleted.
