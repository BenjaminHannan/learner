# bm-398e RESULTS-rent: span scores on one GPU rental (steps 2 and 4)

Task: handoff rent-bm398e, label claude-benchmarks-bm398e. Registered test bm-398e, steps 2 and 4
(span scores on drafts and on T's LoCoMo replies). Code run, never edited. Counts only: no
question, answer or reply is quoted. Nothing fitted or scored here.

## Credit gate (first)

`vastai show user --raw` credit number: 4.582765401269754 (>= 0.35, gate passed, rental allowed).

## Duplicate gate

origin/builder-outbox had no artifacts/claude-bm398e-20260926/spans and no
artifacts/claude-bm398e-20260926/RESULTS-rent.md; `vastai show instances` showed no live
instance labelled claude-benchmarks-bm398e (only claude-director-depot, claude-fixsleep-dl5c,
claude-fixsleep-dl6b). Gate passed.

## Rental

- Instance id: 52789000. Offer id: 45996848. GPU: NVIDIA GeForce RTX 4090, 24564 MiB.
- Image: pytorch/pytorch, disk 80. Label: claude-benchmarks-bm398e.
- dph (vast-reported, actual): 0.35111111111111115.
- Created 2026-09-26 17:35:42 UTC; running 2026-09-26 17:40:07 UTC (inside the 6-min start rule);
  destroyed 2026-09-26 ~17:35:42-18:03:55 UTC = ~0.470 h x dph 0.35111111 = ~$0.17.
- Rentals used: 1 of max 4. Running total: ~$0.17 of $0.35 budget (never hit the $0.32 money line).
- `vastai show instances` after destroy: 0 live instances labelled claude-benchmarks-bm398e.

## Environment (rental)

- torch 2.11.0+cu130 (image torch was 2.2.1; upgraded, see deviations), transformers 5.17.0,
  Python 3.10.13.
- pip: kit line (`transformers>=5 safetensors huggingface_hub accelerate numpy`) plus pyarrow
  (installed after `import pyarrow` failed; import not re-verified, instance destroyed).
- BASE (model snapshot, revision 87179e5c1f455ef22e6223592d2d61351b525bfc):
  /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- Exports for all work: HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1.
- Every command run from ~/tree under nohup/setsid with its own log file.

## Step 1: seals, selftest, T hash

- `sha256sum -c artifacts/claude-bm398e-20260926/SEAL.sha256.txt`: 10/10 OK.
- `sha256sum -c artifacts/claude-bm398e-20260926/SEAL-amend1.sha256.txt`: 3/3 OK.
- `python -B scripts/claude_bm398e_trim.py selftest`: BM398E-TRIM-SELFTEST PASS 8/8
  (all 8 PASS lines present; first attempt failed on missing nltk, see traceback below, then passed).
- sha256 of artifacts/claude-bm390-20260925/run2/locomo_T.jsonl:
  35bdf151ba5160efda06cfe4e1cb274c7a0fa894963db8295286927b5e53b3db (matches required value).

## Step 2: fetch

`python -B scripts/claude_bm390.py fetch --data /root/bmdata` printed (verbatim):

{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}

locomo_qa 1986 present. No destroy/stop needed.

## Step 3: both span lanes

ps checked before launch: no spans process running. Both lanes launched once each at
2026-09-26 17:51:38 UTC with own logs.

Lane 1: `python -B scripts/claude_bm398e_trim.py spans --made
artifacts/claude-bm398e-20260926/inputs/made.json --replies
artifacts/claude-bm398e-20260926/inputs/drafts.jsonl --model BASE --out
artifacts/claude-bm398e-20260926/spans/spans_made.jsonl`

- Last log line: `[bm398e] spans done 432 new seconds=46`
- Exit code: not captured (backgrounded via setsid; process reaped; see deviations). No traceback
  in log; done line written and 432-row output file closed.
- Start: 2026-09-26 17:51:38 UTC. End: 2026-09-26 17:52:24 UTC (output file mtime; log seconds=46
  agrees: 17:51:38 + 46 s = 17:52:24).

Lane 2: `python -B scripts/claude_bm398e_trim.py spans --data /root/bmdata --replies
artifacts/claude-bm390-20260925/run2/locomo_T.jsonl --model BASE --out
artifacts/claude-bm398e-20260926/spans/spans_T.jsonl`

- First launch (17:51:38 UTC) crashed at startup with wrong cwd (see deviations); zero rows written.
  Relaunched once, unchanged, from ~/tree at 2026-09-26 17:56:42 UTC (ps confirmed no spans
  process before relaunch).
- Last log line: `[bm398e] spans done 1540 new seconds=281`
- Exit code: not captured (same reason as lane 1). No traceback in log; done line written and
  1540-row output file closed.
- Start: 2026-09-26 17:56:42 UTC. End: 2026-09-26 18:01:23 UTC (output file mtime; log seconds=281
  agrees: 17:56:42 + 281 s = 18:01:23).

## Step 4: row counts, hashes, copy-back, destroy

- spans_made.jsonl: 432 rows,
  sha256 f045117ad6a4689c9c24c8ca32996c3a50752358de988c03f687c14b78927843
- spans_T.jsonl: 1540 rows,
  sha256 59e1fe2460da023daffb199d9a27bfeae90bba569913fa19998f22e4b61beeaf
- spans_made.jsonl.gz (gzip -9 -k): 176974 bytes,
  sha256 e25ab892fb1905938b04d39b2ac7c1930d7c9054dfccbc9b8d3546466bfa7e9b
- spans_T.jsonl.gz (gzip -9 -k): 1318109 bytes,
  sha256 3d15791a0795c075b65fe29a98fcd465b60877778fb8eb1c355d6070fbb996da
- Both .gz files copied to the Mac; sizes and sha256 match the box exactly. THEN destroyed;
  `vastai show instances` confirms 0 live claude-benchmarks-bm398e instances.

## Peak GPU memory seen

Not sampled during the runs (deviation). nvidia-smi after both lanes finished showed 1 MiB used
of 24564 MiB (idle). Span process RSS peaked around ~1.4 GB system memory per ps during lane 2.

## Tracebacks (in full)

1. First selftest attempt (missing nltk), full output tail:

```
Traceback (most recent call last):
  File "/root/tree/scripts/claude_bm398e_trim.py", line 38, in <module>
    import claude_bm390_score as SC  # noqa: E402
  File "/root/tree/scripts/claude_bm390_score.py", line 28, in <module>
    from nltk.stem import PorterStemmer
ModuleNotFoundError: No module named 'nltk'
```

2. Lane 2 first launch (wrong cwd), single error line, no traceback:

```
python3: can't open file '/root/scripts/claude_bm398e_trim.py': [Errno 2] No such file or directory
```

No other errors or tracebacks anywhere. No fit, no scoring, no judge ran here.

## Deviations (every one)

1. Torch upgrade: image torch 2.2.1 is incompatible with the kit's `transformers>=5`
   (transformers 5.17.0 disables its PyTorch integration unless torch>=2.5, so no model could
   load). Upgraded to torch==2.11.0 (+cu130) with `pip uninstall -y torchvision torchaudio`
   after, per the kit's TORCH UPGRADE procedure, then import check passed
   (torch 2.11.0+cu130, transformers 5.17.0, cuda True, AutoModelForCausalLM import OK).
   Eval-only job (no training, no gradients), so the kit's torch-2.8 autocast note does not apply.
2. Installed nltk (pip install -q nltk): the sealed scorer claude_bm390_score.py imports
   PorterStemmer at module top, so no sealed script could run without it. Code itself never edited.
3. Lane 2 first launch ran with cwd /root (backgrounded `&&` chain lost the `cd ~/tree`) and
   crashed at startup writing zero rows; relaunched once, unchanged command, from ~/tree at
   17:56:42 UTC after ps check. Reported here as required.
4. Exit codes of the lane processes were not captured (setsid-backgrounded, reaped before any
   wait). Both lanes printed their done lines with no traceback and closed complete output files
   (432 and 1540 rows); end times come from output-file mtimes cross-checked against log seconds.
5. Peak GPU memory was not sampled during the runs (see section above).
6. Cheapest 4090 offer at first query (id 49234598, dph $0.348) was gone by rent time; rented the
   then-cheapest passing offer 45996848 (RTX 4090, 16 cores, ~185 GB disk, rel 0.9957,
   up/down >200 Mbps; vast-billed dph 0.35111111).
7. Mac-side only: one scp command carrying both .gz paths failed to expand remotely; each file was
   then copied individually and both verified by size + sha256.

## Money

One rental (52789000), ~0.470 h x dph 0.35111111 = ~$0.17. Task running total ~$0.17 of $0.35.
TIME CAP (75 min): lane wall time ~10 min total; never approached.
