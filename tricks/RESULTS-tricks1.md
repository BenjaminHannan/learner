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
  and on 24 of them all five arms agree on one answer that the label disagrees with (e.g. negative egg counts).
- **P2 Wikipedia lookup: PASS (shown).** 4B + Wikipedia 37.5% vs plain 35B 27.5% (paired CI +5.0 to +14.5); on rare facts 35.5% vs 20.0%.
  The 4B searched on every question. The 35B, given the same tool, searched on only 53/400 and guessed the rest, so it gained just 5 points.
- **P3 vote / think: PASS on the vote arm (suggested).** 4B vote-of-8 87.7% vs plain 35B 86.7% on MATH (paired CI -1.7 to +4.0),
  but at 7.5x the tokens. The thinking arm did not finish. 4B pass@8 is 95% on MATH and 75% on GSM-Hard, so a good checker could buy more.

## Exploratory (not pre-registered)
- On the 229 GSM-Hard items at least one arm solves: 4B plain 86.9, +Python 88.2, vote8 89.1, 35B plain 83.4, 35B thinking 90.0.
- PopQA's ceiling here is low partly because many names are shared by several people and gold labels are narrow ("journalist" vs "writer").
