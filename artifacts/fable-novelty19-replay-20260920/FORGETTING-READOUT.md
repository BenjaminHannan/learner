# Experiment 19 — secondary readout: does offline practice cause forgetting?

Written 2026-09-20 by Fable BEFORE any registered seed (1900–1902) has been generated, trained or scored. Secondary and descriptive; it cannot change experiment 19's primary verdict. Purpose: decide whether Astra's experiment 20 (recent-activity inhibition, `design/v3/20-top-mechanism-preregistration-draft.md`) has a measured problem to solve.

## Measurement
For each architecture (D, T), seed (1900, 1901, 1902) and offline arm (R, G, U): score the awake-final checkpoint and the offline-final checkpoint on the same development panels. Cells used: the 7 F (ordinary-fit) cells and the 4 H (short held-out ending) cells. Drop = awake-final answers+strict count minus offline-final count, out of 64. Only runs whose awake checkpoint passed the awake-fit gate count; others are reported as "not scorable". Every seed and cell listed, nothing averaged.

## Rule fixed in advance
"Real forgetting" for an (architecture, arm) = at least one F or H cell drops by >= 7/64 in >= 2 of 3 seeds (same cell not required).
- Real forgetting in any arm of D -> experiment 20 has a problem to fix in our system; send to Astra.
- Real forgetting in T only -> note as a baseline weakness; experiment 20 stays parked for our system.
- None -> experiment 20 parked; no build.
An H cell that starts below 58/64 at awake-final is excluded from the rule for that seed (nothing to forget).

## Fable's predictions
| # | Statement | Probability |
|---|---|---|
| P62 | D shows real forgetting in at least one arm | 0.15 |
| P63 | T shows real forgetting in at least one arm | 0.35 |
| P64 | In D, arm R (pure rehearsal) has no cell dropping >= 7/64 in any seed | 0.80 |
