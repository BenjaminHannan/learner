job: b3g2d (the 10M depth pair's deep twin D: arm B3G2 at 10M, 13 blocks x 192, 4 heads, mlp 5.0651, 9,930,379 trained, seed 400, caps_b3g2.json, pool p10-rung30-s400-a64-L; marks DP-0 to DP-2 sealed in big-run PLAN.md, Addendum 10-11 8:30 AM ET)
queue: 8aB3G2D10M
next_queue: 8aB3G2D10Mb
owner: Whole-model roadmap thread for the Architecture and big-run threads (FINISHED-MODEL-2026-10-09.md item 10; spec design/8a-g-gemma-growth-2026-10-08.md addendum S; queue file from the Architecture thread)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aB3G2D10M.log
stall_minutes: 900
paths: SRC = C:\Users\benja\custom-io\src-b3g2 (custom_io of claude/learner-new-g2 at 1acfde9a73, same as 9dbcbb579c; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3c as an inserted job (WORK\insert\10-depth-pair-D.txt), alone, at the first
  check point after B3 group 2 at 3M. Accum B3G2=64 and MEM 11000 are guesses (unmeasured). Read after: D against S (group 2's own 10M
  seed 400 shape, 7 x 256) on DP-0 to DP-2; cap counters 0 (B3G2-6).
launch: for a manual relaunch only: as fc100.md's launch steps 1-4 (SRC src-b3g2 and its caps.py hash, step 6 below), with 8aB3G2D10M in place
  of 8aFC and 8ab3g2d10m.md in place of fc100.md.
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's B3G2\stdout.txt under WORK\results\Q-pc\ (before it exists the job is building the pool: look for a
  python process with custom_io.g8a.job in its command line). Stalled = its last "step" is the same as in the
  previous status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\Q-pc\8aB3G2D-10M-s400\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in B3G2\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum B3G2
     doubled (64->128->256). Already 256: stop, NEEDS ATTENTION. (DP-2: an out-of-memory death is re-run, same seed.)
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Launch <next_queue> as in fc100.md's launch steps 2-3 (q<next_queue>_run.cmd, log WORK\q<next_queue>.log).
  9. Save a copy of this card as 8ab3g2d10mb.md (queue <next_queue>, next_queue 8aB3G2D10Mc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md.
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done)
max_restarts: 2
next: the chain waiter goes on (other inserted jobs, B3 s401 if alive, then g2c10s and c30s) when this queue ends
never: change seed, data, caps, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
