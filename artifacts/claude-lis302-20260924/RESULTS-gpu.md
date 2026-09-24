# lis-302 GPU measurements (REPORT ONLY, 2026-09-24)

Two GPU measurements on BensPC over lis-301's DEV readings (959 dev rows/preds
from origin/builder-outbox). No registered marks, no training, no panel.
Listener code run unmodified.

## 1. Token probs

- Command (lis-300 venv python, `PYTHONUTF8=1`, model
  `C:/Users/benja/lis301/work/run/merged`): tokprobs script with
  `--model <merged> --rows dev_rows.jsonl --pred dev_pred.jsonl --out tokprobs.jsonl`.
- Merged safetensors sha256 verified on BensPC before the run:
  `b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890` (match).
- Script printed `done on cuda`. Process exited, GPU freed.
- Rows done: 959 of 959 (every id matches dev_pred).

### check_minp vs recorded minimum conf

- Rows with a non-empty conf list: 817 of 959 (142 rows have `conf: []`, so no
  recorded minimum exists to compare).
- Rows where `|check_minp - min(conf)| > 0.01`: 95 of 817.
- Of the 95: 65 check_minp lower, 30 check_minp higher.
- All 817 compared rows: median absolute diff 0.000131, max absolute diff ~0.9996
  (one row with check_minp ~0.000006 vs recorded min ~0.999562).
- Example rows (ids only, no turns quoted): largest gap on `w6-0124`
  (check 0.000006 vs recorded 0.999562); a mid-size gap on `o0a2-m032`
  (check 0.106540 vs recorded 0.879450).

## 2. Exp-261 checker pass

- Checker input: `checks.json` from origin/main (753 queries). Ran the sealed
  `claude_earcheck261_checker.py` unmodified.
- llama-server: I started my own instance (see Deviations), PID 8840, stopped it
  afterwards by that exact PID. Nothing else touched.
- Checker summary: n = 753, fallbacks = 0, median = 281.5 ms, p90 = 287.8 ms,
  max = 489.2 ms.
- No VRAM spill signs: p90 ≈ median (no 4x slowdown tail); nvidia-smi after the
  run showed 90% util at 202 W (healthy compute, not the under-100-W spill idle).
  VRAM with the Qwen model loaded: ~13.9 GB of 16.3 GB.

## Device

- BensPC NVIDIA GeForce RTX 5070 Ti (16303 MiB), `cuda` for tokprobs
  (torch 2.11.0+cu128, transformers 5.17.0, reused lis-300 venv, as in lis-301).
- Checker model: `Qwen3.8-27B-UD-IQ4_XS.gguf` (present) served by
  `C:\llama-b10679\llama-server.exe` (present).

## Server: started, not reused

- Port 8081 was already held by PID 17056 (started 2026-09-23 05:57, still
  running, untouched): a llama-server with the brief's flags but NO `-m` model,
  i.e. a model-less router (`model_path: none`). One probe checker query against
  it failed with HTTP 400 (`model name is missing from the request`), so it was
  unusable for this step.
- I started my own server with the brief's exact flags plus `-m <GGUF>` and
  `-c 4096`, on port 8082 (only deviation: the port), waited for /health ok,
  recorded PID 8840, ran all 753 queries against it, then stopped PID 8840.
- GGUF and exe both present; no skip needed.

## Deviations (env only; listener/checker code untouched)

1. Port 8082 instead of 8081 for my llama-server (8081 occupied by the model-less
   PID 17056, which I never touched). The `--url` pointed at my port.
2. `-c 4096` included per the brief (same as the pre-existing instance's flags).
3. Staging copies of the sealed scripts and dev inputs were transferred to
   `C:/Users/benja/lis302/work/` on BensPC (hashes verified equal after copy);
   lis-301's own files were not modified.
4. Servers started over ssh do not survive ssh disconnect on BensPC (two launcher
   PIDs died with their sessions), so the server ran in the same ssh session as
   the checker; it was stopped by exact PID at the end of that session.

## What it means (plain high-school English)

- Both GPU measurements finished cleanly: 959 token-prob rows and 753 checker
  answers, zero fallbacks, fast responses (typical answer in ~0.28 s).
- The re-derived per-row minimum matches the recorded confidence almost exactly
  most of the time (typical gap ~0.0001), but on 95 of 817 rows the two differ by
  more than 0.01, mostly with the re-derived minimum lower. That is just a count,
  not a verdict on which number is right.

## What it doesn't mean

- It doesn't mean the reader is good or bad: this task registers no marks and
  grades nothing. These are raw GPU readings for the listener thread to use.
- It doesn't mean the checker agrees with the reader: pYES values are recorded,
  not judged, here.
