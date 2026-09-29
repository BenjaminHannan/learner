# Five days, five kinds: pass marks

Written 2026-09-29 03:35 UTC (`date -u`) by the Opus manager's helper "five-days sealer" (Claude), **before any run they judge**. No chain, probe, pilot or night of this test has been run anywhere (checked: no `runs/` folder here; the only thing run is the selftest of the code, `SELFTEST-run.log`, on random-initialised nets with tiny step counts, and the pure-python marks selftest). Marks as code: `scripts/opus_fd_marks.py` (its selftest checks 10 synthetic cases, one per verdict). Driver: `scripts/opus_fd_run.py`. Reasons and mechanics: `DESIGN.md`. Seal: `SEAL.sha256.txt`. **These marks are not changed after any score is seen.** If a mark is badly chosen the run is reported as it stands and a new test with a new addendum follows.

Scope: the practised 1.6M-weight loop of the few-example ruler (`artifacts/claude-fewex-20260927`) and its 1.6M plain same-size net, code-made puzzles only. Not the small card experiments, not the village model. Dev panels only: no holdout, test or blind panel is built for scoring or opened.

Source of the design: `design/research/lead-sweep-2026-09-29/SYNTHESIS.md` section 3 test 4 (lines 197-215) and `angle-5-sleep.md` test MD1. What changed from that text is listed in DESIGN.md section "What I changed from the sweep's version, and why". Every change makes a mark stricter or fixes a hole; none loosens one.

## The one change
**What the night replays for the OLD kinds.** Everything else is identical between the two sleep arms (same nets, same day data and batch order, same night length, same optimiser, same round draws, same day items in the night, same 3 draw seeds).

| arm | old-kind items in each of the 512 night updates | true labels |
|---|---|---|
| **store** (A, today's sleep with the 16-item store) | 4 items per old kind sampled from a FIXED store of 16 items per kind (sums4 and grids5: first 16 of the ruler's replay pool; each day kind: first 16 of its own 64 support items) | yes |
| **fresh** (B, the change) | 4 FRESH code-made puzzles per old kind per update (2,048 per kind per night), never equal to any panel, support, store or probe-pool item, never repeated inside a stream | yes |

Both arms also rehearse the current day's kind from its own 64 support items (8 items per update, weight 0.5), exactly as the ruler's sleep does. The old kinds share the other 0.5 equally (0.25 each on night 1, which makes night 1 identical to the sealed `Learner.sleep`; checked bit for bit in the selftest for loop and plain).
This is a **disclosed puzzle-only upper bound**: real user data has no generator (angle-5 section 3b). A PASS licenses nothing about real data.

Arms run: loop-store, loop-fresh, plain-store, plain-fresh, seeds 0 and 1 (`runs/<arm>-<night>-s<seed>`), plus one shared night-0 / reference job per architecture and seed (`runs/ref-<arm>-s<seed>`). Plain arms use the ruler's plain net (eight distinct width-128 blocks, 1,619,965 weights, lr from its source-only sweep); the loop has 1,645,726 weights (1.57 percent apart).

## Schedule: five days, a new held-out kind each day
| day | kind | generator / checker (file) | graded size | dev panel |
|---|---|---|---|---|
| 1 | 9x9 maze | `claude_fewex_data.make_maze`, `claude_rsn358m_maze.check_maze` | 9x9 | 300 (the ruler's dev) |
| 2 | graph hop distance | `claude_dir_h1_kinds.py:75 make_graph`, `check_graph` (H1) | 14 nodes | 300 (H1's dev) |
| 3 | rank of each digit | `claude_dir_h1_kinds.py:212 make_rank`, `check_rank` (H1) | 9 digits | 300 (H1's dev) |
| 4 | compose (two lookups in a row) | `claude_dir_a_kinds.py:95 make_compose`, `A.check` | level 4 | 200 (own seed) |
| 5 | odd-one-out name | `claude_dir_a_kinds.py:151 make_odd`, `A.check` | level 6 | 200 (own seed) |

Old kinds before day 1 (both practised by the source nets): sums4 and grids5 (200 each, the ruler's old panels). "Earlier kind" at night 5 = these two plus days 1-4 = **six rows**; day 5's kind is the *current* kind (reported, not a gain row: both arms rehearse it identically).
Five code-made kinds exist beyond sums and grids (maze, graph, rank, and eight more in `claude_dir_a_kinds.py`), so the plan is **fixed at five days**; nothing is short. Day 4 and 5 use the smaller of each kind's two levels (rule: keeps 64 examples learnable). Reserves in order: assoc, member, moddiff, bitop.
**Rule K (kind substitution, applies only BEFORE the first chain starts, never after):** (K1) graph or rank stays only if H1's `DEV-GATE-<kind>.json` says PASS; if not, the next unused reserve takes that day. (K2) compose, odd and any reserve must pass the learnability pilot (`opus_fd_run.py pilot`): practised loop, both seeds, 64 examples, 2,048 updates, at least 60 of 200 on a pilot panel built from its own seed (never the dev panel); if not, the next unused reserve takes that day. The plan actually used is written to `runs/*/plan.json` and the run states it.

## One day / one night / one probe
- **Day d:** from the current net (day 1: the practised source net), adapt a copy on the kind's 64 support items with the ruler's equal-practice recipe (512 batches x 32 x 4 = 2,048 updates, loop lr 1e-3, plain lr from its source sweep). Day-end score of every kind seen so far is recorded before the night.
- **Night d:** 512 optimizer updates (the harness length), from the day-end net, **3 independent draws** (different night seeds, same for both arms). The chain continues from draw 0 only (recorded); draws 1 and 2 exist to measure the noise and to average.
- **Probe after each night (every arm):** adapt a COPY of the night-d net (draw 0) on the first k of the ruler's 16,384-maze pool for that seed (fresh 9x9 mazes, disjoint from every day, night and dev maze; night-0 probe = the ruler's own equal-practice rungs) and score the 300 dev mazes at 9x9. Nights 1-4: k = 64 only (curve). Night 5: the full ladder k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384, so **F_few** (mean of k = 1..64) and **F_eq** (mean of all 8) exist for night 5; k = 64 is also probed on draws 1 and 2. Night 0 (the practised net, both full ladders) is the `ref` job.
- Scores: fixed depth from the source's `source.json`, learned-stop `right` counts, exactly the ruler's scorer (`claude_fewex_bench.score`).

## Marks (each seed on its own; seeds are never pooled; "both seeds" means each seed passes)
Let, for each earlier-kind row r and seed: A_r = mean of the 3 night-5 draws of loop-store, B_r = the same for loop-fresh, d_r = B_r - A_r, SE_r = sqrt((var_A + var_B)/3) (sample variances of the 3 draws), **margin_r = max(6, 2 x SE_r)**. Counts are of the panel's own size (200 or 300).
- **CLEAN (validity):** every night has all 3 draws; every fresh stream served exactly 2,048 items per old kind per draw with **0 items overlapping** any panel, support, store or probe-pool item (counted in the raw JSON). Otherwise the run is **VOID** (no verdict).
- **ELIGIBLE row:** the kind was *learned* (day-end score at least 30 percent of the panel, in BOTH loop arms of that seed; sums4 and grids5 always) and is not *ceilinged* (A_r <= panel size minus the bar). **INFORMATIVE:** in both seeds sums4, grids5 and the maze row are eligible and at least 4 of the 6 earlier rows are eligible. Not informative means NOT SHOWN.
- **GAIN (M1):** every eligible earlier row, in both seeds: d_r >= **20 of 200** (or **60 of 300** for maze, graph, rank) AND d_r > margin_r.
- **PLASTICITY, F_few (M2):** loop-fresh night-5 F_few >= its night-0 F_few - **10.5**, both seeds (night 0 from the `ref` job). This is the noise bar for F_few; see the limit in the self-check, point 5.
- **PLASTICITY, F_eq (M3):** loop-fresh night-5 F_eq >= its night-0 F_eq - **8.0**, both seeds.
- **PLAIN ROW (M4, a row a plain net cannot pass):** loop-fresh night-5 probe at k = 64 (mean of the 3 draws, of 300) >= plain-fresh's same number + **60**, both seeds. (Night 0: practised loop 126 / 173 of 300 on dev against practised plain 29 / 14; a plain net cannot pass unless it keeps its own tiny lead, and the row also tells if the loop's head start survives five nights.)
- **PASS** = CLEAN, INFORMATIVE, GAIN, M2, M3 and M4, in both seeds.
- **PROVED WRONG (every-seed reading; the result that would prove it wrong, fixed now):** either (W1) in BOTH seeds, at least 3 eligible rows and every eligible earlier row has d_r below **5 of 200 (8 of 300)**: then the size of the store is not what limits sleep and generator replay is not the lever; or (W2) in BOTH seeds, BOTH loop arms (store and fresh) lose more than **15 F_eq points** between night 0 and night 5: then loss of plasticity is real whatever the replay, and the next single change is an L2-toward-start pull (angle-5 section 4). W1 and W2 are each a verdict on their own.
- **NOT SHOWN:** anything else with a valid run. (One seed passing is NOT SHOWN.)
- **Plain net note (report, not a mark):** if the plain-fresh arm also passes GAIN on 4 or more earlier rows in both seeds, the write-up says "not architecture-specific".

## Report only (decides nothing)
Per night and draw: every seen kind's score for all four arms; day-end scores; the maze k = 64 probe curve over nights 0-5 for every arm (the "gets better with use" curve); F_few and F_eq at night 0 vs night 5 for the two loop arms; the plain arms' F_few/F_eq; for each later day's kind, the score learned from the practised start with no earlier kinds (`ref-day{d}.json`, next to the chain's day-end score: this separates "carrying old kinds" from "learning new kinds faster or slower"); stream stats; seconds; source sha256.

## Noise: where each bar comes from (marks self-check point 1)
- Sleep draws, recomputed here from `artifacts/claude-distill-20260928/sleeps/*.json` (3 draws per cell, 4 cells per arm): largest SD over cells, sums4 / grids5 of 200 and 9x9 of 300: **R16 (16-store, our store arm's recipe): 3.8 / 5.3 / 35.2**; R128: 20.1 / 6.1 / 36.2; D16: 7.0 / 9.5 / 29.5 (shown, this file's author ran the recount). These are single-maze-day sleeps; the night-5 draw SDs are unmeasured, so the run's own per-row margin max(6, 2 x SE) is part of every gain test.
- Gain bar on 200-count rows: 20. Two SE of a difference of two 3-draw means at SD 5.3 is 8.7; at the worst D16 SD 9.5 it is 15.5; bar 20 is above both. (The R128 sums SD of 20.1 would need 32.8, which is why the per-row margin is also required.)
- Gain bar on 300-count rows: **60**, raised from the sweep's 30. Two SE of a difference of two 3-draw means at the worst measured SD 35.2 is 57.5, and the sweep's 30 was below one SE of that.
- F_eq bar 8.0 and F_few bar 10.5: `artifacts/claude-dir-lr-20260928/NOISE.md` (2 x 3.96 and 2 x 5.23, the all-starts recipe on the ruler's dev curves; direct same-start seed gaps are at most 2.5 in F_eq).
- W2's 15 and M4's 60 are design choices above these bars (labelled **suggested**).
- Untested noise: probe noise after a night (the chain net is one draw); F_eq at night 5 rests on draw 0 only.

## Marks self-check (Ben's list, one line each)
1. **Every bar above measured run-to-run noise:** yes, sources quoted above (draw SDs recomputed from the distill sleep files; F_eq 8.0 and F_few 10.5 from NOISE.md; 300-count gain bar raised to 60 to clear 2 SE at SD 35.2). Where a cell's draws are noisier than measured, the per-row margin max(6, 2 x SE) is also required.
2. **"Every seed" reading:** PROVED WRONG only if BOTH seeds break the gate (W1 both seeds all rows under the small threshold; W2 both seeds both arms); a single seed passing or failing is NOT SHOWN.
3. **Fair comparator:** the store arm is the deployed recipe (harness sleep) with a 16-item store, the KS/T1 comparator; the 128-item store (R128) sees 8x more stored puzzles and is not required (KS PASSMARKS.md line 29 reasons the same way) and is **untested** here; the plain net is never the comparator for the gain (different architecture). A no-night arm scores 0 of 200 on old kinds after a maze day in every arm of the ruler (RESULTS-EQ.md, Old kinds table), so it is never the higher comparator.
4. **A row a plain net cannot pass, and not just memorising:** M4 (plain probe cannot follow the loop); CLEAN (0 overlaps counted, fresh streams never repeat, panels are disjoint by content key; the store arm's 16 items are the only repeated items and are not scored); the report-only `ref-day` rows. A plain-fresh arm is run so "not architecture-specific" is measured, not assumed.
5. **F_few beside F_eq as its own required row:** M2 (F_few) and M3 (F_eq), each required. **Honest limit:** the practised loop's night-0 F_few is only 13.8 / 16.2, so a fall of more than 10.5 needs near collapse; M2 can fail only if the probe nearly dies. M3 (F_eq, 51 at night 0) is the sensitive row and W2 uses it. F_few's own falling-more-than-15 test is impossible by arithmetic, so W2 is stated in F_eq.
6. **Sleep gates use the mean of 3 sleep draws, margin max(6, 2 x SE):** yes for GAIN (M1) and the plain row; the plasticity rows M2/M3 use the chain net (draw 0), declared above.

## Confounds and limits, stated first (each is **suggested** or **untested**, none is shown)
- The probe is on mazes, and mazes are day 1's kind, rehearsed at every later night. A high night-5 probe can mean "kept the maze skill" and not "kept the ability to learn". The arm with fresh mazes is favoured by this. It is therefore only a check that plasticity did not collapse, not a measure of learning speed; the report-only `ref-day` rows are the cleaner look at later-day learning speed (**suggested**).
- Positive transfer between kinds could raise later-day scores; negative interference could lower them. Untested.
- Kind order is fixed (one order, not permuted). Untested.
- Generator replay is a puzzle-only upper bound. It does not transfer to user data (**untested**).
- The chain is one path per arm and seed (draw 0 continues). The variation over chains is two seeds.
- Nothing here uses the small card experiments or the village model.

## What each verdict licenses
- **PASS:** "at night 5, fresh generator replay kept six earlier kinds much better than a 16-item store, in two seeds, and the maze probe did not collapse (F_few / F_eq within the noise bars)" for code-made puzzles only, as an upper bound. Not "the net keeps improving": the probe measures no improvement, only no collapse.
- **PROVED WRONG (W1):** store size is not the limit at this size; look at the update instead (KS lead 0 / H6). **(W2):** many nights do erode plasticity; next single change is an L2-toward-start regulariser.
- **NOT SHOWN:** no claim either way.

## Predictions (guesses, before any run)
PASS 20 percent (the sweep gave the gain alone 40 percent; I require all six rows on both seeds plus three plasticity/plain rows). PROVED WRONG 10 percent. NOT SHOWN 65 percent. VOID 5 percent.

## Blind recount
A separate step, given only this file, `scripts/opus_fd_marks.py` and the raw `runs/` JSON, recounts every mark before any RESULTS file is written.

## Plain-language summary for Ben
Each "day" the net learns one brand-new kind of puzzle from only 64 examples. Each "night" it replays old puzzles so it does not forget them. We run five days: mazes, then graph distances, then ranking numbers, then two more code-made kinds, so by the end there are six old skills to keep. The single thing we change is the night: one version replays the same 16 saved puzzles per skill (today's way); the other makes brand-new puzzles for every old skill each time (which only works because a computer can make these puzzles, so this is a best case, not a real-world method). After each night we also give a copy of the net 64 new mazes and see how well it learns them, to check it has not gone stiff after many nights. It passes only if the fresh-puzzle nights keep every old skill at least 20 of 200 (60 of 300 for the bigger tests) better than the saved-16 nights, in both of two runs, and the learning check does not collapse, and a same-size plain net cannot do the same. It counts as proved wrong if the fresh puzzles help almost nothing in both runs, or if the learning check falls badly in both versions. Nothing has been run yet.
