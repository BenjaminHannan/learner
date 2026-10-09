job: gx (test GX stage 1: 2 runs of GX-3M, one at a time, about 20-24 h; design/8a-gx-experts-2026-10-09.md)
queue: 8aGX   (stage 2 = queue 8aGXD, HELD until stage 1 reads GO and Ben says go)
owner: thread "many experts with many layers" (spec and marks); scheduling by the big-run thread
gpu: yes
start_when: gate G1's queue 8aG1f has printed "queue 8aG1f-pc done" AND Ben has said go in the Mac session. Never while any G1 job runs.
paths: SRC = C:\Users\benja\custom-io\src-8gx (a NEW folder: branch claude/project-thread-x2cm2v at its pushed head; never edit src-8ag or src-8ag-tk)
  WORK = C:\Users\benja\custom-io\work (shared with G1: the 3M pool p10-rung30-s400-a64 and its s401 twin are reused, not rebuilt)
setup:
  1. Copy the branch into SRC (git archive or gh_fetch.py, as for src-8ag). Get-FileHash SRC\custom_io\g8a\caps.py must be
     3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78. Else stop, NEEDS ATTENTION.
  2. CPU check in SRC: python -m custom_io.tests.test_moe must end "ALL OK".
  3. Start the queue like G1's: local_runner run --work WORK --queue custom_io\queue_local\8aGX-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt, log WORK\q8aGX.log.
  4. Report-only memory look: 15 minutes after 8aGX-3M-s400's B2 starts training, report dedicated and shared GPU memory (nvidia-smi and Task Manager's
     "Shared GPU memory") and its last "step" line. The thread decides from it whether s401 may run alongside (a later, separate go).
stall / spill / crlf: as G1's card g1f (results/8a-g/pc-job-cards/g1f.md on claude/project-thread-yha868), with Q = 8aGX and SRC above; on a spill (shared GPU memory past 1 GB) stop the run and double only B2's accum (4 -> 8 -> 16), rerun from the start.
done_when: the log prints "queue 8aGX-pc done" and every WORK\results\8aGX-pc\<job>\RESULT.json says "status": "ok".
results: push WORK\results\8aGX-pc to branch claude/8a-g-pc-results under results/8a-g/pc/8aGX-pc/ (no checkpoints; keep them on the PC).
score: python -m custom_io.g8a.analyze_gx --results results/8a-g/pc --out results/8a-g/pc/8aGX-pc/analyze_gx.json (any machine, read-only)
never: change seeds, data, marks, steps, learning rate, the code or any setting not named here; never touch G1's or TK's folders; never start 8aGXD without the thread's release and Ben's go.
