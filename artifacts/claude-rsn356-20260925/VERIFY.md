# rsn-356 verification (sleep research thread, 2026-09-25 19:30 UTC)

**rsn-356 = registered FAIL; the "proved wrong" clause triggered.** Pairing a puzzle with its one-fact twin did
not make the net read the deciding fact. My recount and a blind second recount (did not see RESULTS.md) agree.

| mark | bar | s1 (paired / unpaired) | s2 (paired / unpaired) |
|---|---|---|---|
| T1 fresh panel296 | paired ≥ unpaired + 6 | 231 / 235 FAIL | 231 / 227 FAIL |
| T2 held-out change pairs, both right (600) | paired ≥ unpaired + 30 | 455 / 453 FAIL | 449 / 455 FAIL |
| T3 invented (checked) | ≤ 2 | 0 everywhere PASS | 0 everywhere PASS |

- Proved wrong: T2 within ±12 on both seeds (+2, −6).
- Observation, NOT a registered result: all four twin-mix runs beat 296's plain net (225 / 217) on the fresh panel
  (227-235) and transfer (254-257 vs 238); counting rose to 24-25 of 30 (296: 12). Both arms share the extra
  "one fewer" count puzzles and "I don't know" puzzles, so the mix, not the pairing, is the likely cause. It
  was run on a different machine (BensPC, --workers 0), so it needs its own registered test (296 vs the
  unpaired mix, same machine) before anyone counts it. It is also more counting-like practice, so under Ben's
  "no targeted practice" rule it would need a gain on held-out kinds, not only on counting.
- Compare pairs: 0 both-right in every run (the net gives the same answer to both twins), a floor neither arm moved.
- T3's 0 relies on the fact-check: raw, 5 answers per panel were given without the fact.
