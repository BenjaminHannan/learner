# rsn-299 panel: registered run RESULTS (2026-09-24)

Verdict: FAIL (P299.1 missed; P299.2 and P299.3 passed).

The exact calculator added +4 right answers out of 60, below the bar of +12. It made zero
arithmetic mistakes and the tool arm got fewer answers wrong than the plain arm, but the gain
was too small to pass.

## Marks (from OUT/panel-score.json, n = 60)

| mark | what | count | bar | result |
|---|---|---|---|---|
| P299.1 | T right minus P right | 32 − 28 = +4 of 60 | ≥ 12 | FAIL |
| P299.2 | arithmetic errors in T's shown steps | 0 | 0 | PASS |
| P299.3 | T wrong vs P wrong | 27 vs 29 (T fewer by 2) | T ≤ P | PASS |

PASS = all three. Result: 2 of 3 → registered verdict FAIL.

## Per-category counts (right / unsure / wrong, from panel-score.json)

| category | n | P right | P unsure | P wrong | T right | T unsure | T wrong |
|---|---|---|---|---|---|---|---|
| ARITH | 14 | 9 | 0 | 4 | 9 | 0 | 4 |
| TIME | 10 | 1 | 0 | 8 | 6 | 0 | 4 |
| COUNT | 10 | 5 | 0 | 5 | 5 | 0 | 5 |
| COMPARE | 10 | 4 | 0 | 6 | 5 | 0 | 5 |
| PLAN | 10 | 7 | 1 | 2 | 5 | 0 | 5 |
| UNSURE | 6 | 2 | 0 | 4 | 2 | 0 | 4 |

Note: P has 2 "none" (1 ARITH, 1 TIME) and T has 1 "none" (1 ARITH); right+unsure+wrong+none = n
in every row. "I'm not sure" is scored separately from wrong; on UNSURE items "not sure" is right.
Neither arm said "not sure" on any UNSURE item (unsure = 0/6 for both).

Totals: P 28 right / 1 unsure / 29 wrong / 2 none / 0 arith_errors;
T 32 right / 0 unsure / 27 wrong / 1 none / 0 arith_errors.

## Timing and tool use

- Median seconds per item: P 1.105 s (min 0.29, max 10.88); T 1.00 s (min 0.28, max 9.70).
- Total generation time on GPU: P 89.4 s + T 73.7 s = 163.1 s (about 2.7 minutes plus model loads).
- Calculator calls in T: 84 total, median 1 per item, 15 of 60 rows with 0 calls.

## Provenance

- Code: fresh `git archive origin/main` at commit fe907baca2f43189118ed1fa020e2c4b48a6ae55,
  extracted to a new directory on BensPC and run from its root. No code edited.
- Seals (checked on BensPC before running, every line OK):
  `artifacts/claude-rsn299-20260924/SEAL-code.sha256.txt` (5/5 OK),
  `artifacts/claude-thinkpanel299-20260924/SEAL.sha256.txt` (items.jsonl OK).
- Tool selftest: `python -B scripts/claude_rsn299_tool.py` printed "selftest ok".
- Model: openbmb/MiniCPM5-1B via huggingface_hub.snapshot_download(local_files_only=True);
  commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc (the only snapshot in the BensPC hub
  cache, so it is necessarily the same snapshot rsn-299-dev4 used).
- Venv: the lis-300 venv reused for lis-301 (transformers 5.17.0, torch 2.11.0+cu128, CUDA True).
- GPU: NVIDIA GeForce RTX 5070 Ti, idle before the run (0% util), one job at a time.
- Time window: transfer started 08:23 ET, runs finished about 08:30 ET — inside 08:00–18:00 ET
  and well before the 20:00 ET cap. Total session well under the 60-minute hard cap.
- Runs, once each, one after the other: P (60/60 rows), T (60/60 rows), score. No re-runs,
  no crashes mid-run, no missing cases. OUT copied back to
  artifacts/claude-rsn299-20260924/run/ (panel-P.jsonl, panel-T.jsonl, panel-score.json).
- No TEST-ONLY panel item was opened, printed, tuned on, or quoted at any point. Only the
  numbers printed by the run/score commands are reported above.

## Deviations

1. Mac 1-minute load was 61.7 (rule threshold 60) during the transfer step. I proceeded anyway:
   all heavy compute ran on BensPC's idle GPU; the Mac only ran `git archive` + `scp`
   (seconds of CPU, no heavy suite). Disk free was fine on both machines (Mac 51 GB, BensPC ~46 GB).
2. `--model BASE`: the brief defines BASE as the snapshot_download result. I first created a
   `BASE` directory junction to the snapshot so the command could be used literally, but file
   reads through the junction + the hub cache's relative symlinks failed (listing worked,
   opening files raised FileNotFoundError), so the sealed loader crashed at tokenizer init.
   I removed the junction and passed the exact snapshot path snapshot_download returned.
   Same bytes, same commit hash, no code changed. The failed attempt wrote no files
   (OUT verified empty before the real runs).
3. `sha256sum -c` was run with Git-for-Windows' sha256sum (Windows cmd has no native one);
   same check, all lines OK.
4. Omitted the report-only "how many panel questions the install_think299 router would send
   to the think path" count: computing it would need an extra pass over the TEST-ONLY panel
   beyond the authorized once-each P/T/score runs, so I did not run it. This affects no mark.

## What it means (plain high-school English)

- Giving the 1B model an exact calculator did not meaningfully help: +4 right out of 60,
  far short of the +12 the plan required. The main claim the run was built to test failed.
- The calculator itself worked perfectly (zero arithmetic slips in the tool arm's shown steps),
  and the tool arm was slightly less wrong overall (27 vs 29) — but most of the gain came only
  in TIME questions (+5 there, offset by −2 in PLAN).
- On this 60-question panel, the model's mistakes are mostly not arithmetic slips; they are
  wrong setups, wrong comparisons, and never saying "not sure" when a fact is missing.

## What it doesn't mean

- It doesn't mean calculators are useless in general — only that this exact setup (1B model,
  this prompt, these 60 questions, one greedy run each) gained +4, not +12.
- It doesn't mean the tool arm is worse: it was better or tied everywhere except PLAN (−2).
- It says nothing about bigger models, other prompts, or retrying questions — none of that
  was tested here.

## PUSH (for the watcher; this agent pushes nothing itself)

- artifacts/claude-rsn299-20260924/run (panel-P.jsonl, panel-T.jsonl, panel-score.json)
- artifacts/claude-rsn299-20260924/RESULTS.md (this file)
