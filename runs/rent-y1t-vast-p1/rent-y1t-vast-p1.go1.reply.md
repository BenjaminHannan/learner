Sun Sep 27 16:29:24 UTC 2026
job rent-y1t-vast-p1
y1t vast pass, job rent-y1t-vast-p1 (first), kit 4a0b63b3ad7f96cc8ee712db24442453c7b5b840, start 2026-09-27T16:29:25Z
NOTE: pass start (first); spent so far $0.00
NOTE: offer 46151926: RTX_4090, 81.4 TFLOPS, at $0.4145/h (196.4 TFLOPS per $/h, the best that fits; estimated chain 64 minutes), host 135676, machine 29558, CUDA 13.2, download $0.00390625/GB, upload $0.00390625/GB
NOTE: created instance 52989756 (RTX_4090, $0.4145/h); waiting up to 360 s for it to run
NOTE: instance 52989756 is 'loading', not running, after 360 s
destroy 52989756: Are you sure you want to destroy instance 52989756? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 52989756 (did not come up); vast no longer lists it
NOTE: offer 52159510: RTX_5090, 108.1 TFLOPS, at $0.5356/h (201.8 TFLOPS per $/h, the best that fits; estimated chain 50 minutes), host 406325, machine 142894, CUDA 13.0, download $0.005208333333333333/GB, upload $0.005208333333333333/GB
NOTE: create on offer 52159510 did not answer OK, but instance 52991051 appeared with this task's label; waiting up to 360 s for it to run
NOTE: instance 52991051 is 'loading', not running, after 360 s
destroy 52991051: Are you sure you want to destroy instance 52991051? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 52991051 (did not come up); vast no longer lists it
NOTE: offer 47784808: RTX_4080, 48.6 TFLOPS, at $0.2681/h (181.2 TFLOPS per $/h, the best that fits; estimated chain 108 minutes), host 91303, machine 30620, CUDA 13.2, download $0.0026041666666666665/GB, upload $0.0026041666666666665/GB
NOTE: created instance 52992266 (RTX_4080, $0.2681/h); waiting up to 360 s for it to run
NOTE: instance 52992266 is running and answers ssh
NOTE: guard started (pid 17914; /Users/ben-hannan/premonition-watch/y1t-vast/guard.log): at the $1.50 cap or the time cap (2026-09-27T20:54:30Z) it copies back, then destroys, else stops
tree: NO-TREE
TREE marked 4a0b63b3ad7f96cc8ee712db24442453c7b5b840
NOTE: tree ~/tree made from 4a0b63b3ad7f96cc8ee712db24442453c7b5b840 (NO-TREE): TREE marked 4a0b63b3ad7f96cc8ee712db24442453c7b5b840
kit on the rental matches 4a0b63b3ad7f96cc8ee712db24442453c7b5b840
NOTE: setup: SETUP started pid=624 2026-09-27T16:44:47Z
NOTE: setup done: age=0m setup end 2026-09-27T16:46:22Z
CHECK claude_y1t_data.py rc=0 selftest ok
CHECK claude_y1g_doubt.py rc=0 selftest ok
CHECK claude_y1t_h1run.py rc=0 selftest ok
CHECK claude_bm398r_train.py rc=0 BM398R-TRAIN-SELFTEST PASS 6/6
VERSIONS 2.11.0+cu128 12.8 5.17.0
GPUNAME NVIDIA GeForce RTX 4080, 595.84
NOTE: checks: 4 of 4 selftests ok; VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA GeForce RTX 4080, 595.84
LAUNCH chain 2026-09-27T16:46:33Z rc=0 pid=2160 cap=180m
NOTE: LAUNCH chain 2026-09-27T16:46:33Z rc=0 pid=2160 cap=180m;
NOTE: running: step drafts, log age 0 min, GPU 1 16376 8.36, $0.15 spent; LAST drafts age=0m 
NOTE: running: step drafts, log age 0 min, GPU 2603 16376 112.85, $0.16 spent; LAST drafts age=0m [y1t] drafts 700/1762
NOTE: chain done: drafts rc=0; train rc=1; 
NOTE: copied back 12 files listed by the rental; every one matches its sha256 there
destroy 52992266: Are you sure you want to destroy instance 52992266? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 52992266 (PARTIAL: 1 of 6 steps ended rc=0; step train ended rc=1); vast no longer lists it
NOTE: wrote RESULTS-vast.md: PARTIAL: 1 of 6 steps ended rc=0; step train ended rc=1
LEDGER-SUGGESTION (for the Director): 2026-09-27 16:55 UTC answering from memory: y1t on vast, 52989756 RTX_4090 at $0.4145/h; 52991051 RTX_5090 at $0.5611/h; 52992266 RTX_4080 at $0.2833/h, $0.19, PARTIAL: 1 of 6 steps ended rc=0; step train ended rc=1
PASS-END 2026-09-27T16:55:12Z
rc=0
