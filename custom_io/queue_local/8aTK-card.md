job: tk (test TK / TKN: up to 4 runs of 3M on BensPC, one at a time, kill-first; design/tokens-experiment-2026-10-09.md, Addenda A and B)
queue: 8aTK (files 8aTK-pc-1.txt, 8aTK-pc-2.txt, 8aTK-pc-3.txt; 8aTK-pc.txt is the old all-in-one queue, reference only; 8aTK-mac-*.txt are NOT in use)
owner: Architecture ambiguities thread (spec and marks); scheduling by the big-run thread
gpu: yes (BensPC RTX 5070 Ti)
start_when: the big-run thread names a free PC gap (first gap after G1; it must never delay the B3 ladder) AND Ben has said go in the Mac session. Never while any other GPU job runs (GPU-BUSY.txt).
paths: SRC = C:\Users\benja\custom-io\src-8ag-tk (a NEW folder: branch claude/project-thread-qtxfp4 at commit 1ed55c8d5d96 exactly; never "the pushed head", never edit src-8ag or src-8gx)
  WORK = C:\Users\benja\custom-io\work (shared with G1: the 3M pools p10-rung30-s400-a64 and p10-rung30-s401-a64, data8a, data and data_big are reused, not rebuilt)
setup:
  1. Copy the branch at 1ed55c8d5d96 into SRC (git archive or gh_fetch.py, as for src-8ag). Get-FileHash SRC\custom_io\g8a\caps.py must be
     3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78. Else stop, NEEDS ATTENTION.
  2. CPU check in SRC: python -m custom_io.tests.test_tok_think must end "ALL OK".
  3. Cost check (report-only, minutes, GPU): python -m custom_io.g8a.tok_cost --cloze <a training jsonl of WORK\g8a\pools\p10-rung30-s400-a64> --out WORK\results\8aTK-cost.json
  4. Step 1: local_runner run --work WORK --queue custom_io\queue_local\8aTK-pc-1.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt, log WORK\q8aTK-1.log.
     Report steps/s 15 minutes in (G1's G-B2 3M: 1.02 steps/s; 24,000 steps, about 6.5 h).
  5. After step 1 ends, push its results (below), then the stop check (read-only, any machine with the repo):
     python -m custom_io.g8a.analyze_tk --results <G1 controls: results/8a-g/pc/8aG1d-pc and 8aG1e-pc> <results/8a-g/pc/8aTK-pc-1> --stop-check TK
     STOP: TK reads "proved wrong (seed 400, kill-first)"; TKN does not run; tell the architecture thread. CONTINUE: step 2 = 8aTK-pc-2.txt
     the same way (TK s401, then TKN s400), when the big-run thread's PC order allows it. NO DECISION: a needed result is missing; fix that first.
  6. After step 2: ... --stop-check TKN. STOP: TKN s401 does not run ("window needed (seed 400, kill-first)"). CONTINUE: step 3 = 8aTK-pc-3.txt (TKN s401).
  7. After the last run: the full readout, analyze_tk without --stop-check, plus --cost WORK\results\8aTK-cost.json.
stall / spill / crlf: as G1's card g1f (results/8a-g/pc-job-cards/g1f.md on claude/project-thread-yha868), with Q = 8aTK-pc-N and SRC above; on a spill double only B2's accum (4 -> 8 -> 16).
done_when: each step's log prints "queue 8aTK-pc-N done" and every WORK\results\8aTK-pc-N\<job>\RESULT.json says "status": "ok".
results: push WORK\results\8aTK-pc-N (and 8aTK-cost.json) to branch claude/8a-g-pc-results under results/8a-g/pc/8aTK-pc-N/ (no checkpoints; keep them on the PC), with the --stop-check line saved next to them.
never: change seeds, data, marks, steps, learning rate, the code or any setting not named here; never touch G1's, GX's or B3's folders.
