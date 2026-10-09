# Round 6: report / ledger / receipt / spreadsheet practice, scored on a second independent layout set (2026-10-04; marks in PASS-MARKS-6.md fixed before training)

12 runs on six RTX 5090 boxes (TABV control and RLV, seeds 0-5), each scored on three eval sets. Rows in `results6/` (sha-checked, 60 files), table in `results6/SCORE6.txt`, scorer `score6.py`.
Blind-2 = 12 new layout families (3 report, 2 ledger, 2 receipt, 2 spreadsheet, 3 other) written by a separate Claude worker; I never opened the file, so the practice frames could not be matched to it.

## Verdict by the fixed marks: **partial, no claim** (PASS needed >= +5 with interval above 0; FAILS < +2)
| chain, mean of 6 (SD) | TABV | RLV | paired gain (95% interval) |
|---|---|---|---|
| **Blind-2, all 192 (headline)** | 62.5 (5.4) | 66.3 (2.7) | **+3.8 (-1.5 to +9.1)**, 4/6 up |
| Blind-2 report | 63.5 | 69.8 | +6.2 (-1.5 to +13.9) |
| Blind-2 ledger | 66.7 | 68.8 | +2.1 (-10.1 to +14.3) |
| Blind-2 receipt | 51.6 | 53.1 | +1.6 (-6.1 to +9.3) |
| Blind-2 spreadsheet | 68.2 | 69.3 | +1.0 (-8.8 to +10.9) |
| Blind-2 other | 62.2 | 68.1 | +5.9 (-1.5 to +13.3) |
| Blind-1 all (guard) | 76.2 | 77.3 | +1.1 (-8.2 to +10.5) |
| old own-wording all (guard) | 78.3 | 85.3 | +7.0 (-0.1 to +14.1) |

- Shown: both guards held (neither lost points); train fit 91-98% (gate met). All gains point the same way (every kind and every eval set is >= 0) but none is significant except call 1 on the old set and "seen" finals on Blind-2.
- Shown: a new author's layouts are harder: TABV scores 62.5% on Blind-2, 76.2% on Blind-1 and 78.3% on my own wording. The recipe's real out-of-style level is about 62-76%, not 81%.
- Shown: the weakest Blind-2 families are the warehouse slip (47-49%), recipe steps (39-46%) and shop receipt (56-57%); the strongest are the tweet post (82-90%) and sheet cells (76-81%).
- Suggested, untested: style practice gives a small, consistent lift (+1 to +6) that more seeds might confirm but does not close the gap to new authors; with 6 seeds (SD 3-5) a true +4 cannot be told from zero.
- Not shown: any person-written or other-vendor layouts; wording the practice frames cannot reach (receipts with abbreviations).
- Caveats: Blind-2 written by a Claude worker, grammar unchecked; the control TABV was re-run (different filter), not reused.

Cost round 6: about $0.8 (6 boxes x ~25 min, rates $0.39-0.48/h); credit $15.78 at 15:41Z (shared).
