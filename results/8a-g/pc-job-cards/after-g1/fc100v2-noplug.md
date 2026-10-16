job: fc100 part 2 of 2 (100M fit check on B3 group 2: peak memory and step time of five dense 512-wide ~100M thinker shapes, 21, 26, 30, 34 and 37 layers, on group 2's model and inputs)
queue: 8aFC2
next_queue: none (no restarts: a spill or out-of-memory IS the measurement)
owner: Whole-model roadmap thread for the Architecture and big-run threads (FINISHED-MODEL-2026-10-09.md item 10, shape list revised 4:38 PM ET 10-11, exact values 4:41 PM ET; spec design/8a-g-gemma-growth-2026-10-08.md addenda S and W)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aFC2.log
stall_minutes: 180
paths: SRC = C:\Users\benja\custom-io\src-b3g2 (custom_io of claude/learner-new-g2 with the reader-rule fixes, see SRC\G2-SETUP-OK.txt; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = 8aFC2
starts_when: started by the post-G1 chain waiter (C:\Users\benja\custom-io\q8aPost3_wait.ps1, v3d, log WORK\q8aPost-waiter.log)
  right after fc100 part 1 (queue 8aFC) built the pool. The steps below are for a manual relaunch only.
runs: 8a-data (checks G1's inputs), 8aFC2-caps-3M-s400 (writes WORK\g8a\pools\p10-rung30-s400-a64-L.caps-B3G2\caps.json from
  caps_b3g2.json; --maxh 1e-9 then skips its arm, so "arm_failed" with B3G2 "skipped_maxh" is EXPECTED: nothing trains), then ten
  runs of 20 updates (256 rows each, no eval): the five shapes at accumulation 64 (4 rows per pass), then the five at 256 (1 row per
  pass). All d 512, 8 heads, NO PLUG (Ben, 4:12 PM ET 11 Oct: Gemma's own 512 numbers through a zero-start LayerNorm(512); "eg_pre": true
  in each --cfg; install_rr.ps1 proved that state with `eg check cpu pre` before installing); trained counts (b3g2, caps_b3g2; the
  architecture thread's no-plug list of 7:20 PM ET, configs.b3_cfg 100M noplug, counted at G2f's 74d6e92c75): 21 layers (mlp 4.83496)
  = 102,299,413; 26 (3.13379) = 102,300,918; 30 (2.18066) = 102,294,742; 34 (1.45215) = 102,294,716; 37 (1.00879) = 102,288,034.
launch: 1. SRC\G2-SETUP-OK.txt must exist, Get-FileHash SRC\custom_io\g8a\caps.py must be
     32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E, WORK\g8a\pools\p10-rung30-s400-a64-L must exist (fc100 part 1),
     and WORK\STOP must not exist; else stop, report.
  2. Write C:\Users\benja\custom-io\q8aFC2_run.cmd (ASCII), these 5 lines:
     @echo off
     set PYTHONUTF8=1
     set PYTHONUNBUFFERED=1
     cd /d C:\Users\benja\custom-io\src-b3g2
     C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\8aFC2-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\q8aFC2.log 2>&1
  3. Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\q8aFC2_run.cmd'}
  4. Copy this card to C:\Users\benja\pc-jobs\fc100v2.md with started = now (ET).
stall_check: the live log is the running run's WORK\results\Q-pc\<run>\stdout.txt. Stalled = its last "step" is the same as in the
  previous status while a custom_io.train process runs -> report only. (Never use LastWriteTime on Windows.)
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done". Then report, for each of the ten 8aFC2-<blocks>x512-a<accum> runs: status,
  n_params, steps_per_s, peak_mem_mib, peak_reserved_mib from its RESULT.json (or the error line from stdout.txt), and the largest
  shared GPU memory seen during it. The Architecture thread applies FINISHED-MODEL item 10 rule (3): the deepest shape that fits
  16 GB with a step time at most 1.25 x that of 21 x 512 (same accumulation).
on_spill: report only (the numbers are the result)
on_crash: report only (an out-of-memory run fails fast and the next run starts; that is expected). If 8aFC2-caps-3M-s400 failed
  before writing the caps, all ten runs fail for lack of caps.json: report that.
max_restarts: 0
next: the chain waiter starts fc100 part 3 (answer speed, card fc100v3.md) itself when this queue ends, then g2c3
never: change any line of the queue file; run two queues at once; touch G1's results, pools or checkpoints;
  delete anything
