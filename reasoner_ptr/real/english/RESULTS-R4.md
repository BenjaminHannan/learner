# English with generated practice questions: results (6 paired seeds, 2026-10-04)

Marks: `PASS-MARKS-R4.md` (commit d4695114e, before training). Same fresh test as round 3 (`FRESH-EN-R3.json`,
192 questions). One change from round 3: 8000 generated examples per seed (`gen_english.py`) added to the 48-question
bank. Numbers: `ANALYSIS-R4.json`; rows in `results4/box*/out/`. Fast lane, not a sealed headline test.

## Verdict: both marks PASS (shown)

| | fresh exact | contains | new-word answers | yes/no | train bank fit |
|---|---|---|---|---|---|
| allptr, bank only (round 3) | 34.7% | 42.8% | 33.0% | 47.0% | 100% |
| **allptr + generated (round 4)** | **92.6%** | 94.4% | 93.0% | 90.9% | 94.6% |
| bare 1.2B LM, zero-shot | 29.7% | 76.0% | 34.8% | 0.0% | |
| bare 1.2B LM, 8-shot (the bar) | 75.0% | 77.6% | 76.8% | 72.7% | |

- Judged 1, generated vs bank only: **+57.9 points, CI +38.7 to +77.1** (per seed 68, 21, 68, 69, 61, 60). PASS (mark +15).
- Judged 2, vs the best bare-LM row (8-shot, 75.0%): **+17.6, CI +14.7 to +20.6** (per seed 14 to 21). PASS (mark +10).
  Every seed beats the bare model by at least 14 points.
- Seeds are now tight: 89% to 96% (round 3: 21% to 68%).
- Zeroing the core's 8 vectors drops it to 0.0%. On the generated held-out panel (held-out names and nouns) it gets 99.7%.
- Per family: negation 99, giver/recipient 98, comparison 95, two relations 95, which-one 87, event order 82
  (8-shot LM: 81, 88, 84, 72, 75, 50). Event order is the weakest for both.
- Wrong answers are now near misses ("her porch" for "the porch", "lit a tall candle by the piano"), plus some
  yes/no flips and swapped names.

## Caveats (suggested, untested)
- In-family test: the fresh set and the generator cover the same six question kinds. Word overlap between a fresh
  passage and its nearest generated passage is low (mean max word-Jaccard 0.27; none above 0.8), and seed-0 accuracy
  is 86% on the less-similar half and 92% on the more-similar half. New kinds of question are untested.
- The talker sees every prompt word (allptr), so the frozen LM does part of the reading; the lesion says the core is
  still needed, but zeroing is a crude lesion.
- The fresh set was written by a helper agent and read once by me; nobody else has checked it.
- The 8-shot LM is one prompt format; a better prompt could raise the bar.

## Cost
About $0.89 on vast for 6 boxes (`LEDGER.md`); credit $4.08 at 05:31 UTC.
