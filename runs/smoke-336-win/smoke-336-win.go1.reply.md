Smoke test queued — verifying BensPC can run the joined agent via the Windows shim.
Spec confirmed — now locating the BensPC access path.
BensPC is reachable — now checking the remote environment.
Tree layout mapped — now assembling the combined codebase.
Package verified — now staging the run on BensPC.
Pre-flight checks passed — transferring the tree to BensPC.
Staging complete — launching the smoke run on BensPC.
First attempt failed fast — capturing the full error.
Failure is a missing model cache, not the shim — verifying the details.
Verdict is clear — writing up the results.
Results written — confirming the artifacts will reach the watcher.
FAIL — BensPC cannot run the joined month-end agent right now. The smoke run exited 1 after ~2 seconds with zero rows. The Windows `resource` shim works; the blocker is a missing MiniLM model snapshot in BensPC's cache. Sunday's registered run 336 should not stay on BensPC as-is.

Marks table (integer counts):

| check | count / value |
|---|---|
| command exit code | 1 |
| wall time (s) | ~2 (1.68 measured) |
| rows in arm_smoke.jsonl | 0 (file not created) |
| expected rows (e2e-dev-01 user turns) | 20 (day1=6, day2=7, day3=7) |
| median ms per turn | n/a (0 rows) |
| slowest ms per turn | n/a (0 rows) |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16303 MiB |
| READER sha256 match | 1/1 (b4fd93a2…d21b890 full match) |
| BASE snapshot match | 1/1 (87179e5c…525bfc) |
| self122_head.pt sha256 match | 1/1 (5ca02173…c8ee25) |
| winshim `import resource` on BensPC | 1/1 ok |
| `import fable_reasoner50` on BensPC | 1/1 ok |
| MiniLM snapshot on BensPC | 0 (missing) |
| code files edited | 0 |
| TEST-ONLY panel items opened/quoted | 0 |
| time used (min, cap 20, end-by 20:00 ET) | ~9, finished 09:24 ET |

Every move:
1. `git fetch -q origin main builder-outbox`; read task, rent-kit section A, runner source, and DEV README via `git show` only.
2. Built combined tree (builder-outbox, then main on top, self122_head.pt copied in, sha verified) and packed tree.tgz (155 MB).
3. Verified BensPC idle (GPU ~599 MiB used, no python running), READER sha full match, BASE snapshot present.
4. Copied tree to C:/Users/benja/lis301/work/smoke336win/tree on BensPC, verified winshim/resource.py, DEV bank, and self122_head.pt there.
5. Ran the exact specified command (lis-301 venv python 3.10.9, PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, --lives e2e-dev-01). Exit 1.
6. Re-ran once to capture the log verbatim; confirmed out dir never created (0 rows).
7. Read-only diagnostics: winshim import ok, reasoner50 import ok, MiniLM cache dir absent (cache holds only scibert + MiniCPM5-1B).
8. Wrote new files only: artifacts/claude-smoke336win-20260924/RESULTS.md + run/smoke336win_console.txt. Left pushing to the watcher.

Every miss / deviation:
- Miss: arm_smoke.jsonl not written (0 of >=20 rows); PASS criteria not met.
- Exact error: `MISSING-CACHE: the self122 MiniLM router did not load (FileNotFoundError(2, 'The system cannot find the path specified')); restore the Hugging Face snapshot, then rerun. Nothing was run.` No Python traceback (SystemExit preflight, HF_HUB_OFFLINE=1 so no mid-run download).
- Deviation: none from the specified command or tree recipe. Two extra read-only import probes and one log-capture rerun; no flags changed, no code edited.

What it means in plain English: think of the agent as needing three keys to start — the reader model, the base model, and a small router model. The first two keys are on BensPC and fine, and the new Windows adapter for the missing system part works. But the third key (the MiniLM router snapshot) was never copied to BensPC, so the run locks itself out before doing anything.

What it doesn't mean: this says nothing about the quality of the agent or the DEV data — zero turns ran, so zero judgments about replies. It also doesn't mean BensPC is hopeless: restore that one cached snapshot and re-run this exact smoke, or keep run 336 on a rented Linux GPU.
