# Round 4: composed two-step training wording on the real model (2026-10-04; marks in PASS-MARKS-4.md fixed before training)

**Verdict by the fixed marks: PASS.** Chain rate (both calculator calls right, in order) on the 192 fresh two-step questions: 54.9% -> 81.4%, paired gain +26.6 (95% interval +14.8 to +38.3), all 6 seeds up. Needed: gain >= +10 and lower bound > 0.

Change: training wording only. COMP = the round-3 fixed frames plus ~11,000 composed frames (narrative / question-first / table / distance built from interchangeable parts; any frame sharing a sentence or 6-gram with an eval frame dropped). Same seeds 0-5, same eval, same everything else. Baseline = round-3 TWO runs. Rows in `results4/` (sha-checked).

| mean of 6 seeds (SD) | TWO (round 3) | COMP | paired gain (95% interval) |
|---|---|---|---|
| **chain, all 192** | 54.9 (9.3) | **81.4 (4.6)** | **+26.6 (+14.8 to +38.3)**, 6/6 up |
| call 1 right | 78.2 (8.2) | 93.8 (0.7) | +15.5 (+6.6 to +24.5) |
| call 2 right given call 1 | 70.0 (7.8) | 86.8 (4.7) | +16.8 (+6.8 to +26.8) |
| table layout | 29.9 (17.7) | 61.5 (4.3) | +31.6 (+9.9 to +53.3), 6/6 |
| question-first | 51.0 (15.2) | 78.5 (8.0) | +27.4 (+4.6 to +50.2), 5/6 |
| narrative | 61.5 (15.8) | 88.2 (9.0) | +26.7 |
| distance | 77.1 (10.6) | 97.6 (1.6) | +20.5 |
| unseen / seen finals | 57.1 / 52.6 | 80.9 / 81.9 | +23.8 / +29.3 |

- Shown: gate met (train fit 97.9-100%). Final answer right 81.0% vs chain 81.4%, so the copy path still carries the result (no answer shortcut).
- Shown: the gain is on every layout and seed; the seed spread also shrank (SD 9.3 -> 4.6). Table layout is still the weakest (61.5%).
- Suggested, untested: wording variety, not model depth, was the main limit; remaining errors are mostly table layout and call 2 after a wrong call 1.
- Not shown: layouts nobody wrote (eval layouts are still four families authored by the same model, fast lane); questions over 49 tokens (core cap); the PC checkpoints.
- Operational: 3090 boxes with the cu124 image failed pip on two boxes (no run started); the two 5090 boxes (torch 2.8 cu128 image) finished 2 runs in ~13 min vs ~23 min on a 3090.
