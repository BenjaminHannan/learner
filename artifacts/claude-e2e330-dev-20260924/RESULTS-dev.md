# e2e-330-dev: DEV dress rehearsal (REPORT ONLY, 2026-09-24) — STOPPED, nothing ran

No arm ran. The first prescribed command (arm G) exits during the runner's
MiniLM preflight, before any life, any GPU work, or any output file. Per the
task's stop rule ("If something breaks, stop and report"), the remaining four
arms were not attempted. Month-end code untouched (no edits anywhere).

## What was verified (integer counts)

- Combined tree: `git archive origin/builder-outbox` + `git archive origin/main`
  on top (main wins), plus `artifacts/fable-self122-20260922/self122_head.pt`
  copied from the Mac repo. Staged at `C:/Users/benja/e2e330dev/tree/` on BensPC.
- `self122_head.pt` sha256 on BensPC == Mac repo copy:
  `5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25` (match).
- READER safetensors sha256 on BensPC
  (`C:/Users/benja/lis301/work/run/merged/model.safetensors`):
  `b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890` (match).
- Venv: `C:/Users/benja/lis300/venv/Scripts/python.exe`, Python 3.10.9,
  torch 2.11.0+cu128, transformers 5.17.0, `torch.cuda.is_available()` True.
  No pip install was needed.
- BASE: `snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True)`
  failed (cache held only `refs/main`, no blobs), so it was downloaded once as
  the task allows. Snapshot path:
  `C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc`.
  BASE commit hash: `87179e5c1f455ef22e6223592d2d61351b525bfc`
  (equals the pre-existing `refs/main` pin).
- DEV bank seal on BensPC (step 1): 3/3 OK
  (`turns.jsonl` OK, `truth.jsonl` OK, `README.md` OK).
- GPU at staging time: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total,
  15467 MiB free.
- Arm modules import cleanly on BensPC (read-only check, no run):
  `claude_lis_e2e_arms` OK, `claude_e2e330_arms` OK, `claude_e2e336_twin` OK.

## Arms run: 0 of 5. Scorer lines: none (no `arm_*.jsonl` exists anywhere)

Wall time per arm: G 0 s of agent work (preflight exit in <60 s);
330a, 330a_334, 330a_cre, twin: not attempted (stopped per task rule).

## The breakage (exact error, then underlying traceback)

Prescribed command (from `C:/Users/benja/e2e330dev/tree`, `PYTHONUTF8=1`):

`python -B scripts/claude_e2e336_run.py --bank
artifacts/claude-e2e331-dev-20260924 --out
artifacts/claude-e2e330-dev-20260924/run --arm claude_lis_e2e_arms:build_G
--name G --model C:/Users/benja/lis301/work/run/merged`

Exact output (the runner's whole stdout, exit before any life):

`MISSING-CACHE: the self122 MiniLM router did not load
(ModuleNotFoundError("No module named 'resource'")); restore the Hugging Face
snapshot, then rerun. Nothing was run.`

Underlying traceback (same machine, read-only
`import fable_self122; route122("what is your name?")`):

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../scripts/fable_self122.py", line 45, in <module>
    import fable_self105 as S105
  File ".../scripts/fable_self105.py", line 58, in <module>
    import fable_self99 as S99
  File ".../scripts/fable_self99.py", line 42, in <module>
    import fable_loop90_agent as L90
  File ".../scripts/fable_loop90_agent.py", line 45, in <module>
    import fable_bench73_english_arm as B73
  File ".../scripts/fable_bench73_english_arm.py", line 58, in <module>
    import fable_bench65_notebook_arm as B65
  File ".../scripts/fable_bench65_notebook_arm.py", line 43, in <module>
    from fable_qual56_reasoner import QualifierAwareReasoner
  File ".../scripts/fable_qual56_reasoner.py", line 39, in <module>
    import fable_reasoner50 as R50
  File ".../scripts/fable_reasoner50.py", line 57, in <module>
    import resource
ModuleNotFoundError: No module named 'resource'
```

## Diagnosis (two stacked blockers for arms G, 330a, 330a_334, 330a_cre)

1. `import resource` (Unix-only stdlib; absent on Windows Python 3.10.9) sits in
   the preflight's import chain (`fable_reasoner50.py` line 57, used at line 704
   for peak-RSS reporting). The runner converts this into `MISSING-CACHE` and
   exits. This hits all four non-twin arms; the twin arm skips the preflight.
2. Behind it, the MiniLM-L6-v2 snapshot the preflight wants
   (`~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/`)
   is absent on BensPC (that cache holds only scibert blobs and the
   MiniCPM5-1B refs entry; no snapshot dir anywhere in the staged trees or
   profile cache). So even a Windows-tolerant preflight would fail until the
   snapshot is staged. It was not staged: the task allows downloading only
   READER and BASE.
3. Not the cause: the READER (sha match), BASE (downloaded once, hash above),
   the tree, the seal (3/3 OK), the venv (torch/transformers/CUDA all good),
   or the arm modules (all three import OK). No output was written on BensPC
   (`artifacts/claude-e2e330-dev-20260924/` does not exist there).

## What it means (plain high-school English)

- The rehearsal never started: zero lives ran, zero replies, zero scores. This
  says nothing about whether the agent is good or bad.
- The failure is in the test harness's startup check on Windows, not in the
  agent: a Mac-only system module is imported by the check, and the small
  helper model the check looks for is not installed on the Windows machine.

## What it doesn't mean

- It doesn't mean the reader, the agent layers, or the DEV bank are broken:
  every one of those checked out fine where it could be checked.
- It doesn't mean the twin arm is broken: it was not attempted (stop rule),
  and it skips the failing check by design.
