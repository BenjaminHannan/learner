# reframe-5 result: FAIL (not proved wrong) — reframing helped on 3-number puzzles and hurt on 4-number ones

Marks: PASSMARKS-reframe5.md (main 134415540, committed 17:57:18 UTC; the run started when ask-24 ended, ~20:33 UTC, and finished 21:30 UTC).
Run: the creative thread's container CPU, 57.1 minutes, base MiniCPM5-1B, no training. Summary: cpu/reframe5_summary.json.
Test: 79 fresh puzzles (1 dropped as a DEV overlap), 52 with 3 numbers and 27 with 4. The budget was 30 samples per
puzzle in both arms (reframe used 2,370 = 79 × 30).

| | Puzzles solved (of 79) | 3-number (of 52) | 4-number (of 27) | Correct full answers |
|---|---|---|---|---|
| plain (30 guesses at the puzzle) | 39 | 32 | 7 | 68 |
| reframe (30 guesses spread over easier pieces, carried back by code) | 46 | 41 | 5 | 95 |

- R1 (reframe ≥ 1.5 × plain, so ≥ 58.5): NOT MET (46).
- R2 (4-number: reframe ≥ plain): NOT MET (5 vs 7).
- Proved wrong (reframe ≤ plain overall): not met (46 > 39). Inconclusive (plain < 10): no.
- Verdict: FAIL on the registered pass marks; the idea is not proved wrong.
- Check: every one of the 95 sub-puzzle hits carried back to a correct full answer (95 = 95), as the selftest
  requires. Sample counts add up.

What it means (shown, puzzles only): spending guesses on code-written easier pieces solved 9 more 3-number puzzles
(32 to 41), but 2 fewer 4-number ones (7 to 5). There, the pieces still have 3 numbers, and splitting 30 guesses over many
restatements leaves few guesses for each. Suggested: reframing helps when a piece becomes easy (2 numbers) and costs
when it does not. A smarter split (pick the most promising restatements, as a feasibility judge could) is
untested. It would be a separate registered test, not a re-run of this one.
