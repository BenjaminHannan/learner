# Round 7: lifting the real core's 49-token query limit (2026-10-04; marks in PASS-MARKS-7.md fixed before training)

6 runs (seeds 0-5, one per RTX 5090 box; the seed-0 box was about 20x slow and was replaced). Rows in `results7/` (sha-checked, 36 files), table in `results7/SCORE7.txt`, scorer `score7.py`. Control = the six TABV runs of round 6 (same seeds, frames and short sets), nothing re-run.

## Verdict by the fixed marks: **PASS** (all three parts)
1. **RUNS: met.** All 192 long questions (55 to 150 tokens) ran in all 6 seeds, no refusal. The 49-cap core raises "query physical cap49 includesEOS" on every one (shown on CPU on a 60-token query; it runs once the cap is 160).
2. **USABLE: met.** Long-set chain 66.6% (SD 2.7; seeds 63.0 to 71.4), mark was >= 50.
3. **NO-DROP: met.** Paired gain LONG minus TABV on the short sets:
| chain, mean of 6 (SD) | TABV | LONG | paired gain (95% interval) |
|---|---|---|---|
| old own-wording, all 192 | 78.3 (3.4) | 78.0 (3.9) | -0.3 (-4.9 to +4.4) |
| Blind-1, all 192 | 76.2 (5.3) | 77.6 (5.1) | +1.4 (-8.1 to +10.8) |
| Blind-2, all 192 | 62.5 (5.4) | 65.9 (3.1) | +3.4 (-0.5 to +7.2), 5/6 up |
Gate met (train fit 89 to 96%).

- Shown: long questions are no harder than short ones for this model. Long-set chain by length: 55-80 tokens 69.0%, 81-110 tokens 62.7%, 111-150 tokens 67.5%. Call 1 right 79.9%, call 2 given call 1 83.4%.
- Shown: by layout on the long set: chat 94, spreadsheet 88, first-person 92, question-first 80, table 70, receipt 68, other 58, report 51, instruction 46, ledger 44 (the same weak styles as the short sets).
- Suggested, untested: the cap was only an input guard; the core's position codes (sinusoidal, up to 4095) and relative attention handled 150 tokens after training on longer items.
- Not shown: longer than 150 tokens; long questions whose extra text contains numbers or quantity changes (the fillers were digit-free by design, and the real calculator path takes every number in the text as a literal); the PC checkpoints, which were trained with the 49 cap and would need the same retraining.
- Caveats: filler for the long eval set was written by a separate Claude worker; the layouts come from the two blind sets (Claude-written); fresh weights.

Cost round 7: about $0.6 (six boxes about 6-8 min each at $0.45/h plus the slow box ~$0.15); credit $11.21 at 16:36Z (shared).
