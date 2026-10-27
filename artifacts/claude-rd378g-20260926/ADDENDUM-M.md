# rd-378g addendum M (2026-09-27 12:17:41 UTC): pass names, R's recorded folder, and who watches the chain

Written after ADDENDUM-L (b6833c2b7) and before any BensPC step for rd-378g has run. The experiment does not change.
This file adds three things to the runner, at the Director's request (12:00 UTC) and from a check of rd-378's run
record. It is sealed in SEAL-ADD-M.sha256.txt.

## 1. Pass names
The Director named the passes 185-rd378g-benspc-bo-p1 to p4 (12:00 UTC). Each GPU line names its own job literally.
They stay in handoff/held/ until the Director releases p1 in its turn: after 358s (160-164), rv390 (173/174) and
y1t (180).

## 2. R's recorded folder is searched first (kit fix, bo378g.sh only)
- rd-378's run record says R (merged sha256 dbcc8db5...8510) is kept at C:/Users/benja/rd378/tree/WORK/nrun/merged
  (artifacts/claude-rd378-20260925/RESULTS-benspc.md:141-144, builder-outbox).
- ADDENDUM-L's search looked only 2 levels below a folder named *rd378*, so it would have missed R there. It would then
  have copied R from the Mac, or used the 57% fallback, while R was on BensPC all along.
- `bo378g.sh find-r` now hashes that recorded folder first, then searches as before.
- `bo378g.sh state` also prints one OUT line per step output file (bytes and age in minutes; counts only). The two write
  steps log only when they end, so the size of their output file is their progress.
- SEAL-ADD-L's bo378g.sh line is replaced by SEAL-ADD-M's. The other seven files of ADDENDUM-L are unchanged.

## 3. Who watches the chain, and how a hung step is stopped (as y1t's ADDENDUM-8)
The kit never stops a process. That must not read as "nobody can".

**Who watches:** this thread.
- A self-wake runs every hour, from the moment 185-rd378g-benspc-bo-p1 reports LAUNCH until RESULTS-benspc.md exists.
- On each wake the thread reads the watcher's status on builder-outbox. It then queues a read-only peek,
  000-rd378g-peek-N (BASH-ONLY, GPU: no, DISK: 1). The peek runs, over ssh, the sealed kit's
  `"C:\Program Files\Git\bin\bash.exe" C:/Users/benja/rd378g2/tree/handoff/kit/rd378gpc/remote/bo378g.sh state`.
  It prints the output:
  - the steps;
  - each log's last line and age;
  - the OUT sizes and ages;
  - every python.exe with its PID and command line;
  - GPU memory and power;
  - free disk.
  It changes nothing.
- The watcher holds GPU passes while any python.exe runs, so the passes' STALLED notes rarely appear. The peeks are
  the watch.

**When a step counts as hung:** either of these holds.
- The running step's python.exe is alive, and neither its log nor its OUT file has changed for at least 30 minutes, on
  two peeks at least 10 minutes apart.
- The chain is still running 5 hours after LAUNCH. The estimate for the whole chain is about 2 hours, or 3 with the
  one out-of-memory retry; this is a guess.

**The stop:** an owner-stop job, 000-rd378g-stop-<step> (BASH-ONLY, GPU: no).
- It names the one PID the last peek showed for the step: the venv launcher python.exe, whose command line runs that
  step's sealed script.
- Just before acting, it lists python.exe again (the kit's procs.ps1, read only). It stops nothing (NOT-STOPPED) unless
  that PID still exists and its command line still runs the same script with the same arguments.
- It then runs `taskkill /T /F /PID <that PID>`, which ends the launcher and its child and nothing else. It checks that
  the PID is gone and prints the process list again.
- chain.cmd then records a non-zero rc for that step.
  - If the step is dialogs, train, devcheck or write59, the chain ends (chain.done).
  - If it is score, whenoff, g5G or g5R, the chain goes on to the next step.
  - A later pass collects the results and writes RESULTS-benspc.md as PARTIAL. Nothing is started again.

**Limits:**
- Only this run's own python.exe on BensPC is ever stopped, one exact PID at a time. Never a Mac process, never another
  job's process, never a delete.
- If a stop is refused (a permission check, or the PID no longer matches), the thread tells the Thread manager and the
  Director. It does not look for another way.

## Unchanged
- PASSMARKS.md, addenda A-L, the rows (SEAL-B), the trainer and its settings, the LoCoMo 5-9 test, G1-G5 and their bars,
  the fallback, the wording, and R = 585 of 772.
- The disk floor: launch only with at least 6 GB free, and copy R only with at least 9 GB free.
