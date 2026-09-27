# y1t vast run record (handoff/kit/y1tvast/pass.sh, job rent-y1t-vast-p1b, kit 44c385094ae20e772a92ab6a973dd609311d17b5, written 2026-09-27T18:09:29Z)

**COMPLETE: all 6 steps ended rc=0.** No verdict here: the thread scores the sealed DEV marks in VERIFY-y1t.md. Every line below is
copied by the script, never retyped. The H1 rows are in artifacts/claude-y1tH1-20260926/run (never opened by this job).

## Steps (W/steps.txt; UTC)

    drafts start 2026-09-27T17:46:03Z
    drafts rc=0 end 2026-09-27T17:55:33Z
    train start 2026-09-27T17:55:33Z
    train rc=0 end 2026-09-27T18:04:03Z
    eval start 2026-09-27T18:04:03Z
    eval rc=0 end 2026-09-27T18:05:03Z
    eval_plain start 2026-09-27T18:05:03Z
    eval_plain rc=0 end 2026-09-27T18:06:03Z
    h1_A start 2026-09-27T18:06:03Z
    h1_A rc=0 end 2026-09-27T18:07:03Z
    h1_B start 2026-09-27T18:07:03Z
    h1_B rc=0 end 2026-09-27T18:08:03Z

Minutes per step: drafts 9.5; train 8.5; eval 1.0; eval_plain 1.0; h1_A 1.0; h1_B 1.0; 

## Last lines
- drafts_log.txt:

    {"items": 1762, "train_rows": 2852, "repeat": 2, "answer_rows": 713, "idk_rows": 713, "dev_rows": 291, "counts": {"answerable_greedy_right": 490, "answerable_n": 888, "corrected_greedy_right": 30, "corrected_n": 53, "idk_all_wrong": 175, "idk_never_told": 874, "never_told_greedy_right": 719, "never_told_n": 874, "own_greedy": 490, "own_sample": 223}, "minutes": 9.2}

- train_log.txt:

    {"steps": 357, "loss_first10": 0.4713, "loss_last10": 0.1972, "lora_params": 4128768, "merged_layers": 96, "train_seconds": 411.9, "train_tokens": 631552, "peak_gpu_mb": 2282, "seconds": 492.1}

- eval_log.txt (last two):

    {"pick": {"candidates": [{"config": "C3", "right": 19, "wrong": 10, "never_told_idk": 5, "eligible": false}, {"config": "C4", "right": 15, "wrong": 8, "never_told_idk": 5, "eligible": false}, {"config": "V", "right": 18, "wrong": 12, "never_told_idk": 6, "eligible": false}, {"config": "A1", "right": 22, "wrong": 20, "never_told_idk": 5, "eligible": false}], "winner": null, "go": false}}
    {"answerable_right": {"A0": 22, "A1": 22, "C3": 19, "C4": 15, "V": 18}, "answerable_wrong": {"A0": 21, "A1": 20, "C3": 10, "C4": 8, "V": 12}, "never_told_idk": {"A0": 4, "A1": 5, "C3": 5, "C4": 5, "V": 6}, "signal": {"C3": {"right_share": 0.864, "signal": false, "wrong_share": 0.6}, "C4": {"right_share": 0.682, "signal": false, "wrong_share": 0.52}, "V": {"right_share": 0.818, "signal": false, "wrong_share": 0.64}, "any": false}}

- eval_plain_log.txt (last two):

    {"pick": {"candidates": [{"config": "C3", "right": 20, "wrong": 10, "never_told_idk": 8, "eligible": false}, {"config": "C4", "right": 11, "wrong": 8, "never_told_idk": 10, "eligible": true}, {"config": "V", "right": 8, "wrong": 5, "never_told_idk": 9, "eligible": true}, {"config": "A1", "right": 26, "wrong": 24, "never_told_idk": 2, "eligible": false}], "winner": "C4", "go": false}}
    {"answerable_right": {"A0": 26, "A1": 26, "C3": 20, "C4": 11, "V": 8}, "answerable_wrong": {"A0": 27, "A1": 24, "C3": 10, "C4": 8, "V": 5}, "never_told_idk": {"A0": 1, "A1": 2, "C3": 8, "C4": 10, "V": 9}, "signal": {"C3": {"right_share": 0.769, "signal": true, "wrong_share": 0.375}, "C4": {"right_share": 0.423, "signal": false, "wrong_share": 0.25}, "V": {"right_share": 0.308, "signal": false, "wrong_share": 0.188}, "any": true}}

- h1_A_log.txt:

    {"asks": 232, "fallback_replies": 33, "minutes": 0.5}

- h1_B_log.txt:

    {"asks": 232, "fallback_replies": 51, "minutes": 0.5}

- setup_log.txt (last three):

    Fetching 11 files:  27%|██▋       | 3/11 [00:00<00:00, 29.77it/s]Fetching 11 files:  91%|█████████ | 10/11 [00:00<00:00, 47.00it/s]Fetching 11 files: 100%|██████████| 11/11 [00:19<00:00,  1.74s/it]
    BASE /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
    setup end 2026-09-27T17:45:16Z

## Machine, money and files
- VERSIONS 2.11.0+cu128 12.8 5.17.0 (torch, CUDA, transformers)
- GPUNAME NVIDIA RTX 5000 Ada Generation, 595.58.03
- MiniCPM5-1B snapshot /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (expected .../87179e5c1f455ef22e6223592d2d61351b525bfc)
- items: 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4 c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4 (train, dev; GATE-RESULT.md has 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4, c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4)
- adapter sha256 on the rental: a4bfaf199f9395c0c32d3316a6a15bfd0c4692654bfae98077c3aa6bab2ef2ca; Mac copy ~/y1t-adapter/adapter398r.pt: a4bfaf199f9395c0c32d3316a6a15bfd0c4692654bfae98077c3aa6bab2ef2ca (never pushed)
- GPU log (one line a minute: UTC, MiB used, MiB total, W): lines=22 peak_used=2776 peak_power=137.6 last=2026-09-27T18:07:08Z 2568 32760 77.55
- selftests: 5 of 5 ok (4 selftests and the import check; checks.txt)
- credit before the first create: 28.468957508839566

| instance | GPU | $/h | created (UTC) | gone or stopped (UTC) | hours | download $ | dollars |
|---|---|---|---|---|---|---|---|
| 53001974 | RTX_5000Ada | 0.35 | 2026-09-27T17:38:20Z | 2026-09-27T18:09:28Z (GONE) | 0.52 | 0.02 | 0.20 |

Total: $0.20 of the $1.30 cap: $/h x hours from each create until vast stopped listing it (GONE) or it was
stopped (STOPPED; its small storage charge is not counted), plus 8 GB x the offer's download $/GB for each
instance that answered ssh (a guess at the download size; an adopted instance is priced at $0.02/GB).

| file | bytes | sha256 |
|---|---|---|
| artifacts/claude-y1t-20260926/run2/chain_log.txt | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| artifacts/claude-y1t-20260926/run2/checks.txt | 389 | 11618b6fa543a78f96e46981b68f6ad5da151986b930ce616e03731bd9f0133b |
| artifacts/claude-y1t-20260926/run2/dev.jsonl | 297105 | 63d4df458b43f62f618aad1674af1c7e8b2a2b5388761f97e09e33d2995d08db |
| artifacts/claude-y1t-20260926/run2/drafts.jsonl | 548718 | 1e1d094197259e860d2e0efd71d8f50d2f2b79976823e19d1f0f28a7d134a76b |
| artifacts/claude-y1t-20260926/run2/drafts_log.txt | 963 | 0a163a918303be5a4ccc6f270b0821cfcf06dcb1be2b0ca6b00ef661d9d5b06d |
| artifacts/claude-y1t-20260926/run2/drafts_summary.json | 384 | 16dfb1a91e758b88339c2528ebab25ced1dae2bb7c8e6d313a5125cb7ba69045 |
| artifacts/claude-y1t-20260926/run2/eval/y1g_rows.jsonl | 40228 | 27b68960c62f82d0c1b43999e1cfd373cd234d0db71367b8c9bb72836ee179b4 |
| artifacts/claude-y1t-20260926/run2/eval/y1g_summary.json | 3897 | 7bfceae24fcd9c1df2a89d2a96a84df04686fc16fb64b0f6a37e2bf21bf02c73 |
| artifacts/claude-y1t-20260926/run2/eval_log.txt | 3082 | 36ba1eca5317acca8263a2232b561436dc597c4f02966ec3a754d6e09ff164ee |
| artifacts/claude-y1t-20260926/run2/eval_plain/y1g_rows.jsonl | 38149 | 0e1efc72af2b75a7d487ba78c0195b3a7745e6b4307c3f510e4985fbf0eb1aa4 |
| artifacts/claude-y1t-20260926/run2/eval_plain/y1g_summary.json | 3758 | 6ec725776f2e306b36c6550bdc2d21410ec49ef64760865b10f1e8ebb8655615 |
| artifacts/claude-y1t-20260926/run2/eval_plain_log.txt | 3080 | 9d802f917c5f1bc576b60040e05662927336351398253931ed2331866f99da8d |
| artifacts/claude-y1t-20260926/run2/gpu_log.txt | 842 | 0c31b98a54bc9b75f905d3b6d255a70c2ce8b467b857b2023832f63aa1230cd5 |
| artifacts/claude-y1t-20260926/run2/manifest-rental.txt | 2345 | 472f2616070e420cd360d01f02a546612e513d2f6b0d49ef4f06458fb4f000f8 |
| artifacts/claude-y1t-20260926/run2/pids.txt | 1243 | a64a99bf9cfb2cd689783c180581f013036fbe3dcf264c51108899271ec6ec75 |
| artifacts/claude-y1t-20260926/run2/setup_log.txt | 2237 | c54c7a31f25ad880d7e1af4e6bdb04e08cf76e22149b42b74ab1f4160a49e166 |
| artifacts/claude-y1t-20260926/run2/state-last.txt | 2211 | b292d17fb3f32c6e4da55768316bbcb4077d44e4942f4035cd59ca5ef0980b1f |
| artifacts/claude-y1t-20260926/run2/steps.txt | 420 | 6981bb29dbed6f60df2f59c65db7464ecce856bd460aef9c76099a34c32e8407 |
| artifacts/claude-y1t-20260926/run2/train.jsonl | 2754760 | b57a41d2441f87973fcf96216cf03569e5c17cec39de5ebe56de0a2f0a38457b |
| artifacts/claude-y1t-20260926/run2/train398r.json | 1153 | 74369b7f22a7e049bd39a4fe3c9011bcf66d4daa6a31fa607ac5862564b31614 |
| artifacts/claude-y1t-20260926/run2/train_log.txt | 6994 | f1b930dc79a485f41ca61116968de707d99465b5147e4ddad25d59b85d1d78a2 |
| artifacts/claude-y1tH1-20260926/run/h1_A_log.txt | 438 | ae5150a0a2f3c3cae6bc8b4cf33ecc9ef120b236f646748d1b64556393b7bfb1 |
| artifacts/claude-y1tH1-20260926/run/h1_B_log.txt | 438 | 228fc5b0442278df187ad92a69cec9328ed4da2689444ec724fd275409c53ba3 |
| artifacts/claude-y1tH1-20260926/run/rows_A.jsonl | 20752 | d388237e5a0bd19376ea328e5e5f952ce742dd8e50132c8c2b5f497f6c41faae |
| artifacts/claude-y1tH1-20260926/run/rows_B.jsonl | 20703 | 59c44f7a25aeb8fc7de3a7957c4726e759cb01c009131d0e867cd02310b5c8b2 |

## Notes (RUN-NOTE-vast.md)

    # y1t vast run notes (handoff/kit/y1tvast/pass.sh; UTC; one line per event)
    - 2026-09-27T17:37:56Z rent-y1t-vast-p1b: pass start (first); spent so far $0.00
    - 2026-09-27T17:38:19Z rent-y1t-vast-p1b: offer 50160636: RTX_5000Ada, 63.6 TFLOPS, at $0.3347/h (190.0 TFLOPS per $/h, the best that fits; estimated chain 82 minutes), host 438484, machine 107776, CUDA 13.2, download $0.0026041666666666665/GB, upload $0.00390625/GB
    - 2026-09-27T17:38:20Z rent-y1t-vast-p1b: created instance 53001974 (RTX_5000Ada, $0.3347/h); waiting up to 360 s for it to run
    - 2026-09-27T17:42:20Z rent-y1t-vast-p1b: instance 53001974 is running and answers ssh
    - 2026-09-27T17:42:20Z rent-y1t-vast-p1b: guard started (pid 80845; /Users/ben-hannan/premonition-watch/y1t-vast/guard.log): at the $1.30 cap or the time cap (2026-09-27T20:57:20Z) it copies back, then destroys, else stops
    - 2026-09-27T17:43:36Z rent-y1t-vast-p1b: tree ~/tree made from 44c385094ae20e772a92ab6a973dd609311d17b5 (NO-TREE): TREE marked 44c385094ae20e772a92ab6a973dd609311d17b5
    - 2026-09-27T17:43:40Z rent-y1t-vast-p1b: setup: SETUP started pid=587 2026-09-27T17:43:40Z
    - 2026-09-27T17:45:48Z rent-y1t-vast-p1b: setup done: age=0m setup end 2026-09-27T17:45:16Z
    - 2026-09-27T17:46:00Z rent-y1t-vast-p1b: checks: 5 of 5 checks ok (4 selftests and the import check); VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA RTX 5000 Ada Generation, 595.58.03
    - 2026-09-27T17:46:03Z rent-y1t-vast-p1b: LAUNCH chain 2026-09-27T17:46:02Z rc=0 pid=2340 cap=180m;
    - 2026-09-27T17:48:08Z rent-y1t-vast-p1b: running: step drafts, log age 0 min, GPU 2690 32760 131.69, $0.08 spent; LAST drafts age=0m [y1t] drafts 400/1762
    - 2026-09-27T17:58:28Z rent-y1t-vast-p1b: running: step train, log age 0 min, GPU 2776 32760 99.99, $0.14 spent; LAST train age=0m {"step": 120, "loss": 0.1233, "s": 139, "projected_train_s": 415, "tokens": 211729}
    - 2026-09-27T18:08:58Z rent-y1t-vast-p1b: chain done: drafts rc=0; train rc=0; eval rc=0; eval_plain rc=0; h1_A rc=0; h1_B rc=0; 
    - 2026-09-27T18:09:14Z rent-y1t-vast-p1b: copied back 24 files listed by the rental; every one matches its sha256 there
    - 2026-09-27T18:09:28Z rent-y1t-vast-p1b: destroyed 53001974 (COMPLETE: all 6 steps ended rc=0); vast no longer lists it
