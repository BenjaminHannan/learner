# E: pass marks for "practice shortens learned thinking time" (written before any H12 run exists; nothing here has been scored)
Fixed 2026-09-28 before any run. Not changed after a score is seen. Scope: loop reasoner on mazes; not the small card experiments, not the village model.

## The one change
None of its own. This is a readout of the H12 test (stop head trained on mazes during the 2,048 adaptation updates; every other thing identical to the baseline ruler). The only thing varied is the amount of practice k (the ruler's rungs 1..16384). Needs H12's holdout JSONs (same schema as eq-runs/*/holdout.json) for practised loop, 2 seeds (0,1). If H12 does not run both seeds, E is VOID.
Optional control (also from H12 if it runs it): fresh loop with the trained stop, same rungs. Report-only.

## Marks (9x9 holdout, mean_rounds and right, per seed)
Let LOW = mean of mean_rounds at k=16,64; HIGH = mean at k=1024,4096,16384. Rungs k=1,4 excluded (right ~0, nothing to think about).
| mark | pass |
|---|---|
| T1 validity | H12's own pass (the stop is now deciding its own time: cap hits < 150 of 300 at k>=64 in both seeds). If not met, E is VOID, not a fail. |
| T2 shorter with practice | HIGH <= LOW - 4 rounds in BOTH seeds. |
| T3 monotone-ish | at least 2 of the 3 steps 16->64->256->1024->4096->16384 windows: rounds at k=16384 <= rounds at k=64 and <= rounds at k=256, in both seeds. |
| T4 not just quitting early | right at k=1024,4096,16384 (learned stop) >= fixed-depth-16 right - 6 of 300, every rung, both seeds. |
| T5 not by chance | difference between seeds in HIGH-LOW has the same sign; if the fresh control is run, fresh HIGH-LOW is reported and E holds only if practised (HIGH-LOW) is at least 4 rounds more negative than fresh in both seeds. |
PASS = T1 valid and T2, T3, T4 met (T5 sign rule met, control rule met if run).

## Result that proves the idea wrong
T1 valid and HIGH >= LOW in either seed, or right falls more than 6 of 300 below fixed-16 at any k>=1024 while rounds fall (thinking shortened by quitting, not by skill).

## Blind recount
A separate step recounts LOW, HIGH and the T2-T5 verdict from the raw JSONs and these marks only.
