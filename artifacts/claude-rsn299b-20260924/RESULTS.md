# rsn-299b panel: registered run RESULTS (2026-09-24)

Verdict: FAIL (P299b.1 missed; P299b.2 and P299b.3 passed).

Voting over 5 calculator runs added +10 right answers out of 60, below the bar of +12.
It made zero arithmetic mistakes and the vote arm got far fewer answers wrong than the
plain arm (10 vs 29), but the gain was too small to pass.

## Marks (from OUT/panel-score.json, n = 60)

| mark | what | count | bar | result |
|---|---|---|---|---|
| P299b.1 | V right minus P right | 38 − 28 = +10 of 60 | ≥ 12 | FAIL |
| P299b.2 | arithmetic errors in V's shown steps | 0 | 0 | PASS |
| P299b.3 | V wrong vs P wrong | 10 vs 29 (V fewer by 19) | V ≤ P | PASS |

PASS = all three. Result: 2 of 3 → registered verdict FAIL.

## Per-category counts (right / unsure / wrong / none, from panel-score.json)

| category | n | P right | P unsure | P wrong | P none | V right | V unsure | V wrong | V none |
|---|---|---|---|---|---|---|---|---|---|
| ARITH | 14 | 11 | 1 | 2 | 0 | 12 | 2 | 0 | 0 |
| TIME | 10 | 0 | 0 | 9 | 1 | 4 | 5 | 1 | 0 |
| COUNT | 10 | 2 | 0 | 8 | 0 | 4 | 2 | 4 | 0 |
| COMPARE | 10 | 6 | 0 | 4 | 0 | 5 | 2 | 3 | 0 |
| PLAN | 10 | 9 | 0 | 1 | 0 | 8 | 1 | 1 | 0 |
| UNSURE | 6 | 0 | 0 | 5 | 1 | 5 | 0 | 1 | 0 |

Totals: P 28 right / 1 unsure / 29 wrong / 2 none / 0 arith_errors;
V 38 right / 12 unsure / 10 wrong / 0 none / 0 arith_errors.
Right+unsure+wrong+none = n in every row. "I'm not sure" is scored separately from
wrong; on UNSURE items "not sure" is right. V's 5 UNSURE-right are "not sure" answers
(the scorer counts them as right, not unsure); P said "not sure" on 0 of 6 UNSURE items.

## Vote and timing report (no mark)

- V rows with fewer than 3 of 5 votes: 16 of 60 (vote distribution: 5 votes 13 rows,
  4 votes 14 rows, 3 votes 17 rows, 2 votes 13 rows, 1 vote 3 rows). The 16 rows
  without a majority were answered "I'm not sure".
- Median seconds per item: P 0.965 s (min 0.32, max 9.77, total 68.7 s);
  V 6.27 s (min 2.58, max 24.47, total 481.9 s, about 8.0 GPU minutes plus model loads).
- Calculator calls per row are recorded in the run files' "calls" fields (not summed here).

## Provenance

- Code: fresh `git archive origin/main` at commit faa7ee2140caa0983066747bdc80224f6f3ff308,
  extracted to a new directory (C:\Users\benja\rsn299bpanel) on BensPC and run from its root.
  No code edited.
- Seals (checked on BensPC before running, every line OK):
  `artifacts/claude-rsn299b-20260924/SEAL-code.sha256.txt` (7/7 OK),
  `artifacts/claude-thinkpanel299b-20260924/SEAL.sha256.txt` (items.jsonl OK).
- Tool selftest: `python -B scripts/claude_rsn299_tool.py` printed "selftest ok".
  `python -B scripts/claude_rsn299b_run.py mock` ran without error.
- Model: openbmb/MiniCPM5-1B via huggingface_hub.snapshot_download(local_files_only=True);
  commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc — the only snapshot in the BensPC
  hub cache, the same snapshot rsn-299-panel used.
- Venv: the lis-300 venv (Python 3.10.9, transformers 5.17.0, torch 2.11.0+cu128, CUDA True).
- GPU: NVIDIA GeForce RTX 5070 Ti, idle before the run (0% util, 15397 MiB free), one job at a time.
- Time window: transfer started about 09:01 ET, score finished about 09:13 ET — inside
  08:00–18:00 ET and well before the 20:00 ET cap. Total session well under the 60-minute hard cap.
- Runs, once each, one after the other: P (60/60 rows), V (60/60 rows), score. No re-runs
  of completed arms, no crashes mid-run, no missing cases. OUT copied back to
  artifacts/claude-rsn299b-20260924/run/ (panel-P.jsonl, panel-V.jsonl, panel-score.json).

## Every deviation

1. OPUS-RULES.txt could not be read: the referenced scratchpad/briefs directory on this
   machine is empty, so the file does not exist. I followed the key points as restated
   in the task (additive only, sealed files untouched, ledger untouched, counts only).
2. BensPC has no `sha256sum` binary, so both seals were checked with an equivalent
   Python hashlib script: all 8 lines OK (7 code + items.jsonl), else I would have stopped.
3. `--model BASE` passed literally fails (the sealed script treats it as a path/repo id
   and tries the network). Per the task's MODEL line, BASE was resolved with
   snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True) and that local path
   was passed as --model. No code edited.
4. The fresh archive contains no OUT/ directory, so the first P attempt crashed with
   FileNotFoundError before writing any row. I created OUT/ with mkdir and reran P once
   cleanly (60/60 rows). Each arm still has exactly one successful run.
5. Strictly read-only rule for the TEST-ONLY panel: the items file was passed as input
   to the sealed run/score commands (as the task orders) but never opened, printed,
   counted by content, or quoted. This file reports only the numbers the score command
   printed plus row counts, medians, and vote-count tallies.
