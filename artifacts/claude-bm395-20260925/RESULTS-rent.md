# RESULTS-rent.md: rent-bm395, ep-382's answering test (rented GPU run, 2026-09-25)

Counts only. No question, answer or reply is opened, printed or quoted anywhere in this file.
Code: unmodified origin/main + origin/builder-outbox tree (main on top). No file edited. No reader needed.

## Credit gate
- `vastai show user --raw` credit at start: 7.063765917599895 (above the $2.50 floor; rented).
- Credit after destroy: 5.645551797599914. The drop is NOT all this task: sibling rentals
  (rent-bm390f, rent-blurt5s, rent-rd-371, rent-dl1) billed the same account concurrently.
  This task's own running total (dph x hours, kit rule) is ~$0.47 of the $1.00 budget. No BUDGET-STOP.

## Seals (step 1, from the tree root, before anything else)
- `sha256sum -c artifacts/claude-bm395-20260925/SEAL.sha256.txt`: 9 lines, every line OK (exit 0).
- `sha256sum -c artifacts/claude-bm390-20260925/SEAL-code.sha256.txt`: 8 lines, every line OK (exit 0).

## Environment (setup on the rental)
- pip: kit line (`transformers>=5 safetensors huggingface_hub accelerate numpy`) plus pyarrow (was missing, installed). Nothing else installed.
- `python -c "import torch, transformers; print(torch.__version__, transformers.__version__)"`: 2.8.0+cu128 5.17.0
- Also present: accelerate 1.15.0, safetensors 0.8.0, numpy 2.3.2, huggingface_hub 1.33.0, pyarrow 25.0.1, torch CUDA available True, GPU NVIDIA GeForce RTX 5090 32607 MiB.
- Model downloads (HF_HUB_OFFLINE=0, the one allowed command; `unset HF_HOME HF_HUB_CACHE` first):
  - BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  - MiniLM = /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 (exactly the required path; no MINILM-PATH stop).
- Everything else ran with `HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1`, each command under nohup/setsid with its own log.

## Fetch (step 2)
Verbatim line:
{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}
locomo_qa 1986 and both sample hashes match the registered values. No DATA-MISMATCH.

## Self-test (step 3)
`python -B scripts/claude_bm395_store_answer.py selftest --data /root/bm395data`, all lines:
PASS smoke_rows_match_turns
PASS smoke_top10_is_prefix
PASS smoke_layout_identical_to_bm25_context
PASS locomo_rows_match_turns
PASS locomo_top10_is_prefix
PASS locomo_layout_identical_to_bm25_context
BM395-SELFTEST PASS
(6 PASS lines, ends with BM395-SELFTEST PASS. No SELFTEST-FAIL.)

## Smoke (step 4, made-up data)
`python -B scripts/claude_bm395_store_answer.py locomo --data artifacts/claude-bm390-20260925/smoke --model BASE --out /root/bm395work/smoke`: exit 0,
printed "wrote locomo_E.jsonl rows=5" and "wrote locomo_E20.jsonl rows=5". No SMOKE-FAIL.

## Registered commands (step 5)
OUT = artifacts/claude-bm395-20260925/run (new folder in the tree). DATA = /root/bm395data.

Lane 1: `python -B scripts/claude_bm395_store_answer.py locomo --data /root/bm395data --model BASE --ks 10,20 --names E,E20 --out artifacts/claude-bm395-20260925/run`
- First printed line: [bm395] conv-26 store_rows=419 questions=199 seconds=113
- 10 [bm395] lines in all (one per chat), last: [bm395] conv-50 store_rows=568 questions=1986 seconds=89
- Last lines: wrote locomo_E.jsonl rows=1986 convs=10 / wrote locomo_E20.jsonl rows=1986 convs=10
- Exit code: 0 (normal completion: both wrote lines present, no traceback, process gone)
- Start: 2026-09-25 ~20:38 UTC. End: 2026-09-25 20:54:53 UTC (output file mtimes).

Lane 2: `python -B scripts/claude_bm390.py locomo --data /root/bm395data --arm bm25:BASE --name Rb2 --out artifacts/claude-bm395-20260925/run`
- First printed line: [bm390] conv-26 bm25 questions=199
- 10 [bm390] lines in all, last: [bm390] conv-50 bm25 questions=204
- Last line: wrote locomo_Rb2.jsonl rows=1986 convs=10
- Exit code: 0 (normal completion: wrote line present, no traceback, process gone)
- Start: 2026-09-25 ~20:40 UTC. End: 2026-09-25 20:47:15 UTC (output file mtime).

## Row counts of run/*.jsonl (wc -l on the Mac copies)
- locomo_E.jsonl: 1986 rows, 354732 bytes, sha256 3f2e1447e2a808e41399749423f588ee31913df2f3e6c2892fbb78a9d25cd127
- locomo_E20.jsonl: 1986 rows, 458342 bytes, sha256 e7f70f5703768697709b2cf93197fdb18aa5b13a9a58caacf8becb9b60e7bcef
- locomo_Rb2.jsonl: 1986 rows, 274003 bytes, sha256 98d10ae9c083331fbe32d21130fa098b3be16405e1442291d337f67d47007ce7
Sizes and hashes match the box exactly (checked before destroy). Validity: 1986 rows each, both commands exit 0, seals OK.

## GPU memory
Peak GPU memory observed during the run: 5823 MiB of 32607 MiB (util 88%, both lanes sharing one RTX 5090). After both lanes: 2 MiB.

## GPU / instances / money
- GPU: RTX 5090 (5090 first per task; no 4090 needed).
- Rental 1: contract 52642227, offer 48989765, dph $0.5037. Wrong image name (manifest unknown), never reached running, destroyed. 0.00 h, $0.00.
- Rental 2: contract 52642566, offer 48989765, dph $0.5037. Running ~20:04 UTC, destroyed 20:15:31 UTC after its container SSH tunnel wedged (key attached per API yet proxy auth denied; reboot did not fix; tree.tgz uploaded via `vastai copy` but never unpacked; no work lost). ~0.19 h x $0.5037 = ~$0.10.
- Rental 3: contract 52644313, offer 52414882, dph $0.5659, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime. Running ~20:18 UTC, destroyed 20:57:51 UTC, confirmed gone (`vastai show instances` shows no rent-bm395). ~0.66 h x $0.5659 = ~$0.37.
- Task total: 3 rentals (within the 4-rental limit), ~$0.47 of the $1.00 budget. No BUDGET-STOP ($0.85 threshold never reached). Watchdog: no 10-min stall (both lanes printed steadily).

## Launch deviations (reported; neither affects validity)
1. Lane 2 first launch (~20:38, same ssh line as lane 1) inherited cwd /root instead of /root/tree (shell `&` split the `cd` chain) and died instantly without starting:
   python3: can't open file '/root/scripts/claude_bm390.py': [Errno 2] No such file or directory
   `ps` confirmed no claude_bm390.py process before retrying.
2. Lane 2 second launch (20:39:48 UTC) used a literal placeholder instead of the BASE path (operator typo) and failed fast offline with:
   OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files. Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
   (tail of the log as observed; the log file was overwritten by the successful run, box since destroyed).
   `ps` confirmed no claude_bm390.py process before the final launch.
3. Lane 2 final launch (~20:40 UTC) with the correct BASE path is the registered run reported above. Lane 1 (PID 1187, started 20:38) ran untouched throughout. No registered command was ever run twice: each failed attempt died at startup with no output file.
4. The two failed attempts started ~2 min after lane 1 rather than at the same minute; both lanes still overlapped on the GPU for the whole run.

## Verdict
Run ONCE per PLAN.md (E + E20 vs Rb2 re-run, same machine, same BASE snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc). All three arms valid (1986 rows each). Scoring is NOT part of this task (done later with scripts/claude_bm390_score.py unchanged).
