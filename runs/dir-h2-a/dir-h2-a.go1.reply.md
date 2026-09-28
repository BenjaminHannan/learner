Rate-limited run — starting the sealed 4-net build with minimal calls.
Duplicate gate clear — no prior results. Reading the sealed specs.
SSH is up (PowerShell shell). Checking the GPU busy marker.
Busy marker names this job (dir-h2-a) — proceeding. Reading the queue file.
Tree transferred. Verifying seals.
18/20 seal lines match; the 2 missing files (358u PASSMARKS) weren't in the step-1 archive list. Fetching those two sealed files so the 20-line check can complete.
20/20 code seal OK. Checking the H2 seal.
Both seals pass. Reporting torch version and running checks.
All checks pass. Looking up the detached-launch method prior builders used before starting training.
No prior-builder launch notes in repo — I'll use WMI `Win32_Process.Create` on `cmd /c <launcher.cmd>` (cmd interprets the batch itself and waits, so the recorded PID stays live and `taskkill /PID /T` can stop the tree). Creating the 4 launcher files locally first, then streaming them over.
Both runs launched (loop-s13 cmd PID 4960/python 6644; plain-s13 cmd PID 15060/python 20720; start 2026-09-28T19:29:13Z). Blocking 5 min, then checking pool lines and GPU memory in one call.
plain-s14 done; loop-s14 at step 59500 with its process tree live. Short blocking wait for loop-s14 to finish.
All 4 nets finished with final.pt files. Sealing the checkpoints (sha256 before any eval).
Writing the seal file on the Mac before any eval runs.
Seal written. Running poison → eval → extra for loop-s13.
loop-s13 evals done (exits 0). Same for plain-s13.
plain-s13 done. Same for loop-s14.
loop-s14 done. Last one: plain-s14.
All 12 eval commands ran exactly once, all exit 0. Copying result files back to the Mac with scp.
All files copied. Verifying the copied JSON files contain the same counts (counts only, no items).
Files match. Checking train_summary.json for exact start/end times for the run note.
Hashes match. Removing the BensPC work folder and confirming.
Writing the run note (fields only, no marks, no verdict).
Staging the push paths (force-add; watcher pushes).
DONE — all 4 runs finished, evaluated once each, artifacts staged, weights kept, work folder removed.

Counts as printed in the files (right of n=300; no verdict — the blind recount judges):
- loop-s13: numbers4 4 / sums4 300 / grids5 300 / P_other 7 / P_train24 117 (sums6 294, grids6 283; poison V1_identical true)
- plain-s13: numbers4 6 / sums4 300 / grids5 298 / P_other 7 / P_train24 300 (poison V1_identical true)
- loop-s14: numbers4 4 / sums4 300 / grids5 300 / P_other 10 / P_train24 174 (sums6 295, grids6 287; poison V1_identical true)
- plain-s14: numbers4 4 / sums4 300 / grids5 287 / P_other 10 / P_train24 300 (poison V1_identical true)
Copied-file checks match stdout exactly. Training minutes: 50.3 / 47.3 / 50.1 / 47.4. Torch 2.11.0+cu128, CUDA 12.8, RTX 5070 Ti. All 12 eval commands exited 0, each run exactly once in poison→eval→extra order.

Deviations:
1. SEAL-code first read 18 OK + 2 FAILED open-or-read: the step-1 archive list omits the two sealed 358u PASSMARKS files that SEAL-code.sha256.txt also seals. Fetched those two files (paths kept, nothing edited) and re-ran: 20/20 OK before training; H2 seal 3/3 OK.
2. Detached launch wrapped the exact task command in new `W/run-<R>.cmd` files (redirect needs a shell; sealed code untouched) via WMI Win32_Process.Create; recorded cmd PIDs (4960/15060/22552/18212) plus python child PIDs for pair 1. Planned stop was taskkill /PID /T; never needed.
3. Run end times in RUN-NOTE.md are final.pt LastWriteTimeUtc on BensPC (loop-s13 20:19:33Z, plain-s13 20:16:33Z, loop-s14 21:20:33Z, plain-s14 21:17:52Z).
4. nvidia-smi shows two background `Python310\python.exe` processes with N/A memory (not this job's venv python, untouched, present throughout; GPU still ran both nets at 80% util). Per-process compute MiB reads N/A for all processes on this WDDM driver; 5-min totals were 5113/16303 MiB. No third concurrent run (2-at-once plan; all finished inside the cap, so no TOO-SLOW case).
5. GPU-BUSY.txt named `dir-h2-a` throughout = this job; left to the watcher. No rentals, no installs, no downloads. `C:/Users/benja/dirh2/` removed by exact path, confirmed gone. Staged for push: `runs/` (24 files + RUN-NOTE.md) and `SEAL-run.sha256.txt` only — no weights. Final.pt files kept at `C:/Users/benja/premonition-models/dirh2/<R>/` and `~/premonition-models/dirh2/<R>/`, sha256-checked equal.
