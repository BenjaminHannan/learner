# rent-bm398r RESULTS-rent (GPU rental, 2026-09-26)

Registered runs of the Benchmarks thread: Part 1 = bm-398i GPU check (adapter on/off
switch, nothing trained), Part 2 = bm-398r (train one reader adapter on code-made
practice, then produce its replies). Code run unmodified; counts only; no question,
answer or reply is quoted. Nothing scored here; the Benchmarks thread scores on its
own machine.

## Gates
- CREDIT GATE: `vastai show user --raw` credit = 6.357862396269859 (>= 1.50, proceed).
- DUPLICATE GATE: origin/builder-outbox had no artifacts/claude-bm398r-20260926/run
  and no artifacts/claude-bm398r-20260926/RESULTS-rent.md; `vastai show instances`
  showed no live instance labelled claude-benchmarks-bm398r. Proceed.

## Rental
- Label: claude-benchmarks-bm398r. GPU filter: RTX 5090, reliability >= 0.98.
- Rental 1: contract 52766092, offer 43690890 (US), dph ~0.5378. Never left
  "loading" (SSH connection refused); past the 6-min start rule, destroyed by exact
  id 15:07:28Z. $0.00, nothing ran, nothing copied.
- Rental 2: contract 52767015, offer 50135004 (KR), dph 0.5037037. Reached
  "running" ~3 min after create but its SSH proxy died (kex_exchange_identification:
  Connection closed by remote host, 4 attempts over ~5 min); destroyed by exact id
  15:15:24Z. $0.00, nothing ran, nothing copied.
- Rental 3: contract 52768265, offer 45668964 (KR, RTX 5090, rel 0.9899, 8 CPU,
  80 GB disk), image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, dph 0.5037037.
  Created 15:15:33Z, running + SSH OK 15:19:18Z, destroyed 16:33:27Z after verified
  copy-back. ~1.30 h x $0.5037037 = ~$0.65.
- Task total ~$0.65 of $1.50 budget (3 rentals of max 4). Money rule ($1.40) and
  time cap (2 h 45 min) never hit. Post-destroy: 0 claude-benchmarks-bm398r live.

## Setup
- Streamed to ~/tree per task: builder-outbox E20 file, then origin/main scripts +
  data-manifest + bm398i/bm398r dirs. No tree staged on the Mac.
- Adapter upload: ~/premonition-models/bm397t-adapter397t.pt -> /root/adapter397t.pt,
  16576151 bytes both sides, sha256 621edd1631072a152f77c83cd1967ac811d1a3d80c66fa9a85bd576af88f7233
  both sides (no ADAPTER-MISMATCH). Never pushed.
- pip: kit line (transformers>=5 safetensors huggingface_hub accelerate numpy) plus
  pyarrow (25.0.1). DEVIATION (env-only, no code edit): claude_bm398r_train.py imports
  claude_bm390_score, which needs nltk (PorterStemmer); first train launch crashed
  ModuleNotFoundError (traceback below, exit 1, /root/bmwork/r398 empty). Installed
  nltk 3.10.3 env-only (same precedent as rd-371's peft fix) and relaunched the
  identical command once. Nothing else installed.
- Versions: torch 2.8.0+cu128 (cuda True), transformers 5.17.0, python 3.11.13,
  pyarrow 25.0.1.
- BASE (HF_HUB_OFFLINE=0, one command):
  /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  (revision 87179e5c1f455ef22e6223592d2d61351b525bfc as expected).
- Everything else ran with HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  PYTHONUTF8=1 from ~/tree (absolute script paths), each command under
  nohup/setsid with its own log. DATA=/root/bmdata, WORK=/root/bmwork,
  OUTI=artifacts/claude-bm398i-20260926/run-gpu, OUT=artifacts/claude-bm398r-20260926/run,
  E20=artifacts/claude-bm395-20260925/run/locomo_E20.jsonl.

## Step 1: seals and selftests
- `sha256sum -c artifacts/claude-bm398i-20260926/SEAL.sha256.txt`: 5 OK, exit 0.
- `sha256sum -c artifacts/claude-bm398i-20260926/SEAL-amend1.sha256.txt`: 3 OK, exit 0.
- `sha256sum -c artifacts/claude-bm398r-20260926/SEAL.sha256.txt`: 13 OK, exit 0.
- `python -B scripts/claude_bm398i_switch.py selftest` ends "BM398I-SELFTEST PASS 9/9".
- `python -B scripts/claude_bm398r_data.py selftest` ends "BM398R-DATA-SELFTEST PASS 16/16".
- `python -B scripts/claude_bm398r_train.py selftest` ends "BM398R-TRAIN-SELFTEST PASS 6/6".
- E20 sha256: e7f70f5703768697709b2cf93197fdb18aa5b13a9a58caacf8becb9b60e7bcef (match).
- DEVIATION (launcher, no code edit): the first batch launch backgrounded `cd ~/tree`
  along with the command, so the rdata/rtrain selftests started in /root and failed
  instantly (can't open '/root/scripts/...'). Relaunched unchanged with absolute
  paths; all three selftests pass. No code edited.

## Step 2: fetch
- `python -B scripts/claude_bm390.py fetch --data /root/bmdata` printed verbatim:
{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}
- locomo_qa 1986, mmlu300 e294f5fc...f76c049, gsm8k300 df57d09b...8706b949 as required.

## Step 3: Part 1 (bm-398i), sequential fresh processes, --adapter /root/adapter397t.pt
- Run a (`--out OUTI/a`), start 2026-09-26T15:25:57Z, end 2026-09-26T15:30:18Z
  (files written 15:28Z), exit 0 (inferred: process gone, result.json +
  replies398i.jsonl written, log ends with the JSON line; no exit wrapper on this
  first launch). Verbatim final JSON line:
{"items": {"gsm8k": 15, "mmlu": 40, "locomo": 20}, "wrapped": 96, "adapter": {"kind": "file", "keys": 192, "sha256": "8e3702036f235e1068aac5f14bdcb034e0cd936d94569e1cb8666d42581c029f"}, "I1_off_equals_base": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I1_off_logits_max_abs_diff": 0.0, "I2_mixed_off_equals_base": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I2_mixed_on_equals_on": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I2_off_logits_after_mixing_max_abs_diff": 0.0, "I3_on_differs_from_base": {"gsm8k": "15/15", "mmlu": "33/40", "locomo": "20/20", "all": "68/75"}, "on_logits_max_abs_diff": 16.703125, "switches_between_requests": 149, "I1": true, "I2": true, "I3": true, "verdict": "PASS", "seconds": 146}
- Run b (`--out OUTI/b`), start 2026-09-26T15:30:33Z, end 2026-09-26T15:35:30Z
  (files written 15:32Z), exit 0 (recorded). Verbatim final JSON line:
{"items": {"gsm8k": 15, "mmlu": 40, "locomo": 20}, "wrapped": 96, "adapter": {"kind": "file", "keys": 192, "sha256": "8e3702036f235e1068aac5f14bdcb034e0cd936d94569e1cb8666d42581c029f"}, "I1_off_equals_base": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I1_off_logits_max_abs_diff": 0.0, "I2_mixed_off_equals_base": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I2_mixed_on_equals_on": {"gsm8k": "15/15", "mmlu": "40/40", "locomo": "20/20", "all": "75/75"}, "I2_off_logits_after_mixing_max_abs_diff": 0.0, "I3_on_differs_from_base": {"gsm8k": "15/15", "mmlu": "33/40", "locomo": "20/20", "all": "68/75"}, "on_logits_max_abs_diff": 16.703125, "switches_between_requests": 149, "I1": true, "I2": true, "I3": true, "verdict": "PASS", "seconds": 145}
- Pass log lines (run a): base 40 s, off 76 s, on 93 s, mixed 146 s.
  (run b): base 39 s, off 76 s, on 92 s, mixed 145 s.

## Step 4: Part 2 data
- train (`--part train --seed 3990 --convs 150`): exit 0, rows 1800,
  sha256 7e1ec3019fb73c55e39e1d3aebf27432b12b2a468ce0b1248ba7e9b9419af120 (match).
- dev (`--part dev --seed 3991 --convs 20`): exit 0, rows 240,
  sha256 1f0015461a13dd1ae18eba75089483810233c4c6d990c216c5a3e38727e9ba58 (match).

## Step 5: train once
- Command: `python -B scripts/claude_bm398r_train.py --base BASE --train
  WORK/train.jsonl --dev WORK/dev.jsonl --out WORK/r398`.
- First launch (start 15:36:29Z) crashed with exit 1 on missing nltk (traceback
  below); /root/bmwork/r398 stayed empty. After the env-only nltk install, the
  identical command relaunched once (start 2026-09-26T15:37:32Z, end
  2026-09-26T16:04:32Z), exit 0.
- dev_before line: {"dev_before": {"n": 240, "right": 114, ...}, "s": 62}.
- Step lines: step 1 then every 5 steps to step 225 (46 step lines).
  step-1 projected_train_s = 1534; step-10 projected_train_s = 1332.
  Full step-1 line: {"step": 1, "loss": 2.7735, "s": 7, "projected_train_s": 1534, "tokens": 71457}.
  Full step-10 line: {"step": 10, "loss": 0.6526, "s": 59, "projected_train_s": 1332, "tokens": 634093}.
  Full step-225 line: {"step": 225, "loss": 0.3588, "s": 1241, "projected_train_s": 1241, "tokens": 13367125}.
- dev_after_lora: {"n": 240, "right": 186, ...} (dev 114 -> 186, +72).
- dev_after_merged_first40: {"n": 40, "right": 28, ...}.
- Final line: {"steps": 225, "loss_first10": 1.1989, "loss_last10": 0.2003,
  "lora_params": 4128768, "merged_layers": 96, "train_seconds": 1241.3,
  "train_tokens": 13367125, "peak_gpu_mb": 7118, "seconds": 1374.0}.
- train398r.json contents: device cuda, dtype torch.bfloat16, train_rows 1800,
  dev_rows 240, recipe {rank 16, alpha 32, dropout 0.05, lr 0.0002, batch 8,
  epochs 1, seed 3992, checkpointing true, answer_only_logits true},
  lora_params 4128768, steps 225, train_seconds 1241.3, train_tokens 13367125,
  peak_gpu_mb 7118, loss_first10 1.1989, loss_last10 0.2003,
  adapter_sha256 f98c54a9cabc29cbc80995e571d232d69fcdd249ea859b5d0ad692ba7627cfdf,
  merged_layers 96, merged model.safetensors ed25ff6e602e93d81602de315dfdc0032fbea1d1c238387b0115fa362f66393d,
  seconds 1374.0.
- MERGED = WORK/r398/merged (model.safetensors 2161290944 bytes, sha above).
- Copied WORK/r398/train398r.json to OUT/train398r.json (sha match).
- Traceback of the first (nltk) crash, in full:
Traceback (most recent call last):
  File "/root/tree/scripts/claude_bm398r_train.py", line 272, in <module>
    sys.exit(main())
             ^^^^^^
  File "/root/tree/scripts/claude_bm398r_train.py", line 207, in main
    res["dev_before"] = dev_check(model, tok, dev, devrows)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/tree/scripts/claude_bm398r_train.py", line 93, in dev_check
    by[key][0] += int(right(reply, r))
                      ^^^^^^^^^^^^^^^
  File "/root/tree/scripts/claude_bm398r_train.py", line 72, in right
    import claude_bm390_score as S
  File "/root/tree/scripts/claude_bm390_score.py", line 28, in <module>
    from nltk.stem import PorterStemmer
ModuleNotFoundError: No module named 'nltk'

## Step 6: scored runs (each launched once; `ps` checked before every later launch)
- Lane 1: `python -B scripts/claude_bm390.py locomo --data DATA
  --arm plain:MERGED --name TR --out OUT`. Start 2026-09-26T16:05:36Z, end
  2026-09-26T16:32:24Z (file written 16:26Z), exit 0. Last line:
  "wrote locomo_TR.jsonl rows=1986 convs=10".
- Lane 2a: `.../claude_bm398r_eval.py evidence --data DATA --e20 E20 --model MERGED
  --name R --out OUT`. Start 2026-09-26T16:05:36Z, end 2026-09-26T16:10:57Z,
  exit 0. Last lines: "wrote locomo_GR.jsonl rows=297",
  "wrote locomo_GDR.jsonl rows=297", "wrote locomo_E20R.jsonl rows=297".
- Lane 2b: same with `--model BASE --name B`. Start 2026-09-26T16:11:02Z, files
  written 16:13Z, exit 0 observed 16:18:17Z. Last lines:
  "wrote locomo_GB.jsonl rows=297", "wrote locomo_GDB.jsonl rows=297",
  "wrote locomo_E20B.jsonl rows=297".
- Lane 2c: `.../claude_bm390.py general --task mmlu --data DATA --arm plain:MERGED
  --name TR --out OUT`. Start 2026-09-26T16:18:17Z, file written 16:18Z, exit 0
  observed 16:25:12Z. Last line: "wrote mmlu_TR.jsonl rows=300".
- Lane 2d: same with `--task gsm8k`. Start 2026-09-26T16:25:12Z, file written
  16:25Z, end 2026-09-26T16:32:24Z, exit 0. Last line: "wrote gsm8k_TR.jsonl rows=300".
- No relaunch was needed in step 6 (every command wrote its files first try).

## Files (row counts by `wc -l`, sha256; Mac copies match the box exactly)
- OUT/gsm8k_TR.jsonl: 300 rows, 17552 B, 826a5168cac7da7a2d87712d8417f90afe87a8a87e5147a74fee4105466b22e9
- OUT/locomo_E20B.jsonl: 297 rows, 70204 B, bd19c66d84357503cfb83313c5ad03352d1934c633563a0c5163b032cc141b80
- OUT/locomo_E20R.jsonl: 297 rows, 65023 B, fc3fb115fba1cd2a3e4ea03ac25d0b10e52f9981f896be8e0a4a535baa84229b
- OUT/locomo_GB.jsonl: 297 rows, 39235 B, e1e37fb20081391cdb5e39c8beb41484b6201756c7b20bb92ffe8793d00d28ca
- OUT/locomo_GDB.jsonl: 297 rows, 70207 B, af9f49b8121172e33244b830ef23c2600c6c1e3dbcc97d6d58d2789e48847306
- OUT/locomo_GDR.jsonl: 297 rows, 65190 B, 28fce35ffc1ca496f1b1c43d8d1543c8bde0437f8b470c0eae2f53cff2684bf2
- OUT/locomo_GR.jsonl: 297 rows, 37713 B, 74beffde2e8fb64aeea60eeff9446c9503c7483ab6e467602a1a3a599f37352a
- OUT/locomo_TR.jsonl: 1986 rows, 264498 B, 25e1c72c7c79625fcde11f2b8a3f1a0cc6e4bba7b427a8a580add3ba47bbb2bd
- OUT/mmlu_TR.jsonl: 300 rows, 19277 B, 3d0dd1c523b0d7fb7fda93d31df68cf784d3fdb1abeb564cf5435ff865e934d2
- OUT/train398r.json: 1825 B, 1bb299c30b381b20b9ff14ee8842011e8db5abaab692cff0a53a7b504250760d
- OUTI/a/replies398i.jsonl: 65434 B, b6bfdbf36927e88ca5c3f39349fd0f336a49af3e0bb69b4002dbb16e7faa733d
- OUTI/a/result.json: 880 B, bf2d52200be33dfb94a17e3eeadf2f04214ee979e16467fec3a2758cd489f3a2
- OUTI/b/replies398i.jsonl: 65434 B, b6bfdbf36927e88ca5c3f39349fd0f336a49af3e0bb69b4002dbb16e7faa733d (byte-identical to a)
- OUTI/b/result.json: 880 B, fac2e747f0ae99119974a60e080e818a3ab248150aac0e5c7eb7ff71df07b35b (differs only in seconds)
- adapter398r.pt -> ~/premonition-models/bm398r-adapter398r.pt: 16576151 B,
  f98c54a9cabc29cbc80995e571d232d69fcdd249ea859b5d0ad692ba7627cfdf (match, never pushed).
- MERGED (2 GB) not copied, per task.

## Peak GPU memory
- Max nvidia-smi reading: 10008 MiB (during training).
- Train self-report peak_gpu_mb: 7118.
- Scored runs: 5074 MiB. Part 1: not sampled (small).
- No OOM anywhere.

## Deviations (all reported)
1. Rentals 1-2 failed (loading stall / dead SSH proxy); destroyed, $0 each; rental 3 ran everything.
2. Selftest launcher cwd bug on first rdata/rtrain launch; relaunched unchanged; 9/9, 16/16, 6/6 all pass. No code edit.
3. Train first launch crashed ModuleNotFoundError: No module named 'nltk' (full
   traceback above); installed nltk 3.10.3 env-only and relaunched the identical
   command once; exit 0. No code edit.
4. Run-398i-a has no recorded exit-code file (wrapper added from run b onward);
   exit 0 inferred from completed files + clean final JSON line. All other
   commands have recorded exit 0.

## Outcome
All registered commands finished with exit 0; all row counts and hashes as
expected. Copy-back verified by size+sha256 before destroy; instance destroyed and
confirmed gone. Nothing scored on this machine. Code never edited.
