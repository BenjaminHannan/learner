job: g1e (Gate G1: 3M-s401 only; its two 10M jobs run in queue 8aG1f, started by q8aG1f_wait.ps1)
queue: 8aG1e
next_queue: 8aG1f
owner: Whole-model roadmap thread (Gate G1, spec design/8a-g-gemma-growth-2026-10-08.md addenda D-H)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aG1e.log
stall_minutes: 900
paths: SRC = C:\Users\benja\custom-io\src-8ag   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's PT\stdout.txt if it exists, else its B2\stdout.txt, under WORK\results\Q-pc\. Stalled = its last "step"
  is the same as in the previous status (pc-status.md) while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "STOP file present: 2 runs not started" and "queue Q-pc done"; then
  WORK\results\Q-pc\Q-3M-s401\RESULT.json says "status": "ok" (else report). WORK\STOP is there on purpose (9 Oct,
  9 AM ET): it keeps the 10M jobs out of this queue. Never remove it; q8aG1f_wait.ps1 moves it when this runner exits.
on_spill: report only. 3M-s401 spilled at accum 4 (0.43 steps/s) and is kept running to its end on purpose: a restart
  would throw away 9,500 steps, and accum 4 keeps it identical to 3M-s400 (spec addendum H, 9 Oct 9 AM ET).
on_crlf: report only (the data checks of this queue already passed)
on_crash: report only (any other Traceback, an arm rc not 0, or the runner gone before done)
max_restarts: 0 (nothing in this queue is restarted)
next: q8aG1f_wait.ps1 (already running, log WORK\q8aG1f-waiter.log) starts 8aG1f, installs g1f.md and moves this card to done\
never: change seeds, data, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch finished result folders or checkpoints; never run two G1 queues at once
