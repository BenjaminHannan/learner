# Creative-1 results (2026-10-24, Vast box 57448229, Qwen3.5-0.8B; prereg `PREREG-creative1.md`)

| arm | HARD acc (n=300) | HARD answered | HARD precision | C2 dev acc (n=256) |
|---|---|---|---|---|
| F0 first try | 10.7 | 100 | 10.7 | 16.4 |
| C16 check + abstain | 5.3 | 16.7 | 32.0 | 21.5 (answered 37.1, precision 57.9) |
| F1 first try after sleep | 14.0 | 100 | 14.0 | 35.5 |
| C16 after sleep | 14.3 | 68.3 | 21.0 | 40.2 (answered 98.0, precision 41.0) |

v1's first try on C2 dev was 34.8%. Sleep data: 307 of 1024 pool puzzles had a fitting program (415 pairs), plus
1000 dreams with known programs and 334 dreams where Qwen's own program fit. That is 1749 pairs in total.

## Verdicts
- K1 FAIL, and the pre-registered "wrong if" holds: C16 (5.3) <= F0 + 5. **Shown.**
- K2 FAIL: F1 is +3.3 over F0, short of the +10 mark. Not "wrong", because F1 > F0.
- K3: after one night, the first try on C2 dev goes from 16.4% to 35.5%, about level with v1's 34.8%. But see the cause below.

## Cause (shown, from the logged examples)
Most of the "fitting" programs are lookup tables of the examples, such as `lambda x: 3200 if x == 20 else 5408 if x == 26 else 648`.
They pass the check and then return a wrong answer on the new input. Sleep trained on those, so the habit grew. After
sleep, F0 "fits the examples" on 77% of C2 dev puzzles but gets only 35.5% right. Lesson: a check is only worth as much
as the cheats it rules out. Creative-2 (`PREREG-creative2.md`) bans branching programs, as one change.
