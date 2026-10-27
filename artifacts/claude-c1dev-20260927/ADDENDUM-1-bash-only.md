# c1-dev addendum 1: runs without an LLM builder (Everyday chat thread, 2026-09-27 12:27 UTC, before any run)

**Why:** the Thread manager (12:19 UTC) pointed out that k2-c1dev-benspc was an LLM-builder BensPC GPU job. The Director
stopped releasing that kind at 11:12 UTC, because free builders stall while holding the GPU (y1t, rd378g). I asked the
Director at 12:24. So nothing waits on the answer, this addendum converts the job, and k2 moves to handoff/held/ (superseded).

**What is the same:** the plan, the marks and the code. PLAN.md is unchanged, SEAL-2 covers the same 24 files, and
the four arms (D, T, Q, L) run the same commands through the winnl2 and twin-b wrappers into outC1/chat_<arm>.jsonl. An arm
that exits non-zero is run once more (the runner skips conversations already written). Scoring stays in this thread.

**What changes:**
- Kit: handoff/kit/c1devpc (62a5944c8), modelled on the tested y1tpc kit. The tree on BensPC is `git archive` of that
  pinned commit, so the run measures claude_e2e02d.py as it is there (SEAL-2, 24 of 24), whatever changes on main later.
  The pass checks SEAL-2, the three model folders, and four selftests through the winnl2 wrapper. It then starts
  remote/chain.cmd once, detached, only on an idle BensPC: no python.exe, at most 700 MiB of GPU memory in use,
  GPU-BUSY.txt naming the pass, and at least 4 GB free on C: (the run writes about 2 MB; Ben's floor is 3 GB).
  A later pass reports progress, or collects the chats and logs and writes RESULTS-benspc.md (counts only).
- V1: the old job checked each log's first lines while the arm ran. The kit checks the same lines when it collects:
  the winnl2 line, the twin-b line, and logD's exact c1dev settings line (W_PLACE02D=system). A V1 FAIL makes the run
  unusable for PLAN.md's readings. The talker also refuses any other W placement by itself (claude_c1dev_talker.py).
- Cap and watch: the old 2 h 30 min cap and its stop by PID are gone, because the kit never stops a process. This thread
  watches instead. From LAUNCH until RESULTS-benspc.md exists, a self-wake checks the watcher status every hour, and I
  queue a read-only peek (the kit's `boc1dev.sh state`) when progress is unclear. An arm counts as hung when its
  python.exe is alive and its log has not changed for 30 minutes on two peeks at least 10 minutes apart, or when the
  chain is still running 5 hours after LAUNCH (estimate for the whole chain: 1 to 2 hours, a guess). Then I queue an
  owner-stop job (BASH-ONLY, GPU: no) on y1t ADDENDUM-8's pattern. It re-lists python.exe, acts only if that one PID
  still runs the same command, and runs `taskkill /T /F /PID <PID>`. Stopping this run is my call as its owner. It never
  touches another job's process.
- Mock test (a local stand-in for BensPC's ssh, WMI launch, process list and GPU, with a stand-in chain that writes the
  same files): the full path ran from no tree, through a 4/4 checks launch, to COMPLETE with V1 OK on all four logs, then
  DONE. BUSY (the marker named another job), RUNNING with a STALLED note (a 40-minute-old log), and DIED (no python.exe,
  no chain.done) each did what the script says. chain.cmd itself cannot run here (cmd.exe). It follows y1t's tested
  chain.cmd, with CRLF line endings and `call :arm` in place of repeated blocks.
- Jobs: handoff/held/190-c1dev-benspc-bo-p1..p3.md, three identical state-driven passes (BASH-ONLY: yes, GPU: yes).
  The Director places them.
