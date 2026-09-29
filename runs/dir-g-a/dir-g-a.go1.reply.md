Starting your GPU build — checking gates and seals before launch.
No duplicate found, but the GPU shows busy — verifying if it's this job or another.
Busy marker confirms this job. Reading sealed specs and checking for existing runs.
Shell quoting is proving tricky — trying alternate connection methods.
GPU idle, disk OK. Streaming sealed code to BensPC.
Archive is fine locally — switching to scp transfer instead of streaming.
Extraction succeeded. Verifying contents.
scp works. Compressing the tree for the slow link.
Tree in place. Running seal checks.
All seals pass (20/20, 3/3, 5/5). Checking torch, then selftests.
All checks pass. Starting the 200-step timing gate.
s13 launched (PID 20888). Waiting 2 min, then checking the log header.
Header lines match exactly. Waiting to the 5-minute mark for the memory reading.
Long wait timed out — checking current status.
Step 11000/60000 at min 18.6 — on pace (~101 min/net). Waiting for s13 to finish.
Log hasn't advanced in 40 min — checking if the process is alive.
Process died. Checking the log tail for the error.
No traceback — process vanished silently. Checking if BensPC rebooted.
s13 restarted clean (PID 27640, headers match). Waiting 60 min, then liveness check.
Step 38000/60000, alive and on pace. Waiting for finish.
s13 finished (98 min). Sealing final.pt before eval.
s13 sealed. Launching s14 (GPU free), evals will wait until training is done to avoid contention.
s14 headers match. Waiting 65 min.
s14 finished (98 min). Sealing, then poison+eval for s13.
s13 eval done. Running s14 poison.
Both evals done once each. Bundling result files for copy-back.
Extracting counts and log details for the run note.
Writing the run note.
Run note done. Moving final.pt files to model dirs.
Cleanup verified. Final check of push-ready files.
DONE — both primary nets finished, sealed, evaluated; no marks verdict (blind recount's job).

**Runs finished:** g-s13 and g-s14 (loop-G, K=4, pool h2, MODE=parallel, BensPC RTX 5070 Ti, torch 2.11.0+cu128/CUDA 12.8). s13: 02:45:45Z–04:23:48Z (98 min wall). s14: 04:24:23Z–06:02:40Z (98 min wall). Each eval and poison ran exactly once per checkpoint; both final.pt sealed before eval.

**tests.json counts as printed (integers, no verdict):**
- g-s13 — numbers4: S_pick 30, S_rand0 19, S_rand_mean 16.25, S_any 42, D 3.177; sums4: 300/300/300.0/300; grids5: 300/300/299.75/300; sums6: 297/296/295.5/298; grids6: 273/260/259.0/273; numbers5: 0/0/0.0/0.
- g-s14 — numbers4: S_pick 24, S_rand0 13, S_rand_mean 13.0, S_any 33, D 2.897; sums4: 300/300/300.0/300; grids5: 300/300/300.0/300; sums6: 295/294/295.0/296; grids6: 293/293/291.0/294; numbers5: 0/0/0.0/0.

**Practice exactness, last 3 log records (numbers4 per-stream / winner / any):**
- g-s13: step 59000 [0.261,0.179,0.226,0.230]/0.224/0.719; 59500 [0.264,0.183,0.218,0.233]/0.225/0.726; 60000 [0.280,0.198,0.231,0.250]/0.240/0.756.
- g-s14: step 59000 [0.312,0.264,0.279,0.247]/0.276/0.805; 59500 [0.322,0.264,0.279,0.251]/0.279/0.810; 60000 [0.291,0.243,0.255,0.220]/0.252/0.755.

**Poison V1:** both nets V1_identical true (sums 100/100, grids 100/100, numbers 100/100 identical). **steps_block_nograd:** 0 on both nets (and timing).

**Every deviation:**
1. `git archive | ssh tar` streaming hung on the 27 MB payload — used scp of gzipped tarballs instead; identical sealed bytes, seals 20/20, 3/3, 5/5.
2. Step-1 archive list omits 2 of 20 SEAL-code files (358u PASSMARKS.md, PASSMARKS-draft.md); fetched them from origin/main and verified — 20/20 OK, no code touched.
3. BensPC rebooted ~01:11Z, silently killing first s13 launch (PID 20888) at step 11000 with no traceback; relaunched the identical command from scratch (98 min). Partial log truncated by relaunch; no checkpoint existed, nothing evaluable lost.
4. nvidia-smi on WDDM shows no per-process compute memory (N/A) — recorded totals (11995/16303 MiB at ~5 min).
5. Poison+eval ran after both trainings (contention-free); per-checkpoint order kept, each exactly once.
6. Unrelated origin/main commit 70cb215ac landed mid-run; sealed tree already verified, unaffected.
7. 5-min memory reading came from the first identical s13 launch; 30-min projection replaced by step/min pacing post-reboot (both ~98 min, inside the 10 h cap).

**PUSH-ready (watcher to force-add; artifacts/ is ignored):** artifacts/claude-dir-g-build-20260928/runs/ (6 files per run + RUN-NOTE.md) and SEAL-run.sha256.txt. Weights never in repo: final.pt kept at C:/Users/benja/premonition-models/dirg/g-s13|g-s14/ and ~/premonition-models/dirg/g-s13|g-s14/ (sha256-matched both); C:/Users/benja/dirg/ removed and confirmed gone.
