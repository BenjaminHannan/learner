Sun Sep 27 19:34:56 UTC 2026
job rent-y1v-vast-p1
y1v vast pass, job rent-y1v-vast-p1 (first), kit 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf, start 2026-09-27T19:34:57Z
NOTE: pass start (first); spent so far $0.00
NOTE: offer 44375061: RTX_3090, 35.3 TFLOPS, at $0.1394/h (253.1 TFLOPS per $/h, the best that fits; estimated chain 119 minutes), host 155125, machine 39565, CUDA 13.0, download $0.015625/GB, upload $0.016927083333333332/GB
NOTE: created instance 53020519 (RTX_3090, $0.1394/h); waiting up to 360 s for it to run
NOTE: instance 53020519 is 'loading', not running, after 360 s
destroy 53020519: Are you sure you want to destroy instance 53020519? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 53020519 (did not come up); vast no longer lists it
NOTE: offer 43165145: RTX_5090, 108.1 TFLOPS, at $0.5127/h (210.9 TFLOPS per $/h, the best that fits; estimated chain 40 minutes), host 410852, machine 142018, CUDA 13.0, download $0.015625/GB, upload $0.016927083333333332/GB
NOTE: created instance 53021391 (RTX_5090, $0.5127/h); waiting up to 360 s for it to run
NOTE: instance 53021391 is running and answers ssh
NOTE: guard started (pid 69091; /Users/ben-hannan/premonition-watch/y1v-vast/guard.log): at the $1.00 cap or the time cap (2026-09-27T21:36:37Z) it copies back, then destroys, else stops
tree: NO-TREE
TREE marked 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf
NOTE: tree ~/tree made from 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf (NO-TREE): TREE marked 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf
kit on the rental matches 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf
NOTE: setup: SETUP started pid=1401 2026-09-27T19:45:06Z
NOTE: setup done: age=0m setup end 2026-09-27T19:50:12Z
CHECK claude_y1t_data.py rc=0 selftest ok
CHECK claude_y1g_doubt.py rc=0 selftest ok
CHECK claude_y1v_train.py rc=0 selftest ok (8 LoRA modules on self_attn q/k/v/out_proj, none on conv, merge matches)
CHECK claude_bm398r_train.py rc=0 BM398R-TRAIN-SELFTEST PASS 6/6
CHECK imports rc=0 IMPORTS OK the 4 step scripts, 247 local files read, 49 other modules imported (nltk 3.10.3)
VERSIONS 2.11.0+cu128 12.8 5.17.0
GPUNAME NVIDIA GeForce RTX 5090, 580.159.03
NOTE: checks: 5 of 5 checks ok (4 selftests and the import check); VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA GeForce RTX 5090, 580.159.03
LAUNCH chain 2026-09-27T19:50:49Z rc=0 pid=4052 cap=64m
NOTE: LAUNCH chain 2026-09-27T19:50:49Z rc=0 pid=4052 cap=64m;
NOTE: running: step drafts, log age 0 min, GPU 12624 32607 519.65, $0.23 spent; LAST drafts age=0m Loading weights:   0%|          | 0/148 [00:00<?, ?it/s]Loading weights: 100%|██████████| 148/148 [00:00<00:00, 6025.54
NOTE: running: step drafts, log age 0 min, GPU 15785 32607 520.99, $0.27 spent; LAST drafts age=0m [y1t] drafts 700/1762
NOTE: running: step train, log age 0 min, GPU 15653 32607 519.98, $0.37 spent; LAST train age=0m {"step": 165, "loss": 0.1992, "s": 139, "projected_train_s": 175, "tokens": 286185}
NOTE: chain done: drafts rc=0; train rc=0; eval rc=0; eval_plain rc=0; 
NOTE: copied back 20 files listed by the rental; every one matches its sha256 there
destroy 53021391: Are you sure you want to destroy instance 53021391? This is irreversible and will delete all data. [y/N] destroying inst
NOTE: destroyed 53021391 (COMPLETE: all 4 steps ended rc=0); vast no longer lists it
NOTE: wrote RESULTS-vast.md: COMPLETE: all 4 steps ended rc=0
LEDGER-SUGGESTION (for the Director): 2026-09-27 20:09 UTC answering from memory: y1v on vast, 53020519 RTX_3090 at $0.1394/h; 53021391 RTX_5090 at $0.5789/h, $0.41, COMPLETE: all 4 steps ended rc=0
PASS-END 2026-09-27T20:09:46Z
rc=0
