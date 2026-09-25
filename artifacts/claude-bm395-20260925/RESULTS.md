# bm-395 RESULTS: ep-382's answering test (after using LoCoMo for development)

Run on a rented RTX 5090, 20:38-20:55 UTC 2026-09-25, about $0.47 of the $1.00 cap (RESULTS-rent.md). Sealed at
main 725c3c64b before the run; the seals checked OK on the rental. Every arm has 1,986 rows, and both registered
commands exited 0. Scored with scripts/claude_bm390_score.py (sealed), `--primary E --baselines Rb2 --report Rb,E20`.

## Verdict: registered FAIL
E - Rb2 = **+1.66** F1 points on categories 1-4 (1,540 questions), 95% interval [+0.31, +3.03]. The pass mark
needed at least +3.0 with the interval above 0. The interval is above 0, so the store's lines do help, but by less
than the registered mark.

| Arm (plain MiniCPM5-1B, same machine) | 1-4 F1 | cat 1 / 2 / 3 / 4 | confident wrong | lines found* |
|---|---|---|---|---|
| E: memory store's top 10 | 26.84 | 21.22 / 25.57 / 12.48 / 30.85 | 569 | 65.7% |
| Rb2: BM25's top 10 (bm-390's Rb, re-run) | 25.18 | 13.54 / 27.26 / 11.72 / 29.83 | 625 | 51.7% |
| E20 (report only): memory store's top 20 | 29.85 | 25.58 / 27.34 / 12.92 / 34.17 | 498 | 75.2% |
| Rb (bm-390, BensPC) | 25.06 | 13.63 / 26.93 / 12.06 / 29.65 | 615 | 51.7% |
| For scale (bm-390): T, whole chat | 27.50 | | 467 | |
| For scale (bm-390): Qwen3.5-2B, whole chat | 47.87 | | 402 | |

*Share of the 1,531 questions with usable evidence where at least one evidence line was shown.

Report-only paired differences (same bootstrap): E20 - Rb2 +4.67 [+3.24, +6.08]; E20 - E +3.01 [+1.82, +4.23];
Rb2 - Rb +0.13 [-0.25, +0.50].

Recount: a second scorer written independently for bm-390 (recount4/, from the LoCoMo repo's own code) gives the same
headline and category numbers for all four arms (recount/recount395.json). Its interval for E - Rb2 is
[+0.28, +2.98] because it draws its resamples differently. The verdict is the same.

## Predictions (PLAN.md)
- H1 right: +1.66 is between +1.0 and +7.0.
- H2 wrong: the mark was not met (I had leaned yes, about 55%).
- H3 right: the gain is bigger on multi-hop (+7.68) than on single-hop (+1.02). Temporal questions went slightly
  down (-1.69).
- H4 right: Rb2 is within 1.0 of Rb (25.18 vs 25.06; 1,810 of 1,986 replies are identical).
- H5 right: E20 scored above E (29.85 vs 26.84).
- H6 right: category 5 is within 5 points (12.33 vs 10.99).

## Why the gain is smaller than the finding rate suggested
The store found an evidence line for 65.7% of questions, against BM25's 51.7%, with the question as asked as the
query. But the plain 1B scores less on what the store finds: F1 is 35.77 when found and 9.74 when not, against
BM25's 38.58 and 10.88. The store found 276 questions' evidence that BM25 missed: 123 single-hop, 81 multi-hop,
59 temporal and 13 open-domain. BM25 found 62 that the store missed. The +3.8 estimate in PLAN.md assumed the same
F1 when found, and that assumption is what went wrong. Why F1 when found is lower was not tested. One untested
guess is that a found line may be less useful when the other 9 lines shown are near-misses by meaning.

## What it leads to (as registered)
- The store stays: it finds more lines, it scores higher with the interval above 0, and it makes fewer confident
  wrong answers (569 vs 625). But ep-382 did not pass its own registered mark. Whether it joins 0.2 anyway is the
  month-end thread's call; it has these numbers.
- E20 is report only. Showing 20 lines scored 29.85, above the plain 1B reading the whole chat (27.50). k = 20 was
  seen on LoCoMo practice, so any build that uses it must say so. It cannot be claimed as a LoCoMo win; the
  untouched test (LongMemEval, bm-399) decides.
- Retrieval tuning on LoCoMo stops here. The next lever is answering: with the evidence shown, the plain 1B's F1
  is only 36-39, and Qwen3.5-2B reading everything scores 47.87.

## Deviations (from RESULTS-rent.md)
Lane 2 (Rb2) failed to start twice before its registered run: once from the wrong folder (file not found), and once
from a mistyped model path (offline load error). Neither loaded a model or wrote output. The run reported is its
third start, with the correct path. Both lanes still overlapped on the GPU. Lane 1 (E, E20) started once and ran
untouched.
