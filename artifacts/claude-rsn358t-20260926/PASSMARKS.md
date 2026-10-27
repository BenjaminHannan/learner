# rsn-358t pass marks (fixed before any 358t or 358i result; sleep research thread, 2026-09-26 15:11 UTC)

Question (unchanged from 358a and 358i): does the loop (it thinks in rounds and has a learned stop) solve BIGGER puzzles than it practised better than its plain same-size twin?

**Design change tested (one): the loop's training schedule.** It is copied in outline from the Tiny Recursive Model (TRM):
- The state is carried from segment to segment, detached.
- Each segment runs 4 rounds without gradient, then 4 rounds with gradient.
- Each segment is graded once, on its final round only. The answer is never graded on a fresh first pass alone.
- A puzzle leaves the batch once it has been right at the end of 2 segments in a row.
- A batch lives up to 16 segments.
- The weights are averaged with EMA 0.999, and the EMA weights are the ones tested.

Code: scripts/claude_rsn358t_run.py (docstring, `selftest`). Why: artifacts/claude-rsn358i-20260926/NOTE-vs-TRM.md rows 1, 2 and 4.

**Everything else is 358i's (scripts/claude_rsn358i_run.py):**
- the legend grids and half-narrow attention;
- the net sizes, data stream, 60,000 optimizer steps, batch 256, lr and schedule;
- the v2 stop rule with 48 test rounds.

The plain arm's training is 358i's, unchanged. It also keeps an EMA copy, which touches nothing it trains on.

This was designed with no 358i or 358t number known. The unregistered maze trial and the 358i small trial were known (both are in the repo).

**Seeds:** 1, 2, 3, 4. Each seed trains 1 loop and 1 plain, so 8 trainings.
**Tests:** artifacts/claude-rsn358i-20260926/tests/, byte-identical to 358i's sealed files. They are TEST-ONLY and each is run once per checkpoint.

**Plain for grading:** for each test, take the higher 4-seed mean of plain raw (final-raw.pt) and plain EMA (final.pt), and use that arm's per-seed counts. This way EMA cannot be the loop's only edge.

| mark | pass |
|---|---|
| G0 validity | On every seed, both loop EMA and plain raw are right on >= 210/300 of the practised-size tests in at least 2 of 3 kinds. Otherwise INCONCLUSIVE. |
| G1 bigger | The 4-seed mean of loop - plain is >= +30 on at least 2 of sums6 / grids6 / numbers5, and >= -10 on the third. AND on at least 3 of 4 seeds, loop - plain > 0 on each of those (at least 2) tests. |
| G2 practised | The 4-seed mean of loop - plain is >= -10 on each practised-size test. |
| G3 stop | On at least 3 of 4 seeds: loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test. AND mean rounds on sums6 > on sums4. |
| G4 report | Every test, per seed and arm: loop EMA, loop raw, plain raw, plain EMA. The loop at fixed rounds. sums8/10/12 and grids7. |
| G5 report | "Does the gap grow?": the 358t loop - plain gap next to 358i's gap per test (358i's RESULTS.md), and 358t loop minus 358i loop. Report only; it never changes G0-G3. |

**PASS = G0, G1, G2 and G3.** Anything else with G0 met is a FAIL, and it stays a FAIL.
**Proved wrong** (for this schedule): G0 met, and the mean loop - plain is <= +5 on all three bigger tests.

**Next step after each outcome** (EXIT-RULE-ADDENDUM-1):
- FAIL: the next learned design, two states (a separate scratch state and answer, TRM row 3).
- PASS: this schedule replaces 358i's for 358b3, the size-scaling test 358s and 358m.

**Prediction before running:** PASS 30%.
- The 358i trial showed the loop leading on grids with the old schedule. So this mostly tests whether sums6 clears +30, and whether rounds past 16 now help.
- Main risk: at equal optimizer steps each puzzle is seen for up to 16 segments. The loop therefore sees fewer distinct puzzles than 358i's loop did.
