# smoke-336-win RESULTS: FAIL (BensPC, 2026-09-24)

Verdict: FAIL. The joined month-end agent did not run on BensPC. Exit code 1
after ~1.7 s wall time. Nothing was written: `arm_smoke.jsonl` was not created
(the `--out` directory was never created on BensPC). No code was edited.

## Command (from tree root, exactly as specified)

```
python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-smoke336win-20260924/run --arm claude_chat338_run:build_P --name smoke --model C:/Users/benja/lis301/work/run/merged --gen-model C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc --lives e2e-dev-01
```

- Python: C:/Users/benja/lis300/venv/Scripts/python.exe (3.10.9)
- Env: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
- Exit code: 1. Wall time: ~1.7 s (WALLSEC 1.68 on run 1; rerun for log capture
  identical). GPU idle before run (~599 MiB used); process exited immediately.

## Exact error (console stdout, in full)

```
MISSING-CACHE: the self122 MiniLM router did not load (FileNotFoundError(2, 'The system cannot find the path specified')); restore the Hugging Face snapshot, then rerun. Nothing was run.
```

Traceback: none. The runner raises SystemExit with the message above
(scripts/claude_e2e336_run.py preflight, lines ~212-218); there is no Python
traceback. The full console output is preserved in `run/smoke336win_console.txt`.

## Counts

- Rows written to arm_smoke.jsonl: 0 (file not created; expected >= 20 = the 20
  user turns of DEV life e2e-dev-01, plus any confirm_answer rows).
- Median ms per turn: n/a (nothing ran).
- Slowest ms per turn: n/a (nothing ran).
- GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total.
- Lives attempted: e2e-dev-01 only (20 user turns: day1=6, day2=7, day3=7).

## Verified inputs (all matched, none pushed)

- Combined tree: git archive origin/builder-outbox, then git archive
  origin/main on top; self122_head.pt copied in, sha256
  5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).
  Tree on BensPC: C:/Users/benja/lis301/work/smoke336win/tree (scripts,
  winshim, DEV bank all present).
- READER C:/Users/benja/lis301/work/run/merged/model.safetensors sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (full match).
- BASE C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  (commit hash matches expected 87179e5c...).
- DEV bank artifacts/claude-e2e331-dev-20260924 (dev data, 10 lives, 194 turns,
  131 facts) present in tree. No panel file opened, read, or quoted.

## What this means (and does not mean)

- The Windows `resource` shim is NOT the blocker: `import resource` via
  scripts/winshim succeeds on BensPC (ru_maxrss=0 namespace), and
  `import fable_reasoner50` (the module with the Unix-only `import resource`)
  succeeds with scripts + scripts/winshim on sys.path, exactly as the runner
  sets up on nt.
- The blocker is the missing self122 MiniLM snapshot on BensPC:
  C:/Users/benja/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2
  does not exist (cache holds only allenai scibert and openbmb MiniCPM5-1B).
  The preflight calls fable_self122.route122 with HF_HUB_OFFLINE=1, so it
  cannot download mid-run and exits before any turn.
- Recommendation: Sunday's registered run 336 should NOT stay on BensPC as-is.
  Either restore the MiniLM snapshot to benja's Hugging Face cache on BensPC
  and re-run this smoke, or keep 336 on a rented Linux GPU per
  design/v3/30-modes/330-rent-kit.md.
