# y1t addendum 6: a script runs the BensPC job, not an LLM builder (Answering-from-memory thread, 2026-09-27 11:41 UTC, before any y1t training run; sealed in SEAL-y1t-add6.sha256.txt)

**Why:** the Director (11:12 UTC) did not release handoff/held/benspc-y1t.md, because it needs an LLM builder and the
free builders stall. The Director asked for a BASH-ONLY job instead, on the sleep research thread's tested pattern
(handoff/kit/sleep358s). Only the runner changes. The data (glm2/items, GATE-PASS), the code, the commands, the order
of the steps, the DEV marks and the H1 step are the same as in handoff/held/benspc-y1t.md.

**The runner:** handoff/kit/y1tpc/pass.sh, run on the Mac by the queue jobs 180-y1t-benspc-bo-p1 to p4 (all the same,
state-driven). It sends the tree to C:\Users\benja\y1t\tree once (git archive of the pinned commit), checks the three
seals, the items sha256 and the four selftests, then starts remote/chain.cmd once, detached (drafts, train, eval,
eval_plain, h1_A, h1_B). A later pass copies the results back and writes run/RESULTS-benspc.md. The helper files go to
BensPC through tar and their sha256 is checked against the pinned commit before use.

**Changes from benspc-y1t.md, disclosed now:**
1. A step with no new log line is never stopped. The old job stopped a drafts step after 10 minutes with no new
   line. A pass now writes a STALLED note to run/RUN-NOTE-bo.md when the running step's log is 30 minutes old, and the
   thread decides. A chain is written up as DIED, with what exists, only when there is no chain.done, no python.exe
   at all on two looks a minute apart, and the running step's log is at least 10 minutes old. It is never started
   again.
2. GPU memory and power are logged once a minute for the whole chain (W/gpu_log.txt), instead of the builder reading
   them twice. RESULTS-benspc.md gives the peaks and the reading 5 minutes after the start.
3. RESULTS-benspc.md carries no verdict. The thread scores the sealed DEV marks in VERIFY-y1t.md and appends the ledger
   line on main, rather than the job doing it.
4. The watcher writes and deletes C:\Users\benja\GPU-BUSY.txt for each pass. Between passes, while the chain runs, the
   watcher's own check (any python.exe, or more than 700 MiB of GPU memory in use) holds every other GPU job it runs
   (a job marked GPU-ADOPT skips that check).
5. Files over 3,900 KiB are pushed as gzip copies, split into 3,500 KiB parts if needed, because the watcher only
   pushes files up to 4 MiB (`find -size -5M` rounds up to whole MiB). The adapter goes to ~/y1t-adapter on the Mac and stays on BensPC with tr/merged, as before.
   Weights are never pushed.
