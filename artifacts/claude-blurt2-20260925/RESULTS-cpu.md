# blurt-2 learning loop, CPU run: PASS (registered marks in PASSMARKS-blurt2.md)

Run: thread CPU container, 4 cores, $0, 172 minutes, plain MiniCPM5-1B (snapshot 87179e5c), code main 62f8df010.
The GPU repeat (handoff/queue/blurt2-loop.md) has not run yet; if it finishes, PASS needs it too.

| | count |
|---|---|
| Temperature (DEV rule) | 1.0 (42 lucky of 1,740 DEV blurts vs 40 at 1.5) |
| Fresh test puzzles (23 overlaps with practice/DEV dropped) | 127 |
| S0: reasoner alone before sleep | 6/127 |
| Practice: reasoner right | 21/400 |
| Practice misses cracked by at least one of 30 blurts (wins) | 173/379 (313 of 11,370 blurts right, 2.8%) |
| W (own right + wins, 194 examples), seeds 0 / 1 | 15/127, 19/127 (mean 17) |
| C (own right only, repeated to 194), seeds 0 / 1 | 6/127, 6/127 (mean 6) |
| Practice wins the reasoner then solves alone: W / C | 47, 44 / 4, 3 (of 173) |

- L1 learning: mean W − S0 = 17 − 6 = +11 (mark ≥ +8): PASS.
- L2 the creative wins caused it: mean W − mean C = +11 (mark ≥ +5), and each W seed (15, 19) beats each C seed
  (6, 6): PASS.
- Proved-wrong clause: not triggered. Inconclusive clauses: not triggered (173 wins; S0 5%).
Verdict: PASS on the CPU run.

What it means: when the 1B could not solve a puzzle, its random rule-keeping guesses sometimes hit; practising those
hits in a short "sleep" made the 1B solve almost three times as many brand-new puzzles on its first try (6 to 15-19 of
127). Practising only what it already knew did nothing (6 to 6).
What it does not mean: this is one puzzle family (fresh puzzles of the same kind); no transfer to other problems is
shown. 17/127 is still low. The practice wins are only partly remembered (about 45 of 173). Two seeds is a small
sample; the seed gap (4) is smaller than the effect (+11).
Wins for the sleep thread: cpu/wins/wins.jsonl (173 rows, agreed format, source "creative-blurt").
