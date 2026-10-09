job: tk (test TK / TKN: up to 4 runs of 3M on a Mac, one at a time, kill-first; design/tokens-experiment-2026-10-09.md, Addendum A)
queue: 8aTK (files 8aTK-mac-1.txt, 8aTK-mac-2.txt, 8aTK-mac-3.txt; 8aTK-pc.txt is only the superseded PC fallback)
owner: Architecture ambiguities thread (spec and marks); scheduling by the big-run thread
gpu: yes (mps)
machine: the M3 Pro Mac when it arrives, or the M1 Pro once the experts test's (GX) stage 1 has finished there. ONE Mac for all four runs (a pairing is fair only on one device).
start_when: Ben says go in that Mac's session. Never while another training job runs on that Mac. Re-ask Ben before each next step (2 and 3).
paths: SRC = a NEW folder, e.g. ~/custom-io/src-8ag-tk: branch claude/project-thread-qtxfp4 at commit <PIN> exactly (git archive <PIN> | tar -x -C SRC; never "the pushed head", never edit another src folder)
  WORK = ~/custom-io/work (new for this Mac unless the GX test already made one)
setup:
  1. Copy the branch at <PIN> into SRC. shasum -a 256 SRC/custom_io/g8a/caps.py must be 3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78 (compare ignoring case). Else stop, NEEDS ATTENTION.
  2. Env (cd SRC first; in every shell): export PYTHONPATH=SRC:<site-packages of a Python env with torch (mps) and transformers >= 5.19>
     export CUSTOM_IO_EG2=<local copy of EmbeddingGemma 2 at revision 914f7f89142e33e77833254d9c9b90c3cef7303b (custom_io/models/eg.py EG_REV)>. If the Mac has none: scp -r benspc:C:/Users/benja/eg2 ~/eg2 (ssh benspc), and check its config is that revision.
  3. Data, copied from the PC WORK (C:\Users\benja\custom-io\work), same bytes as G1's controls, so nothing is rebuilt (job.py get_pool reuses a pool whose MANIFEST.json and train.jsonl hash match):
     8a-inputs/data-pool and 8a-inputs/own-data (what the g8a-data line reads);
     g8a/pools/p10-rung30-s400-a64 and g8a/pools/p10-rung30-s401-a64 (the 3M pools: key p<own rung>-<web slice>-s<seed>-a<max ans>; each is large, seed 401 only before step 2);
     data8a (own72, web/slice_rung*.jsonl, READY.json: the g8a-data line only re-checks sha256 of each file and skips the ones that match; if data8a is absent it downloads the 2.15 GB FineWeb-Edu shard and rebuilds, so copy it);
     data and data_big (the skills builds `local_runner setup` makes; the queue passes them as --skills / --big-data).
     Not determined from the code alone: the exact byte size of the pools and whether the PC's WORK/data8a/READY.json is intact; check with `ls` on the PC before copying and tell Ben.
  4. Awake: run everything under caffeinate -dimsu (e.g. caffeinate -dimsu python -m ...) for the whole run, laptop on power.
  5. Device check: python -m custom_io.tests.test_tok_think must end "ALL OK" (scatter_reduce 'amax' and index_add on mps/cpu fallback; the runner sets PYTORCH_ENABLE_MPS_FALLBACK=1). Then the short mps smoke: python -m custom_io.g8a.tok_cost --stub --small --letters 300 --device mps (must finish and print the 3-arm table). Any failure: stop, NEEDS ATTENTION.
  6. Step 1: caffeinate -dimsu python -m custom_io.local_runner run --work WORK --queue custom_io/queue_local/8aTK-mac-1.txt --device mps --par 1   (log to WORK/q8aTK-1.log). Report steps/s 15 minutes in (G1 on the PC: 1.02 steps/s; the 3M run is 24,000 steps).
  7. After the run ends, run the stop check (read-only). G1 controls = results/8a-g/pc/8aG1d-pc and (when it appears) results/8a-g/pc/8aG1e-pc on origin/claude/8a-g-pc-results; TK results = WORK/results/8aTK-mac-1:
     python -m custom_io.g8a.analyze_tk --results <G1 control dirs> WORK/results/8aTK-mac-1 --stop-check TK
     STOP: TK reads "proved wrong (seed 400, kill-first)"; TKN does not run; push results and tell Ben. CONTINUE: ask Ben, then run 8aTK-mac-2.txt the same way (TK s401, then TKN s400).
     After step 2: ... --stop-check TKN (needs TK s400 and TKN s400). STOP: TKN s401 does not run ("window needed (seed 400, kill-first)"). CONTINUE: ask Ben, then 8aTK-mac-3.txt (TKN s401).
     After the last run: full readout without --stop-check (add --cost for a cost JSON if one was made).
stall / spill / crlf: not applicable on a Mac (no shared-memory spill). If a run stalls (no new train event for 30 minutes) or the Mac sleeps, stop and tell Ben; the runner resumes only from a missing RESULT.json, so a restart begins that run again. Do not change accum or any other setting.
precision: the runner drops bf16 on mps, so TK/TKN run fp32 against G1's bf16 controls from the PC. Disclosed in the readout; marks unchanged.
done_when: the log prints "queue 8aTK-mac-N done" for the step and every WORK/results/8aTK-mac-N/<job>/RESULT.json says "status": "ok".
results: push WORK/results/8aTK-mac-1 (and -2, -3) to branch claude/8a-g-pc-results under results/8a-g/mac/8aTK-mac/ (RESULT.json, stdout.txt, stdout.events.txt, rc.txt, box.json; no checkpoint.pt), with the --stop-check line saved as a file next to them.
never: change seeds, data, marks, steps, learning rate, the code or any setting not named here; never touch G1's folders; never start while another training job runs on that Mac.
