# Practice launch (2026-09-28)

Started 2026-09-28T19:07:03Z (date -u). Recipe: PASSMARKS-C.md (12,000 batches of 64, guard SOURCE_SEED+300).
- seed 0: pid 18068, 2 threads, log artifacts/claude-relnet-eq-20260928/practice-s0.log, out runs/relnet-s0
- seed 1: pid 18069, 1 thread, log practice-s1.log, out runs/relnet-s1
- hand-over helper: pid 18540 (scripts/claude_relnet_eq_rebalance.py, log rebalance.log). When seed 0 exits it waits for
  seed 1's next checkpoint, stops seed 1 by its exact PID and resumes it on 3 threads (new PID in rebalance.log).
- Expected finish (suggested): seed 0 about +6 h, seed 1 about +8 h (TIMING-ESTIMATE.md).
- Weights (source.pt) stay local and untracked; hashes go in source.json.

## Restart after the container restart (2026-09-28)
- **What happened (shown):** the container restarted at about 20:40 UTC and killed practice s0, practice s1 and the
  hand-over helper. Read at 20:44 UTC (`date -u`), no training: `runs/relnet-s0/resume.pt` holds **step 6000**
  (saved 20:39:38 UTC, 5,552 s of training); `runs/relnet-s1/resume.pt` holds **step 2000** (saved 20:12:06 UTC,
  3,901 s). Both files hold the net, the AdamW state (33 parameter entries), the schedule (last_epoch = step), the
  round-draw RNG and the source-puzzle RNG, so the recipe carries on exactly where it stopped.
- **Lost (shown):** seed 0 under a minute of work after its step-6000 save; seed 1 about 28 minutes (roughly 850 steps
  after step 2000; its step-3000 checkpoint had not yet been written). Untracked logs before the restart are kept as
  `practice-s{0,1}.before-restart.log`; the restart appends to `practice-s{0,1}.log`.
- **Relaunched 2026-09-28T20:44:33Z**, detached, same script and recipe, from resume.pt:
  - seed 0: PID 702, **1 thread**, resumes at step 6000 (6,000 to go)
  - seed 1: PID 704, **2 threads**, resumes at step 2000 (10,000 to go)
- **Why this split (suggested):** the pre-restart logs gave 0.93 s/step for seed 0 on 2 threads and 1.95 s/step for
  seed 1 on 1 thread. With 3 cores, seed 1 has far more left, so it gets 2 threads: seed 1 about 10,000 x 0.93 s =
  2.6 h (about 23:20 UTC), seed 0 about 6,000 x 1.95 s = 3.3 h (about 00:00 UTC on Sep 29). The other split (seed 0
  on 2, seed 1 on 1) would leave seed 1 running about 5 h. No hand-over helper this time (not needed; nothing to
  relaunch). Guard scoring adds a few minutes at the end of each.
- **Does resuming give the same result as a straight run? Untested.** RNG, optimizer and schedule are restored, but
  seed 0 changes from 2 to 1 threads, and float sums differ with the thread count, so the weights will not be
  bit-identical to a run that never stopped. The same is true of any two runs on different thread counts; the recipe
  is unchanged.
