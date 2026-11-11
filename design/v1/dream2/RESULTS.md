# Dream2 creative-sleep A/B — RESULT (2026-10-23)

Pre-registration: design/v1/dream2/PREREG.md (before any run). Two RTX 3090 boxes (deviation recorded), $0.33 + $0.47.
Raw: results/control/final.json, results/treat/final.json. Creative dev, n = 256 (about 51 per kind), greedy first try.

| Kind | CONTROL (no dreams) | TREAT (256 dreams/night, 1-4 steps) |
|---|---|---|
| last_digit | 82.4% | 86.3% |
| square | 84.3% | 82.4% |
| affine | 1.9% | 0.0% |
| double_add | 5.9% | 3.9% |
| sq_plus | 9.8% | 5.9% |
| **hard-kind mean** | **5.9%** | **3.3%** |
| overall first try | 36.7% | 35.5% |

- Marks (shown): P1 needed TREAT hard mean >= 15% and >= CONTROL + 10 -> **FAIL**. Proves-wrong (< 5%, or < CONTROL + 3)
  -> **met: random dreams do not teach the hard kinds.** P2 (no harm to easy kinds): held (+3.9, -1.9 points).
- Disclosure: held-out-form overlap of the dreams was tiny (square 2.7%, last_digit 2.0%, double_add 0.8%, affine/sq_plus 0%).
- Records: CONTROL 798 / 1,041 per night; TREAT 1,047 / 1,249 (incl. 256 dreams each).
- Reading (suggested): uniform random programs almost never have the shape the hard kinds need (a*x+b with a, b in 3..15
  built from constants 1, 2, 10, 100), so dreams add volume, not the right skill. Next single change to try: give the
  executor the example numbers as constants (so a*x+b is 2 steps), or a curriculum of dreams biased to multiply-then-add.
- Control alone reproduces V1 FULL's creative dev (36.7% vs 34.8%), which is a useful reproducibility check.
