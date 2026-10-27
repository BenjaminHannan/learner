# y1t addendum 8: who watches the BensPC chain, and how a hung step is stopped (Answering-from-memory thread, 2026-09-27 11:51 UTC, before any y1t training run; sealed in SEAL-y1t-add8.sha256.txt)

**Why:** the Thread manager's review of ADDENDUM-6 (11:4x UTC). The kit (0c454cda4, ADDENDUM-7) never stops a
process, and the old job's 4-hour cap and stop-by-PID are gone. A hung step would hold the BensPC GPU for every other
job. "The pass never stops a process" must not read as "nobody can". The kit does not change. This addendum only adds
who watches the chain, and the stop, which is a separate owner job.

**Who watches:** this thread.
- From the moment 180-y1t-benspc-bo-p1 reports LAUNCH until RESULTS-benspc.md exists, a self-wake wakes the thread
  every hour.
- On each wake the thread reads the watcher's status on builder-outbox, then queues a read-only peek, 000-y1t-peek-N
  (BASH-ONLY, GPU: no). The peek runs the kit's `boy1t.sh state` on BensPC and prints its output: the step, each log's
  last line and age, every python.exe with its PID and command line, and the GPU memory, power and free disk.
- The passes' own STALLED notes rarely appear, because the watcher holds GPU passes while python.exe runs. So the peeks
  are the watch.

**When a step counts as hung:** both of these hold.
- The running step's python.exe is alive, and its log has not changed for at least 30 minutes, on two peeks at least
  10 minutes apart.
- Or the chain is still running 8 hours after LAUNCH. This is a cap in place of the old job's 4 hours. The estimate for
  the whole chain is 2 to 4 hours, a guess.

**The stop:** an owner-stop job, 000-y1t-stop-<step> (BASH-ONLY, GPU: no). It follows the pattern of
000-bash-stop172-go2 and the taskkill /T test recorded for BensPC.
- It names the one PID that the last peek showed for the step: the venv launcher python.exe, whose command line runs
  that step's sealed script.
- Just before it acts, it lists python.exe again. It stops nothing (NOT-STOPPED) unless that PID still exists and its
  command line still runs the same script with the same arguments.
- It then runs `taskkill /T /F /PID <that PID>`, which ends the launcher and its child, and nothing else. It checks the
  PID is gone and prints the process list.
- chain.cmd then records a non-zero rc for that step and ends (chain.done). A later pass writes RESULTS-benspc.md as
  PARTIAL. Nothing is started again.

**Limits:**
- Only this run's own python.exe on BensPC is ever stopped, one exact PID at a time. Never a Mac process, never
  another job's process.
- If the stop is refused (a permission check, or the PID no longer matches), the thread tells the Thread manager and
  the Director and does not look for another way.

**Also for VERIFY-y1t.md (Thread manager, 11:4x UTC):**
- An h1_A failure ends the chain (chain.cmd's `goto end`), so h1_B does not run then. The old job said to report a
  5b failure and still finish step 6. Collection still happens, but h1_B is skipped. VERIFY will disclose this; the
  sealed kit is not edited.
- The watcher's push limit changed at b03ed54ef from `find -size -5M` to `-5120k` (files just under 5 MiB). The kit's
  3,900 KiB gzip threshold is still safe.
- VERIFY gives C: free space before the run (p1's DISK line) and after it (the collecting pass's DISK line). That
  checks the 2.2 GB estimate in ADDENDUM-7.
