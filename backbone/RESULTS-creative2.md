# Creative-2 results (2026-10-24, Vast box 57450816, Qwen3.5-0.8B; prereg `PREREG-creative2.md`)
One change from Creative-1: the checker rejects if/else, comparisons and and/or (`--no-branch`).

| arm | HARD acc (n=300) | HARD answered / precision | C2 dev acc (n=256) | C2 dev answered / precision |
|---|---|---|---|---|
| F0 first try | 9.3 | 100 / 9.3 | 15.2 | 100 / 15.2 |
| C16 check + abstain | 5.0 | 6.3 / 78.9 | 21.9 | 23.0 / 94.9 |
| F1 first try after sleep | 15.7 | 100 / 15.7 | **46.5** | 100 / 46.5 |
| C16 after sleep | 16.0 | 21.0 / 76.2 | **67.6** | 69.1 / **97.7** |

v1 first try on C2 dev: 34.8%. Sleep data: 216 of 1024 pool puzzles fit (310 pairs), 1000 dream programs, and 240 Qwen-fit dreams.

## Verdicts
- K1' FAIL: C16 (5.0) is below F0 (9.3) on HARD. Precision is 78.9%, just under the 80% mark and above the 60% "wrong" line.
  The 0.8B rarely finds a correct three-step program in 16 tries, so checking mostly abstains.
- K2 FAIL: F1 is +6.4 over F0, short of the +10 mark. Not "wrong", because F1 > F0.
- K3 (no mark): on v1's own puzzle kinds (C2 dev), one sleep night takes first try from 15.2 to 46.5, and check-and-abstain
  from 21.9 to 67.6 at 97.7% precision. That beats v1 (34.8) and is now honest: no lookup tables are possible.
- Versus Creative-1, the ban turned precision from 21-41% into 76-98%. That is shown on both sets.

Plain reading: the loop works where the model can find the rule at all (one- and two-step kinds). HARD's three-step held-out
compositions are beyond a 0.8B with 16 samples. Next one-change test: a bigger model (Qwen3.5-4B or the 35B-A3B) on HARD.
