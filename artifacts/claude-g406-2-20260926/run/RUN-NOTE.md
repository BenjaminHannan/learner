# g406-2 run note (written 2026-09-27 03:06 UTC, date -u; late: the run started before the run-note rule reached this job)

- Machine: Ben's Mac, through the watcher (job handoff/queue/madeup-g406-2-mac.md; job agent via rungo4.sh). No PIDs are visible from this thread.
- Started: the watcher logged "launch madeup-g406-2-mac" at 2026-09-26 20:44:18 local (EDT) = 00:44:18 UTC 09-27.
- Expected steps: seal, selftests and leak check, then g406b (mu-405b's 240 packets, GLM low, up to 3 attempts, 70-minute cap), then g406, then RESULTS.md.
- What happened (from the watcher status push on builder-outbox at 03:02 UTC):
  - The job agent's shell killed the g406b command at its 80-minute limit ("shell tool terminated command after exceeding timeout 4800000 ms").
  - The job's err.txt was last written at 22:06 local = 02:06 UTC.
- Cause, as relayed by the Director at 03:06 UTC from Ben's Mac Claude (not checked here): the opencode Go plan has hit its usage limit. opencode.log shows "Go usage limit exceeded" from about 00:57 UTC. So GLM rows written after about 00:57 UTC are suspect.
- State: no RESULTS expected. Stopping the job needs its exact opencode PID killed on the Mac, and that is pending with the Director and the Thread manager.
- Next: g406-2 is re-queued as a fresh job with its long steps run in the background, after the plan resets. The seal (21d2ef2fd) and the marks are unchanged.
