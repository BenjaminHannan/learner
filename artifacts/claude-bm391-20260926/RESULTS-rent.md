# RESULTS-rent.md: rent-bm391, public-benchmark scorecard run (2026-09-26)

Verdict: BUDGET-STOP. No registered scorecard. Only 1 of 9 registered commands finished
(lane-3 mmlu_R, 300 rows). The agent arms run ~2 rows/min on LoCoMo, so 3 x 1986-row
runs (~14 h per arm) cannot fit in the $3.50 budget. Partial EP382 logs for ER (457 rows)
and E (446 rows) plus the finished mmlu_R (300 rows) were copied back. Counts only below.
No question, answer or reply is quoted.

## Credit gate

`vastai show user --raw` credit at gate: 9.058110260469903 (>= $4.00, proceeded).
Credit after destroy: 7.48771440146988.

## Duplicate gate

origin/builder-outbox had no artifacts/claude-bm391-20260926/run and no
artifacts/claude-bm391-20260926/RESULTS-rent.md. `vastai show instances` showed one live
instance labelled rent-382b (id 52674739), not rent-bm391. No duplicate; proceeded.

## Code tree (kit section A)

Tree = `git archive origin/builder-outbox` + `git archive origin/main` on top, plus
self122_head.pt (sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25, OK).
READER = ~/premonition-models/lis301-merged/ (model.safetensors sha256
b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890, verified on Mac and
on the box after upload).
OUT = artifacts/claude-bm391-20260926/run (new folder). DATA = /root/bm391data.
WORK = /root/bm391work.

## Rental

- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. Instance id 52677751, label rent-bm391,
  offer 52604857. Image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel, disk 100.
- Rented 2026-09-26T01:51:26Z, running within ~5 min (inside the 6-min rule, 1 rental).
- dph $0.5102962962962964. Destroyed 2026-09-26T08:03:50Z. Billed duration 6.21 h.
  Projected dollars 6.21 x 0.5103 = ~$3.17. Billed credit diff $1.57 (billing may lag).
  Budget $3.50 not exceeded; money-rule $3.20 stop executed on projection.
- Post-destroy `vastai show instances`: 0 instances (the unrelated rent-382b instance
  seen at gate time was also gone; I destroyed only 52677751).
- Peak GPU memory used seen: 16933 MiB. 11 GiB+ free confirmed at lane-3 start
  (20384 MiB free = 19.9 GiB).

## Setup on the rental

- pip line per kit plus pyarrow (pyarrow import OK afterwards). Nothing else installed.
- `python -c "import torch, transformers; print(torch.__version__, transformers.__version__)"`:
  2.8.0+cu128 5.17.0.
- `unset HF_HOME HF_HUB_CACHE` done. With HF_HUB_OFFLINE=0 for the one download command:
  - BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  - MiniLM = /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41
    (exactly the required path; no MINILM-PATH stop).
- `export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1` for everything after.
- route122 check: no raise; returned
  ('D8', {'top1': 'D8', 'conf': 0.9732, 'margin': 3.595, 'top3': [('D8', 14.24), ('OOS', 10.65), ('C2', 3.32)], 'tau': 0.6, 'mu': 1.5, 'guard': 'pass'}).
- Every command ran under nohup/setsid with its own log file.

## Step 1: seals and selftests (all OK)

- `sha256sum -c artifacts/claude-bm391-20260926/SEAL.sha256.txt`: 3/3 OK (PLAN.md,
  baselines.sha256.txt, scripts/claude_bm391_prf.py), exit 0.
- `sha256sum -c artifacts/claude-bm390-20260925/SEAL-code.sha256.txt`: 8/8 OK, exit 0.
- `sha256sum -c artifacts/claude-e2e382-20260925/SEAL-code.sha256.txt`: 239/239 OK, exit 0.
- `python -B scripts/claude_e2e382_test.py`: "claude_e2e382_test: 10/10 OK", exit 0.
- `python -B scripts/claude_e2e383_test.py`: "claude_e2e383_test: 13/13 OK", exit 0.

## Step 2: Sleep base checkpoint

- `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out /tmp/r44` printed:
  {"stage": "base", "seed": 4102, "seconds": 37.0, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- Copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt on the box.
  sha256: 2ada54ac81544b399c60cf5a574517387b58ea43bdf04d7d93f7d2c9ff069057.
  (Kept on the rental only; destroyed with the box. Not in the step-6 copy list.)

## Step 3: fetch (verbatim line)

{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}

locomo_qa 1986, mmlu300 and gsm8k300 hashes match the pinned values. No stop.

## Step 4: smoke on made-up data (SD = artifacts/claude-bm390-20260925/smoke, WORK/smoke)

All 6 exit 0 with wrote lines:

| # | Command | Start (UTC) | End (UTC) | Exit | Last wrote line |
| Es locomo | agent:claude_e2e382:build_382b --limit-q 2 | 2026-09-26T04:26:46Z | 2026-09-26T04:27:29Z | 0 | wrote locomo_Es.jsonl rows=2 convs=1 |
| Es gsm8k | agent:claude_e2e382:build_382b --limit 2 | 2026-09-26T04:27:29Z | 2026-09-26T04:27:48Z | 0 | wrote gsm8k_Es.jsonl rows=2 |
| Rs locomo | agent:claude_e2e383:build_383 --limit-q 2 | 2026-09-26T04:27:48Z | 2026-09-26T04:28:28Z | 0 | wrote locomo_Rs.jsonl rows=2 convs=1 |
| Rs gsm8k | agent:claude_e2e383:build_383 --limit 2 | 2026-09-26T04:28:28Z | 2026-09-26T04:28:53Z | 0 | wrote gsm8k_Rs.jsonl rows=2 |
| ERs locomo | agent:claude_e2e383:build_383e --limit-q 2 | 2026-09-26T04:28:53Z | 2026-09-26T04:29:32Z | 0 | wrote locomo_ERs.jsonl rows=2 convs=1 |
| ERs gsm8k | agent:claude_e2e383:build_383e --limit 2 | 2026-09-26T04:29:32Z | 2026-09-26T04:29:56Z | 0 | wrote gsm8k_ERs.jsonl rows=2 |

Smoke files went to WORK/smoke per the task (not OUT); step 6 required only OUT, so smoke
jsonl files were not copied back (deviation, recorded here). Exit codes and wrote lines above.

## Step 5: registered commands

Pace finding: each LoCoMo arm sustained ~2 rows/min (~25 s/question: per-question agent
rebuild + turn with READER and BASE; models cached per process, GPU spiky 0-17%, work is
largely sequential per question). 1986 rows need ~14 h per arm: infeasible in budget.
Lanes 1+2 started together 2026-09-26T04:31:34Z. Lane 3 started 2026-09-26T05:56:35Z after
both lanes printed their first [bm390] line with 20384 MiB (19.9 GiB) free. No command was
relaunched; `ps` was checked before every launch.

| # | Command | Start (UTC) | End (UTC) | Exit | First printed line | Last wrote line |
| L1 | LOCOMO(claude_e2e383:build_383e, ER) | 2026-09-26T04:31:34Z | 2026-09-26T07:58:24Z | 143 (SIGTERM, budget) | sleepcheck: logging every sleep to artifacts/claude-bm391-20260926/run/sleep_ER.jsonl; stop on missing checkpoint = True | [bm390] conv-41 turns=696 questions=193 (no locomo_ER.jsonl wrote line; unfinished) |
| L2 | LOCOMO(claude_e2e382:build_382b, E) | 2026-09-26T04:31:34Z | 2026-09-26T07:58:24Z | 143 (SIGTERM, budget) | sleepcheck: logging every sleep to artifacts/claude-bm391-20260926/run/sleep_E.jsonl; stop on missing checkpoint = True | [bm390] conv-41 turns=696 questions=193 (no locomo_E.jsonl wrote line; unfinished) |
| L3a | GENERAL(mmlu, claude_e2e383:build_383, R) | 2026-09-26T05:56:35Z | 2026-09-26T06:49:52Z | 0 | [transformers] `torch_dtype` is deprecated! Use `dtype` instead! | wrote mmlu_R.jsonl rows=300 |
| L3b | GENERAL(gsm8k, claude_e2e383:build_383, R) | 2026-09-26T06:49:52Z | 2026-09-26T07:58:24Z | 143 (SIGTERM, budget) | [transformers] `torch_dtype` is deprecated! Use `dtype` instead! | (no wrote line; unfinished, no gsm8k_R.jsonl) |

Finished registered commands: L3a only.
Unfinished (partial output copied back): L1, L2. Unfinished (no output): L3b.
Never started: GENERAL(mmlu,383e,ER), GENERAL(gsm8k,383e,ER), GENERAL(mmlu,382b,E),
GENERAL(gsm8k,382b,E), LOCOMO(383,R) beyond the stub below.

Kill-window deviation (reported, not a relaunch): killing the three running pythons took
effect at 07:58:24Z; before the lane-driver shells were killed, each driver auto-advanced
and launched its lane's next command. Those three stubs ran ~30 s, wrote no output files,
and were killed by exact PID (3277 lane3-locomo-R, 3279 lane1-mmlu-ER, 3281 lane2-mmlu-E).
Their logs end at weight-loading lines; no wrote lines; not relaunched. Lane drivers then
killed (PIDs 2612, 2613, 2999). Final `ps` count of matching processes: 0.

## Step 6: copy back, destroy, ledger

Copied back OUT (5 files), sha256 verified identical box-vs-Mac, then destroyed 52677751,
confirmed 0 instances, appended the ledger line.

| File | Bytes | sha256 |
| ep382_ER_locomo.jsonl | 156295 | b576dd6777fe875feacf4fb9eeadb6a1703567fca9f26e8682277208b40cd25f |
| ep382_E_locomo.jsonl | 152582 | dbb00749595ce58a812fc37affe013721bf01987e7c267ea08ba5838e2193d46 |
| mmlu_R.jsonl | 103469 | 4660101142a21c0313b9d876753e2e70efe717bd8bd39faeb9534c23b526dfa8 |
| sleep_E.jsonl | 17919 | 6612f8eed428ef22db7004a7dbc4cf674f0d0ca4688f95476b25fb90183ccdef |
| sleep_ER.jsonl | 17919 | 8c47dcbe48fefffbd00f90821ab8545a4db4051adc3add11c8b79c8191c8afa8 |

No locomo_*.jsonl, no *_reading files, no ep382_R_gsm8k/mmlu, no sleep_R, no gsm8k files:
the killed commands never reached their wrote lines.

Row counts of every run/*.jsonl file (this checkout):

| File | Rows |
| ep382_ER_locomo.jsonl | 457 |
| ep382_E_locomo.jsonl | 446 |
| mmlu_R.jsonl | 300 |
| sleep_E.jsonl | 99 |
| sleep_ER.jsonl | 99 |

Per EP382 log (rows; counts per "outcome"):

| File | Rows | outcome counts |
| ep382_ER_locomo.jsonl | 457 | replaced 396, all_failed 61 |
| ep382_E_locomo.jsonl | 446 | replaced 387, all_failed 59 |

Per sleep log (rows; checkpoint_exists true):

| File | Rows | checkpoint_exists true |
| sleep_E.jsonl | 99 | 99/99 |
| sleep_ER.jsonl | 99 | 99/99 |

## Tracebacks and errors (full)

1. Step-3 first launch failed with: `python: can't open file '/root/scripts/claude_bm390.py':
   [Errno 2] No such file or directory`. Cause: my ssh wrapper grouped `cd /root/tree`
   with the first backgrounded command only, so the second ran from /root. No code fault.
   Relaunched unchanged (correct cwd); fetch then printed the OK line above. Reported as deviation.
2. setup_pip.log contains one expected ModuleNotFoundError for pyarrow before its install
   in the same command chain (traceback: `ModuleNotFoundError: No module named 'pyarrow'`);
   `pip install -q pyarrow` then ran and `import pyarrow` verified OK.
3. No traceback in any smoke, lane, step1, step2 or fetch log. Killed commands exited 143
   (SIGTERM); no crash, no relaunch.

## Other deviations

- OPUS-RULES.txt path from the lis-302 header does not exist on this Mac (empty scratchpad
  dir); followed the task text's additive-only/fictional-names/TEST-ONLY/ledger rules instead.
- READER upload: single-stream rsync was ~179 KB/s; 4 parallel scp streams tripped the ssh
  proxy ("Connection closed by remote host"); 2 streams with retries delivered 41 x 40 MB
  chunks, reassembled md5-identical, sha256-verified. No code or data changed.
- handoff/held/rent-bm391.md does not exist on origin/main; rented per the task's own
  GPU/BUDGET lines (RTX 5090 first, $3.50 budget).
- Killed at projected $3.12 (6.11 h x $0.5103) approaching the $3.20 money-rule line;
  billed credit diff at destroy was $1.57 (billing may lag).

## What this means

- The three Premonition 0.2 candidates got no registered LoCoMo/MMLU/GSM8K numbers from
  this rental: 1/9 commands finished. B1-B9 and M1/M3/M4 cannot be judged from this run.
- What exists: 300 finished mmlu_R rows (R arm) plus partial EP382 traces (ER 457, E 446
  question-attempt rows with outcome counts; 99+99 sleep rows, all checkpoint_exists true).
- Lesson for a retry: at ~2 LoCoMo rows/min/arm, one RTX 5090 needs ~14 h per arm (~42 h
  for three lanes), i.e. roughly a $20+ budget, or a faster per-question path. The general
  tests are the cheap part (mmlu_R finished in 53 min including model load).
