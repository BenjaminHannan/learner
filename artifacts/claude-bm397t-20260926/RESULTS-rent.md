# rent-bm397t RESULTS-rent (GPU rental, benchmarks thread task 2026-09-26)

Label: rent-bm397t. Counts only. No question, answer or reply is quoted.
Nothing was trained on any benchmark. No file was edited (scripts run, never edited).

## Credit gate
- `vastai show user --raw` credit: 7.337024797469866 (balance 0). Above $3.00, proceeded.

## Duplicate gate
- origin/builder-outbox has no artifacts/claude-bm397t-20260926/run and no
  artifacts/claude-bm397t-20260926/RESULTS-rent.md (grep bm397t empty).
- `vastai show instances` at start: 52677751 rent-bm391, 52683743 02c-dev,
  52683960 rent-brd6. No live instance labelled rent-bm397t. Proceeded.

## Rental (kit section B)
- Filter: gpu_name=RTX_5090 reliability>=0.98 rentable=true, -o dph; >=8 CPU,
  >=60 GB disk; prefer up/down >=200 Mbps.
- Rental 1: id 52684428, offer 45669313, RTX 5090, dph 0.5037037037037037.
  Created 2026-09-26 03:07:13 UTC, running ~03:07:43 (within 6-min rule).
  SSH proxy (ssh9.vast.ai:14428) rejected every registered key; two other live
  instances accepted the same key at the same time. Destroyed ~03:18:05 UTC,
  ~0.181 h x $0.5037 = ~$0.091, $0 result data. No requeue issue (nothing ran).
- Rental 2: id 52685550, offer 44188476, RTX 5090, dph 0.5037037037037037,
  disk 80 GB, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime,
  South Korea KR. Created 2026-09-26 03:18:22 UTC, running 03:20:51 UTC
  (within 6-min rule). SSH OK (ssh7.vast.ai:15550). GPU NVIDIA GeForce RTX 5090.
  Destroyed 2026-09-26 04:23:49 UTC, ~1.091 h x $0.5037037 = ~$0.5495.
- Task total: 2 rentals (max 4, HOST-FAIL not triggered), ~1.272 h, ~$0.64
  of $1.40 budget. No BUDGET-STOP, no watchdog destroy (every poll showed new
  log lines), hard stop 10:35 UTC never approached. Post-destroy
  `vastai show instances` confirms 0 rent-bm397t live.
- Running total was kept throughout; at no point did projected spend exceed $1.40.

## Tree (kit section A, task variant)
- `git fetch -q origin main builder-outbox` OK. Tree = `git archive
  origin/builder-outbox` then `git archive origin/main` on top (main wins).
  self122_head.pt not needed and not copied. tree.tgz 184673336 bytes.
  Upload via scp/rsync --partial to /root/tree.tgz (slow proxy link, resumed
  to 100%), extracted to /root/tree. OUT = /root/tree/artifacts/
  claude-bm397t-20260926/run (NEW folder). DATA = /root/bm397tdata.
  WORK = /root/bm397twork. MERGED was never copied back (2.1 GB).

## Box setup (ONLY downloads allowed)
- Image torch: 2.8.0+cu128, cuda available True.
- pip: kit line `pip install -q "transformers>=5" safetensors huggingface_hub
  accelerate numpy` plus `python -c "import pyarrow" || pip install -q pyarrow`
  (pyarrow was missing, installed 25.0.1). Nothing else installed.
- `python -c "import torch, transformers; print(torch.__version__,
  transformers.__version__)"`: 2.8.0+cu128 5.17.0.
- Box python: 3.11.13.
- `unset HF_HOME HF_HUB_CACHE`, one offline=0 command:
  snapshot_download('openbmb/MiniCPM5-1B',
  revision='87179e5c1f455ef22e6223592d2d61351b525bfc').
- BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- Then `export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1`
  for everything else. Every rental command ran under setsid/nohup with its own
  log file in /root/bm397twork/logs/.

## Step 1: seals + selftests (from tree root)
- `sha256sum -c artifacts/claude-bm397t-20260926/SEAL.sha256.txt`: 10/10 OK
  (PLAN.md, claude_bm397t_data.py, claude_bm397t_train.py, claude_bm397t_judge.py,
  claude_bm397_judge.py, claude_blurt2.py, claude_bm390.py, claude_bm390_score.py,
  claude_bm396_audit.py, claude_bm391_prf.py).
- `sha256sum -c artifacts/claude-bm390-20260925/SEAL-code.sha256.txt`: 8/8 OK
  (claude_bm390.py, claude_bm390_score.py, PASSMARKS.md, data-manifest.json,
  smoke locomo10.json, smoke mmlu300.jsonl, smoke gsm8k300.jsonl,
  390-public-bench-plan.md).
- `python -B scripts/claude_bm397t_data.py selftest`: ends
  "BM397T-DATA-SELFTEST PASS 8/8".
- `python -B scripts/claude_bm397t_train.py selftest`: ends
  "BM397T-TRAIN-SELFTEST PASS 5/5".
- No SEAL-MISMATCH. Deviation: the first train-selftest launch used a wrapper
  without an absolute cd and failed with "can't open file
  '/root/scripts/claude_bm397t_train.py'"; it was relaunched once with
  `bash -c 'cd /root/tree && ...'` unchanged script and passed. Reported here.

## Step 2: fetch
- `python -B scripts/claude_bm390.py fetch --data /root/bm397tdata` printed
  exactly (verbatim):
{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}
- Hashes match the task (locomo_qa 1986,
  mmlu300 e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049,
  gsm8k300 df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949).

## Step 3: practice data (code-made, fictional names)
- `python -B scripts/claude_bm397t_data.py --seed 3970 --convs 180 --out
  /root/bm397twork/train.jsonl`: {"rows": 1800, "kinds": {"single": 1080,
  "list": 360, "when": 360}}.
- `python -B scripts/claude_bm397t_data.py --seed 3971 --convs 20 --out
  /root/bm397twork/dev.jsonl`: {"rows": 200, "kinds": {"single": 120,
  "when": 40, "list": 40}}.
- sha256 train: 0654bd2f60ac002d1465cc55a45cd462bd8b68be8d9c7606c2894b7856f06237
  (matches). sha256 dev:
  675a2d854153700c80eee701a290cb4b2c39c58a4dd2065640b56caa67942da9 (matches).
- Box `python --version`: Python 3.11.13. No DATA-MISMATCH.

## Step 4: train once
- Command: `python -B scripts/claude_bm397t_train.py --base BASE --train
  /root/bm397twork/train.jsonl --dev /root/bm397twork/dev.jsonl --out
  /root/bm397twork/t397`. Launched once ~03:53 UTC, finished same hour.
- Printed JSON lines (verbatim, progress-bar lines omitted):
{"dev_before": {"n": 200, "right": 116, "by_kind": {"list": "19/40", "single": "90/120", "when": "7/40"}, "median_words": 6.0}}
{"step": 25, "loss": 0.1563, "s": 41}
{"step": 50, "loss": 0.021, "s": 55}
{"step": 75, "loss": 0.0306, "s": 70}
{"step": 100, "loss": 0.4272, "s": 85}
{"step": 125, "loss": 0.0044, "s": 100}
{"step": 150, "loss": 0.0081, "s": 115}
{"step": 175, "loss": 0.0025, "s": 129}
{"step": 200, "loss": 0.0556, "s": 144}
{"step": 225, "loss": 0.0029, "s": 159}
{"dev_after_lora": {"n": 200, "right": 199, "by_kind": {"list": "40/40", "single": "120/120", "when": "39/40"}, "median_words": 2.0}}
{"dev_after_merged": {"n": 200, "right": 199, "by_kind": {"list": "40/40", "single": "120/120", "when": "39/40"}, "median_words": 2.0}}
{"steps": 225, "loss_first10": 0.7709, "loss_last10": 0.078, "lora_params": 4128768, "merged_layers": 96, "seconds": 189.7}
- Final line has "steps": 225. MERGED = /root/bm397twork/t397/merged
  (model.safetensors sha256
  9719c266db9bb9d4ffe41ed7bbcb6d5952e948b80db7c25731b08448923a8e3a).
- train397t.json full content on box (1012 bytes, sha256
  0919dac923f153ca0e40839beb4a98130b06151b6afa3609432c8749677eecfa):
  dev_before n 200 right 116 (list 19/40, single 90/120, when 7/40)
  median_words 6.0; steps 225; loss_first10 0.7709; loss_last10 0.078;
  lora_params 4128768; dev_after_lora n 200 right 199 median_words 2.0;
  merged_layers 96; dev_after_merged n 200 right 199 median_words 2.0;
  merged_files model.safetensors 9719c266...; seconds 189.7;
  adapter_sha256 621edd1631072a152f77c83cd1967ac811d1a3d80c66fa9a85bd576af88f7233.
- Copied /root/bm397twork/t397/train397t.json to OUT/train397t.json.

## Step 5: registered scoring (each launched once; ps checked before the one
  ordered Lane-2 follow-up; no crash, so no relaunch)
- Lane 1 locomo: `python -B scripts/claude_bm390.py locomo --data
  /root/bm397tdata --arm plain:/root/bm397twork/t397/merged --name TS --out
  .../run`. Start 2026-09-26 03:58:27 UTC. End: output file mtime
  2026-09-26 04:19:12 UTC (log tail read 04:22:03 UTC). Exit code 0
  (process exited; wrote line present; zero traceback lines in log).
  First content line: `[bm390] conv-26 plain questions=199`.
  Last line: `wrote locomo_TS.jsonl rows=1986 convs=10`.
- Lane 2a mmlu: `python -B scripts/claude_bm390.py general --task mmlu --data
  ... --arm plain:.../merged --name TS --out .../run`. Start 2026-09-26
  03:58:27 UTC (together with Lane 1). End: file mtime 2026-09-26 03:58:42 UTC.
  Exit code 0 (same basis). First content line: `wrote mmlu_TS.jsonl rows=300`
  (only content line besides the weight-loading bar). Last line: identical
  `wrote mmlu_TS.jsonl rows=300`.
- Lane 2b gsm8k: `python -B scripts/claude_bm390.py general --task gsm8k
  --data ... --arm plain:.../merged --name TS --out .../run`. Start
  2026-09-26 04:00:35 UTC (after mmlu process was gone). End: file mtime
  2026-09-26 04:03:18 UTC. Exit code 0 (same basis). First/last content line:
  `wrote gsm8k_TS.jsonl rows=300`.
- Exit-code note: the setsid/nohup wrappers did not capture `$?` to a file;
  0 is inferred from clean exit + wrote line + `grep -c traceback = 0` on all
  three logs. No relaunch was needed for any lane.

## OUT files (copied back before destroy; sizes+sha256 match the box)
- locomo_TS.jsonl: 1986 rows, 276376 bytes, sha256
  30eb5dc4fe6b15999222500d683c05b71c1ba234f94880c79cb0255eea3f0f9e
- mmlu_TS.jsonl: 300 rows, 18933 bytes, sha256
  fa830d3283a49407d0aa27260ddfdf736fefb1cd31d035855dec95c4fe002257
- gsm8k_TS.jsonl: 300 rows, 57772 bytes, sha256
  c6bb2f1497f1e3fdfb6b20b76acfca2c0afd44e73bc21337b7cc2e37da5165a1
- train397t.json: 1012 bytes, sha256
  0919dac923f153ca0e40839beb4a98130b06151b6afa3609432c8749677eecfa
- Total OUT rows: 2586.

## Adapter (not pushed)
- /root/bm397twork/t397/adapter397t.pt: 16576151 bytes (~15.8 MB),
  sha256 621edd1631072a152f77c83cd1967ac811d1a3d80c66fa9a85bd576af88f7233.
- Copied to ~/premonition-models/bm397t-adapter397t.pt (same size+sha256).
  MERGED (2.1 GB) was not copied back per the task.

## Resources
- GPU: NVIDIA GeForce RTX 5090, 32607 MiB total. Peak used seen: 5074 MiB
  (also 4154 MiB during early scoring; 1 MiB idle after runs).
- No scoring or audit was run here; the benchmarks thread scores on CPU.

## Tracebacks
- None. `grep -ci traceback` = 0 on all 10 box logs (seals, data_selftest,
  train_selftest, fetch, data_train, data_dev, train, locomo_TS, mmlu_TS,
  gsm8k_TS).

## Deviations and misses
- Train-selftest first launch failed on the wrapper cwd (reported above);
  script unchanged, relaunched once, PASS 5/5.
- Rental 1 destroyed for broken SSH proxy (reported above); 1 extra rental,
  ~$0.09.
- Slow proxy upload needed rsync --partial resume (no extra download, same file).
- Exit codes inferred as 0 as documented (no traceback, wrote lines present).
- lis-302 common rules followed: additive only (new run/ files + new
  RESULTS-rent.md + ledger append + out-of-repo adapter copy; no existing file
  edited), fictional names only in code-made data, and this report is the
  final-reply report.
