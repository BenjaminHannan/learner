# brd-6 GPU results (registered run, rental rent-brd6, 2026-09-26)

Registered question: at equal exposure, do twice as many different won puzzles widen coverage more?
Code: unmodified origin/main scripts/claude_brd6.py. Model: plain openbmb/MiniCPM5-1B,
commit 87179e5c1f455ef22e6223592d2d61351b525bfc (only model downloaded).
Test panel md5 018f09ff751477d0b9b001ec78ad2ab2 verified on the rental before the run.
Selftest printed "selftest ok".

## Whole brd6_summary.json

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {"1.0": 41, "1.5": 47},
 "temp_chosen": 1.5,
 "n_train": 800,
 "n_test": 240,
 "temp": 1.5,
 "n_test_3num": 160,
 "base": {"cov@1": 11, "cov@5": 31, "cov@10": 56, "cov@30": 108, "lucky": 231},
 "W4_examples": 199,
 "W8_examples": 398,
 "passes_each": 597,
 "W4_own": 20,
 "W4_wins": 179,
 "W8_own": 33,
 "W8_wins": 365,
 "W4_mean_len": 7.74,
 "W8_mean_len": 7.74,
 "W4_share_3num": 0.859,
 "W8_share_3num": 0.859,
 "W4_steps": 75,
 "W8_steps": 75,
 "W4_seed0": {"cov@1": 18, "cov@5": 64, "cov@10": 95, "cov@30": 162, "lucky": 499},
 "W4_seed1": {"cov@1": 20, "cov@5": 67, "cov@10": 104, "cov@30": 159, "lucky": 531},
 "W4_seed2": {"cov@1": 15, "cov@5": 57, "cov@10": 98, "cov@30": 160, "lucky": 498},
 "W8_seed0": {"cov@1": 18, "cov@5": 70, "cov@10": 109, "cov@30": 161, "lucky": 536},
 "W8_seed1": {"cov@1": 20, "cov@5": 64, "cov@10": 102, "cov@30": 160, "lucky": 521},
 "W8_seed2": {"cov@1": 17, "cov@5": 51, "cov@10": 83, "cov@30": 147, "lucky": 508},
 "ci95_W8_minus_W4_cov30_pct": [-5.72, 2.09],
 "ci95_W4_minus_base_cov30_pct": [15.79, 27.87],
 "ci95_W8_minus_base_cov30_pct": [13.77, 26.61],
 "minutes": 20.8
}
```

## Registered clauses (PASSMARKS-brd6.md)

- PASS ("more distinct puzzles help at equal exposure"): W8's cov@30 >= W4's cov@30 + 12 in
  EVERY seed, AND the 95% interval for W8 - W4 above 0.
  Numbers: per-seed W8 - W4 cov@30 = seed0: 161-162 = -1; seed1: 160-159 = +1;
  seed2: 147-160 = -13. Required >= +12 in every seed: FALSE (0 of 3).
  95% CI for W8 - W4 = [-5.72, 2.09], not above 0: FALSE.
  => PASS clause: NOT MET.
- Proved wrong: upper 95% bound of W8 - W4 below +2.5 points (6 puzzles).
  Numbers: upper bound = 2.09 < 2.5: TRUE.
  => PROVED WRONG.
- Otherwise NOT SHOWN: n/a (proved-wrong fired).
- Inconclusive: W8 fewer than 300 examples (actual 398: no), OR lower 95% bound of
  W4 - base at or below 0 (actual lower bound 15.79 > 0: no).
  => NOT inconclusive.

Registered verdict: PROVED WRONG. At equal exposure (597 example passes, 75 optimizer
steps each arm; matched mean answer length 7.74 and 3-number share 0.859), training on
the wins from 800 practice puzzles (398 examples) does not widen test coverage beyond
training on the wins from the first 400 (199 examples): cov@30 W4 = 162/159/160,
W8 = 161/160/147; W8 - W4 95% CI [-5.72, 2.09].

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (vast.ai offer 45669284, South Korea, rel 0.9975).
- Wall: run launched 03:08:20Z, summary written ~03:29Z; script-reported minutes 20.8.
- Cost: instance 52683960 created 03:00:40Z, destroyed 03:35:25Z (~0.58 h x $0.469/h
  = ~$0.27 of the $1.00 budget; 1 rental, no re-rents; account credit 7.48 at start).
- gpu/ copied back before destroy: brd6_summary.json, streams.json, practice.jsonl,
  log.txt. No weights saved or pushed. Code never edited.
