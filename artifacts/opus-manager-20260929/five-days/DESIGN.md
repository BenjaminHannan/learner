# Five days, five kinds: design

Written 2026-09-29 (Opus manager's helper "five-days sealer", Claude). Governing marks: `PASSMARKS.md` (same folder), written first and sealed with this file and the scripts (`SEAL.sha256.txt`). Nothing here has been trained or scored on real source nets: the source checkpoints (`qual-{loop,plain}-s{0,1}/source.pt`) live only on Ben's Mac. What *was* run here is `SELFTEST-run.log` (random-initialised nets, tiny step counts, CPU) and the pure-python marks selftest.

## The question, in plain words
Ben's problem 5: does sleep keep helping over many nights, and does it keep the old skills? Everything measured so far is one day and one night (or three nights in a different, larger reasoner). This test lives through five days. Each day the net learns a brand-new kind of puzzle from 64 examples; each night it sleeps (the harness's 512-update sleep). After each night we also check that the net can still learn: we give a copy 64 new mazes and score it. The sleep uses a fixed 16-item store per kind today; the one change is to replay fresh code-made puzzles instead. That is a disclosed upper bound, because real data has no generator.

## What is reused, unchanged (imported, never edited)
| Piece | From | Used for |
|---|---|---|
| Nets (loop 1,645,726 weights, plain 1,619,965), tensors, losses | `claude_fewex_net.py` | everything |
| `Learner` (AdamW wd 0.1, warm-up 50, 4 updates per batch), scorer `score`, `load_model`, `dump` | `claude_fewex_bench.py` | days, nights (optimiser and update), probes, scoring |
| Equal-practice pool of 16,384 mazes per seed, `batches`, qualified-source identity check | `claude_fewex_eq_bench.py` | the plasticity probe (so night 0 is the ruler's own rung) |
| sums, grids, mazes, dev/old panels, replay pool | `claude_fewex_data.py`, `claude_rsn358a_envs.py`, `claude_rsn358m_maze.py` | old kinds, day 1 |
| graph, rank, panels, checkers | `claude_dir_h1_kinds.py` (H1) | days 2, 3 |
| compose, odd (and reserves assoc, member, moddiff, bitop) | `claude_dir_a_kinds.py` (helper A) | days 4, 5 |

The sealed scorer calls `B.exact`; the driver routes it by puzzle kind to each kind's own checker (the same trick H1's bench uses; the sealed file is not edited).

## The generalised night
`opus_fd_run.night()` is `Learner.sleep` (`claude_fewex_bench.py:208`) with the two old kinds replaced by a list. Per update: for each old kind, 4 items (weight 0.5 / number of old kinds); 8 items of the day's kind from its 64 support (weight 0.5); one shape-homogeneous group per kind, the loop with a random number of rounds (1-16) and gradient through at most 6, plain with one pass; one optimiser step on the weighted sum; no stop-head loss (as in the harness).
**Check:** with old = sums4 + grids5 and the store arm the function reproduces `Learner.sleep` bit for bit (`torch.equal` on every tensor after two updates, loop and plain; both lines in `SELFTEST-run.log`).
**Arms differ only in the old items.** The store draw (`rng.sample(store, 4)`) is made in both arms so every random stream stays aligned; in the fresh arm those items are discarded and replaced by fresh ones from a separate stream. The day's items and the round draws are therefore identical across arms.
**Weights per old kind get thinner as kinds are added** (0.25 each on night 1, 0.083 each on night 5). That is the harness's own 50/50 split between "the new day" and "everything old", carried forward; it is the same in both arms and is a possible reason old kinds fade (untested; a weight sweep is not part of this test).

## Where the fresh puzzles come from, and why they cannot leak
- One `FreshStream` per old kind and night draw, seeded by string (`opus-fd-fresh-<kind>-<night seed>`), generators = the same functions that made the panels.
- It skips (and counts) any puzzle whose content key is in the kind's forbidden set: dev panel, holdout panel keys (built only to be avoided, never scored: H1's `panels()` builds both splits; the maze forbidden set has the ruler's 1,272 panel layouts), the 64 support, the 16 store, the ruler's replay pool and the fresh-guard panels (sums4/grids5), and for mazes the 16,384-layout probe pool. It never repeats a puzzle inside a stream.
- The run records, per draw and kind: served, skipped, overlap with forbidden (must be 0). CLEAN in the marks requires 0 and exactly 2,048 served. The selftest checks 300 fresh items per kind: 0 overlap, all distinct (maze skipped 49 of 349 to avoid the forbidden layouts, shown).
- Maze layouts number only 100,352 at 9x9 (spanning trees of the 4x4 room grid); the 16,384-layout probe pool plus 1,272 panel layouts are all avoided, so the fresh maze stream draws from what remains. Disclosed.
- Kind-by-kind disjointness of dev vs support: asserted in the selftest for all seven kinds.

## The plasticity probe
The probe adapts a copy of the night-d net (draw 0) on the first k mazes of the ruler's own pool with the ruler's own batch order and 2,048 updates, and scores the 300 dev 9x9 mazes. Night 0 = the practised source net: this is exactly the ruler's `pre` ladder, so the `ref` job's night-0 numbers should reproduce the ruler's dev curves (51.21 / 51.67 F_eq for the practised loop, 34.04 / 32.62 practised plain; report-only sanity check, not a mark: a difference would mean the Mac run is not bit-reproducible).
Probe schedule: nights 1-4 at k = 64 only (curve), night 5 the full ladder (F_few and F_eq) on draw 0, plus k = 64 on draws 1 and 2. This trades detail for time (a full ladder every night would add about 27 adaptations per chain).
**Confound (stated in the marks too):** the probe kind is day 1's kind, which nights keep rehearsing. So the probe partly measures kept maze skill. It can only show that plasticity did *not* collapse; it cannot show improvement. The report-only `ref-day{d}` rows learn each later day's kind from the practised start (no earlier kinds); comparing them with the chain's day-end scores is the cleaner (but confounded by transfer) look at learning speed on new kinds.

## Kinds chosen for days 4 and 5, and why
Beyond mazes, H1's graph and rank there are eight more code-made kinds in `claude_dir_a_kinds.py` (assoc, compose, parity, member, multi, moddiff, odd, bitop). I chose **compose** (follow two lookup tables in a row: name to name to digit; a two-step relation) and **odd** (which name differs from its row-mates; a comparison), because they are unlike each other and unlike graph (spreading), rank (counting) and maze (path), and unlike sums and grids. Their tokens avoid the graph/maze vocabulary by construction (`claude_dir_a_kinds.py` header and selftest). Not chosen: multi (nearest neighbour of rank), moddiff (digit arithmetic like sums), parity (long xor chains are hard for a small net at 64 examples), assoc and member (trivial lookups; kept as reserves). Learnability with 64 examples is **untested**; rule K in the marks (a pilot on a private panel, and H1's dev gate for graph and rank) decides substitutions before any chain, never after.
Sizes: the smaller level of each kind (compose 4 names-per-table, 11x3 grid; odd length 6, 3x7 grid).

## Cost (estimates, labelled; the Mac numbers scale from the ruler, mine are from this loaded box)
Measured here in the selftest (one thread, the 4-core box was fully loaded by other work, load average about 10): loop 4.8 s per 32-item batch, i.e. 41 min per 2,048-update adaptation; plain 2.3 s, 19 min; a 512-step night with 3 old kinds 8.2 min (loop), 2.5 min (plain). The ruler on the Mac ran its 8-rung dev ladder plus 2 sleeps and scoring in 169 min for the loop (about 21 min per rung) and 120 min for plain (about 15 min).
Per loop chain (Mac estimate): 19 adaptations (5 days, 4 probes at k = 64, 8 rungs at night 5, 2 extra draws at k = 64) about 400 min; 15 nights about 130 min; scoring about 75 min; **about 10 h**. Per plain chain about 5.5 h. Per `ref` job (8 rungs + 4 day references = 12 adaptations): loop about 4.5 h, plain about 3.2 h. Total about 75 core-hours; with 10 cores (8 chains + 2 refs at once, the other 2 refs when a ref finishes) **about 10-11 h wall**, $0. The job is resume-safe (each stage writes its JSON and net; a rerun skips finished stages). A 3-cycle pilot is not offered: the marks need five days.
Disk: about 20 nets per chain at 6.6 MB, 8 chains: about 1.1 GB, kept local, never pushed.

## What I changed from the sweep's version, and why
1. Gain bar for the 300-count rows raised from 30 to 60: draw SD there is up to 35.2 (recomputed from the distill sleeps), so 30 was under one SE.
2. Per-row margin max(6, 2 x SE) is *also* required (the sweep had it in the header only).
3. The plasticity gate and the "proved wrong" fall are stated in F_eq (0-51 scale); F_few has its own required row, but it starts at 14-16, so a fall of 15 is impossible there and 10.5 nearly is (limit stated in the marks).
4. Added eligibility rules (kind learned, not ceilinged) so an unlearned kind cannot silently make PASS impossible or silently pass; a minimum of 4 eligible rows and the maze row must be informative.
5. Added a fourth arm (plain-fresh) so "not architecture-specific" is measured, and defined the plain row as the k = 64 probe gap (a plain net starts 100 to 160 of 300 behind on mazes at k = 64).
6. Added the `ref` job (night-0 ladder, and each later day's kind learned from the practised start) to make the confound visible.
7. Dev panels only and no holdout at all (Ben's rule); a later holdout confirmation, if wanted, is a separate step.

## Risks and what is untested
- **Untested:** every result. No real source net has been touched. The graph and rank kinds are unproven learnable (H1's job is running); compose and odd have never been trained on.
- The probe confound and one-order/one-path limits are in the marks.
- The night's per-kind share shrinks with each added kind; a 16-item store for a day kind is 16 of its 64 examples.
- Chain nets differ between arms from night 2 on, so day-end scores compare different starting nets; the "learned in both loop arms" rule protects the gain rows only against unlearned kinds.
- F_eq at night 5 rests on one net (draw 0). W2 and M3 inherit that.
- fp32 CPU results can differ in the last bits between machines; the selftest used 2 threads on Linux x86, the job uses 1 thread on the Mac.
- The selftest mini chains use 8 inference rounds and 8 dev items to fit 5 minutes; real runs use 48 rounds and full panels (`REAL` in the driver). The real-size timing is projected, not measured.
- If H1's graph or rank gate is INCONCLUSIVE the plan changes (rule K); the marks then apply unchanged to the substituted kinds.

## Files
`PASSMARKS.md`, `DESIGN.md`, `SELFTEST-run.log`, `SELFTEST-marks.log`, `SEAL.sha256.txt`, `queue-opus-fd-1.md`; scripts `scripts/opus_fd_run.py`, `scripts/opus_fd_marks.py`.

## How to run (after the dependencies in the queue file are met)
```
python -B scripts/opus_fd_run.py selftest --threads 2
python -B scripts/opus_fd_run.py pilot --kind compose --seed 0 --source-root <runs>      # rule K2, also odd, seeds 0 and 1
python -B scripts/opus_fd_run.py ref   --arm loop  --seed 0 --source-root <runs>
python -B scripts/opus_fd_run.py chain --arm loop  --night fresh --seed 0 --source-root <runs>
python -B scripts/opus_fd_marks.py score --runs artifacts/opus-manager-20260929/five-days/runs --out SCORE.json
```
