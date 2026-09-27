# y1v vast run notes (handoff/kit/y1vvast/pass.sh; UTC; one line per event)
- 2026-09-27T19:34:57Z rent-y1v-vast-p1: pass start (first); spent so far $0.00
- 2026-09-27T19:35:03Z rent-y1v-vast-p1: offer 44375061: RTX_3090, 35.3 TFLOPS, at $0.1394/h (253.1 TFLOPS per $/h, the best that fits; estimated chain 119 minutes), host 155125, machine 39565, CUDA 13.0, download $0.015625/GB, upload $0.016927083333333332/GB
- 2026-09-27T19:35:05Z rent-y1v-vast-p1: created instance 53020519 (RTX_3090, $0.1394/h); waiting up to 360 s for it to run
- 2026-09-27T19:41:21Z rent-y1v-vast-p1: instance 53020519 is 'loading', not running, after 360 s
- 2026-09-27T19:41:33Z rent-y1v-vast-p1: destroyed 53020519 (did not come up); vast no longer lists it
- 2026-09-27T19:41:36Z rent-y1v-vast-p1: offer 43165145: RTX_5090, 108.1 TFLOPS, at $0.5127/h (210.9 TFLOPS per $/h, the best that fits; estimated chain 40 minutes), host 410852, machine 142018, CUDA 13.0, download $0.015625/GB, upload $0.016927083333333332/GB
- 2026-09-27T19:41:37Z rent-y1v-vast-p1: created instance 53021391 (RTX_5090, $0.5127/h); waiting up to 360 s for it to run
- 2026-09-27T19:42:38Z rent-y1v-vast-p1: instance 53021391 is running and answers ssh
- 2026-09-27T19:42:38Z rent-y1v-vast-p1: guard started (pid 69091; /Users/ben-hannan/premonition-watch/y1v-vast/guard.log): at the $1.00 cap or the time cap (2026-09-27T21:36:37Z) it copies back, then destroys, else stops
- 2026-09-27T19:44:57Z rent-y1v-vast-p1: tree ~/tree made from 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf (NO-TREE): TREE marked 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf
- 2026-09-27T19:45:06Z rent-y1v-vast-p1: setup: SETUP started pid=1401 2026-09-27T19:45:06Z
- 2026-09-27T19:50:18Z rent-y1v-vast-p1: setup done: age=0m setup end 2026-09-27T19:50:12Z
- 2026-09-27T19:50:41Z rent-y1v-vast-p1: checks: 5 of 5 checks ok (4 selftests and the import check); VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA GeForce RTX 5090, 580.159.03
- 2026-09-27T19:50:49Z rent-y1v-vast-p1: LAUNCH chain 2026-09-27T19:50:49Z rc=0 pid=4052 cap=64m;
- 2026-09-27T19:50:54Z rent-y1v-vast-p1: running: step drafts, log age 0 min, GPU 12624 32607 519.65, $0.23 spent; LAST drafts age=0m Loading weights:   0%|          | 0/148 [00:00<?, ?it/s]Loading weights: 100%|██████████| 148/148 [00:00<00:00, 6025.54
- 2026-09-27T19:55:12Z rent-y1v-vast-p1: running: step drafts, log age 0 min, GPU 15785 32607 520.99, $0.27 spent; LAST drafts age=0m [y1t] drafts 700/1762
- 2026-09-27T20:05:00Z rent-y1v-vast-p1: running: step train, log age 0 min, GPU 15653 32607 519.98, $0.37 spent; LAST train age=0m {"step": 165, "loss": 0.1992, "s": 139, "projected_train_s": 175, "tokens": 286185}
- 2026-09-27T20:09:11Z rent-y1v-vast-p1: chain done: drafts rc=0; train rc=0; eval rc=0; eval_plain rc=0; 
- 2026-09-27T20:09:32Z rent-y1v-vast-p1: copied back 20 files listed by the rental; every one matches its sha256 there
- 2026-09-27T20:09:44Z rent-y1v-vast-p1: destroyed 53021391 (COMPLETE: all 4 steps ended rc=0); vast no longer lists it
- 2026-09-27T20:09:46Z rent-y1v-vast-p1: wrote RESULTS-vast.md: COMPLETE: all 4 steps ended rc=0
