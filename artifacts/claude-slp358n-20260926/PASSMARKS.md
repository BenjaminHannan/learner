# slp-358n pass marks (fixed before any run; 2026-09-26 ~00:10 UTC, sleep research thread)

Question: does a night of sleep (practising the day's puzzles with checked answers, mixed half-and-half with old
practice, small steps) make the small reasoner better at FRESH puzzles of the day's kind, compared with a night of
the same length spent only on old practice, and without harming what it already knew?
Code: scripts/claude_slp358n_nights.py (imports scripts/claude_rsn358a_run.py and claude_rsn358a_envs.py).
Seeds 1 and 2, 3 day/night cycles, CPU. Scored by exact code after 8 rounds of thinking. Tests are fixed, made by
code (seed 58600), never a day item (day items that happen to equal a test item are dropped and counted).

Arms: S sleep (day puzzles + right answers), R rehearsal-only night (same steps), Z placebo night (answers shuffled
between same-shape puzzles), N no night.

| mark | what (after night 3, each seed) | pass |
|---|---|---|
| M1 learns from the day | S − R on day_grids (400 fresh 5x5 grids) | ≥ +20 |
|  | S − R on day_sums (400 fresh 5-6 digit sums) | ≥ +20, or both S and R ≥ 360 (ceiling: then sums are uninformative and say so) |
| M2 not a placebo | S − Z on day_grids and on day_sums | ≥ +20 each (same ceiling rule for sums) |
| M3 no harm | S on harm_sums4 and harm_grids4 (300 each, practised sizes) | ≥ N − 6 each |
| report | transfer_sums8, transfer_grids6; mornings after nights 1 and 2; the day's own tries; Z and R vs N harm | report |

**PASS = M1, M2 and M3 on both seeds.** Otherwise FAIL (stays FAIL).
**Proved wrong ("a night on the day's checked answers teaches the reasoner more than extra old practice"):** S − R ≤ +5
on day_grids AND on day_sums on both seeds (with neither at the ceiling).

Predictions: M1 grids likely (5x5 is new to it and the night shows it answers); sums may sit near the ceiling;
M3 likely with half rehearsal and lr 1e-4; Z likely hurts the day kinds (wrong answers) and may hurt harm tests.
This is a small-net, CPU test of the night pipeline for the reasoner, not a claim about the joined agent.
