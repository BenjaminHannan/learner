# dir-h2 builder run note (queue job dir-h2-a, 2026-09-28)

Job: loop and plain, seeds 13 and 14 (4 nets), defaults only, on BensPC.
No marks and no verdict are recorded here; the blind recount step judges.

Common: GPU NVIDIA GeForce RTX 5070 Ti, torch 2.11.0+cu128, CUDA 12.8,
python C:/Users/benja/lis300/venv/Scripts/python.exe (3.10.9).
GPU-BUSY.txt named "queue job dir-h2-a" (this job) for the whole run.
Free disk on C: at start about 14.1 GB (over the 3 GB floor).
Memory line recorded after 5 min (19:34:55Z): nvidia-smi total 5113 MiB /
16303 MiB used, GPU-Util 80%; per-process compute memory reads N/A for every
process on this WDDM driver, so no per-net MiB is available; about 11 GB free,
and no third concurrent run was started (plan was two at a time; all 4 runs
finished inside the cap regardless).
Launch method: WMI Win32_Process.Create on `cmd /c C:\Users\benja\dirh2\W\run-<R>.cmd`
(new launcher files only; sealed code untouched); each run logged to W/<R>.log.
Two runs at once; the next pair started when the first pair finished.
Every run printed the pool line below as its first log line (pool built in ~89 s).

h2 pool line (identical in all 4 logs):
h2 pool: 36782 practice pairs over 1519 hands, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool

## loop-s13
- start (date -u, WMI launch): 2026-09-28T19:29:13Z (cmd PID 4960, python child 6644)
- end (date -u, final.pt LastWriteTimeUtc on BensPC): 2026-09-28T20:19:33Z
- minutes (train_summary.json): 50.3; weights 6438302; steps 60000/60000
- final.pt: 25764244 bytes, sha256 b1e803ed9f68322edc3a22d78cbe82fa143a4418b5a174b027c474128336a4e4
- last log line: {"step": 60000, "ce": 0.0957, "exact": 0.8787, "halt_bce": 0.1026, "lr": 0.0, "min": 50.3, "exact_by_kind": {"grids4": 0.972, "grids5": 0.894, "numbers3": 1.0, "numbers4": 0.4, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 0.999}, "dev": {"sums4": 200, "grids5": 199}}

## plain-s13
- start (date -u, WMI launch): 2026-09-28T19:29:13Z (cmd PID 15060, python child 20720)
- end (date -u, final.pt LastWriteTimeUtc on BensPC): 2026-09-28T20:16:33Z
- minutes (train_summary.json): 47.3; weights 6385149; steps 60000/60000
- final.pt: 25573143 bytes, sha256 736e24d9d48c404585ca87d458f3277ae230d6daa2bfb142f44f1137d1d65b91
- last log line: {"step": 60000, "ce": 0.0008, "exact": 0.9984, "halt_bce": 0.0, "lr": 0.0, "min": 47.3, "exact_by_kind": {"grids4": 1.0, "grids5": 0.991, "numbers3": 1.0, "numbers4": 1.0, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 1.0}, "dev": {"sums4": 200, "grids5": 199}}

## loop-s14
- start (date -u, WMI launch): 2026-09-28T20:30:25Z (cmd PID 22552)
- end (date -u, final.pt LastWriteTimeUtc on BensPC): 2026-09-28T21:20:33Z
- minutes (train_summary.json): 50.1; weights 6438302; steps 60000/60000
- final.pt: 25764244 bytes, sha256 b1124937910718c7ee7fce728230608cf4972d13e5fc6f783b69083c5ea59e21
- last log line: {"step": 60000, "ce": 0.0859, "exact": 0.8967, "halt_bce": 0.0946, "lr": 0.0, "min": 50.1, "exact_by_kind": {"grids4": 0.969, "grids5": 0.894, "numbers3": 1.0, "numbers4": 0.522, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 1.0}, "dev": {"sums4": 200, "grids5": 199}}

## plain-s14
- start (date -u, WMI launch): 2026-09-28T20:30:25Z (cmd PID 18212)
- end (date -u, final.pt LastWriteTimeUtc on BensPC): 2026-09-28T21:17:52Z
- minutes (train_summary.json): 47.4; weights 6385149; steps 60000/60000
- final.pt: 25573143 bytes, sha256 31de714ca356da16e3e6cb94ddf76845519e8af78006e715a9cfb0f78520d0e0
- last log line: {"step": 60000, "ce": 0.0016, "exact": 0.9967, "halt_bce": 0.0, "lr": 0.0, "min": 47.4, "exact_by_kind": {"grids4": 1.0, "grids5": 0.981, "numbers3": 1.0, "numbers4": 1.0, "sums1": 1.0, "sums2": 1.0, "sums3": 1.0, "sums4": 1.0}, "dev": {"sums4": 200, "grids5": 193}}

## Evals
poison, eval and extra ran exactly once per checkpoint, in that order, after
its sha256 was sealed; all 12 commands exited 0. No test item was opened or
printed; only counts were recorded.

## Deviations
1. The step-1 archive list names only SEAL-code.sha256.txt, but that file seals
   20 paths including two 358u PASSMARKS files that were not transferred, so the
   first `sha256sum -c` read 18 OK + 2 FAILED (missing files). The two sealed
   PASSMARKS files were fetched (keeping paths, nothing edited) and the check
   re-ran 20/20 OK before any training started.
2. Detached launch wrapped the exact task command in a new `W/run-<R>.cmd` file
   (stdout redirect needs a shell; sealed code untouched). The recorded PID is
   the cmd process; the python training process ran as its child (child PIDs
   recorded for the first pair). The planned stop method was taskkill /PID
   <cmd-PID> /T; it was never needed (no pool-line mismatch, no TOO-SLOW case).
3. Run end times above are the final.pt write times (LastWriteTimeUtc) on BensPC,
   i.e. training end; process-exit cleanup followed within minutes.
4. nvidia-smi on BensPC lists two background `Python310\python.exe` compute
   processes (PIDs varied) with N/A memory usage. They are not this job's venv
   python, were not started or touched by this job, and were present while the
   GPU still trained both nets at 80% util; left alone.

## Weights and cleanup
- BensPC keeps: C:/Users/benja/premonition-models/dirh2/<R>/final.pt (4 files).
- Mac keeps: ~/premonition-models/dirh2/<R>/final.pt (sha256-checked, match).
- C:/Users/benja/dirh2/ removed by exact path; confirmed gone (Test-Path False).
- Weights are never pushed: only runs/ and SEAL-run.sha256.txt are for PUSH.
