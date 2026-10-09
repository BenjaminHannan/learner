# C1 stop result (pilot 3, masked sampler, DEV only; T1 and T1b never read)
Source: creative/results/pilot3-s100|s101/pilot.json (commits dcdcaf011, 9e63311d9). Both parents: gates passed (signal 786 / 811 practice puzzles, aim, sameness 9.8 / 10.6 distinct legal programs per puzzle); PC frozen at lr 3e-4, 16 visits, 688 updates (the 32-visit retry was worse on both).

| | s100 | s101 |
|---|---|---|
| N masked luck (distinct tries) / twin luck | 13.2% / 4.6% | 13.4% / 5.6% |
| PC masked luck, PC/N, PC-N | 14.7%, 1.11x, +1.5 | 15.5%, 1.16x, +2.1 |
| N -> PC masked first try | 18.8% -> 28.1% (+9.3) | 20.3% -> 31.2% (+10.9) |
| N -> PC plain first try | 10.2% -> 11.7% (+1.6) | 8.6% -> 14.8% (+6.3) |
| N -> PC plain luck over samples (8 per puzzle, repeats counted) | 9.9% -> 12.7% (1.29x, +2.8) | 8.6% -> 14.3% (1.66x, +5.7) |
| puzzle-record loss after sleep (N -> PC) | 4.78 -> 2.15 | 4.86 -> 1.96 |
| skills harm vs warmed | 0.1 points | 0.4 points |

Rule applied (roadmap, 10-06): PC gate judged on plain luck counted over samples at the frozen setting: s100 misses (1.29x, +2.8), s101 passes (1.66x). C1 retires at its DEV gate.

## Shown (my own check of the cap the roadmap thread found)
- At the chosen temperature (0.14 and 0.21) the masked sampler draws about 165 samples per puzzle to get about 10 distinct programs (duplicate rate 94%). Luck over distinct tries is accepted / kept, and a DEV puzzle has 1.97 distinct correct programs on average (median 1, max 5; enumerated over all 52.8 exact legal programs per puzzle). So distinct-try luck is capped near 1.97 / 10 = 20%, and N already sits at 13%: the 1.6x mark (21%) was above the cap. N found 1.30 / 1.42 of the 1.97 correct programs per puzzle; PC found about 10% more.
- The sleep itself worked: puzzle-record loss fell by more than half, first try rose by +9 to +11 points masked, and +1.6 / +6.3 plain.
- s100 at lr 1e-3, 16 visits reached plain luck 16.2% (1.64x) and plain first try 18.0%. Not taken: choosing it after seeing it would be a fourth change made after the numbers.

## Not shown
- Whether a higher temperature (more distinct tries, lower luck base) would give PC room on distinct-try luck: untested.
- What the 128-puzzle noise is on the plain-luck ratio (8 samples per puzzle): the roadmap thread put it at a few points; I did not measure it.

## Small items
- Mac pilot 3 ran lr 3e-3 and 1e-2 rows because the CLI default for `--lrs` still listed them (my bug, fixed in 4f0a94cfb; they were all outside the skills limit and did not change the pick).
- 4.4 h per parent on the Mac CPU, against my 3-4.5 h estimate.
