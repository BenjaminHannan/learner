# bm-397 RESULTS: the copy-only finaliser on the plain 1B's LoCoMo answers (benchmarks thread, 2026-09-26)

Verdict: **registered FAIL.** Mark F1 fails, and the result falls inside the plan's "proved wrong" line (TF − T ≤ +1.0).
Every number is "after using LoCoMo for development". Counts only; no question, answer or reply is quoted.

## Where it ran
The queued BensPC job (006f) ran on the Mac instead: its header said "GPU: shared", not "GPU: yes", which was my
error. It stopped with STOP-NO-GPU-WRONG-HOST, having run nothing (builder-outbox runs/006f-bm397-finalize). The
registered run is the one below. It ran once, on CPU in the benchmarks thread's sandbox (4 cores, fp32, torch
2.14.0+cpu, transformers 5.17.0), with MiniCPM5-1B snapshot 87179e5c.
- Seals: SEAL.sha256.txt 6/6 OK and SEAL-judge 1/1 OK. The drafts' sha256 matches drafts.sha256.txt.
- Self-test: "BM397-SELFTEST PASS 7/7". DATA locomo10.json sha256 79fa87e9…ff4 (bm-390's).
- Arm TF started 2026-09-26T01:55:19Z and took 3,176.5 s. Its printed line:
  {"arm": "TF", "rows": 1986, "reasons": {"changed": 286, "same": 1019, "not_copy": 228, "category_5_untouched": 446, "abstains": 7}, "seconds": 3176.5}
- run/locomo_TF.jsonl: 1,986 rows, sha256 f8f1f7d9948c31f67591a37db4cb153765cec9afd7acf8cb912308ca6829056e.
- Deviation: arms were run one at a time (`--arms T`, then E20 later), not as `--arms T,E20`. Output is identical
  either way, because every call is greedy and independent.

## F1 (gain): FAIL
| | T | TF |
|---|---|---|
| LoCoMo cat 1-4 F1 (sealed scorer) | 27.50 | 27.78 |
| cat 1 / 2 / 3 / 4 | 24.37 / 19.46 / 16.07 / 32.92 | 24.57 / 19.94 / 16.01 / 33.19 |
| confident wrong (cat 1-4) | 467 | 468 |
- TF − T = +0.28. The conversation-level 95% interval (bm-396 cluster_boot, seed 396, 10k) is −0.29 to +0.76. The
  question-level interval (bm-390 boot_diff) is −0.07 to +0.63. The mark was ≥ +5.0 with the interval above 0.
- Per conversation (10): +0.07, +0.14, −0.35, +0.89, +0.60, −1.99, +1.81, +0.46, −0.16, +0.57.

## What the finaliser did (report only)
- Of 1,540 category 1-4 rows: 7 were kept because they abstain, and 1,533 were tried. Of those, the 1B returned the
  draft's own words unchanged 1,019 times ("same"), used words not in the draft 228 times (kept by the copy-only
  rule), and shortened 286 times.
- On the 286 changed rows: F1 rose on 105, fell on 45, and the mean change was +1.50. Median scored words went from
  17 to 11.5.
- Median scored words, cat 1-4: T 10, TF 9.
- bm-396 columns for TF: all_gold_tokens 397 (T 402), zero_overlap 476 (T 475), best_span_f1 47.94 (T 48.30).

## What it means (shown / suggested / untested)
- Shown: asking the plain 1B to shorten its own answers, with only its own words allowed, changes almost nothing.
  It gives the answer back unchanged two times out of three, and cuts little when it does act.
- Suggested: this shows the prompted 1B cannot shorten on instruction. It does not show that the answers' content
  is the whole gap: best-span F1 is still 47.94, so a better cut would gain a lot. The plan's rule, registered
  before the run, sends the next dollar to evidence-conditioned training, which teaches the answerer to answer
  short in the first place.
- Untested: whether a trained answerer, or an explicit final-answer field (design/v3/30-modes/398-...), recovers the
  gap.

## F2 (faithful): FAIL
The blind audit covered all 286 changed rows, since there were fewer than 300. Six blind Opus judges were used: two
per group plus two relabellers. None saw both replies of one question. Labels and key are in audit/; the scored line is
audit/F2-score.json.
- Draft labels: A 103, B 7, C 56, D 119, E 1. Final labels: A 92, B 4, C 63, D 126, E 1.
- lost (a right draft, A, becoming C, D or E) = 13; the bar was ≤ 3. picked (a hedged draft, B, becoming A) = 4; the
  bar was ≤ 3.
- Changes that fixed an answer: B→A 4, D→C 2, D→B 1. Changes that hurt: A→C 8, A→D 5, A→B 2, C→D 4, B→C 1, B→D 1.
- Relabel agreement: 58 of 60.
So the shortening also changed meaning. It turned 13 of 103 right answers into partly right or wrong ones.

## Still to add (registered, running)
The GSM8K/MMLU no-drop marks (AMEND-general); E20F (report only); blind recount.
