# RUN-NOTE: dir-g-a (loop-G seeds 13, 14, primary) on BensPC

Job window (date -u on Mac): start 2026-09-29T00:31:31Z. GPU-BUSY.txt named
"queue job dir-g-a" = this job; left untouched.

## Per-run record

### g-s13
- Launched (first): 2026-09-29T00:46:10Z, WMI PID 20888. Killed by a BensPC
  reboot (~01:11Z, System Boot Time 9/28 9:11 PM local) at step 11000
  (min 18.6), no traceback in the log. Relaunched identical command.
- Launched (final): 2026-09-29T02:45:45Z, WMI PID 27640.
  End: 2026-09-29T04:23:48Z (final.pt mtime). Wall 98.1 min;
  train_summary minutes 97.4.
- GPU: NVIDIA GeForce RTX 5070 Ti. torch 2.11.0+cu128, CUDA 12.8.
  MODE=parallel (no --serial-streams).
- Timing gate (step 5, seed 13, 200 steps, parallel OK first try):
  sec_per_step_mean_after_20 0.0984, peak_cuda_gb 8.84,
  projected_minutes_per_net_60000_steps_alone 98.4, steps_block_nograd 0.
  2 x T = 196.8 min < 540: gate passed, sequential training
  (2 x 8.84 + 2 = 19.68 GB needed > 16.3 GB total).
- Memory line (2026-09-29T00:50:56Z, ~5 min into first launch, nvidia-smi):
  11995MiB / 16303MiB used, free ~4308MiB, util 66%, 222W.
  Per-process compute memory not shown (WDDM lists graphics procs as N/A).
- h2 pool line as printed:
  "h2 pool: 36782 practice pairs over 1519 hands, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool"
- weights line as printed:
  "loop-g K=4 pool=h2 seed 13: 6440350 weights (2048 new), data ready in 83s on cuda"
- Last log line (step 60000, min 97.3): ce 0.0951, exact 0.8505,
  exact_any_stream 0.9408, halt_bce 0.0889, lr 0.0.
- final.pt: 25772687 bytes,
  sha256 6832f4d655242b7183c77edaa1c39c1bce1304083c7ef79937e75580b8739a5f
  (sealed in SEAL-run.sha256.txt BEFORE poison/eval).
- poison (once): V1_identical true (sums 100/100, grids 100/100, numbers 100/100).
- eval (once): tests.json written; counts only, no verdict here.

### g-s14
- Launched: 2026-09-29T04:24:23Z, WMI PID 2812.
  End: 2026-09-29T06:02:40Z (final.pt mtime). Wall 98.3 min;
  train_summary minutes 97.2.
- GPU: NVIDIA GeForce RTX 5070 Ti. torch 2.11.0+cu128, CUDA 12.8.
  MODE=parallel (same timing gate as above).
- Memory: no separate reading (same command/shape as s13; GPU idle before
  launch, s13 done).
- h2 pool line as printed:
  "h2 pool: 36782 practice pairs over 1519 hands, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool"
- weights line as printed:
  "loop-g K=4 pool=h2 seed 14: 6440350 weights (2048 new), data ready in 78s on cuda"
- Last log line (step 60000, min 97.1): ce 0.0911, exact 0.8532,
  exact_any_stream 0.9403, halt_bce 0.083, lr 0.0.
- final.pt: 25772687 bytes,
  sha256 c1049a23815ad158105816d64b8b245a418a85792c56ac9b06260d78c99a8c68
  (sealed in SEAL-run.sha256.txt BEFORE poison/eval).
- poison (once): V1_identical true (sums 100/100, grids 100/100, numbers 100/100).
- eval (once): tests.json written; counts only, no verdict here.

## Seal checks (step 2, sha256sum -c under Git Bash, C:/Users/benja/dirg)
- artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt: 20 of 20 OK.
- artifacts/claude-dir-h2-numbers-20260928/SEAL-h2.sha256.txt: 3 of 3 OK.
- artifacts/claude-dir-g-build-20260928/SEAL-g.sha256.txt: 5 of 5 OK.

## Step-4 checks (all passed)
- claude_rsn358a_envs.py selftest: "selftest ok: 1362 four-hands ...".
- claude_dir_h2_pool.py selftest: ends "selftest ok".
- claude_dir_g_run.py selftest: ends "selftest ok (torch 2.11.0+cu128 CPU fp32)";
  [V2] max abs diff logits 0.0, halt_logit 0.0, ce 4.8e-07, halt_loss 1.2e-07
  (bar 1e-5); [V2b], [K4], [eval], [size] all ok.
- claude_dir_g_run.py check-mask: "check-mask ok: ...".

## Every deviation
1. Transfer: `git archive ... | ssh benspc tar` stalled on the 27 MB stream
   (small stdin works; large-stream ssh stdin hung twice). Used scp of a
   gzipped tarball instead (5.8 MB). Same sealed bytes; all seals 20/20, 3/3, 5/5.
2. The task's step-1 archive list omits 2 of the 20 SEAL-code files
   (artifacts/claude-rsn358u-20260927/PASSMARKS.md, PASSMARKS-draft.md).
   Fetched those 2 sealed files from origin/main and verified: 20/20 OK.
   No code touched.
3. BensPC rebooted ~01:11Z mid-run, killing s13 (PID 20888) at step 11000
   with no error in the log. Relaunched the identical command (PID 27640)
   from scratch; the partial log was truncated by the relaunch redirect
   (no checkpoint had been written; nothing evaluable lost).
4. nvidia-smi on WDDM shows no per-process compute memory (N/A); totals only.
5. Poison+eval ran after both trainings finished (GPU contention avoided);
   per checkpoint order kept (poison then eval), each exactly once.
6. Unrelated origin/main commit 70cb215ac (opus queue files) landed mid-run;
   sealed tree was already archived and verified; unaffected.
7. 5-minute memory reading came from the first (identical) s13 launch; the
   30-minute projection was replaced by step/min pacing after the reboot
   (both nets ~98 min wall, inside the 10 h cap).

No marks, no verdict. Counts are in runs/g-s13/tests.json and
runs/g-s14/tests.json for the blind recount.
