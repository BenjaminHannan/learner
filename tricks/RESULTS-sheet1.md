# Sheet-1 results (2026-10-24): Claude-written instruction sheets for the 4B

Plan and pass marks: `PREREG-sheet1.md` (fixed before the run, including the normal-gold rule). Ran on Ben's PC (RTX 5070 Ti,
vLLM 0.32 in eager mode, greedy), 12:24-13:02Z, commit 99b57b516. Files: `results_sheet1/` (result + summary) and
`/mnt/project-files/results/tricks-sheet1/` (all rows). Two Vast attempts before this produced nothing (slow downloads, ~$0.39).

## Verdict
- Primary rule: best general sheet on train = 4 "Compute then audit". Test: **+6.0 points (95% CI +1.0 to +11.0) → PASS**.
- Pre-registered check: on the 133 test questions with a normal gold (non-negative whole number) the same sheet gains
  **+0.0 (CI -3.8 to +3.8) → QUIRK-DRIVEN**. Shown: the gain is GSM-Hard's odd labels, not better problem solving.
- Read-through: of the 19 questions sheet 4 flipped from wrong to right, 15 have odd golds (fractional or negative answers the
  baseline rounded or "fixed"). On normal golds it fixed 4 and broke 4.

## Every sheet (test, 200 questions; points vs baseline)
| # | set | sheet | test acc | tokens | all | normal-gold (133) | odd-gold (67) |
|---|---|---|---|---|---|---|---|
| 0 | - | baseline (PY_SYS) | 66.0 | 874 | - | - | - |
| 1 | general | Literal program translation | 68.0 | 422 | +2.0 | **-9.0** | +23.9 |
| 2 | general | Equation sheet then compute | 77.0 | 522 | +11.0 | +0.0 | +32.8 |
| 3 | general | Concise decisive solver | 75.5 | **255** | +9.5 | +0.8 | +26.9 |
| 4 | general | Compute then audit (picked on train) | 72.0 | 805 | +6.0 | +0.0 | +17.9 |
| 5 | general | Exact arithmetic discipline | 73.5 | 632 | +7.5 | +0.0 | +22.4 |
| 6 | general | Worked-example template | 54.0 | 231 | **-12.0** | **-22.6** | +9.0 |
| 7 | quirk | Literal rules, no sanity fixes | 75.0 | 396 | +9.0 | +0.0 | +26.9 |
| 8 | quirk | Program-first answer key | 74.0 | 285 | +8.0 | -0.8 | +25.4 |
| 9 | quirk | Solve with small numbers first | 76.0 | 563 | +10.0 | -0.8 | +31.3 |
| 10 | quirk | Quantity table then equation | 74.0 | 580 | +8.0 | -3.0 | +29.9 |
| 11 | quirk | Strict brevity budget | 70.5 | 208 | +4.5 | -6.0 | +25.4 |
| 12 | quirk | Compute then checklist | 78.0 | 483 | +12.0 | +2.3 | +31.3 |

Baseline: 75.9% on normal golds, 46.3% on odd golds. No prompt hit the length guard.

## What it means
- **Shown:** on ordinary word problems, none of the 12 sheets made the 4B more accurate (best +2.3, CI includes 0). All the
  headline gains (+6 to +12) come from teaching it the benchmark's quirk: report the raw computed number, even when it is a
  fraction of a person. Writing sheets from failures finds whatever the scorer rewards, so the check on normal rows was needed.
- **Shown:** sheets can hurt a lot. The "template" sheet cost 23 points on normal golds; the "literal program" sheet cost 9.
- **Suggested (not pre-registered):** sheets cut length a lot at no cost on normal golds. "Concise decisive solver" used 255
  tokens per question instead of 874 (-71%) and scored +0.8 on normal golds. On the Mac that is about 3x faster answers. This
  is the useful finding for a speed-bound local assistant; it needs its own test on a cleaner set before relying on it.
- For the RANKING: "Claude-optimized skill sheet" moves from Tier 1 to "no accuracy gain shown on maths word problems"; keep
  "short-answer sheet" as a cheap speed trick to test.

## Caveats
- One benchmark (GSM-Hard), one model (4B), one sheet-writing round. GSM-Hard's odd golds make it a poor target for prompt search.
- Eager mode on the PC changes speed only; sampling was greedy, as on Vast.
