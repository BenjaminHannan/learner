job: at10m (the agent-turn model B3AT, arm AT, at 10M, seed 400; shape S, 9,824,546 trained; the same pool p10-rung30-s400-a64-L, caps_b3g2.json and readout as AT-1; partner PTC / g2c10s, 9,814,442)
queue: 8aAT10M
next_queue: 8aAT10Mb
owner: Whole-model roadmap thread (PC queue) for the Build the talker thread (code, PR #69) and the big-run thread (gate lines and marks A10-1 to A10-4, big-run PLAN.md eighteenth Addendum 10-12)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aAT10M.log
stall_minutes: 1800
paths: SRC = C:\Users\benja\custom-io\src-at (custom_io of the B3AT commit 6e72a5fae5, branch claude/project-thread-emwjvn; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3e as the inserted job WORK\insert\16-at10m.txt, after 14-ptc10s and before 30-g2q, and only if
  at10m_gate.ps1 (15-at10mgate.txt, just before it) found AT-1 (8aAT, 3M, s400) not proved wrong on AT-1a, AT-1c, AT-1d (and AT-1f if its counters are in RESULT.json) against G2f and g2c3s. Accum AT=64 (a memory guess, B3G2's value at 10M).
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's AT\stdout.txt under WORK\results\Q-pc\ (before it exists the job is building the pool: look for a
  python process with custom_io.g8a.job in its command line). Stalled = its last "step" is the same as in the
  previous status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\Q-pc\8aAT10M-10M-s400\AT\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in AT\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum AT
     doubled (64->128->256). Already 256: stop, NEEDS ATTENTION.
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Write C:\Users\benja\custom-io\q<next_queue>_run.cmd (ASCII), these 5 lines with N = <next_queue>:
     @echo off
     set PYTHONUTF8=1
     set PYTHONUNBUFFERED=1
     cd /d C:\Users\benja\custom-io\src-at
     C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\N-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\qN.log 2>&1
     Start it detached: Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\qN_run.cmd'}
  9. Save a copy of this card as 8aat10mb.md (queue <next_queue>, next_queue 8aAT10Mc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md. (The chain waiter waits while WORK\STOP exists or a runner runs, so it waits for the relaunch.)
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done)
max_restarts: 2
next: the chain waiter goes on to its next inserted job (30-g2q.txt, then 46-tp.txt), then the rest of the chain; the roadmap thread reads RESULT.json against A10-1 to A10-4 (seconds per update: steps_per_s in RESULT.json, or the "elapsed" of the "train" step lines in AT\stdout.txt, one every 500 steps)
never: change seed, data, caps, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
