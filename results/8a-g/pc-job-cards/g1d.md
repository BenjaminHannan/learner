job: g1d (Gate G1, queue 8aG1d-pc: 8aG1d-3M-s400 only, arms B2 then PT, accum 4 each)
owner: Whole-model roadmap thread (Gate G1, spec design/8a-g-gemma-growth-2026-10-08.md addenda D-F)
gpu: yes
started: 2026-10-08 7:10 PM ET
log: C:\Users\benja\custom-io\work\q8aG1d.log
stall_minutes: 900
stall_check: the runner log above is quiet while the job trains. The live log is the newest stdout.txt under
  C:\Users\benja\custom-io\work\results\8aG1d-pc\ (a line about every 500 steps). Older than 45 min while a
  custom_io.train process runs: stalled -> report only.
alive: a python process whose command line contains 8aG1d-pc.txt (the queue runner; its parent is cmd.exe running q8aG1d_run.cmd)
done_when: the log prints "queue 8aG1d-pc done" and results\8aG1d-pc\8aG1d-3M-s400\RESULT.json says "status": "ok"
on_spill: report only. A STOP file is in place on purpose, and a waiter on the PC (cmd.exe /c C:\Users\benja\custom-io\q8aG1e_run.cmd)
  starts G1e when this runner exits, so stopping or relaunching anything here would collide with it.
on_crlf: report only
on_crash: report only
max_restarts: 0
next: nothing; the PC waiter q8aG1e_run.cmd starts G1e, and a Mac poller installs g1e.md and moves this card to done\
never: stop or start any process; change any file other than moving this card to done\ when done
