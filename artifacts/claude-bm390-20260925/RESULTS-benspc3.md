# bm-390 RESULTS-benspc3: TIME-CAP partial, winnl2 PASS (BensPC, 2026-09-25, third attempt)

Verdict: TIME-CAP. The 7-hour cap was reached with lane 1 complete (P, Pm, Pg) and lane 2 partial (Rb OK, T OOM, C killed with no output, Q2 stopped at cap, rest not run). No file was edited; nothing was trained. No benchmark question, answer or reply is quoted anywhere in this file; only counts, hashes, paths, timings and tracebacks.
Winnl2 wrapper: PASS. Smoke passed with 0 CRLF. Seals ALL-OK.

Time: start 2026-09-25 09:35:50 UTC (Mac date), cap 2026-09-25 16:35:50 UTC (7 h). Stopped Q2 at 2026-09-25 16:37:15 UTC (exact PIDs 10028,14012). GPU work only on BensPC; no rentals.
DUPLICATE guard: PASS (origin/builder-outbox has only artifacts/claude-bm390-20260925/RESULTS-benspc.md and RESULTS-benspc2.md; no run/, no RESULTS-rent.md, no RESULTS-benspc3.md before start).

## 1. Seals (step 1, BensPC tree3 C:/Users/benja/lis301/work/bm390/tree3): ALL-OK

- artifacts/claude-bm390-20260925/SEAL-code.sha256.txt: 8 lines, 8 OK, 0 FAIL.
- artifacts/claude-bm390-20260925/SEAL-winnl2.sha256.txt: 3 lines, 3 OK, 0 FAIL.
- artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt: 229 lines, 229 OK, 0 FAIL.

## W CHECK (right after step 1, from tree3 root)

- (a) no wrapper `python -B scripts/claude_winnl2_test.py probe` printed one JSON line:
{"python": "3.10.9", "pathlib_loaded_before_fix": false, "sim": false, "fix": "none", "ok": true, "crlf": 3, "text_ok": true, "metadata_ok": true}
  Expected ok true with crlf above 0 (plain Windows writes \r\n): met (crlf 3).
- (b) with wrapper `python -B scripts/claude_winnl2_wrap.py scripts/claude_winnl2_test.py probe` printed first line:
winnl2: Windows text-mode writes use Linux line endings (newline='')
  then one JSON line:
{"python": "3.10.9", "pathlib_loaded_before_fix": false, "sim": false, "fix": "none", "ok": true, "crlf": 0, "text_ok": true, "metadata_ok": true}
  Expected ok true and crlf 0: met. Not WINNL-FAIL.

## 2. Sleep base checkpoint (step 2, plain as listed)

- Command: `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/bm390/r44c`. Exit 0.
- Printed JSON line:
{"stage": "base", "seed": 4102, "seconds": 13.4, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- Copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in tree3.
- .pt sha256: 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3, size 2969 bytes.

## 3. Data and rival models (step 3, plain as listed)

- Fetch `python -B scripts/claude_bm390.py fetch --data C:/Users/benja/lis301/work/bm390/data3` printed exactly one JSON line (exit 0):
{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "1a44e3041355e7fcc1e4d2b188dec0f2362a2ceb9820f62acd957b29909e3850", "gsm8k300_sha256": "073acc01184dc13caa732adf33fb9d69e049153549d8364401f4320ca0bc555b"}
  locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300 as registered. DATA = C:/Users/benja/lis301/work/bm390/data3 (new folder).
- Rival paths (already downloaded, download nothing):
  - Q2DIR = C:/Users/benja/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc (exists)
  - L12DIR = C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b (exists)
- Load checks (each separately, HF_HUB_OFFLINE=1, to cuda, dtype bfloat16): both RUN, exit 0.
  - Q2: Qwen3_5ForCausalLM 1881825088
  - L12: Lfm2ForCausalLM 1170340608

## 4. Smoke on made-up data (step 4, both through W): PASS

Smoke data: artifacts/claude-bm390-20260925/smoke (fictional people, not a benchmark). OUT = C:/Users/benja/lis301/work/bm390/smoke3. SLEEPCHECK_LOG = C:/Users/benja/lis301/work/bm390/smoke3/sleep_P.jsonl.

- P (agent through W + sleepcheck): exit 0. Start 2026-09-25T09:45:16Z, end 2026-09-25T09:45:55Z (wall 39 s).
  First printed line: `winnl2: Windows text-mode writes use Linux line endings (newline='')`.
  Second line: `sleepcheck: logging every sleep to C:/Users/benja/lis301/work/bm390/smoke3/sleep_P.jsonl; stop on missing checkpoint = True`.
  Last line: `wrote locomo_P.jsonl rows=5 convs=1 bare=5`.
- T (plain through W): exit 0. Start 2026-09-25T09:46:01Z, end 2026-09-25T09:46:09Z (wall 8 s).
  First printed line: `winnl2: Windows text-mode writes use Linux line endings (newline='')`.
  Last line: `wrote locomo_T.jsonl rows=5 convs=1`.
- sleep_P.jsonl: 2 rows, both checkpoint_exists true (2), attempted true 0.
- Files under smoke3: 5 files. CRLF byte counts (all 0):
  locomo_P.jsonl bytes=718 crlf=0; locomo_P_bare.jsonl bytes=852 crlf=0; locomo_P_reading.jsonl bytes=146 crlf=0; locomo_T.jsonl bytes=645 crlf=0; sleep_P.jsonl bytes=434 crlf=0.
  locomo_P.jsonl rows=5; locomo_T.jsonl rows=5.
- Required bar (both exit 0 rows=5, sleep 2 rows both checkpoint_exists true, 0 CRLF): met. Nothing ran on real data before smoke passed.
- Each smoke command launched once; process list checked (GPU free 15460 MiB, only background pythonw, no python.exe jobs).

## 5. Registered arms (step 5): TIME-CAP partial

OUT = artifacts/claude-bm390-20260925/run (inside tree3). DATA = C:/Users/benja/lis301/work/bm390/data3.
W = `python -B scripts/claude_winnl2_wrap.py`. First printed line of every W command is the winnl2 line above. Env every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 (plus SLEEPCHECK_STOP=1 SLEEPCHECK_LOG for P).
Each command its own process, launched once. Process list checked before each launch (no stray python.exe; background pythonw only).

Lane 1 (in order): P, Pm, Pg — all complete.
Lane 2 (in order, plain LoCoMo first): T, Rb, C, Q2, L12, Tm, Tg, Q2m, Q2g, L12m, L12g.
Lane 2 parallel or after: AFTER. P printed first `[bm390] conv-` line at 2026-09-25 ~10:19Z (`[bm390] conv-26 turns=439 questions=199`); nvidia-smi at that time showed 8089 MiB free (below 8192 MiB = 8 GB), so lane 2 ran after lane 1 per the registered rule. GPU free later dropped to 6787 MiB during P QA and 6189 MiB during Pm; never 8 GB free while P ran.

### Lane 1

- P: SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=artifacts/claude-bm390-20260925/run/sleep_P.jsonl W scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo --data DATA --arm agent:claude_e2e330c:build_330c --name P --also-bare --model READER --gen-model BASE --out OUT.
  Start 2026-09-25T09:48:09Z, end 2026-09-25T14:08:47Z (wall ~4 h 20 min). Exit 0 (inferred: wrote line present, no traceback, processes exited, output files present; Mac monitor ssh timed out at ~11:00Z due to client network timeout, server process survived with no relaunch, monitoring resumed by polling BensPC logs — reported as deviation, no duplicate launch).
  First printed line: `winnl2: Windows text-mode writes use Linux line endings (newline='')`.
  Second line: `sleepcheck: logging every sleep to artifacts/claude-bm390-20260925/run/sleep_P.jsonl; stop on missing checkpoint = True`.
  Last line: `wrote locomo_P.jsonl rows=1986 convs=10 bare=1986`.
  No SLEEP-NOT-LEARNING, no STATE-RESET-FAILED, no traceback.
- Pm: W scripts/claude_bm390.py general --task mmlu --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT.
  Start 2026-09-25T14:09:09Z, end 2026-09-25T14:52:33Z (wall 43 min). Exit 0.
  First: winnl2 line. Last: `wrote mmlu_P.jsonl rows=300`. No traceback.
- Pg: W scripts/claude_bm390.py general --task gsm8k --data DATA --arm agent:claude_e2e330c:build_330c --name P --model READER --gen-model BASE --out OUT.
  Start 2026-09-25T14:52:38Z, end 2026-09-25T15:59:17Z (wall ~1 h 07 min). Exit 0.
  First: winnl2 line. Last: `wrote gsm8k_P.jsonl rows=300`. No traceback.

### Lane 2

- T: W scripts/claude_bm390.py locomo --data DATA --arm plain:BASE --name T --out OUT.
  Start 2026-09-25T15:59:31Z, end before 2026-09-25T16:00:14Z (failed fast). Exit non-zero (OOM, no wrote line, no output file).
  First: winnl2 line. Last: no wrote line (crashed on first generate). Full traceback below (CUDA OOM).
  A lane-2 failure does not stop the others.
- Rb: W scripts/claude_bm390.py locomo --data DATA --arm bm25:BASE --name Rb --out OUT.
  Start 2026-09-25T16:00:14Z, end 2026-09-25T16:08:13Z (wall 8 min). Exit 0.
  First: winnl2 line. Last: `wrote locomo_Rb.jsonl rows=1986 convs=10`. No traceback.
- C: W scripts/claude_bm390.py locomo --data DATA --arm closed:BASE --name C --out OUT.
  Start 2026-09-25T16:08:20Z. Mac tool timeout 10 min killed the Mac ssh client at ~16:18:20Z; BensPC process continued (9 conv lines in Mac log, no wrote, no traceback), gone by 2026-09-25T16:26:38Z with no output file. Launched once; process list checked (no python.exe before launch). No wrote line, no traceback captured, no locomo_C.jsonl. Reported as killed/no-output (tool timeout, not cap).
  First: winnl2 line. Last: no wrote line (`[bm390] conv-49 ...` was last conv in partial log, conv-50 missing).
- Q2: W scripts/claude_bm390.py locomo --data DATA --arm plain:Q2DIR --name Q2 --out OUT.
  Start 2026-09-25T16:26:57Z. At time cap 2026-09-25T16:35:50Z still running (loading done, warnings about causal_conv1d/flash-linear-attention fallback, no conv line, no wrote, no traceback). Stopped at 2026-09-25T16:37:15Z by exact PIDs 10028 and 14012 (both StartTime 9/25/2026 12:26:58 PM, paths venv python and system python; no other python processes; GPU free after stop 15540 MiB). No output file. Launched once.
  First: winnl2 line. Last: no wrote line.
- L12, Tm, Tg, Q2m, Q2g, L12m, L12g: never launched (0 files). Time cap reached.

### Run files (counts only, local copy verified against BensPC sizes and sha256)

- gsm8k_P.jsonl bytes=40929 crlf=0 rows=300 sha256=1b94b4507be7b8160e392715eb645783f8ead230c9fcaad13a8c20ed4bb7a6ef
- locomo_P.jsonl bytes=267386 crlf=0 rows=1986 sha256=01df3f97943911a3369c07cf7928909032f8d6314e9b5c2fc4438953fea0d59c
- locomo_P_bare.jsonl bytes=321073 crlf=0 rows=1986 sha256=6cc23aa16c85503008edb9a0827fab88b0d0252995a5048af647a3b4e3210391
- locomo_P_reading.jsonl bytes=1536 crlf=0 rows=10 sha256=255f8ca78925b0f75a12a79d077656bbdfc680471cc2bc68d6f2052795a1b5e6
- locomo_Rb.jsonl bytes=274510 crlf=0 rows=1986 sha256=af15f49e14d89669187c6794e169b9b6bc0f6a40af38ddd957dfe44e1633fe55
- mmlu_P.jsonl bytes=45339 crlf=0 rows=300 sha256=81aef79fe0cd78b56423278b6db858aafb8e07914952f38d4517a7e1dcd305f5
- sleep_P.jsonl bytes=59024 crlf=0 rows=272 sha256=7694e95e8a655e6fe8fabe0956b8703d52595c5709bb4b7477526da571d98cf6
- Total run/*.jsonl files: 7. Row counts above. CRLF counts all 0.
- sleep_P.jsonl: rows 272, checkpoint_exists true 272, attempted true 0.
- Missing (never finished, 0 files): locomo_T.jsonl, locomo_C.jsonl, locomo_Q2.jsonl, locomo_L12.jsonl, general_T_mmlu/gsm8k, general_Q2_mmlu/gsm8k, general_L12_mmlu/gsm8k (names per runner; none exist).

## 6. Copy-back (step 6)

- Copied 7 run/ files above from BensPC tree3 to Mac worktree artifacts/claude-bm390-20260925/run/ via scp. Sizes match BensPC (listed above). Sha256 match BensPC (listed above, case-insensitive).
- Models left on BensPC (READER, BASE, Q2DIR, L12DIR, MiniLM). Data3, r44c, smoke3, tree3 left on BensPC. Nothing deleted.

## 7. Setup notes

- Tree: git archive origin/builder-outbox then origin/main on top, plus self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match), copied to NEW folder C:/Users/benja/lis301/work/bm390/tree3 (161 MB tgz). Earlier trees left as is. Tree3 seal files present before step 1.
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe 3.10.9. Env every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 (plus SLEEPCHECK_STOP=1 SLEEPCHECK_LOG for P).
- READER C:/Users/benja/lis301/work/run/merged model.safetensors exists (sha check from prior attempts b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890, not re-hashed this run to save time; prior attempts matched).
- BASE snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc present.
- MiniLM route122 check from tree3 root prints a route (D8, conf 0.9732), no error.
- pyarrow 25.0.1 imports, no error. Nothing installed or upgraded.
- GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total, driver 591.86, CUDA 13.1. Idle before (15460 MiB free, 0% util, desktop processes only) and after stop (15540 MiB free). During P: free down to 6787 MiB, util up to 45%. During Pm: free 6189 MiB, util 31%. One GPU job at a time kept (only our python.exe plus background pythonw and desktop processes; process list checked before each launch; no rentals).
- No benchmark question, answer or reply is quoted anywhere in this file; only counts, hashes, paths, timings and tracebacks.

## Tracebacks in full

### T OOM (lane2_T, exit non-zero, no output file)

```
winnl2: Windows text-mode writes use Linux line endings (newline='')
Traceback (most recent call last):
  File "C:\Users\benja\lis301\work\bm390\tree3\scripts\claude_winnl2_wrap.py", line 70, in <module>
    main()
  File "C:\Users\benja\lis301\work\bm390\tree3\scripts\claude_winnl2_wrap.py", line 66, in main
    runpy.run_path(target, run_name="__main__")
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 289, in run_path
    return _run_module_code(code, init_globals, run_name,
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 96, in _run_module_code
    _run_code(code, mod_globals, init_globals,
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "scripts/claude_bm390.py", line 540, in <module>
    sys.exit(main())
  File "scripts/claude_bm390.py", line 531, in main
    run_locomo(args)
  File "scripts/claude_bm390.py", line 442, in run_locomo
    reply, n = generate(target, LOCOMO_SYSTEM, user, ANS_TOKENS)
  File "scripts/claude_bm390.py", line 267, in generate
    out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\utils\_contextlib.py", line 124, in decorate_context
    return func(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\generation\utils.py", line 2802, in generate
    result = decoding_method(
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\generation\utils.py", line 3002, in _sample
    outputs = self._prefill(
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\generation\utils.py", line 4109, in _prefill
    return self(**model_inputs, return_dict=True)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\utils\generic.py", line 939, in wrapper
    output = func(self, *args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\models\llama\modeling_llama.py", line 467, in forward
    outputs: BaseModelOutputWithPast = self.model(
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\utils\generic.py", line 1068, in wrapper
    output = func(self, *args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\utils\output_capturing.py", line 286, in wrapper
    outputs = func(self, *args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\models\llama\modeling_llama.py", line 403, in forward
    hidden_states = decoder_layer(
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\modeling_layers.py", line 109, in __call__
    return super().__call__(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\models\llama\modeling_llama.py", line 308, in forward
    hidden_states, _ = self.self_attn(
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1779, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\torch\nn\modules\module.py", line 1790, in _call_impl
    return forward_call(*args, **kwargs)
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\models\llama\modeling_llama.py", line 268, in forward
    attn_output, attn_weights = attention_interface(
  File "C:\Users\benja\lis300\venv\lib\site-packages\transformers\integrations\sdpa_attention.py", line 158, in sdpa_attention_forward
    attn_output = torch.nn.functional.scaled_dot_product_attention(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 4.62 GiB. GPU 0 has a total capacity of 15.92 GiB of which 0 bytes is free. Of the allocated memory 40.92 GiB is allocated by PyTorch, and 107.90 MiB is reserved by PyTorch but unallocated.
```

No other traceback (P, Pm, Pg, Rb exited 0 with wrote lines and no traceback; C and Q2 produced no traceback before stop; smoke passed).

## Deviations

- P Mac monitor ssh client timeout at ~11:00Z (client "Timeout, server not responding"); BensPC P process survived (PIDs 14152,21436), no relaunch, monitoring resumed by polling BensPC logs. No duplicate launch.
- C Mac tool timeout 10 min at ~16:18:20Z killed the Mac client; BensPC C continued then exited with no output by 16:26:38Z. Launched once, not relaunched.
- Q2 stopped at time cap by exact PIDs 10028,14012. No other GPU job running.
- Time cap reached with lane 2 partial; copied back what finished (7 files). Which commands finished: P, Pm, Pg, Rb (all wrote + exit 0). Which did not: T (OOM), C (killed, no output), Q2 (stopped, no output), L12/Tm/Tg/Q2m/Q2g/L12m/L12g (never launched).

PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc3.md artifacts/claude-bm390-20260925/run
