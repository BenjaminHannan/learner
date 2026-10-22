job: tp (test T-P: B2 seed 400 at 3M with self-found programs, self_prog 8; otherwise exactly G1's 3M B2, 3,544,913 trained; G1's pool and 24,000 updates)
queue: 8aTP
next_queue: 8aTPb
owner: Whole-model roadmap thread (G1-OTHER-CAUSES-RANKED-2026-10-12 section 3, cause 3; marks below, written before any run)
gpu: yes
started: @STARTED@
log: C:\Users\benja\custom-io\work\q8aTP.log
stall_minutes: 600
paths: SRC = C:\Users\benja\custom-io\src-tp (G1's src-8ag custom_io with models\ledger.py adding self_prog only; never edit it)   WORK = C:\Users\benja\custom-io\work   Q = <queue> above
starts_when: started by the post-G1 chain waiter v3e as an inserted job (WORK\insert\46-tp.txt) at its check point after the talker runs (G2f, AT-1, G2Q) and 40-g2c10s, before B3 group 1.
change: ONE: self_prog 8. On training rows with no parsed program, mode GEN and an integer gold answer: the NOOP op target gets weight 0 (not 0.1) and each update samples K = 8 programs per such row from the model's own op/operand heads (temperature 1), runs them on the calculator, and trains op/operand/mode (NUM -> that result slot) teacher-forced on the shortest sampled program whose result equals the gold answer; rows with no hit keep their GEN target. No new parameters. The model proposes, the calculator (an outside tool) checks; no hand rule.
marks (sealed, verbatim from section 3 of the ranked-causes file):
  T-P, self-found programs (cause 3). 3M s400, otherwise exactly G1's 3M B2. One change: on training rows with no parsed program
  and an integer gold answer, drop the NOOP op target (weight 0 instead of 0.1) and each update sample K = 8 programs per such row
  from the model's own op/operand heads (temperature 1), run them on the calculator, and train op/operand/mode (NUM -> that result slot)
  teacher-forced on the shortest sampled program whose result equals the gold answer; rows with no hit keep their GEN target.
  Deployable: the model proposes, the calculator (an outside tool) checks; no hand rule.
  - Pass: the four families (table_lookup, seq_next, fewshot_number_rule, rule_apply; 720 dev rows; G1 3M s400 = 219/720 = 30.4%,
    s401 30.3%) >= 38.4% (+8 points), AND pooled-5 >= 72.5, AND chain-5 >= 99.
  - Proved wrong: four-family score <= 32.4% (+2).
  - Between: run s401.
  - Size follow-up only on a pass: the same change at 10M s400, scaling mark = own gain >= +3.3 (WIDE's bar).
cost: about 8-10 h on the PC at 3M (G1 3M B2 took 6.5 h = 23,548 s, 0.98 s per update at accum 4). The sampler adds one no-grad run of K = 8 samples per candidate row (reader and EmbeddingGemma once per row) plus a second EmbeddingGemma/reader pass over the candidate rows. CPU measurement at G1 size (Gemma off, 64-row micro-batch): time per update x1.14-1.2 with ~0-10% candidate rows, x1.5 at 25%, x2.2 at 50%. Watch sp_cand in the log: x1.5 = ~10 h, x2.2 = ~14 h. Disk and memory as G1 (no new parameters); # MEM 9000 as G1.
readout: tp_read.py (read-only; python tp_read.py [WORK\results]) prints the four-family score (correct/n over the 5 splits; G1 = 219/720), pooled-5, chain-5, the per-family table of the four families against G1's 3M s400 B2 (8aG1d-pc), sp_hit / sp_cand / sp_len over training from B2\stdout.txt, and the verdict by the marks above. Nothing is decided here: report RESULT.json status and let the roadmap thread read it.
stall_check: Windows does not refresh LastWriteTime of a file that is still open, so never use it. The live log is the
  running job's B2\stdout.txt under WORK\results\Q-pc\. Stalled = its last "step" is the same as in the previous
  status while a custom_io.train process runs -> report only.
alive: a python process whose command line contains Q-pc.txt (the queue runner)
done_when: the log prints "queue Q-pc done"; then WORK\results\8aTP-pc\8aTP-3M-s400\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in B2\stdout.txt:
  0. Guard: if SRC\custom_io\queue_local\<next_queue>-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. New-Item WORK\STOP (the runner then starts nothing new).
  2. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has Q-pc.txt.
  3. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " Q-pc/".
  4. A leftover WORK\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  5. Write SRC\custom_io\queue_local\<next_queue>-pc.txt: Q-pc.txt with Q-... renamed to <next_queue>-... and --accum B2
     doubled (4->8->16->32). Already 32: stop, NEEDS ATTENTION.
  6. Get-FileHash SRC\custom_io\g8a\caps.py must be 3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78. Else stop.
  7. Move-Item WORK\STOP to WORK\STOP.used-<yyyyMMdd-HHmm>.
  8. Write C:\Users\benja\custom-io\q<next_queue>_run.cmd (ASCII), these 5 lines with N = <next_queue>:
     @echo off
     set PYTHONUTF8=1
     set PYTHONUNBUFFERED=1
     cd /d C:\Users\benja\custom-io\src-tp
     C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\N-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\qN.log 2>&1
     Start it detached: Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\qN_run.cmd'}
  9. Save a copy of this card as tpb.md (queue <next_queue>, next_queue 8aTPc, log WORK\q<next_queue>.log, started now);
     move this card to done\. Log it in actions.md. (The chain waiter waits while WORK\STOP exists or a runner runs, so it waits for the relaunch.)
on_refuse: a job that stops at start because a row is over its pinned caps prints the rows: report only, never edit caps
on_crash: report only (any Traceback, "rows touch the global caps", an arm rc not 0, or the runner gone before done; a "nonfinite_loss" status is also report only: no lr change)
max_restarts: 2
next: the chain waiter goes on to its next step when this queue ends; the roadmap thread reads RESULT.json against the marks
never: change seed, data, caps, marks, steps, learning rate, K, the custom_io code or any setting not named above;
  never touch G1's results, pools or checkpoints; never run two queues at once
