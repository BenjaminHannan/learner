# Two-doors test: pass marks (fixed 2026-10-03 ~19:20 UTC, before any training run)

Fast lane (Ben, 15:14 UTC 10-03): generated held-out split, split seed and marks written here before training.
Source design: `design/info-paths/information-paths.md` §4 (T1, T2). Reimplementation harness, not the PC pipeline.

- Task: `gen_story.py`. Word-list split seed 20261003 (2/3 train, 1/3 held out per list); eval seed 777.
  `EVAL-FORM.json` sha256 284f266f94ee32cdab325be7109f5e80032877c06b19dbc19941bf08d33821d6: 384 questions, 8 cells of 48 = answers seen/unseen x wording train/new x hop one/two.
  Unseen-answer stories use only held-out words (never in any training story). Training stream: never-repeating, train
  words and train wording only, seed 1000+run seed, eval texts excluded.
- Arms (one change each vs A): A pooled exit (today), B pointer exit, C learned-weight pooling, W reader 32->256,
  BW = B + W. Seeds 0-5 for every arm. 3000 updates x batch 16, lr 1e-3, AdamW wd 0.1, cosine, as PR #29.
- Statistics: paired over seeds (same seed both arms), mean difference with 95% t-interval (df 5, t = 2.571).

## B (pointer exit) vs A, on unseen-answer accuracy (192 questions)
- **PASS:** mean B - A >= +25 points, interval lower bound > 0, and B seen-answer accuracy mean >= A seen mean - 5.
- **Lesion (required for PASS):** uniform pointer weights at test must lose >= half of the mean B - A unseen gain.
- **FALSIFIED:** mean B - A < +8 points.

## W (wider door in) vs A, on seen-answer two-hop accuracy (96 questions)
- **PASS:** mean W - A >= +10 points, interval lower bound > 0. **FALSIFIED:** mean < +3.

## BW (both) vs B, on all two-hop accuracy (192 questions)
- **PASS (way in matters once the exit is open):** mean BW - B >= +10, interval lower bound > 0. **FALSIFIED:** < +3.

## C (sharper averages): read, not judged
- If mean C - A on unseen is within 10 points of mean B - A, "more and sharper vectors" is enough and pointing is optional.

Anything between PASS and FALSIFIED is "in between": 4 more paired seeds, then the line stops (PR #23 rule).
Also reported, not judged: train fit, per-cell accuracy, share of wrong unseen answers that are training words, pointer hit rate.
