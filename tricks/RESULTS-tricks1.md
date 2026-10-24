# Tricks-1 results (2026-10-24)

Prereg: `PREREG-tricks1.md`. Two RTX 6000 Ada boxes on Vast, vLLM 0.32, ~50 min, ~$1.10. Stopped early when Ben
cut the Vast budget, so the 4B thinking arm (s_think) and 35B thinking on MATH never finished. Raw rows and result
files: `/mnt/project-files/results/tricks1/{small,big}/`. Table from `summarize.py`.

| arm | GSM-Hard | MATH | PopQA | PopQA rare | PopQA popular | tokens/q | tool calls/q |
|---|---|---|---|---|---|---|---|
| 35B-A3B plain (b_plain) | 63.7 [58-69] | 86.7 [83-90] | 27.5 [23-32] | 20.0 | 35.0 | 917 | 0 |
| 35B-A3B thinking (b_think) | 68.7 [63-74] | - | - | - | - | 3235 | 0 |
| 35B-A3B + Wikipedia (b_wiki) | - | - | 32.5 [28-37] | 26.0 | 39.0 | 39 | 0.22 |
| 4B plain (s_plain) | 66.3 [61-72] | 83.3 [79-87] | 16.0 [12-20] | 16.0 | 16.0 | 827 | 0 |
| 4B + Python (s_py) | 67.3 [62-72] | 85.0 [81-89] | - | - | - | 871 | 1.00 |
| 4B vote of 8 (s_vote8) | 68.0 [63-73] | 87.7 [84-91] | - | - | - | 6875 | 0 |
| 4B + Wikipedia (s_wiki) | - | - | 37.5 [33-42] | 35.5 | 39.5 | 52 | 1.04 |

## Verdicts
- **P1 Python tool: WRONG (shown).** +1.0 point on GSM-Hard (paired CI -2.0 to +4.0), below the 2-point "proved wrong" line. +1.7 on MATH.
  The 4B already does its arithmetic right; its misses are reading misses. GSM-Hard is also noisy: 71/300 items no arm gets,
  and on 22-24 of them (depending on tolerance) all five arms agree on one answer that the label disagrees with (e.g. negative egg counts).
- **P2 Wikipedia lookup: MIXED after a scoring fix (see Corrections).** As first scored: 4B + Wikipedia 37.5% vs plain 35B 27.5% (paired CI +5.0 to +14.5), exactly the +10 bar.
  With whole-word matching: 36.5 vs 27.25 (+9.25, just under the bar on all 400); rare facts 33.5 vs 19.5 (+14, passes).
  The 4B searched on every question. The 35B, given the same tool, searched on only 53/400 and guessed the rest.
- **P3 vote / think: PASS on the vote arm (suggested).** 4B vote-of-8 87.7% vs plain 35B 86.7% on MATH (paired CI -1.7 to +4.0),
  but at 8.1x the tokens on MATH (7.5x on GSM-Hard). Re-analysis of the saved samples: stopping once one answer has 3 votes
  keeps 87.7 on MATH (67.7 on GSM-Hard) with 3.8 (4.2) samples on average. The thinking arm did not finish. 4B pass@8 is 95% on MATH and 75% on GSM-Hard, so a good checker could buy more.

## Exploratory (not pre-registered)
- On the 229 GSM-Hard items at least one arm solves: 4B plain 86.9, +Python 88.2, vote8 89.1, 35B plain 83.4, 35B thinking 90.0.
- PopQA's ceiling here is low partly because many names are shared by several people and gold labels are narrow ("journalist" vs "writer").

## Corrections after an independent review (2026-10-24)
1. `popqa_match` matched short aliases inside other words ("US" in "custom", "ro" in "Croatia"). Fixed to whole-word matching
   (tricks1.py, test added). Rescored: s_plain 16.0, s_wiki 36.5 (rare 33.5), b_plain 27.25 (rare 19.5), b_wiki 31.5 (rare 24.0).
2. The tool loop still offered tools on its final round, so 14 b_wiki rows (2 s_wiki) ended on an unexecuted `<tool_call>` that was
   scored as the answer. Fixed: the last round offers no tools.
3. The comparison "4B + lookup beats 35B" is trick vs no trick. On the 53 questions where the 35B chose to search, it scored
   34.0 vs 22.6 for the 4B with search on the same questions (exploratory, n=53). So the boss with forced lookup may beat the
   4B with lookup; that is the next test.
4. "Misses are reading misses" was not backed by an error analysis; treat it as a guess.
