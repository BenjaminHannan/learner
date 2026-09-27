# y1t vast run record (handoff/kit/y1tvast/pass.sh, job rent-y1t-vast-p1, kit 4a0b63b3ad7f96cc8ee712db24442453c7b5b840, written 2026-09-27T16:55:12Z)

**PARTIAL: 1 of 6 steps ended rc=0; step train ended rc=1.** No verdict here: the thread scores the sealed DEV marks in VERIFY-y1t.md. Every line below is
copied by the script, never retyped. The H1 rows are in artifacts/claude-y1tH1-20260926/run (never opened by this job).

## Steps (W/steps.txt; UTC)

    drafts start 2026-09-27T16:46:33Z
    drafts rc=0 end 2026-09-27T16:54:03Z
    train start 2026-09-27T16:54:03Z
    train rc=1 end 2026-09-27T16:54:33Z

Minutes per step: drafts 7.5; train 0.5; 

## Last lines
- drafts_log.txt:

    {"items": 1762, "train_rows": 2852, "repeat": 2, "answer_rows": 713, "idk_rows": 713, "dev_rows": 291, "counts": {"answerable_greedy_right": 491, "answerable_n": 888, "corrected_greedy_right": 31, "corrected_n": 53, "idk_all_wrong": 175, "idk_never_told": 874, "never_told_greedy_right": 718, "never_told_n": 874, "own_greedy": 491, "own_sample": 222}, "minutes": 7.5}

- train_log.txt:

    ModuleNotFoundError: No module named 'nltk'

- eval_log.txt (last two):

    (no file)

- eval_plain_log.txt (last two):

    (no file)

- h1_A_log.txt:

    (no file)

- h1_B_log.txt:

    (no file)

- setup_log.txt (last three):

    Fetching 11 files:  18%|█▊        | 2/11 [00:00<00:01,  8.94it/s]Fetching 11 files:  91%|█████████ | 10/11 [00:00<00:00, 27.61it/s]Fetching 11 files: 100%|██████████| 11/11 [00:17<00:00,  1.64s/it]
    BASE /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
    setup end 2026-09-27T16:46:22Z

## Machine, money and files
- VERSIONS 2.11.0+cu128 12.8 5.17.0 (torch, CUDA, transformers)
- GPUNAME NVIDIA GeForce RTX 4080, 595.84
- MiniCPM5-1B snapshot /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (expected .../87179e5c1f455ef22e6223592d2d61351b525bfc)
- items: 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4 c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4 (train, dev; GATE-RESULT.md has 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4, c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4)
- adapter sha256 on the rental: none; Mac copy ~/y1t-adapter/adapter398r.pt: none (never pushed)
- GPU log (one line a minute: UTC, MiB used, MiB total, W): lines=8 peak_used=2605 peak_power=122.9 last=2026-09-27T16:53:33Z 2605 16376 113.06
- selftests: 4 of 4 ok (checks.txt)
- credit before the first create: 29.31832711383953

| instance | GPU | $/h | created (UTC) | gone or stopped (UTC) | hours | download $ | dollars |
|---|---|---|---|---|---|---|---|
| 52989756 | RTX_4090 | 0.4145 | 2026-09-27T16:29:41Z | 2026-09-27T16:36:26Z (GONE) | 0.11 | 0.00 | 0.05 |
| 52991051 | RTX_5090 | 0.5611 | 2026-09-27T16:36:34Z | 2026-09-27T16:43:27Z (GONE) | 0.11 | 0.00 | 0.06 |
| 52992266 | RTX_4080 | 0.2833 | 2026-09-27T16:43:30Z | 2026-09-27T16:55:10Z (GONE) | 0.19 | 0.02 | 0.08 |

Total: $0.19 of the $1.50 cap: $/h x hours from each create until vast stopped listing it (GONE) or it was
stopped (STOPPED; its small storage charge is not counted), plus 8 GB x the offer's download $/GB for each
instance that answered ssh (a guess at the download size; an adopted instance is priced at $0.02/GB).

| file | bytes | sha256 |
|---|---|---|
| artifacts/claude-y1t-20260926/run/chain_log.txt | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| artifacts/claude-y1t-20260926/run/checks.txt | 267 | 2a755f5d2e99a138979faf488e6106862701b58a2efc2c5f11d02e13f54a9ef9 |
| artifacts/claude-y1t-20260926/run/dev.jsonl | 297105 | 63d4df458b43f62f618aad1674af1c7e8b2a2b5388761f97e09e33d2995d08db |
| artifacts/claude-y1t-20260926/run/drafts.jsonl | 544581 | f7eeb6506d2c6cc66bafd32635bf1379f1d1d583c12040380899b4abe563adfa |
| artifacts/claude-y1t-20260926/run/drafts_log.txt | 964 | f77f6e779e20145736abdd6f8572091cf017f46b9fb59fdb3a549bc4b54c9bd0 |
| artifacts/claude-y1t-20260926/run/drafts_summary.json | 384 | 23df33abf21b07ef5d2bb81a38ac860edb4065f4e7ba558a71fb2a48d4e07320 |
| artifacts/claude-y1t-20260926/run/gpu_log.txt | 307 | d4c7be93eefc4fa0b7691327c16c7ae338aa8f29f5db62e4e610073d2d46f45c |
| artifacts/claude-y1t-20260926/run/manifest-rental.txt | 1219 | 4050cdd43de9e4d7a451740c43f259549b5f18ad51079eeec07abd7d1e97924a |
| artifacts/claude-y1t-20260926/run/pids.txt | 545 | ac29108acf03a6b38161bbcbf119d0e92302652494bc16c44664c978ce712e92 |
| artifacts/claude-y1t-20260926/run/setup_log.txt | 1871 | fc85b9e0aa637efc0aee5ba3348c09a26d1b6b116f3f361e97a6bdf9772799eb |
| artifacts/claude-y1t-20260926/run/state-last.txt | 1061 | f824f51e5a071300d9fe6f6de4067193797c830f780920a5a8e845fa64b08a93 |
| artifacts/claude-y1t-20260926/run/steps.txt | 140 | 5c68d33769dc17222c990c79e6915122768f20f86c88a11b4523192af303b6e0 |
| artifacts/claude-y1t-20260926/run/train.jsonl | 2741612 | de63a80018ac4d902786d2699a3438cca36a93fe9f68339b192a16d1c5ef15fe |
| artifacts/claude-y1t-20260926/run/train_log.txt | 900 | 9071ebed8c26882c9ab3b5ce12f61fb4922dd829edde8c17ca805342b3adb16e |

## Notes (RUN-NOTE-vast.md)

    # y1t vast run notes (handoff/kit/y1tvast/pass.sh; UTC; one line per event)
    - 2026-09-27T16:29:25Z rent-y1t-vast-p1: pass start (first); spent so far $0.00
    - 2026-09-27T16:29:37Z rent-y1t-vast-p1: offer 46151926: RTX_4090, 81.4 TFLOPS, at $0.4145/h (196.4 TFLOPS per $/h, the best that fits; estimated chain 64 minutes), host 135676, machine 29558, CUDA 13.2, download $0.00390625/GB, upload $0.00390625/GB
    - 2026-09-27T16:29:41Z rent-y1t-vast-p1: created instance 52989756 (RTX_4090, $0.4145/h); waiting up to 360 s for it to run
    - 2026-09-27T16:36:10Z rent-y1t-vast-p1: instance 52989756 is 'loading', not running, after 360 s
    - 2026-09-27T16:36:26Z rent-y1t-vast-p1: destroyed 52989756 (did not come up); vast no longer lists it
    - 2026-09-27T16:36:33Z rent-y1t-vast-p1: offer 52159510: RTX_5090, 108.1 TFLOPS, at $0.5356/h (201.8 TFLOPS per $/h, the best that fits; estimated chain 50 minutes), host 406325, machine 142894, CUDA 13.0, download $0.005208333333333333/GB, upload $0.005208333333333333/GB
    - 2026-09-27T16:36:56Z rent-y1t-vast-p1: ADOPTED instance 52991051 (RTX_5090, $0.5611/h, 'loading', started 2026-09-27T16:36:34Z): it carries this task's label and was made by a create call whose reply was lost
    - 2026-09-27T16:36:56Z rent-y1t-vast-p1: create on offer 52159510 did not answer OK, but instance 52991051 appeared with this task's label; waiting up to 360 s for it to run
    - 2026-09-27T16:43:14Z rent-y1t-vast-p1: instance 52991051 is 'loading', not running, after 360 s
    - 2026-09-27T16:43:27Z rent-y1t-vast-p1: destroyed 52991051 (did not come up); vast no longer lists it
    - 2026-09-27T16:43:29Z rent-y1t-vast-p1: offer 47784808: RTX_4080, 48.6 TFLOPS, at $0.2681/h (181.2 TFLOPS per $/h, the best that fits; estimated chain 108 minutes), host 91303, machine 30620, CUDA 13.2, download $0.0026041666666666665/GB, upload $0.0026041666666666665/GB
    - 2026-09-27T16:43:30Z rent-y1t-vast-p1: created instance 52992266 (RTX_4080, $0.2681/h); waiting up to 360 s for it to run
    - 2026-09-27T16:44:13Z rent-y1t-vast-p1: instance 52992266 is running and answers ssh
    - 2026-09-27T16:44:13Z rent-y1t-vast-p1: guard started (pid 17914; /Users/ben-hannan/premonition-watch/y1t-vast/guard.log): at the $1.50 cap or the time cap (2026-09-27T20:54:30Z) it copies back, then destroys, else stops
    - 2026-09-27T16:44:40Z rent-y1t-vast-p1: tree ~/tree made from 4a0b63b3ad7f96cc8ee712db24442453c7b5b840 (NO-TREE): TREE marked 4a0b63b3ad7f96cc8ee712db24442453c7b5b840
    - 2026-09-27T16:44:47Z rent-y1t-vast-p1: setup: SETUP started pid=624 2026-09-27T16:44:47Z
    - 2026-09-27T16:46:23Z rent-y1t-vast-p1: setup done: age=0m setup end 2026-09-27T16:46:22Z
    - 2026-09-27T16:46:31Z rent-y1t-vast-p1: checks: 4 of 4 selftests ok; VERSIONS 2.11.0+cu128 12.8 5.17.0; GPUNAME NVIDIA GeForce RTX 4080, 595.84
    - 2026-09-27T16:46:33Z rent-y1t-vast-p1: LAUNCH chain 2026-09-27T16:46:33Z rc=0 pid=2160 cap=180m;
    - 2026-09-27T16:46:34Z rent-y1t-vast-p1: running: step drafts, log age 0 min, GPU 1 16376 8.36, $0.15 spent; LAST drafts age=0m 
    - 2026-09-27T16:49:42Z rent-y1t-vast-p1: running: step drafts, log age 0 min, GPU 2603 16376 112.85, $0.16 spent; LAST drafts age=0m [y1t] drafts 700/1762
    - 2026-09-27T16:54:52Z rent-y1t-vast-p1: chain done: drafts rc=0; train rc=1; 
    - 2026-09-27T16:54:56Z rent-y1t-vast-p1: copied back 12 files listed by the rental; every one matches its sha256 there
    - 2026-09-27T16:55:10Z rent-y1t-vast-p1: destroyed 52992266 (PARTIAL: 1 of 6 steps ended rc=0; step train ended rc=1); vast no longer lists it
