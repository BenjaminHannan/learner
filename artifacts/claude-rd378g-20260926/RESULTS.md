# rd-378g results (written 2026-09-27 20:03:30 UTC): G1-G4 PASS; G5 not scored (Ben stopped all threads at 19:57 UTC)

The run: one vast RTX 5090 (instance 52975125, $0.513/h, 108.1 TFLOPS), kit 54cfbbfcb, every step rc=0, guard END DONE,
spent $0.87 (vast/COLLECT.txt). Train: 690 of 690 steps on 5,511 glm3U rows (GLM and Luna only, no Claude), 8.38 min,
dev loss 0.516, peak 12,620 MiB (vast/train/summary.json, vast/drive-state.txt). All seals and the 4 selftests passed
(vast/checks.txt). G's adapter on the Mac matches SEAL-run.

## Marks (LoCoMo 5-9, practice only; any@10 over categories 1-4, 772 questions; vast/notes_confirm.json)
A = heard rows only (store v3): 489 of 772 (63.34%). It matches rd-378u's A rows in every category.
R = the rd-378 writer, from artifacts/claude-rd378u-20260926/notes_confirm.json: 585 of 772 (75.78%).
G = the new writer (store v4 with G's notes): 577 of 772 (74.74%).

| Mark | Bar | Result | |
|---|---|---|---|
| G1 notes still help | G >= A + 5 | +11.40 points | PASS |
| G2 as good as the Claude-trained writer | G >= R - 2 | -1.04 points | PASS |
| G3 no category left behind | each >= A - 3 | cat 1 +7.14, cat 2 +6.71, cat 3 +20.00, cat 4 +13.71 | PASS |
| G4 notes parse | unparsed <= 2% | 5 of 3,122 turns (0.16%) | PASS |
| Proved wrong | G <= A + 1 | +11.40 | not fired |

G wrote 2,262 notes on 3,122 turns. @5: 523 (A 410). @20: 645 (A 569).

## G5 (ADDENDUM-K): not scored
G's and R's notes on the 43 G5 dialogs came back (vast/g5/notes_G.jsonl and notes_R.jsonl, 504 lines each). R reached
the rental, so the 57% fallback is not needed. The g5 make step and the two blind judges were not run: Ben stopped all
threads at 19:57 UTC on 09-27. PASS for rd-378g needs G1-G5 (ADDENDUM-K), so rd-378g has no overall verdict yet.
The G5 write-up must say "no less true than the rd-378 writer", never "trustworthy", and give R's share beside G's.

Blind recount: a separate script re-read both notes_confirm.json files and got the same numbers.
