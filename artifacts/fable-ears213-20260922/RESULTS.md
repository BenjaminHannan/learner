# Exp 213 RESULTS — ears write-safety map + certified gate rescore (director-run GPU wave)

Registered verdict: **PASS** (A1, A2, B1 pass; B2 measured). Seal 5/5 OK after the run.
Run: BensPC RTX 5070 Ti, 2026-09-22 14:35:25–14:39:18 (233 s), frozen 119g + 119h checkpoints, seeds 11911/11912/11913.
Deviation: the first launch (14:13) stopped at the first LTT call because the director had not copied
`fable_abstain64_ltt.py` into the staging folder. No test panel had been opened (the taus are sealed before any
test panel loads). The director copied the file (SHA-256 matches the repo) and relaunched the same sealed batch file.

## Marks (per seed, never averaged)

| mark | result |
|---|---|
| A1 probe (48 sealed fictional sentences) | 48/48 relations right, 0 invented names (the old fallback got 30/48 wrong) |
| A2 frozen checkpoints reproduce sealed taus and counts | exact on both models |
| B1 gate mechanics (LTT on cal only, taus sealed before test) | held |

B2, executed / correct / wrong writes at the certified gate (alpha 0.05) vs the old gate:

| model | seed | certified tau | t_seen certified | t_new certified | t_seen old | t_new old | reading94 / 94b (any gate) |
|---|---|---|---|---|---|---|---|
| 119g | 11911 | none (abstain all) | 0 | 0 | 0/0/0 | 2/2/0 | 0 executed |
| 119g | 11912 | none | 0 | 0 | 3/3/0 | 11/11/0 | 0 executed |
| 119g | 11913 | none | 0 | 0 | 3/3/0 | 10/10/0 | 0 executed |
| 119h | 11911 | none | 0 | 0 | 0/0/0 | 0/0/0 | 0 executed |
| 119h | 11912 | 0.834 | 37/37/0 | 28/28/0 | 0/0/0 | 0/0/0 | 0 executed |
| 119h | 11913 | 0.848 | 51/50/1 | 91/90/1 | 16/16/0 | 31/31/0 | 0 executed |

No threshold could be certified at alpha 0.01 or 0.02 for any model-seed.

## What it means
- The invented-relation bug is closed: an ears reading can only be saved under one of 12 mapped notebook relations.
- For the 119h model, a certified gate lets 2 of 3 seeds write several times more correct facts than the old gate
  on the synthetic test panels, with 2 wrong out of 207 writes (about 1%).

## What it does not mean
- The ears cannot read real text yet: on both reading panels they write nothing, whichever gate is used.
- One seed of 119h and all of 119g cannot be certified at all, so this is not a dependable reader.
- Nothing is wired into the agent.
