# bm-390 RESULTS-benspc2: SMOKE-FAIL, wrapper bug (BensPC, 2026-09-25, second attempt)

Verdict: SMOKE-FAIL. The registered run never started on real benchmark items.
Nothing was run on the real data (no run/ directory was created on BensPC).
Both smoke commands through scripts/claude_winnl_wrap.py crash on Windows
before writing any row, with TypeError in the wrapper itself (not the turn log).
No file was edited; nothing was trained. No benchmark question, answer or reply
is quoted anywhere in this file; only counts, hashes, paths, timings and tracebacks.

Time: start 2026-09-25 06:28:33 UTC, stopped 2026-09-25 ~06:41 UTC (about 13 min,
within the 7-hour cap). GPU work ran only on BensPC; no rentals.
DUPLICATE guard: PASS (origin/builder-outbox has only
artifacts/claude-bm390-20260925/RESULTS-benspc.md, no run/, no RESULTS-rent.md
for bm-390; runs/rent-bm390/rent-bm390.exit exists with rc=0).

## 1. Seals (step 1, BensPC tree2 root C:/Users/benja/lis301/work/bm390/tree2): ALL-OK

- artifacts/claude-bm390-20260925/SEAL-code.sha256.txt: 8 lines, 8 OK, 0 FAIL.
- artifacts/claude-bm390-20260925/SEAL-winnl.sha256.txt: 3 lines, 3 OK, 0 FAIL.
- artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt: 229 lines, 229 OK, 0 FAIL.

## 2. Sleep base checkpoint (step 2)

- Registered command (plain, as listed): `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/bm390/r44b`. Exit 0.
- Printed JSON line: {"stage": "base", "seed": 4102, "seconds": 12.9, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- Copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in tree2.
- .pt sha256: 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3, size 2969 bytes.
- Diagnosis run (extra, same command through the wrapper): exit 1. First line
  `winnl: Windows text-mode writes use Linux line endings (newline='')`, then
  TypeError in claude_winnl_wrap.py line 35 (see smoke traceback below for the
  same error). This extra run is reported as a deviation; the registered plain
  run above is the one that produced the checkpoint.

## 3. Data and rival models (step 3, plain python as listed)

- Fetch command printed exactly one JSON line (counts and hashes only):
  {"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "1a44e3041355e7fcc1e4d2b188dec0f2362a2ceb9820f62acd957b29909e3850", "gsm8k300_sha256": "073acc01184dc13caa732adf33fb9d69e049153549d8364401f4320ca0bc555b"}
  locomo_qa 1986, mmlu_sample 300, gsm8k_sample 300 as registered. Exit 0.
  DATA = C:/Users/benja/lis301/work/bm390/data2 (new folder, created).
- Rival paths (already downloaded, download nothing):
  - Q2DIR = C:\Users\benja\.cache\huggingface\hub\models--Qwen--Qwen3.5-2B\snapshots\15852e8c16360a2fea060d615a32b45270f8a8fc (exists)
  - L12DIR = C:\Users\benja\.cache\huggingface\hub\models--LiquidAI--LFM2.5-1.2B-Instruct\snapshots\0f604ada3f766f9f257460c4c9f0b5d6f69d431b (exists)
- Load checks (each separately, HF_HUB_OFFLINE=1, to cuda, dtype bfloat16): both RUN.
  - Q2: Qwen3_5ForCausalLM 1881825088, exit 0.
  - L12: Lfm2ForCausalLM 1170340608, exit 0.

## 4. Smoke on made-up data (step 4, both through W): FAIL

Smoke data: artifacts/claude-bm390-20260925/smoke (fictional people, not a benchmark).
OUT = C:/Users/benja/lis301/work/bm390/smoke2 (never created; both commands crashed
before mkdir). SLEEPCHECK_LOG = C:/Users/benja/lis301/work/bm390/smoke2/sleep_P.jsonl
(never created).

- P (agent arm through W + sleepcheck wrap): exit code 1. No "wrote ..." line.
  Start 2026-09-25 06:39:58.313 UTC, end 2026-09-25 06:39:58.495 UTC (0.2 s).
  First printed line: `winnl: Windows text-mode writes use Linux line endings (newline='')`.
  Second line: `sleepcheck: logging every sleep to C:/Users/benja/lis301/work/bm390/smoke2/sleep_P.jsonl; stop on missing checkpoint = True`.
  Then the TypeError traceback below (load_locomo read_text, before any turn).
- T (plain arm through W): exit code 1. No "wrote ..." line.
  Start 2026-09-25 06:40:21.018 UTC, end 2026-09-25 06:40:21.110 UTC (0.1 s).
  First printed line: `winnl: Windows text-mode writes use Linux line endings (newline='')`.
  Then the identical TypeError traceback below.
- sleep_P.jsonl: 0 rows; the file was never created. Rows with checkpoint_exists
  true: 0. Rows with attempted true: 0.
- Files under smoke2: 0 files (folder does not exist). Count of "\r\n" in every
  file under smoke2: n/a (0 files, byte count 0 by vacuity).
- Required bar (both exit 0 with rows=5, sleep log 2 rows both checkpoint_exists
  true, 0 "\r\n"): NOT met. Stopped with SMOKE-FAIL; nothing ran on real data.
- Each smoke command was launched ONCE; process list checked before any retry
  (no python processes remained); no retries were made.

### Exact error and full traceback (P smoke; T smoke identical except target lines)

P console stdout (3 lines): SMOKE-P-START marker, the winnl line, the sleepcheck
line. P stderr in full:

```
Traceback (most recent call last):
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 63, in <module>
    main()
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 59, in main
    runpy.run_path(target, run_name="__main__")
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 289, in run_path
    return _run_module_code(code, init_globals, run_name,
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 96, in _run_module_code
    _run_code(code, mod_globals, init_globals,
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "scripts/claude_sleepcheck_wrap.py", line 66, in <module>
    main()
  File "scripts/claude_sleepcheck_wrap.py", line 62, in main
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
  File "scripts/claude_bm390.py", line 423, in run_locomo
    convs = load_locomo(Path(args.data), args.convs)
  File "scripts/claude_bm390.py", line 225, in load_locomo
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1134, in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1119, in open
    return self._accessor.open(self, mode, buffering, encoding, errors,
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 35, in _open
    if newline is None and "b" not in mode and _WRITES & set(mode):
TypeError: argument of type 'WindowsPath' is not iterable
```

T console stdout (2 lines): SMOKE-T-START marker, the winnl line. T stderr in full:

```
Traceback (most recent call last):
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 63, in <module>
    main()
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 59, in main
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
  File "scripts/claude_bm390.py", line 423, in run_locomo
    convs = load_locomo(Path(args.data), args.convs)
  File "scripts/claude_bm390.py", line 225, in load_locomo
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1134, in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1119, in open
    return self._accessor.open(self, mode, buffering, encoding, errors,
  File "C:\Users\benja\lis301\work\bm390\tree2\scripts\claude_winnl_wrap.py", line 35, in _open
    if newline is None and "b" not in mode and _WRITES & set(mode):
TypeError: argument of type 'WindowsPath' is not iterable
```

Diagnosis (one note, code not edited): scripts/claude_winnl_wrap.py replaces
builtins.open and io.open with a Python function _open(file, mode, ...). On
BensPC Python 3.10, pathlib captures io.open at import time
(class _NormalAccessor: open = io.open). A builtin captured this way stays
unbound, but a Python function captured this way binds as a method, so after
the wrapper runs and pathlib is first imported (fresh process, target imports
pathlib after apply), Path.open calls _open with (accessor, path, ...) and
`mode` receives a WindowsPath, hence `"b" not in mode` raises TypeError on the
very first Path.read_text (here load_locomo's locomo10.json, before any model
load or turn). The same wrapper through the same path breaks step 2's wrapped
diagnosis run at torch import (tqdm version lookup reads METADATA via pathlib).
The AMEND's Linux test ran Python 3.11 and its unit test pre-imported pathlib,
so neither hit this path. The sealed turn-log/notebok read-back issue was never
reached.

## 5. Registered arms (step 5): none launched

- No lane-1 and no lane-2 command was started. No run/*.jsonl file exists on
  BensPC (run/ was never created in tree2). Row count of every run/*.jsonl:
  n/a (0 files). Count of "\r\n" in every run/ file: n/a (0 files).
- run/sleep_P.jsonl: does not exist. Rows: n/a. Rows with checkpoint_exists
  true: n/a. Rows with attempted true: n/a.
- Lane 2 parallel or after: neither (stopped at smoke).

## 6. Copy-back (step 6)

- run/ did not exist on BensPC, so there was nothing to copy back and no
  size/sha256 check to perform. Downloaded models and data were left on BensPC
  as instructed. BensPC smoke2/ was never created (0 files). Tree2, data2 and
  r44b were left on BensPC.

## 7. Setup notes (inputs verified, counts only)

- Tree: git archive origin/builder-outbox, then origin/main on top, plus
  self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match),
  copied to NEW folder C:/Users/benja/lis301/work/bm390/tree2. First attempt's
  tree left as is. Tree2 seal files present before step 1.
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe 3.10.9. Env on every
  command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
  (plus SLEEPCHECK_STOP=1 SLEEPCHECK_LOG for P smoke).
- READER C:/Users/benja/lis301/work/run/merged model.safetensors sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- BASE snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc present.
- MiniLM route122 check from tree2 root prints a route (D8, conf 0.9732), no error.
- pyarrow 25.0.1 imports, no error. Nothing installed or upgraded.
- GPU: NVIDIA GeForce RTX 5070 Ti, 16303 MiB total, driver 591.86, CUDA 13.1;
  idle before and after (599 MiB used, 0% util, 8.75 W). No other GPU job was
  running (one job at a time kept).
- No benchmark question, answer, or reply is quoted anywhere in this file;
  only counts, hashes, paths, timings, and the tracebacks above.
