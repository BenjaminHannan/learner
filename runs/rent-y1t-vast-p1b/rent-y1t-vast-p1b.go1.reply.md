Sun Sep 27 17:37:49 UTC 2026
job rent-y1t-vast-p1b
y1t vast pass, job rent-y1t-vast-p1b (first), kit 44c385094ae20e772a92ab6a973dd609311d17b5, start 2026-09-27T17:37:56Z
NOTE: pass start (first); spent so far $0.00
NOTE: offer 50160636: RTX_5000Ada, 63.6 TFLOPS, at $0.3347/h (190.0 TFLOPS per $/h, the best that fits; estimated chain 82 minutes), host 438484, machine 107776, CUDA 13.2, download $0.0026041666666666665/GB, upload $0.00390625/GB
NOTE: created instance 53001974 (RTX_5000Ada, $0.3347/h); waiting up to 360 s for it to run
NOTE: instance 53001974 is running and answers ssh
NOTE: guard started (pid 80845; /Users/ben-hannan/premonition-watch/y1t-vast/guard.log): at the $1.30 cap or the time cap (2026-09-27T20:57:20Z) it copies back, then destroys, else stops
tree: NO-TREE
TREE marked 44c385094ae20e772a92ab6a973dd609311d17b5
NOTE: tree ~/tree made from 44c385094ae20e772a92ab6a973dd609311d17b5 (NO-TREE): TREE marked 44c385094ae20e772a92ab6a973dd609311d17b5
kit on the rental matches 44c385094ae20e772a92ab6a973dd609311d17b5
NOTE: setup: SETUP started pid=587 2026-09-27T17:43:40Z
NOTE: setup done: age=0m setup end 2026-09-27T17:45:16Z
CHECK claude_y1t_data.py rc=0 selftest ok
CHECK claude_y1g_doubt.py rc=0 selftest ok
CHECK claude_y1t_h1run.py rc=0 selftest ok
CHECK claude_bm398r_train.py rc=0 BM398R-TRAIN-SELFTEST PASS 6/6
CHECK imports rc=0 IMPORTS OK the 4 step scripts, 247 local files read, 49 other modules imported (nltk 3.10.3)
VERSIONS 2.11.0+cu128 12.8 5.17.0
GPUNAME NVIDIA RTX 5000 Ada Generation, 595.58.03
NOTE: checks: 5 of 5 checks ok (4 selftests and the import check); VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA RTX 5000 Ada Generation, 595.58.03
LAUNCH chain 2026-09-27T17:46:02Z rc=0 pid=2340 cap=180m
NOTE: LAUNCH chain 2026-09-27T17:46:02Z rc=0 pid=2340 cap=180m;
NOTE: running: step drafts, log age 0 min, GPU 2690 32760 131.69, $0.08 spent; LAST drafts age=0m [y1t] drafts 400/1762
NOTE: running: step train, log age 0 min, GPU 2776 32760 99.99, $0.14 spent; LAST train age=0m {"step": 120, "loss": 0.1233, "s": 139, "projected_train_s": 415, "tokens": 211729}
NOTE: chain done: drafts rc=0; train rc=0; eval rc=0; eval_plain rc=0; h1_A rc=0; h1_B rc=0; 
NOTE: copied back 24 files listed by the rental; every one matches its sha256 there
destroy 53001974: Are you sure you want to destroy instance 53001974? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 53001974 (COMPLETE: all 6 steps ended rc=0); vast no longer lists it
NOTE: wrote RESULTS-vast.md: COMPLETE: all 6 steps ended rc=0
LEDGER-SUGGESTION (for the Director): 2026-09-27 18:09 UTC answering from memory: y1t on vast, 53001974 RTX_5000Ada at $0.35/h, $0.20, COMPLETE: all 6 steps ended rc=0
PASS-END 2026-09-27T18:09:30Z
rc=0
