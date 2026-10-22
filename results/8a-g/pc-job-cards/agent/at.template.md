job: at (AT-1: the agent-turn model B3AT, arm AT, at 3M, seed 400; 4,023,302 trained; the same pool p10-rung30-s400-a64-L, caps_b3g2.json and readout as G2f)
queue: 8aAT
next_queue: 8aATb
owner: Whole-model roadmap thread (PC queue; spec design/8a-g-gemma-growth-2026-10-08.md addendum AD) for the Build the talker thread (code, PR #69) and the big-run thread (marks AT-1a to AT-1f, big-run PLAN.md sixth Addendum 10-11)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aAT.log
stall_minutes: 900
paths: SRC = C:\Users\benja\custom-io\src-at (custom_io of the B3AT commit 6e72a5fae5, branch claude/project-thread-emwjvn; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3e as the inserted job WORK\insert\11-at.txt, right after G2f (B3 group 2, 3M, s400) and only if
  g2f_gate.ps1 (10-g2fgate.txt, just before it) found G2f not proved wrong on the B3G2-1 to B3G2-3 lines readable then. Accum AT=32 (a cautious guess).
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's AT\stdout.txt under WORK\results\Q-pc\ (before it exists the job is building the pool: look for a
  python process with custom_io.g8a.job in its command line). Stalled = its last "step" is the same as in the
  previous status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\Q-pc\8aAT-3M-s400\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in AT\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum AT
     doubled (32->64->128). Already 128: stop, NEEDS ATTENTION.
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Write C:\Users\benja\custom-io\q<next_queue>_run.cmd (ASCII), these 5 lines with N = <next_queue>:
     @echo off
     set PYTHONUTF8=1
     set PYTHONUNBUFFERED=1
     cd /d C:\Users\benja\custom-io\src-at
     C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\N-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\qN.log 2>&1
     Start it detached: Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\qN_run.cmd'}
  9. Save a copy of this card as atb.md (queue <next_queue>, next_queue 8aATc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md. (The chain waiter waits while WORK\STOP exists or a runner runs, so it waits for the relaunch.)
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done)
max_restarts: 2
next: the chain waiter goes on to its next inserted job (20-wide.txt, test WIDE), then g2c3 and B3 group 1; the roadmap thread reads RESULT.json against AT-1a to AT-1f
never: change seed, data, caps, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
