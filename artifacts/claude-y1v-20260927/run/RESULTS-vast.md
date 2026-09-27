# y1v vast run record (handoff/kit/y1vvast/pass.sh, job rent-y1v-vast-p1, kit 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf, written 2026-09-27T20:09:45Z)

**COMPLETE: all 4 steps ended rc=0.** No verdict here: the thread scores the sealed DEV marks in VERIFY-y1v.md. Every line below is
copied by the script, never retyped.

## Steps (W/steps.txt; UTC)

    drafts start 2026-09-27T19:50:49Z
    drafts rc=0 end 2026-09-27T20:01:49Z
    train start 2026-09-27T20:01:49Z
    train rc=0 end 2026-09-27T20:06:49Z
    eval start 2026-09-27T20:06:49Z
    eval rc=0 end 2026-09-27T20:07:49Z
    eval_plain start 2026-09-27T20:07:49Z
    eval_plain rc=0 end 2026-09-27T20:08:49Z

Minutes per step: drafts 11.0; train 5.0; eval 1.0; eval_plain 1.0; 

## Last lines
- drafts_log.txt:

    {"items": 1762, "train_rows": 1654, "repeat": 1, "answer_rows": 827, "idk_rows": 827, "dev_rows": 291, "counts": {"answerable_greedy_right": 774, "answerable_n": 888, "corrected_greedy_right": 38, "corrected_n": 53, "idk_all_wrong": 61, "idk_never_told": 874, "never_told_greedy_right": 21, "never_told_n": 874, "own_greedy": 774, "own_sample": 53}, "minutes": 10.6}

- train_log.txt:

    {"steps": 207, "loss_first10": 0.4649, "loss_last10": 0.1985, "lora_params": 1277952, "merged_layers": 24, "train_seconds": 174.4, "train_tokens": 360791, "peak_gpu_mb": 2365, "seconds": 267.7}

- eval_log.txt (last two):

    {"pick": {"candidates": [{"config": "C3", "right": 35, "wrong": 8, "never_told_idk": 7, "eligible": false}, {"config": "C4", "right": 31, "wrong": 7, "never_told_idk": 7, "eligible": false}, {"config": "V", "right": 31, "wrong": 10, "never_told_idk": 6, "eligible": false}, {"config": "A1", "right": 39, "wrong": 12, "never_told_idk": 6, "eligible": false}], "winner": null, "go": false}}
    {"answerable_right": {"A0": 39, "A1": 39, "C3": 35, "C4": 31, "V": 31}, "answerable_wrong": {"A0": 13, "A1": 12, "C3": 8, "C4": 7, "V": 10}, "never_told_idk": {"A0": 6, "A1": 6, "C3": 7, "C4": 7, "V": 6}, "signal": {"C3": {"right_share": 0.897, "signal": false, "wrong_share": 0.688}, "C4": {"right_share": 0.795, "signal": false, "wrong_share": 0.625}, "V": {"right_share": 0.795, "signal": false, "wrong_share": 0.875}, "any": false}}

- eval_plain_log.txt (last two):

    {"pick": {"candidates": [{"config": "C3", "right": 31, "wrong": 11, "never_told_idk": 7, "eligible": false}, {"config": "C4", "right": 29, "wrong": 9, "never_told_idk": 7, "eligible": false}, {"config": "V", "right": 23, "wrong": 10, "never_told_idk": 8, "eligible": false}, {"config": "A1", "right": 35, "wrong": 18, "never_told_idk": 1, "eligible": false}], "winner": null, "go": false}}
    {"answerable_right": {"A0": 36, "A1": 35, "C3": 31, "C4": 29, "V": 23}, "answerable_wrong": {"A0": 20, "A1": 18, "C3": 11, "C4": 9, "V": 10}, "never_told_idk": {"A0": 0, "A1": 1, "C3": 7, "C4": 7, "V": 8}, "signal": {"C3": {"right_share": 0.886, "signal": false, "wrong_share": 0.519}, "C4": {"right_share": 0.829, "signal": false, "wrong_share": 0.444}, "V": {"right_share": 0.657, "signal": false, "wrong_share": 0.444}, "any": false}}

- setup_log.txt (last three):

    Fetching 11 files:   9%|▉         | 1/11 [00:00<00:06,  1.55it/s]Fetching 11 files:  18%|█▊        | 2/11 [00:01<00:04,  2.02it/s]Fetching 11 files:  64%|██████▎   | 7/11 [00:01<00:00,  8.38it/s]Fetching 11 files:  82%|████████▏ | 9/11 [00:01<00:00,  6.16it/s]Fetching 11 files:  91%|█████████ | 10/11 [00:19<00:00,  6.16it/s]Fetching 11 files: 100%|██████████| 11/11 [00:34<00:00,  5.23s/it]Fetching 11 files: 100%|██████████| 11/11 [00:34<00:00,  3.15s/it]
    BASE /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
    setup end 2026-09-27T19:50:12Z

## Machine, money and files
- VERSIONS 2.11.0+cu128 12.8 5.17.0 (torch, CUDA, transformers)
- GPUNAME NVIDIA GeForce RTX 5090, 580.159.03
- LFM2.5-1.2B-Instruct snapshot /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b (expected .../0f604ada3f766f9f257460c4c9f0b5d6f69d431b)
- items: 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4 c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4 (train, dev; GATE-RESULT.md has 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4, c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4)
- adapter sha256 on the rental: cc34cce909893a4c05cce58390f872a89afb3becc3bf582a225c70c379c87065; Mac copy ~/y1v-adapter/adapter398r.pt: cc34cce909893a4c05cce58390f872a89afb3becc3bf582a225c70c379c87065 (never pushed)
- GPU log (one line a minute: UTC, MiB used, MiB total, W): lines=18 peak_used=15785 peak_power=522.8 last=2026-09-27T20:07:50Z 12620 32607 520.20
- selftests: 5 of 5 ok (4 selftests and the import check; checks.txt)
- credit before the first create: 27.536335756039563

| instance | GPU | $/h | created (UTC) | gone or stopped (UTC) | hours | download $ | dollars |
|---|---|---|---|---|---|---|---|
| 53020519 | RTX_3090 | 0.1394 | 2026-09-27T19:35:05Z | 2026-09-27T19:41:33Z (GONE) | 0.11 | 0.00 | 0.02 |
| 53021391 | RTX_5090 | 0.5789 | 2026-09-27T19:41:37Z | 2026-09-27T20:09:44Z (GONE) | 0.47 | 0.12 | 0.40 |

Total: $0.41 of the $1.00 cap: $/h x hours from each create until vast stopped listing it (GONE) or it was
stopped (STOPPED; its small storage charge is not counted), plus 8 GB x the offer's download $/GB for each
instance that answered ssh (a guess at the download size; an adopted instance is priced at $0.02/GB).

| file | bytes | sha256 |
|---|---|---|
| artifacts/claude-y1v-20260927/run/chain_log.txt | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| artifacts/claude-y1v-20260927/run/checks.txt | 457 | be49ade29c30a087878d1a8eb00c95b4a8c846b98d85717c9a945972159d6763 |
| artifacts/claude-y1v-20260927/run/dev.jsonl | 297105 | 63d4df458b43f62f618aad1674af1c7e8b2a2b5388761f97e09e33d2995d08db |
| artifacts/claude-y1v-20260927/run/drafts.jsonl | 584683 | 6876b629b152c2a1b2519160410d6252a0203d47aeaefd2fee9b986b5d971f53 |
| artifacts/claude-y1v-20260927/run/drafts_log.txt | 1395 | deaeb9db135f51351f5ffa31c25f7e1db218c88f50e7ba69a94b0d7a87ebdd74 |
| artifacts/claude-y1v-20260927/run/drafts_summary.json | 381 | 03cdcd68aa064646d419d3bd39b97c9a560543b66ed043c842ea9d9072270eae |
| artifacts/claude-y1v-20260927/run/eval/y1g_rows.jsonl | 35756 | a72f920ca827f426f36e4ea57758060d1270eacd422f7ea7e18d22c222cad5fe |
| artifacts/claude-y1v-20260927/run/eval/y1g_summary.json | 3739 | 2fa38b69d340983d4f5027d4a2c3ee2167c1885851f614d34307a1801a36acb7 |
| artifacts/claude-y1v-20260927/run/eval_log.txt | 3518 | 28a8a5797ae6c563fd6edf1ddde83fe1603c5d80f8419db0803242a32c31dd2a |
| artifacts/claude-y1v-20260927/run/eval_plain/y1g_rows.jsonl | 40406 | ae1e3a724a811aeff93cb221705bad0210787293690236ea327f081b3604faa5 |
| artifacts/claude-y1v-20260927/run/eval_plain/y1g_summary.json | 3718 | f1b5778b3f7e5ed2625b8ec8590f5264fcc75f83343e4b96e7149bc2f59dc7ac |
| artifacts/claude-y1v-20260927/run/eval_plain_log.txt | 3520 | c237ce8b6c24b5ae0d7921cd4299c0a476636bd065c2d66241c44cfef5a8e77f |
| artifacts/claude-y1v-20260927/run/gpu_log.txt | 720 | e7aaded887a165beee3d8074a1578cabc5139c20da3f4bbe71034265b8dda4ab |
| artifacts/claude-y1v-20260927/run/manifest-rental.txt | 1986 | 92563669e98b00fbd600110fa284b22e2c8e6fabf1b2a8038846c8ae5f9785cf |
| artifacts/claude-y1v-20260927/run/pids.txt | 867 | 99788159ea3db3d40d03e5a90cf309a4405735971c4b06e7ac0f722b17ec54b3 |
| artifacts/claude-y1v-20260927/run/setup_log.txt | 2564 | 99eef047aee131abe9d94dc45f2cbfff4f1914553ccfac1fbbc25b90dd837bc9 |
| artifacts/claude-y1v-20260927/run/state-last.txt | 1893 | 90209c24421963fe7bcf06b19a7033f1def0c3afdbe2f567e42517815f045999 |
| artifacts/claude-y1v-20260927/run/steps.txt | 286 | 918671cd005bee47fc0c8b01fce8ea840e7a3dcadf02be7495dc7e4909860daa |
| artifacts/claude-y1v-20260927/run/train.jsonl | 1588581 | 1fbdc6d746f4c36f8a2b5deaba68c55ca9f9cc58cbbe693bedd1c0207258a7b7 |
| artifacts/claude-y1v-20260927/run/train398r.json | 1155 | 36ed8cd1e0c26a810c413e69389afc381094e2556b2614eb9b9c03b63e408574 |
| artifacts/claude-y1v-20260927/run/train_log.txt | 4903 | 888151945bcf39ea54ee7ef0116ad7bb694d9121e5503304774bac614092e5cc |

## Notes (RUN-NOTE-vast.md)

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
