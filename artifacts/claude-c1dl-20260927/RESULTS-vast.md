# c1-dl vast run record (handoff/kit/c1dlv, job rent-c1dl-2-collect, kit 19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb, written 2026-09-27T18:39:09Z)

**COMPLETE: arm DL has 336 rows over 60 conversations.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md) against c1-dev's T, Q and L chats. Every line
below is copied by the script, never retyped. The replies are in the chat files and are not quoted here.

## Card and money

- Card: RTX_4090, 81.4 TFLOPS, $0.428/h, 190 TFLOPS per $/h (estimate 32 min); guard: END DONE spent 0.23
- Rentals (id, $/h, created, gone; epoch seconds):
    53001665 0.126 1790530566 1790531180
    53003253 0.106 1790531183 1790531736
    53004719 0.428 1790531739 1790533122
- Spent by the kit's own count (GPU $/h x hours plus each started host's download at its $/GB): $0.23. The Director's ledger is the record.

## V1 (first two log lines; logDL also has the c1dev settings line)

- V1 DL OK

- c1dev line in logDL: c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none

## Rows per arm (expected 336 rows, 60 conversations)

    DL rows=336 conversations=60

## Steps (W/steps.txt, UTC)

    DL start 2026-09-27T18:12:43Z
    DL rc=0 end 2026-09-27T18:15:47Z

Minutes per arm: DL 3.1; 

## Last lines of each log
- logDL.txt:

    [ch403/DL] dev02e-chat-59 turns=6 lines={'answer': 6}
    [ch403/DL] dev02e-chat-60 turns=6 lines={'answer': 6}

## Machine and files
- VERSIONS 2.11.0+cu128 12.8 5.17.0 3.11.13 (torch, CUDA, transformers, python)
- GPUNAME NVIDIA GeForce RTX 4090 (8, 9) bf16-sum 4.0
- selftests: 4 of 4 ok (checks.txt); SEAL-2: SEAL-2 24/24
- model (pinned snapshot path, models.txt; LFM only): models--LiquidAI--LFM2.5-1.2B-Instruct@0f604ada3f766f9f257460c4c9f0b5d6f69d431b 
- GPU log (one line a minute: UTC, MiB used, MiB total, W, GPU %): lines=18 peak_used=2794 MiB peak_power=128.7 W
- Manifest check at copy-back: 2026-09-27T18:18:29Z COPY-CHECK: 12 of 12 files arrived and match the rental's manifest (chat rows: DL=336)

| file | bytes | sha256 |
|---|---|---|
| artifacts/claude-c1dl-20260927/run-vast/chat_DL.jsonl | 108785 | 0acabb5405bf8227522b4224ae81a6b977b23634c9d8117ac9de0fc9ab759c2d |
| artifacts/claude-c1dl-20260927/run-vast/checks.txt | 297 | ad8b712eae0acc1261cb78d3516e13184c7ad46ebedde19eb18e20305509f708 |
| artifacts/claude-c1dl-20260927/run-vast/dl-tail.txt | 833 | 90a22ad889b5b85d2b07be8e1d16c1c717750464d1d9a814d7538f2eee35351a |
| artifacts/claude-c1dl-20260927/run-vast/drive-state.txt | 474 | 7af7478a31c7e46d8a91fbd08fa516e3a711d810432ea377ef768e9cebf64619 |
| artifacts/claude-c1dl-20260927/run-vast/drive.log | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| artifacts/claude-c1dl-20260927/run-vast/END.txt | 20 | 365f9e7c46eab7d467234b6ce4fd58f391314b7dcfef02fffca2c870f5354f43 |
| artifacts/claude-c1dl-20260927/run-vast/gpu_log.txt | 681 | 1790d768aa41f804628c6d094b1f8db73d848cf48f86c651ac9457a5508994dd |
| artifacts/claude-c1dl-20260927/run-vast/logDL.txt | 4113 | 1ed480dfced10dce55ef609ca709207593faa3d4859912fd8ca49984bf3d9fb9 |
| artifacts/claude-c1dl-20260927/run-vast/mac-log.txt | 2625 | 6fd91317f10ca7a1bbd43654d4792b2902ea827856a8d758549380622f11d946 |
| artifacts/claude-c1dl-20260927/run-vast/MANIFEST.sha256 | 947 | e20eab43cb9fac28dc109f4afe3449ef3ac4e2fa780bf483a516e5aa2fb7b5b0 |
| artifacts/claude-c1dl-20260927/run-vast/models.txt | 119 | 40b3d709a7e821ec92a81c6cdbc70e5386086af8bfb2f38c5675e423882db1c4 |
| artifacts/claude-c1dl-20260927/run-vast/pip-tail.txt | 1719 | 1e02a298ef482c5234b552249c6dccbfb22d6103cff0e5f300d2e4e5b40ef238 |
| artifacts/claude-c1dl-20260927/run-vast/rentals.txt | 111 | b6ff2786ff3087ec0688e232ca50f7398db97dc5c5a2c0bfd4954e923d00bf41 |
| artifacts/claude-c1dl-20260927/run-vast/steps.txt | 63 | c1b2ca61ef1f27848d7e472045a9c314b2a66a594f1877daed69e4efab93ab35 |
| artifacts/claude-c1dl-20260927/run-vast/torch.txt | 94 | 15e624c54e6bfa6ae0300df2733e51a87614b14408f042ffb2b8c0948b8fdbbf |
