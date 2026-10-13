job: ptc3s (arm PTC = the plain 3M model with worked steps on every row, TRAINED WITH THE CALCULATOR: calc_train; same pool p10-rung30-s400-a64-L, caps_b3s.json, seed 400 and eg_embed as g2c3s)
queue: 8aPTC3S
next_queue: 8aPTC3Sb
owner: Whole-model roadmap thread (PC queue; spec design/8a-g-gemma-growth-2026-10-08.md addendum AG, section 38: the calculator fairness rule, arm PTC)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aPTC3S.log
stall_minutes: 600
paths: SRC = C:\Users\benja\custom-io\src-ptc (custom_io of claude/learner-new-g2 at 1acfde9a73 = src-b3g2 + the PTC overlay files from install_ptc.ps1; never edit it, never edit src-b3g2)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3e (C:\Users\benja\custom-io\q8aPost3_wait.ps1, log WORK\q8aPost-waiter.log) as the inserted job
  WORK\insert\13-ptc3s.txt, at its insert check point after group 2 at 3M, right after 11-at and 12-g2c10s and before 14-ptc10s, 30-g2q and 46-tp.
  Accum PTC=16, as g2c3s's PTS=16 (cautious: long rows pad micro-batches to up to 2,000 letters).
launch: for a manual relaunch only: as fc100.md's launch steps 1-4 (SRC src-ptc and its caps.py hash, step 6 below), with 8aPTC3S in place
  of 8aFC and ptc3s.md in place of fc100.md.
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's PTC\stdout.txt under WORK\results\Q-pc\ (before it exists the job is building the pool: look for a
  python process with custom_io.g8a.job in its command line). Stalled = its last "step" is the same as in the
  previous status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\Q-pc\8aPTC3S-3M-s400\RESULT.json says "status": "ok" (else report); also read cap_hits in that RESULT.json: calc_mismatch / calc_rows is mark M1 (at most 0.1%), and the cap-hit "total" must be 0 (the calc_* counters are outside it)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in PTC\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum PTC
     doubled (16->32->64). Already 64: stop, NEEDS ATTENTION.
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Launch <next_queue> as in fc100.md's launch steps 2-3 (q<next_queue>_run.cmd, log WORK\q<next_queue>.log).
  9. Save a copy of this card as ptc3sb.md (queue <next_queue>, next_queue 8aPTC3Sc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md.
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done)
max_restarts: 2
next: the chain waiter runs 14-ptc10s (card ptc10s.md) next, then the other inserts in name order (30-g2q, 46-tp), then the chain goes on
never: change seed, data, caps, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
marks: (spec addendum AG, fixed before any PTC run; this card only runs the job, it judges nothing)
  M1 works: calc_mismatch at most 0.1% of training rows (cap_hits in RESULT.json); PTC 3M pooled-5 at least g2c3s's `calc` pooled-5 minus 2.0.
  M2 uses the tool (prediction, not a gate): `nocalc` drops PTC's 13-family block by 5 or more at 3M.
  M3 the question: fair gap = (B3G2 10M - B3G2 3M) - (PTC 10M - PTC 3M), reported beside the same gap with PTS's `calc` lesion; if PTC's gain and PTS-with-calculator's
  gain differ by more than 1.5, later size reads need a trained PTC. Proved wrong ("the calculator explains the size gap"): the fair gap at or below -1.0 on seed 400.
  Intact = calculator on; the lesion is `nocalc` (RESULT.json lessons.nocalc), not `calc`.
cost: about 3 PC hours (a guess from g2c3s's run and the per-row mask cost); $0
