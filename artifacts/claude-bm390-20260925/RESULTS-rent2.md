# bm-390 RESULTS-rent2: finishing run on rented RTX 5090 (2026-09-25, rent-bm390f)

Registered finishing run of bm-390 (AMEND-finish.md): the plain-model arms that did not run on BensPC.
No file was edited; nothing was trained. No benchmark question, answer or reply is quoted anywhere in this
file; only counts, hashes, paths, timings and tracebacks. P, P_bare, Rb and P's general tests were NOT rerun.

Verdict: COMPLETE. All 14 registered commands exited 0 with the expected row counts. MODE = registered
(no gqa wrapper needed). No traceback in any registered command.

## 0. Credit and duplicate gates

- `vastai show user --raw`: credit 8.683039608599906 (balance 0) at first check; re-check before rent:
  credit 8.651363460599903. Above $5.00 both times: no CREDIT-STOP.
- DUPLICATE guard: PASS. origin/builder-outbox has no artifacts/claude-bm390-20260925/run2 and no
  artifacts/claude-bm390-20260925/RESULTS-rent2.md; `vastai show instances` showed no live instance
  labelled rent-bm390f (only an unrelated rsn-353b instance).

## 1. Seals (tree root /root/tree, before anything else)

- artifacts/claude-bm390-20260925/SEAL-code.sha256.txt: 8 lines, 8 OK, 0 FAIL.
- artifacts/claude-bm390-20260925/SEAL-finish.sha256.txt: 4 lines, 4 OK, 0 FAIL.
- Any mismatch would have been SEAL-MISMATCH: none.

## 2. Setup

- Tree: `git archive origin/builder-outbox` then `git archive origin/main` on top (main wins),
  161 MB tgz, unpacked to /root/tree. OUT = artifacts/claude-bm390-20260925/run2 (new folder in tree).
  DATA = /root/bm390data (outside tree). WORK = /root/bm390work.
- pip: kit line (`transformers>=5` safetensors huggingface_hub accelerate numpy) plus pyarrow
  (first `import pyarrow` failed, installed, re-verified OK). Nothing else installed.
- Versions: torch 2.8.0+cu128, transformers 5.17.0.
- Model downloads (HF_HUB_OFFLINE=0, the only downloads):
  - BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  - Q2DIR = /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
  - L12DIR = /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
- Env for everything else: HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1.
  Every command under setsid/nohup with its own log file.

## 3. Fetch (step 2)

`python -B scripts/claude_bm390.py fetch --data /root/bm390data`, exit 0,
start 2026-09-25T17:54:34Z, end 2026-09-25T17:55:39Z. Verbatim line:

{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}

locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300, both sample hashes exactly the registered
Linux values: no DATA-MISMATCH.

## 4. Load checks (step 3, each separately, HF_HUB_OFFLINE=1, bfloat16, to cuda)

- Q2 first attempt: exit 1, `SyntaxError: invalid decimal literal`. Cause: Mac-side shell quoting
  mangled the one-liner (r'...' and 'cuda' quotes stripped), NOT a model failure. Retried by piping
  the exact code via base64 (no file written): exit 0.
- Q2 retry: `Qwen3_5ForCausalLM 1881825088`, exit 0, start 2026-09-25T17:59:16Z, end 2026-09-25T17:59:21Z.
  Matches BensPC expectation. RUN.
- L12: `Lfm2ForCausalLM 1170340608`, exit 0, start 2026-09-25T18:00:58Z, end 2026-09-25T18:01:01Z.
  Matches BensPC expectation. RUN.

## 5. Long-prompt checks (step 4, made-up diary, each alone on GPU)

- BASE `python -B scripts/claude_bm390_longctx.py --model BASE`, exit 0,
  start 2026-09-25T18:02:11Z, end 2026-09-25T18:02:17Z:

{"model": "87179e5c1f455ef22e6223592d2d61351b525bfc", "device": "cuda", "context": 131072, "prompt_tokens": 31114, "gqa_off": false, "ok": true, "reply_chars": 1, "seconds": 1.17, "peak_gib": 3.95, "sdpa_calls": 48, "sdpa_enable_gqa_calls": 48}

  ok true and peak_gib 3.95 <= 8.0: MODE = registered, PY = `python -B` (plain `python3 -B`,
  no wrapper) for every command in steps 5 and 6.

- Q2DIR (registered mode, no --gqa-off), exit 0:

{"model": "15852e8c16360a2fea060d615a32b45270f8a8fc", "device": "cuda", "context": 262144, "prompt_tokens": 35760, "gqa_off": false, "ok": true, "reply_chars": 7, "seconds": 2.28, "peak_gib": 8.0, "sdpa_calls": 24, "sdpa_enable_gqa_calls": 24}

  ok true and peak_gib 8.0 <= 12.0: RUN.

- L12DIR (registered mode, no --gqa-off), exit 0:

{"model": "0f604ada3f766f9f257460c4c9f0b5d6f69d431b", "device": "cuda", "context": 128000, "prompt_tokens": 32710, "gqa_off": false, "ok": true, "reply_chars": 15, "seconds": 0.94, "peak_gib": 4.57, "sdpa_calls": 24, "sdpa_enable_gqa_calls": 24}

  ok true and peak_gib 4.57 <= 12.0: RUN.

- MODE = registered. No LONGCTX-FAIL. (F3 predicted the registered path fits: holds.)

## 6. Smoke (step 5, made-up data)

`python -B scripts/claude_bm390.py locomo --data artifacts/claude-bm390-20260925/smoke --arm plain:BASE
--name T --out /root/bm390work/smoke`, exit 0, start 2026-09-25T18:08:30Z, end 2026-09-25T18:08:34Z.
First content line: `[bm390] smoke-1 plain questions=5`.
Last line: `wrote locomo_T.jsonl rows=5 convs=1`. Smoke PASS (no SMOKE-FAIL).

## 7. Registered commands (step 6)

Each its own process, launched once (ps checked before each chained launch; no retries needed:
every command exited 0 on its first launch). Lanes:

- Lane 1 (plain MiniCPM5-1B) started 2026-09-25T18:09:59Z (T launch).
- Lane 2 (LFM2.5-1.2B) started 2026-09-25T18:13:11Z (L12 launch) with 27036 MiB GPU free.
- Lane 3 (Qwen3.5-2B) started 2026-09-25T18:16:26Z (Q2 part 1 launch) with 21273 MiB GPU free.
- A failing command would not stop the others: none failed.
- "First line" below is the command's first content line (wrapper date stamp and
  `Loading weights` progress bars omitted; general tasks print no [bm390] lines).

| # | Command | Start (UTC) | End (UTC) | Exit | First printed line | Last wrote line |
|---|---|---|---|---|---|---|
| T | locomo plain:BASE --name T | 2026-09-25T18:09:59Z | 2026-09-25T18:57:54Z | 0 | `[bm390] conv-26 plain questions=199` | `wrote locomo_T.jsonl rows=1986 convs=10` |
| C | locomo closed:BASE --name C | 2026-09-25T18:59:11Z | 2026-09-25T19:05:19Z | 0 | `[bm390] conv-26 closed questions=199` | `wrote locomo_C.jsonl rows=1986 convs=10` |
| Tm | general mmlu plain:BASE --name T | 2026-09-25T19:09:17Z | 2026-09-25T19:10:26Z | 0 | (progress bars only) | `wrote mmlu_T.jsonl rows=300` |
| Tg | general gsm8k plain:BASE --name T | 2026-09-25T19:14:07Z | 2026-09-25T19:26:15Z | 0 | (progress bars only) | `wrote gsm8k_T.jsonl rows=300` |
| L12 | locomo plain:L12DIR --name L12 | 2026-09-25T18:13:11Z | 2026-09-25T18:55:34Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-26 plain questions=199` | `wrote locomo_L12.jsonl rows=1986 convs=10` |
| L12m | general mmlu plain:L12DIR --name L12 | 2026-09-25T18:59:20Z | 2026-09-25T18:59:29Z | 0 | transformers causal_conv1d fallback warning | `wrote mmlu_L12.jsonl rows=300` |
| L12g | general gsm8k plain:L12DIR --name L12 | 2026-09-25T19:04:25Z | 2026-09-25T19:12:55Z | 0 | transformers causal_conv1d fallback warning | `wrote gsm8k_L12.jsonl rows=300` |
| Q2p1 | locomo plain:Q2DIR --name Q2 --part 1 --convs conv-26,conv-30 | 2026-09-25T18:16:26Z | 2026-09-25T18:28:18Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-26 plain questions=199` | `wrote locomo_Q2.part1.jsonl rows=304 convs=2` |
| Q2p2 | locomo plain:Q2DIR --name Q2 --part 2 --convs conv-41,conv-42 | 2026-09-25T18:30:26Z | 2026-09-25T18:55:42Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-41 plain questions=193` | `wrote locomo_Q2.part2.jsonl rows=453 convs=2` |
| Q2p3 | locomo plain:Q2DIR --name Q2 --part 3 --convs conv-43,conv-44 | 2026-09-25T18:59:28Z | 2026-09-25T19:13:04Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-43 plain questions=242` | `wrote locomo_Q2.part3.jsonl rows=400 convs=2` |
| Q2p4 | locomo plain:Q2DIR --name Q2 --part 4 --convs conv-47,conv-48 | 2026-09-25T19:14:12Z | 2026-09-25T19:26:54Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-47 plain questions=190` | `wrote locomo_Q2.part4.jsonl rows=429 convs=2` |
| Q2p5 | locomo plain:Q2DIR --name Q2 --part 5 --convs conv-49,conv-50 | 2026-09-25T19:27:23Z | 2026-09-25T19:35:30Z | 0 | transformers causal_conv1d fallback warning, then `[bm390] conv-49 plain questions=196` | `wrote locomo_Q2.part5.jsonl rows=400 convs=2` |
| Q2m | general mmlu plain:Q2DIR --name Q2 | 2026-09-25T19:37:03Z | 2026-09-25T19:37:30Z | 0 | transformers causal_conv1d fallback warning | `wrote mmlu_Q2.jsonl rows=300` |
| Q2g | general gsm8k plain:Q2DIR --name Q2 | 2026-09-25T19:41:53Z | 2026-09-25T19:59:41Z | 0 | transformers causal_conv1d fallback warning | `wrote gsm8k_Q2.jsonl rows=300` |

Q2 part rows sum: 304 + 453 + 400 + 429 + 400 = 1986 (all 10 conversations covered).
Part expectations all met exactly (304, 453, 400, 429, 400).
Q2p2 printed no new log line for ~12 min mid-run (conv-41 line 18:42Z to conv-42 line); the process
was verified active throughout (CPU TIME == elapsed, GPU 99%), so no watchdog destroy; it finished
normally. No other log gap exceeded 10 min.

## 8. run2/ files (counts only, Mac copy verified)

14 files, sizes and sha256 match the rental box (ALL_MATCH):

| File | Rows (wc -l) | Bytes | sha256 |
|---|---|---|---|
| locomo_T.jsonl | 1986 | 333388 | 35bdf151ba5160efda06cfe4e1cb274c7a0fa894963db8295286927b5e53b3db |
| locomo_C.jsonl | 1986 | 334498 | 6d13014675f4642147b46d1eafe3372251a92046b3e3d82829634ea7a7eb8895 |
| mmlu_T.jsonl | 300 | 43827 | ef1b4e6b2666130679cf6ee92e9c937c17168ad2d5a7dbf12d21b35ba2c9fd62 |
| gsm8k_T.jsonl | 300 | 215399 | 29e814f502a0e5045fa0f63e1151240508d01a156f74f6ba482058fdd82e244e |
| locomo_L12.jsonl | 1986 | 298721 | 5afc0a26c24ba00fa826e5f9d40a5c0afa53b8f0fe6e6e0ee611bf8dd6353ac6 |
| mmlu_L12.jsonl | 300 | 19028 | 40068cfe70729129664001ca1647b776f22482951b6424385d8d06ed2e0d5297 |
| gsm8k_L12.jsonl | 300 | 165686 | 1a1cddf660e68c4d228fa4c18a64eeaad21a328e23a538b5c3a197053f920d05 |
| locomo_Q2.part1.jsonl | 304 | 39334 | b70f55be9c17f21edf473741d81f1e62f442cf9649960d02aaf37399f770555f |
| locomo_Q2.part2.jsonl | 453 | 57749 | 3352ea2c2c90c7167ffca2a990d3a085579e5b8352cd50a5310f79f39ae4a129 |
| locomo_Q2.part3.jsonl | 400 | 50798 | 74c0eead85ec9168b33afb9e513b60284270c6205fc2794feaad16136c4eb448 |
| locomo_Q2.part4.jsonl | 429 | 54142 | 88ab38f9efb1cc566a3968ffe5a296878d553cccc4eca2c45cdf9568c012b880 |
| locomo_Q2.part5.jsonl | 400 | 50271 | e6d702c9e18e3c2ad8919d3cbe8e0348c9c8156bdbfc352aacfe1247f746b45c |
| mmlu_Q2.jsonl | 300 | 18940 | 847a4743bda4d372c125a373e6ee719805f39b448a939eb7a997233e7af3c56f |
| gsm8k_Q2.jsonl | 300 | 208448 | 69c1acea4f31d8b15cae5ba4d79d78c2c33c3669b95c7425f1f36bf51661e259 |

Total rows: 9744. Row counts equal every wrote line. Question/answer/reply text never opened
(files only line-counted and hashed).

## 9. GPU, money, copy-back, destroy

- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. Peak GPU memory sampled: 20668 MiB used
  (11442 MiB free) with all three lanes running; sampling only, true peak may be higher.
- Lanes started with 27036 MiB free (lane 2) and 21273 MiB free (lane 3); no lane ever waited.
- Instance id 52625917 (label rent-bm390f, offer 48989852). dph $0.494444.
  Created ~2026-09-25T17:43Z, running 17:46:51Z, destroyed ~20:01Z.
  Billed duration at destroy check: 8260.4 s = 2.29 h x $0.494444/h = ~$1.13.
  Running total $1.13 of the $3.00 budget (never near the $2.60 stop; 1 rental, no re-rents).
- Copy-back BEFORE destroy: all 14 run2/*.jsonl scp'd to the Mac, sizes and sha256 match
  (section 8). THEN destroyed by exact id; `vastai show instances` confirms 0 rent-bm390f live
  (only other agents' instances remain, untouched). Ledger line appended.
- Tracebacks: none in any registered command (14/14 exit 0). The only non-zero exit in the job
  was the Mac-side quoting SyntaxError on the first Q2 load attempt (section 4), which never ran
  any model code; full text: `SyntaxError: invalid decimal literal`, exit 1.

PUSH: artifacts/claude-bm390-20260925/RESULTS-rent2.md artifacts/claude-bm390-20260925/run2 artifacts/fable-predictions-ledger.md
