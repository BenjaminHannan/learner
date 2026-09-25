# bm-390 RESULTS-benspc: SMOKE-FAIL (BensPC, 2026-09-25)

Verdict: SMOKE-FAIL. The registered run never started on real benchmark items.
Nothing was run on the real data (no run/ directory was created on BensPC).
The agent-arm smoke command crashes on Windows before writing any row; the
plain-model smoke command passes. No file was edited; nothing was trained.

Time: start 2026-09-25 03:17 UTC, stopped 2026-09-25 ~03:35 UTC (about 18 min,
within the 7-hour cap). GPU work ran only on BensPC; no rentals.

## 1. Seals (step 1, from the BensPC tree root, before anything else): ALL-OK

- artifacts/claude-bm390-20260925/SEAL-code.sha256.txt: 8 lines, 8 OK, 0 FAIL.
- artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt: 229 lines, 229 OK, 0 FAIL.

## 2. Sleep base checkpoint (step 2)

- Command: `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/bm390/r44` (about 13 s).
- Printed JSON line: {"stage": "base", "seed": 4102, "seconds": 12.9, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- Copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in the tree (copied in, never written directly).
- .pt sha256: 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3, size 2969 bytes.

## 3. Data and rival models (step 3)

- Fetch command printed exactly one JSON line (counts and hashes only):
  {"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "1a44e3041355e7fcc1e4d2b188dec0f2362a2ceb9820f62acd957b29909e3850", "gsm8k300_sha256": "073acc01184dc13caa732adf33fb9d69e049153549d8364401f4320ca0bc555b"}
  locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300 as registered. No DATA-MISMATCH, no network error.
- Rival downloads (the single command allowed with HF_HUB_OFFLINE=0; both approved by Ben 02:12 UTC 2026-09-25):
  - Q2DIR = C:\Users\benja\.cache\huggingface\hub\models--Qwen--Qwen3.5-2B\snapshots\15852e8c16360a2fea060d615a32b45270f8a8fc
  - L12DIR = C:\Users\benja\.cache\huggingface\hub\models--LiquidAI--LFM2.5-1.2B-Instruct\snapshots\0f604ada3f766f9f257460c4c9f0b5d6f69d431b
- Load checks (each separately, HF_HUB_OFFLINE=1, to cuda, dtype bfloat16): both RUN.
  - Q2: Qwen3_5ForCausalLM 1881825088
  - L12: Lfm2ForCausalLM 1170340608

## 4. Smoke on made-up data (step 4): FAIL

Smoke data: artifacts/claude-bm390-20260925/smoke (fictional people, not a benchmark).

- P (agent arm): exit code 1. No "wrote ..." line (crashed before writing). Wall time 8.2 s (first run).
  Full console begins with `sleepcheck: logging every sleep to C:/Users/benja/lis301/work/bm390/smoke/sleep_P.jsonl; stop on missing checkpoint = True`,
  loads READER then BASE weights (219/219 shards each), then crashes with the traceback below.
- T (plain arm): exit code 0. Last line: `wrote locomo_T.jsonl rows=5 convs=1`. Output file has 5 rows. (Wall time not separately measured.)
- sleep_P.jsonl: 0 rows; the file was never created (crash happened on the first turn, before any sleep).
  Rows with checkpoint_exists true: 0. Rows with attempted true: 0.
- Required bar (both exit 0 with rows=5, sleep log 2 rows both checkpoint_exists true): NOT met. Stopped with SMOKE-FAIL; nothing ran on the real data.

### Exact error and full traceback (P smoke console, in full)

```
sleepcheck: logging every sleep to C:/Users/benja/lis301/work/bm390/smoke/sleep_P.jsonl; stop on missing checkpoint = True
[transformers] `torch_dtype` is deprecated! Use `dtype` instead!
Loading weights: 219/219 shards (READER), then 219/219 shards (BASE)
Traceback (most recent call last):
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_sleepcheck_wrap.py", line 66, in <module>
    main()
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_sleepcheck_wrap.py", line 62, in main
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
  File "scripts/claude_bm390.py", line 432, in run_locomo
    locomo_agent(builder, aargs, conv, args.limit_q, rows, reading, bare)
  File "scripts/claude_bm390.py", line 363, in locomo_agent
    reply, _, _ = R.one(agent, text)
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_e2e336_run.py", line 158, in one
    parts = agent.turn(text)
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_nb323_turnlog.py", line 320, in _turn323
    turn_id = log.append_begin(text)
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_nb323_turnlog.py", line 229, in append_begin
    self._append({"kind": "BEGIN", "turn_id": turn_id,
  File "C:\Users\benja\lis301\work\bm390\tree\scripts\claude_nb323_turnlog.py", line 221, in _append
    raise TurnLog323Corrupt("turnlog323: read-back mismatch")
claude_nb323_turnlog.TurnLog323Corrupt: turnlog323: read-back mismatch
```

Diagnosis (one note, code not edited): the sealed turn-log writer opens the log
in text mode and writes line + "\n", then reads back in binary mode expecting
exactly line + "\n". On Windows, text-mode writing translates "\n" to "\r\n",
so the binary read-back never matches and every first agent turn raises
TurnLog323Corrupt. The plain-model path never touches this writer, which is why
T smoke passes and P smoke fails. The P command was launched twice in total
(first run for the result, one log-capture re-run after confirming no python
process remained; both exit 1 with the identical traceback); no registered
(step 5) command was ever launched.

## 5. Registered arms (step 5): none launched

- No lane-1 and no lane-2 command was started. No run/*.jsonl file exists on
  BensPC (run/ was never created). Row count of every run/*.jsonl: n/a (0 files).
- Lane 2 parallel or after: neither (stopped at smoke).

## 6. Copy-back (step 6)

- run/ did not exist on BensPC, so there was nothing to copy back and no
  size/sha256 check to perform. Downloaded models and data were left on BensPC
  as instructed. BensPC smoke outputs (locomo_T.jsonl, 5 rows, 650 bytes) were
  left on BensPC.

## 7. Setup notes (inputs verified, counts only)

- Tree: git archive origin/builder-outbox, then origin/main on top, plus
  self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match),
  copied to NEW folder C:/Users/benja/lis301/work/bm390/tree. Tree seal files
  present before step 1.
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe 3.10.9. Env on every
  command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
  (except the single rival-download command with HF_HUB_OFFLINE=0).
- READER C:/Users/benja/lis301/work/run/merged model.safetensors sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- BASE snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc present.
- MiniLM was missing on BensPC; copied the Mac's pinned snapshot
  (rev 1110a243fdf4706b3f48f1d95db1a4f5529b4d41, 3 files: config.json,
  model.safetensors, vocab.txt) to
  C:/Users/benja/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2
  with the same snapshots/<rev>/ layout (copy, nothing moved or deleted).
  Router check from the tree root prints a route (D8, conf 0.9732), no error.
- pyarrow was missing; installed pyarrow 25.0.1 into the same venv (pip needed
  REQUESTS_CA_BUNDLE/SSL_CERT_FILE unset: the machine's preset CA path does not
  exist). Nothing else installed or upgraded.
- GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total, driver 591.86, CUDA 13.1;
  idle before and after (about 599 MiB used by desktop processes, 0% util).
  No other GPU job was running (one job at a time kept).
- DUPLICATE check: artifacts/claude-bm390-20260925/run does not exist on
  origin/builder-outbox (checked before starting); this was the single run
  attempt, and it stopped at smoke.
- No benchmark question, answer, or reply is quoted anywhere in this file;
  only counts, hashes, paths, timings, and the traceback above.
