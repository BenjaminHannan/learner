job: g1e (Gate G1, queue 8aG1e-pc: 8aG1e-3M-s401, then 8aG1e-10M-s400, then 8aG1e-10M-s401)
owner: Whole-model roadmap thread (Gate G1, spec design/8a-g-gemma-growth-2026-10-08.md addenda D-F)
gpu: yes
started: <ET time the Mac waiter launched G1e>
log: C:\Users\benja\custom-io\work\q8aG1e.log
stall_minutes: 900
stall_check: the runner log above is quiet while a job trains. The live log is the newest stdout.txt under
  C:\Users\benja\custom-io\work\results\8aG1e-pc\ (a line about every 500 steps). Older than 45 min while a
  custom_io.train process runs: stalled -> report only.
alive: a python process whose command line contains 8aG1e-pc.txt (the queue runner)
done_when: the log prints "queue 8aG1e-pc done"; then every results\8aG1e-pc\<job>\RESULT.json says "status": "ok" (else report)
on_spill: a custom_io.train process with shared GPU memory over 1024 MiB, or "CUDA out of memory" in an arm's stdout.txt:
  0. Guard: if custom_io\queue_local\8aG1f-pc.txt (or a later letter) exists, someone already relaunched: report only.
  1. Note the failing job (8aG1e-3M-s401, 8aG1e-10M-s400 or 8aG1e-10M-s401) and arm (its B2 or PT folder).
  2. New-Item C:\Users\benja\custom-io\work\STOP (the runner then starts nothing new).
  3. Stop by exact PID, after checking each command line: the custom_io.train process, its custom_io.g8a.job
     parent, and the custom_io.local_runner process whose command line has 8aG1e-pc.txt.
  4. Edit C:\Users\benja\GPU-BUSY.txt: remove only the lines that contain " 8aG1e-pc/".
  5. A leftover C:\Users\benja\custom-io\work\g8a\pools\*.lock: rename it to <name>.stale-<yyyyMMdd-HHmm>.
  6. Write custom_io\queue_local\8aG1f-pc.txt (next free letter): all lines of 8aG1e-pc.txt, minus the g8a: lines
     of jobs whose results\8aG1e-pc\<job>\RESULT.json says "status": "ok"; rename the remaining jobs 8aG1e-... to
     8aG1f-...; in the failing job's --accum double only the failing arm (4->8->16, 8->16). Already 16: stop, NEEDS ATTENTION.
  7. Get-FileHash C:\Users\benja\custom-io\custom_io\g8a\caps.py must be
     3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78 (the 36-slot fix). Else stop, NEEDS ATTENTION.
  8. Move-Item C:\Users\benja\custom-io\work\STOP to C:\Users\benja\custom-io\work\STOP.used-<yyyyMMdd-HHmm>.
  9. Relaunch with: <RELAUNCH: the exact command that started G1e, with 8aG1e replaced by 8aG1f>
  10. Save this card as g1f.md with every 8aG1e changed to 8aG1f; move g1e.md to done\.
on_crlf: a hash, "expected" or MANIFEST error naming a data file, before any training: sha256 the file with \r\n read
  as \n. If that equals the file's value below, write the LF bytes to <file>.lf, rename <file> to <file>.crlf and
  <file>.lf to <file>, then do on_spill steps 0-4 and 6-10 with no accum change. Any other file or value: report only.
  slice_rung3.jsonl 59c70dc5e2c3abebd2b650641cefc6762fb623a0ae82525eda3044f2ad09aef7
  slice_rung10.jsonl 5a5f23e70f8f244df7640f6fbebf787f07ecafd13afe1312a3b1ba72b1a44e2a
  slice_rung30.jsonl fe28aa2e3d0f32aa8b5b5057d83d1d1e769efa70fc4ba70fb6d5739fc5bc997f
  own72_MANIFEST.json e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0
on_crash: report only (any other Traceback, an arm rc not 0, or the runner gone before done)
max_restarts: 2 per job
next: nothing; the roadmap thread scores G1 when it ends
never: change seeds, data, marks, steps, learning rate, the custom_io code or any setting not named above;
  never touch finished result folders or checkpoints; never start G1 jobs in parallel with each other
