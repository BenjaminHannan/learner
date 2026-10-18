# GW-LD (proposal): does labelling GW-L's own states close the coverage gap? Marks fixed before any run, and before GW-LS's sealed read

**Status: PROPOSAL, not authorized, nothing run.** Written Oct 18 while the GW-LS round-8 sealed read is held (coordinator ruling Q96).
Its design does not depend on that read. It is written now so the GW-LS result cannot shape it. Labels: shown / suggested / untested as usual.

## Why this, from the GW-LS rounds (practice data only; `game/WALL-SOLVE-RESULT.md`, "erosion diagnosis")
- GW-LS started competent: GW-L, with played agreement 36 / 37% and a ready ratio of 2.3 / 6.3. It eroded under self-copying:
  - held-out S top-1 at r0 -> r7: 62.4 -> 50.1% (s200) and 64.8 -> 55.0% (s201);
  - nav agreement of kept rows 43-48% -> 28-29%;
  - practice non-habit at r8: 4.78 / 5.07, against 5.88 / 5.90 at r1.
- Explore noise is ruled out (3-6% of rows). The copied labels are the student's own navigation on its own states, where Z7 measured it
  about 19 points worse than on held-out states. **Suggested:** coverage is binding; start competence is necessary but not sufficient.
- This proposal tests the coverage half directly. It is labeller-labelled, so it is not itself the self-taught step. If it passes, the
  self-taught step (GW-LS2: GW-LS started from the GW-LD student) gets its own marks.

## The test (one change between arms: where the 16,000 new labelled views come from)
- **Students:** the GW-L 64k merged checkpoints, s200 / s201, each with a fresh rank-8 add-on. Training uses `game/probe.py train` exactly
  as GW-L (Adam 1e-3, minibatch 256, gradient norm 0.5). Data = the original 64,000 views plus 16,000 new views. 2 epochs over 80,000 rows,
  about 625 updates. Identical in both arms.
- **Arm D (own states):** the GW-L checkpoint of the same seed plays 400 practice games: T = 1, explore 0.10, act stream as `game/play.py`.
  Run seed 398 (s200) / 399 (s201), days 40-43 (unused; GW-LS used days 4-35 and Z8 days 0-3).
  - Every visited view is labelled by the labeller. Duplicates and any held-out view are dropped.
  - 16,000 views are sampled uniformly with seed = model seed.
- **Arm O (off-policy, the control):** the same worlds (days 40-43), but the GW-L data rule (`probe gen`: labeller move with chance 0.5,
  else uniform random), the same dedupe and drop rules, and 16,000 views sampled the same way.
- **Seeds:** 200 and 201 (a screen). Arms are paired by seed, by training budget and by worlds.

## Marks (both seeds; fixed now)
- **M1 coverage (primary).** Each trained student plays 200 fresh practice games (days 50-51). The own-state gap is its top-1 on its own
  visited nav / act views minus its held-out S top-1 (the Z7 metric: visits, first 200 games).
  - **Pass:** arm D gap >= -5 points on both seeds, **and** arm D gap - arm O gap >= +5 points on both.
  - **Proved wrong:** arm D gap <= -15 on both seeds, **or** arm D gap - arm O gap < +2 on both. Own-state labels then do no better than
    more off-policy labels.
  - Otherwise: no verdict. For scale, Z7 measured GW-L at -19.5 / -19.3.
- **M2 play (one sealed read per arm and seed; 100 sealed maps; `game.score --arm model --picker sample --temp 1.0`; paired by world;
  `game.analyze.boot_diff`).**
  - **Pass:** on both seeds, arm D non-habit >= arm O + 0.3 with CI low > 0, **and** arm D non-habit >= GW-L + 0.3 with CI low > 0.
    GW-L's sealed non-habit is 5.46 / 5.85.
  - **Proved wrong:** arm D non-habit <= arm O non-habit on both seeds.
  - Otherwise: no verdict. Reported, not marked: total, stone %, pickaxe %, mean length.
- **What each outcome decides.**
  - M1 and M2 pass: coverage was binding and labelling own states fixes it. Next is GW-LS2 (self-imitation from the arm-D student),
    with its own marks.
  - M1 pass, M2 not: coverage closes but does not turn into play. The play gap is elsewhere (survival / depth); re-diagnose.
  - M1 proved wrong: one aggregation round does not close coverage. Iterated aggregation needs new marks, or coverage is not the lever.

## Venue and cost
- This kind of free cloud container (4 cores), **$0**.
- Collection: about 1 h a seed. Training: about 625 updates at 2 threads, about 3.5 h per arm-seed (GW-L took 6.9 h for 2,500 updates at
  4 threads), so 4 runs take about 7 h in pairs. Then M1 games (about 30 min a student) and 4 sealed reads (about 15 min each).
  About 10-11 h of wall clock in total.
- No Mac (GW-O), no Vast, no spend bid. Code is new (a small driver over `probe.gen` / `probe.train` / `gwls_checks`-style Z7 code), so it
  is a draft until the coordinator reviews it.
