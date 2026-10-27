# c1-dev vast run record (handoff/kit/c1devv, job rent-c1dev-2-collect, kit d0072550e7756cbfb99a184f3c891faf78049463, written 2026-09-27T16:51:59Z)

**COMPLETE: all 4 arms have 336 rows over 60 conversations.** Counts only, no verdict: the Everyday chat thread scores it (PLAN.md, ADDENDUM-2-vast.md). Every line
below is copied by the script, never retyped. The replies are in the chat files and are not quoted here.

## Card and money

- Card: RTX_4090, 81.4 TFLOPS, $0.402/h, 202 TFLOPS per $/h (estimate 102 min); guard: END DONE spent 0.87
- Rentals (id, $/h, created, gone; epoch seconds):
    52972843 0.402 1790520744 1790523969
- Spent by the kit's own count (GPU $/h x hours plus each started host's download at its $/GB): $0.87. The Director's ledger is the record.

## V1 (first two log lines; logD also has the c1dev settings line)

- V1 D OK
- V1 T OK
- V1 Q OK
- V1 L OK

- c1dev line in logD: c1dev: talker = claude_e2e02d.Talker; W_PLACE02D=system; MAX_NEW02D=160; HIST_PAIRS=6; SLEEP02D=off; reader = none; reasoner = none

## Rows per arm (expected 336 rows, 60 conversations)

    D rows=336 conversations=60; T rows=336 conversations=60; Q rows=336 conversations=60; L rows=336 conversations=60

## Steps (W/steps.txt, UTC)

    D start 2026-09-27T14:56:18Z
    D rc=0 end 2026-09-27T15:08:13Z
    T start 2026-09-27T15:08:13Z
    T rc=0 end 2026-09-27T15:19:55Z
    Q start 2026-09-27T15:19:55Z
    Q rc=0 end 2026-09-27T15:41:18Z
    L start 2026-09-27T15:41:18Z
    L rc=0 end 2026-09-27T15:45:12Z

Minutes per arm: D 11.9; T 11.7; Q 21.4; L 3.9; 

## Last lines of each log
- logD.txt:

    [ch403/D] dev02e-chat-59 turns=6 lines={'answer': 6}
    [ch403/D] dev02e-chat-60 turns=6 lines={'answer': 6}

- logT.txt:

    [ch403/T] dev02e-chat-59 turns=6 lines={'answer': 6}
    [ch403/T] dev02e-chat-60 turns=6 lines={'answer': 6}

- logQ.txt:

    [ch403/Q] dev02e-chat-59 turns=6 lines={'answer': 6}
    [ch403/Q] dev02e-chat-60 turns=6 lines={'answer': 6}

- logL.txt:

    [ch403/L] dev02e-chat-59 turns=6 lines={'answer': 6}
    [ch403/L] dev02e-chat-60 turns=6 lines={'answer': 6}

## Machine and files
- VERSIONS 2.11.0+cu128 12.8 5.17.0 3.11.13 (torch, CUDA, transformers, python)
- GPUNAME NVIDIA GeForce RTX 4090 (8, 9) bf16-sum 4.0
- selftests: 4 of 4 ok (checks.txt); SEAL-2: SEAL-2 24/24
- models (pinned snapshot paths, models.txt): models--openbmb--MiniCPM5-1B@87179e5c1f455ef22e6223592d2d61351b525bfc models--Qwen--Qwen3.5-2B@15852e8c16360a2fea060d615a32b45270f8a8fc models--LiquidAI--LFM2.5-1.2B-Instruct@0f604ada3f766f9f257460c4c9f0b5d6f69d431b 
- GPU log (one line a minute: UTC, MiB used, MiB total, W, GPU %): lines=51 peak_used=4412 MiB peak_power=115.2 W
- Manifest check at copy-back: 2026-09-27T15:45:39Z COPY-CHECK: 18 of 18 files arrived and match the rental's manifest (chat rows: D=336 T=336 Q=336 L=336)

| file | bytes | sha256 |
|---|---|---|
| artifacts/claude-c1dev-20260927/run-vast/chat_D.jsonl | 199879 | fdf39bbd36acbd1c9baccffe7912a3a40c5c5ec1e2d2ac0252eb185bf3507c57 |
| artifacts/claude-c1dev-20260927/run-vast/chat_L.jsonl | 120097 | 05c957f4b533dcc7d0e497392547eaf11bc5404d89d1e125824ef5eec03beb9e |
| artifacts/claude-c1dev-20260927/run-vast/chat_Q.jsonl | 186247 | 943a8259961464193f1f34eca121e65b342a121a4ff68290a82ef5dba731d6d7 |
| artifacts/claude-c1dev-20260927/run-vast/chat_T.jsonl | 201482 | 5116832df81ac9ef28694f7f07e6195932ee7346713d1a4735d4e38271bcc829 |
| artifacts/claude-c1dev-20260927/run-vast/checks.txt | 297 | ad8b712eae0acc1261cb78d3516e13184c7ad46ebedde19eb18e20305509f708 |
| artifacts/claude-c1dev-20260927/run-vast/dl-tail.txt | 1615 | 51a9b25ffcbc96e18c0337a5239341817f13125576a6d9b864a87a2dfa52a5a5 |
| artifacts/claude-c1dev-20260927/run-vast/drive-state.txt | 716 | 1a14201635b9ed9f562efa1da249c8bde8244806ac5749725ac37588238a48e3 |
| artifacts/claude-c1dev-20260927/run-vast/drive.log | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| artifacts/claude-c1dev-20260927/run-vast/END.txt | 20 | cfd4ae00061e49f407d969d0931f0746877dcc9ec5cf9d2968bf05788fecec90 |
| artifacts/claude-c1dev-20260927/run-vast/gpu_log.txt | 2088 | 6b1575843ca3ea46098424404dee358f6141662df31c306bb68b6893b812b296 |
| artifacts/claude-c1dev-20260927/run-vast/logD.txt | 3619 | 57ed189ed9a7818d48601d7734846c6b5736b99b1c8f177dce8cdb6177949d07 |
| artifacts/claude-c1dev-20260927/run-vast/logL.txt | 3921 | 84ea550a6b7c8f30cc7c2868eeb99a376fca7774b3c3fdab21d6db4063901425 |
| artifacts/claude-c1dev-20260927/run-vast/logQ.txt | 4409 | 0a532e6f8aa2efb892ffc233ee7a1a37cd90f5dc661cdb26ae4c0fc3c7d58682 |
| artifacts/claude-c1dev-20260927/run-vast/logT.txt | 3487 | 4b93311684fba56d356302f918c0fc75b77e42721b3cea57ef061618a10e3ecc |
| artifacts/claude-c1dev-20260927/run-vast/mac-log.txt | 2378 | 225aa965402703113ca64837458ecff93e109453be41f1088acdaeee6ccc9ba9 |
| artifacts/claude-c1dev-20260927/run-vast/MANIFEST.sha256 | 1431 | 216df3545203cb48df8af31d1c34b84b877bb0257cca6c8b8a38dcb294b3f18f |
| artifacts/claude-c1dev-20260927/run-vast/models.txt | 333 | 863072c51f03475f54cde9109213a5b7553f05761e8294f8c3e741f572aa4b8f |
| artifacts/claude-c1dev-20260927/run-vast/pip-tail.txt | 1719 | 1e02a298ef482c5234b552249c6dccbfb22d6103cff0e5f300d2e4e5b40ef238 |
| artifacts/claude-c1dev-20260927/run-vast/rentals.txt | 37 | 3fc9c15efe4284a9ec98740c24f802ac315d089a754734478efbcdbcacce5c77 |
| artifacts/claude-c1dev-20260927/run-vast/steps.txt | 244 | e31de457ae9639170a2b49ad5888949b3b3b8ebbbbccfbcb49fa8904a4e5c44a |
| artifacts/claude-c1dev-20260927/run-vast/torch.txt | 94 | 15e624c54e6bfa6ae0300df2733e51a87614b14408f042ffb2b8c0948b8fdbbf |
