job: wide (test WIDE: B2 seed 400 at about 10M by width, rung 10MW: 448 wide, 7 heads, 2 blocks, mlp 4.8, 12 rounds, 10,173,509 trained; G1's 10M pool and 24,000 updates)
queue: 8aWIDE
next_queue: 8aWIDEb
owner: Whole-model roadmap thread (spec design/8a-g-gemma-growth-2026-10-08.md addendum AB; marks there: pass >= 76.31, fail <= 75.01)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aWIDE.log
stall_minutes: 600
paths: SRC = C:\Users\benja\custom-io\src-wide (G1's src-8ag custom_io with configs.py adding rung 10MW only; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3e as an inserted job (WORK\insert\20-wide.txt) at its check point after B3 group 2 at 3M (G2f).
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's B2\stdout.txt under WORK\results\Q-pc\. Stalled = its last "step" is the same as in the previous
  status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\Q-pc\8aWIDE-10MW-s400\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in B2\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum B2
     doubled (8->16->32). Already 32: stop, NEEDS ATTENTION.
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Write C:\Users\benja\custom-io\q<next_queue>_run.cmd (ASCII), these 5 lines with N = <next_queue>:
     @echo off
     set PYTHONUTF8=1
     set PYTHONUNBUFFERED=1
     cd /d C:\Users\benja\custom-io\src-wide
     C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\N-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\qN.log 2>&1
     Start it detached: Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\qN_run.cmd'}
  9. Save a copy of this card as wideb.md (queue <next_queue>, next_queue 8aWIDEc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md. (The chain waiter waits while WORK\STOP exists or a runner runs, so it waits for the relaunch.)
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done)
max_restarts: 2
next: the chain waiter goes on to its next step when this queue ends; the roadmap thread reads RESULT.json against the marks
never: change seed, data, caps, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
