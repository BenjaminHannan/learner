job: tk (test TK / TKN: 4 runs of 3M, one at a time, about 26 h; design/tokens-experiment-2026-10-09.md)
queue: 8aTK
owner: Architecture ambiguities thread (spec and marks); scheduling by the big-run thread
gpu: yes
start_when: gate G1's queue 8aG1f has printed "queue 8aG1f-pc done" AND Ben has said go in the Mac session. Never while any G1 job runs.
paths: SRC = C:\Users\benja\custom-io\src-8ag-tk (a NEW folder: branch claude/project-thread-qtxfp4 at its pushed head; never edit src-8ag)
  WORK = C:\Users\benja\custom-io\work (shared with G1: the 3M pool p10-rung30-s400-a64 and its s401 twin are reused, not rebuilt)
setup:
  1. Copy the branch into SRC (git archive or gh_fetch.py, as for src-8ag). Get-FileHash SRC\custom_io\g8a\caps.py must be
     3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78. Else stop, NEEDS ATTENTION.
  2. CPU check in SRC: python -m custom_io.tests.test_tok_think must end "ALL OK".
  3. Cost check (report-only, minutes, GPU): python -m custom_io.g8a.tok_cost --cloze <a training jsonl of WORK\g8a\pools\p10-rung30-s400-a64> --out WORK\results\8aTK-cost.json
  4. Start the queue like G1's: local_runner run --work WORK --queue custom_io\queue_local\8aTK-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt, log WORK\q8aTK.log.
stall / spill / crlf: as G1's card g1f (results/8a-g/pc-job-cards/g1f.md on claude/project-thread-yha868), with Q = 8aTK and SRC above; on a spill double only B2's accum (4 -> 8 -> 16).
done_when: the log prints "queue 8aTK-pc done" and every WORK\results\8aTK-pc\<job>\RESULT.json says "status": "ok".
results: push WORK\results\8aTK-pc and 8aTK-cost.json to branch claude/8a-g-pc-results under results/8a-g/pc/8aTK-pc/ (no checkpoints).
never: change seeds, data, marks, steps, learning rate, the code or any setting not named here; never touch G1's folders.
