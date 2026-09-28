# H8: adversarial review of the pending races and tests, before any is scored

Written 2026-09-28 20:35 UTC (`date -u`) by Director helper H8. Read-only: I ran no training, no GPU, no rental, and
edited no existing file. This box has no torch (`import torch` fails), so no net code was run. What I did run is
plain Python over the raw JSON files already on main (recounts, noise arithmetic, one small simulation).

Labels: **shown** = I counted it from a raw file or the code and you can too; **suggested** = my reading or a
calculation that rests on stated assumptions; **untested** = nobody has run it. Counts are "x of N".
Severity: **BLOCKS** = the verdict word cannot be trusted or the test cannot finish as sealed;
**WEAKENS** = a verdict is possible but says less than its wording claims; **NIT** = cosmetic or cheap.

Ruler used for comparison: `artifacts/claude-fewex-20260927/RESULTS-EQ.md`, `RACE-PASSMARKS.md`,
`RACE-ADDENDUM-1.md`, `ADDENDUM-4.md`, `PROTOCOL.md`, and the raw `eq-runs/*/{adapt,holdout}.json`.

---------------------------------------------------------------------------------------------------------------

## 1. Short answer

| Test | State now | Can it give a meaningful verdict as sealed? | Worst finding |
|---|---|---|---|
| Patch race (A) | Practice done, no maze score yet | Only a "not higher" reading; a PASS is close to unreachable | X1 sleep gates are inside noise; P1 the control is handicapped; P2 no writes-off control |
| Distill in sleep | Already run and scored: NOT PASSED, NOT PROVED WRONG | The verdict word stands; two "Shown" lines are stronger than the counts | D1 marks below noise; D2 over-claims |
| Relation-net race (C) | Practice running (started 19:07 UTC) | Not on CPU: about 54 h per dev run (TIMING-ESTIMATE) | R1 needs the GPU addendum ADDENDUM-4 asks for; X1; X2 |
| H1 held-out kinds | Nothing run | Yes for kind-by-kind; graph's plain arm is a weak comparator | H1-a V3 lets a broken ladder through; H1-b expressivity |
| H2 numbers pool | Nothing run | Yes, but a PASS cannot say "fewer repeats" was the cause | H2-a repeats and target variety are changed together |
| H3 settle gate | Code never run | Verdict word can differ from its own marks | H3-a code says "any", marks say "every"; H3-b decay on the gate |
| H6 sleep length | Held | Yes, if the mid-night curve is added | H6-a cannot tell "moved too far" from "memorised the 300 puzzles"; H6-c no carry-over row |

Counts: BLOCKS 4 (X1, X2, R1, H3-a), WEAKENS 18 (R2 repeats X2), NIT 13. Every BLOCKS item is fixable by an addendum or a
3-line code edit **before the first maze score** (nothing has been scored for A, C, H3; H1, H2, H6 have not run).

What is sound (shown): every number I recounted matches the sealed page (section 5). Seal-before-score order holds
in the git history for the distill test (marks committed 15:52:26 UTC; first sleep started 17:44:48, last 19:24:48). The F_eq bars (+10, +5) are far
above counting noise (about 1.4 points for a difference of two eight-rung means, H1 PASSMARKS.md:46) and above the
loop's own seed spread (0.29). No test uses Claude-written training text: every puzzle and answer comes from
code (the generators and solvers named in each DESIGN). No design has a maze-only rule beyond what the baseline
loop already gets (plug-in docstrings: relnet plug-in L19, patch plug-in L15-16).

---------------------------------------------------------------------------------------------------------------

## 2. Cross-cutting findings (they hit more than one test)

### X1. BLOCKS: the old-kind sleep gates ("within 6 of 200") are smaller than the noise in the number they judge
Where: patch `PASSMARKS.md:36-39`, `scripts/claude_patch_eq_report.py:100-103`; relnet `PASSMARKS-C.md:45-48`,
`scripts/claude_relnet_eq_race.py:71-76`; H3 `PASSMARKS.md:46-47`. All three copy RACE-PASSMARKS.md:5 ("within three points").

Evidence (shown, from the distill run's raw files `artifacts/claude-distill-20260928/sleeps/*.json`):
- Same net, same recipe, only the sleep's random draw changes. Old-kind count after the sleep, R128 arm, three draws:
  sums4 s0 k64 = 174, 158, 134; s0 k16384 = 79, 78, 60; s1 k64 = 152, 158, 158; s1 k16384 = 42, 69, 43.
  grids5 = 104, 104, 94 / 86, 85, 80 / 132, 139, 127 / 121, 131, 132.
  Pooled spread of one draw: about 14 of 200 on sums, about 5 of 200 on grids.
- The same recipe re-run on the rebuilt nets moved the ruler's own recorded sleep numbers by (`distill RESULTS.md:50-52`):
  sums 25, 3, 3, 41 and grids 5, 4, 46, 21 (all "of 200"). So a re-run of the same thing swings by up to 46.
- The gate compares a design's single sleep score with the loop's single recorded score (loop after-sleep sums at
  k = 16,384: 76 and 83 of 200; k = 64: 149 and 155, from `eq-runs/loop-s{0,1}-pre/adapt.json`).

What it does (suggested, my simulation with those spreads, no true difference between design and loop, independent
noise): a design exactly equal to the loop passes all four sleep gates in one seed about 24% of the time
(0.237) and in both seeds about 6% (0.056). A design that really gains +12 F_eq in both seeds but is otherwise equal
to the loop is: PASS 6%; REJECTED 58% under the patch/H3-text reading ("in every seed that gains"); REJECTED 94%
under the relnet/H3-code reading ("in any seed"); NOT PROMOTED the rest. The spread I used excludes net-to-net
differences, so the real chance is if anything worse.

Fix (a Director decision; it must be an addendum committed before any maze score): keep the sealed gates, but judge
them on the mean of three sleep draws per branch for both the design and the loop, with the margin
`max(6, 2 x SE)` where SE comes from those draws. The distill run already has the draw machinery
(`claude_fewex_distill_sleep.py`, draws at `seed + k`, `+101`, `+202`; about 5 minutes each per branch on one CPU thread,
`distill RESULTS.md:72`). It needs the k = 64 and k = 16,384 checkpoints of each arm, so the harness must be run
with checkpoint saving on. Cheapest test that separates "gate too tight" from "design forgets": run the loop's own
sleep three times from one saved checkpoint per branch and look at the spread before the design is scored.

### X2. BLOCKS (the word, not the numbers): three different readings of "a maze gain made only by breaking an old-kind gate"
- Patch: `PASSMARKS.md:44-46` and code `scripts/claude_patch_eq_report.py:121-124`: REJECTED if there is a gain and **every**
  gaining seed breaks a gate.
- Relnet: `PASSMARKS-C.md:55-56`, code `scripts/claude_relnet_eq_race.py:100-101`: REJECTED if **any** seed gains and breaks a gate.
- H3: text `PASSMARKS.md:54-55` says "in every seed"; its code `scripts/claude_dir_h3_report.py:41-42` says `any(...)`
  (copied from the sparse test, `claude_sparse_race.py:99-102`). **Text and code disagree inside one test.**
- The original race wording has this clause only for Test A (`RACE-PASSMARKS.md:7`) and never says which reading;
  Test C originally had none (`RACE-PASSMARKS.md:11`).
Why it matters: with X1's noise the two readings give REJECTED 58% versus 94% for the same real winner.
Fix: one sentence in an addendum, "REJECTED-by-breaking needs every gaining seed to break a gate", and change the H3 and relnet
report code to match (3 lines each). Cheapest test: feed both report scripts one fake pair of seeds (one gains and breaks, one
gains and passes) and see that they print different words today.

### X3. WEAKENS: F_eq is mostly the many-example rungs, so it cannot say "few examples"
Shown from `eq-runs/*/holdout.json`: share of F_eq that comes from k >= 256: practised loop 86.4% / 84.2%, practised
plain 95.1% / 98.5%. F_few (mean of k = 1, 4, 16, 64): loop 13.83 / 16.17, plain 3.33 / 1.00. Practised-loop 9x9
rung counts: seed 0 = 1, 0, 28, 137, 256, 271, 257, 274; seed 1 = 1, 0, 3, 190, 262, 236, 284, 255 (of 300).
A design whose mechanism helps only at k <= 64 needs +20 points on each of those four rungs to reach +10 F_eq
(4 of the 8 rungs). A real few-example gain of +12 there would read NOT PROMOTED. Ben's goals page says the main
measure is "how few examples a new kind takes" (`design/v3/30-modes/ben-goals-2026-09-26.md:24`).
The scripts already compute F_few (relnet race `summary`, L44), so the fix is free: make "F_few at least +X over the loop"
a required second row of the verdict sentence (X fixed before scoring), or say "F_eq" only, not "few-example".

### X4. WEAKENS: "no higher than the loop in both seeds = REJECTED" is not evidence of "wrong"
Under no true difference each seed is above or below the loop about half the time, so "not above in both" happens
about 25% of the time by luck (suggested). Designs also swing more between seeds than the loop does: the loop's two
seeds differ by 0.29 F_eq, but the sparse loop's two seeds were +3.88 and -6.25 from the loop
(`artifacts/claude-sparse-20260928/RESULTS.md`, sparse 54.88 / 45.04 vs loop 51.00 / 51.29, recounted). Fix: use the words
"not shown" unless both seeds are at least 2 points below the loop; report the per-seed difference next to the verdict.

### X5. NIT: the plain arm's learning rate is tuned, the design arms' is not
`PROTOCOL.md:17`: plain's maze rate is chosen from 5e-4 / 1e-3 / 2e-3, the loop uses 1e-3. Every design arm also uses 1e-3
(patch plug-in L207-209). That favours the baseline, not the designs, so it does not endanger a PASS. Just say so.

---------------------------------------------------------------------------------------------------------------

## 3. Per-test findings

### 3.1 Patch race (`artifacts/claude-patch-eq-20260928/`)

**P1. WEAKENS: the control is trained for a different adapter than the one used on mazes.** The "loop with episodes"
learns during practice with plain SGD at lr 0.01 through a second-order step (`scripts/claude_patch_eq_practice.py:60`
`INNER_LR = 0.01`, inner step L160). At maze time it is adapted with AdamW 1e-3, 50-step warm-up (plug-in L207-209 for the
patch; `PROTOCOL.md:17` for the loop). The patch is trained for the very write it uses at maze time (plug-in L160-167).
So "the same training" (`RACE-PASSMARKS.md:7`) is met in letter, but the control's practice is tuned for a mechanism it never uses.
The mark compares to `loop_ep` only (`PASSMARKS.md:34`, code `report.py:96`); the baseline loop is report-only
(`PASSMARKS.md:56`, code `report.py:110`). If the episodes hurt the loop, the patch clears +10 over a handicapped control.
Fix: mark 1 = +10 over the higher of `loop_ep` and the baseline loop (baseline is already scored: 51.00 / 51.29).
Cheapest test: none; it is a rule change, both numbers are already reported.

**P2. WEAKENS: no "same net, writes off" control.** The fresh arm is a different net (untrained, `DESIGN.md:62-65`). Nothing
separates "the writes helped" from "the practised patch net, with its extra parts and 2,000 episodes, is simply a better
starting net" (extra parts = writer, rank slots, gate; +7,041 stored numbers = +0.43%). Also the memory is an
average: `RHO = 0.9` (`claude_patch_net.py:34`, blend at plug-in L121-124), so after a few dozen writes the patch mostly holds the
last ~10 batches (0.9^10 = 0.35); at k = 16,384 it cannot hold "16,384 examples", and at k >= 256 (84-99% of F_eq, X3)
any gain must come from the ordinary updates. Fix: one dev ladder per seed with the practised patch net and
`Net.WRITES = False` (`--init pre`; a 5-line plug-in like `claude_patch_eq_fresh.py`), and read the patch's gain over
that, not only over `loop_ep`. Cost: the four-rung version (k = 1, 4, 16, 64) is 4 x 512 batches x 3.1 s, about 1.8 h at one thread per seed; a full ladder about 3.5 h of maze updates.
Cheapest test: the four-rung version on the dev panel, one seed first.

**P3. WEAKENS: equal updates are not equal compute.** Each write runs every puzzle in the batch to its own stop, up to
48 rounds, with no gradient (plug-in L132-158, L160-167). The design's own measurement: 4.7 s per maze batch against
3.1 s for the loop (`DESIGN.md:86-87`), +52% (shown, the design's number). The marks are fair to the ruler (equal updates)
but the verdict sentence should say "at 1.5x the compute".

**P4. WEAKENS: sleep trains with the patch on, then removes it before scoring.** `Learner.sleep` (plug-in L244-262):
`loop_train` uses the stored patch (`step` takes the buffers when `patch is None`, L74-76) for all 512 updates, then
`remove_patch()` (L261). Old-kind gates 3-4 and post-sleep maze scores are then a train/test mismatch by design.
Effect size: untested; the patch term is `0.25 x gate x (B (A h))` with entries bounded by `1/sqrt(8*256)` (`claude_patch_net.py:39`).
Fix: also score old kinds after sleep with the patch kept (report-only), or sleep with the patch removed. Cheapest test:
the k = 64 sleep on dev with both settings, one seed.

**P5. NIT:** old-kind mark 3 ("at least 190 of 200") cannot fail: both practised patch nets scored 200 / 200 on
grids and sums in the guard (`runs/patch-s{0,1}/source.json`, recounted); size mark 5 cannot fail (1,652,767 vs
1,645,726 = +0.43%, recounted). Fine as validity gates, but do not count them as evidence.

Recount, patch (shown): stored numbers 1,648,671 + 4,096 = 1,652,767; +7,041 = +0.428% over 1,645,726; guard 200 / 200 on
both kinds for all four practised nets; fixed depths recorded patch s0 48, s1 8, loop_ep s0 8, s1 32.

### 3.2 Distill in sleep (`artifacts/claude-distill-20260928/`), already run

Seal order (shown): PASSMARKS committed 15:52:26 UTC (abf0bf81a; the file itself says 15:53, a clock skew of under a minute, harmless), first sleep started
17:44:48, last 19:24:48 (from `started_utc` in the 60 sleep files). Marks were not changed after scores. Recount matches `BLIND-RECOUNT.md`.

**D1. WEAKENS: three marks sit below the noise.** I recomputed the per-draw differences D128 minus R128 from the 12 paired draws
(4 cells x 3 draws share the same puzzle and round sequence):
- sums4: mean +4.5, SD of a paired draw 17.1, SE 4.9, above zero in 7 of 12 draws. Bar M1 = +20 is 3 SE away.
- grids5: mean +9.75, SD 10.7, SE 3.1, above zero in 10 of 12 draws.
- 9x9 maze: mean -0.67, SD 27.0 (of 300), SE 7.8. M2 asks each cell's 3-draw mean to be no more than 6 below R128;
  a cell mean has SE about 15.6, so a D128 with **no** effect passes one cell about 65% of the time and all four cells about 18%.
  "M2 fail in 2 cells" therefore carries almost no information.
Fix (for the next distill test, not this one): set bars from the measured draw spread first (a 3-draw pilot on R128 costs about 15 minutes).

**D2. WEAKENS: "Shown" lines that the counts only suggest.** `RESULTS.md:21-24`:
- "consistent small gain ... D128 above R128 in all 4 cells on both kinds": true for 3-draw cell means; at draw level it is
  7 of 12 on sums (0.9 SE). Line 26-27 of the same file already says sums "is within draw noise", so the two lines disagree.
- "D128 cost 9x9 maze skill in the two k = 16,384 cells (-18 and -10)": I get -14.0 over those 6 draws, SE 7.7, 5 of 6 draws
  below zero (-38, -9, -7, -35, +11, -6); at k = 64 it is +12.7, SE 11.7. Suggested at k = 16,384 (1.8 SE), not shown.
- "W128 is as good or better on sums (-1.75)": -1.75 with SE 4.5 cannot tell better from worse. Not shown either way.
Fix: relabel these three to suggested. The verdict word (NOT PASSED, NOT PROVED WRONG) needs no change.

**D3. NIT (disclosed): the rebuilt nets are not the ruler's nets.** Seed 1's source chose fixed depth 8 instead of 16
(`RESULTS.md:46-48`), R128 draw 0 does not equal the ruler's record (`RESULTS.md:50-52`). The comparison D vs R is like for
like (same rebuilt nets), so the result stands, but it says nothing about the ruler's absolute numbers. Cause of the
rebuild: checkpoints were kept local (`PASSMARKS.md:11-12`). This is a general risk, see R1's second point.

Recount, distill (shown): R128 vs D128 vs W128 cell means for s0 k64 sums4 155.3 / 160.0 / 179.0; s1 k16384 grids5
128.0 / 129.7 / 129.0; s0 k16384 9x9 281.0 / 263.0 / 276.3; 60 sleep files present (5 arms x 2 branches x 2 seeds x 3 draws).

### 3.3 Relation-net race (`artifacts/claude-relnet-eq-20260928/`)

**R1. BLOCKS (timeliness, not the marks): it cannot finish on CPU as sealed, and the sealed fallback is not followed.**
`TIMING-ESTIMATE.md` (b): about 54 h per dev run at one thread, about 30 h at two, four dev runs about 216 core-hours,
then the holdout (about 32 core-hours). I re-derived: 4,096 maze batches x 41.3 s = 47.0 h, plus sleeps and scoring
(shown, arithmetic from the file's own measurements). `ADDENDUM-4.md:15` says: if a measured estimate overturns CPU
feasibility, "a separate GPU addendum must be committed before the first new maze score, with strict fp32, TF32 disabled,
and CPU-equivalent smoke results; at most one rental and $4". `PASSMARKS-C.md:80-81` instead says "I report it and do not
change the recipe". Practice is running (`PRACTICE-LAUNCH.md`, started 19:07 UTC, about 6 to 8 h). Fix: write the GPU addendum
now, or shrink the ladder to the two practised runs ("pre", seeds 0 and 1, about 108 core-hours) and add the fresh copies
later (`TIMING-ESTIMATE.md` lists this). Ben's Vast permission is $4 per job (09-28 19:14 UTC per the brief).
Second point (untested risk): the practised weights stay local and untracked (`PRACTICE-LAUNCH.md`, last line). A GPU run on
another machine cannot resume from them, and the distill run shows what a rebuild costs (D3). Copy `source.pt` (6.6 MB) somewhere
durable and record the sha256 already written to `source.json`.

**R2. WEAKENS: the "any" reading of REJECTED** (X2), the only one of the three that turns one noisy seed into REJECTED.

**R3. NIT: a sealed "shown" that is stale.** `PASSMARKS-C.md:78-79` says the net costs 4-6x the loop per step ("shown").
The timing probe later measured 12.1x per maze update (41.3 s vs 3.42 s at one thread) and 3.8x per practice step.
`TIMING-ESTIMATE.md` already says so; the sealed page should carry a one-line pointer.

**R4. WEAKENS: a mazes-only win cannot separate "better few-example learner" from "a pair state fits reachability".** Suggested.
The plug-in takes the same geometry inputs as the loop and no maze rule (plug-in docstring L19), so it is not more maze-built than the
baseline. But a per-cell-pair state is the natural shape of a reachability problem. Fix: word the verdict "on mazes"; the cheapest
test is to run the two practised relnet sources on one of H1's new kinds once H1's harness accepts a plug-in (graph is the
sharp one).

**R5. NIT:** seed 1 is stopped and resumed on more threads (`claude_relnet_eq_rebalance.py:38-46`). Resume restores weights, optimizer,
schedule and both RNG streams, but float summation order changes with thread count, so the two seeds are not bit-comparable.
Harmless; disclose it in RESULTS.

Recount, relnet (shown): weights 1,644,198 vs 1,645,726 = -0.093%; 12,000 x 3.18 s = 10.6 h; maze-batch ratio 41.3 / 3.42 = 12.08.

### 3.4 H1 held-out kinds (`artifacts/claude-dir-h1-heldout-20260928/`)

**H1-a. WEAKENS: V3 (usable ladder) can pass on the wrong arm.** `PASSMARKS.md:16`, code `scripts/claude_dir_h1_marks.py:67-74`:
V3 passes if **any** of the four arms in **any** seed has at least three rungs strictly between 10% and 90%. A ladder where only the
fresh plain net sits in that band while the practised loop is at 0 or at 100 passes V3. M4 (F_eq >= 20, L29) catches a floor but
not a ceiling: a practised loop at 100 on every rung makes M1, M2, M2b, M3 pass with nothing learned about "few examples".
Fix: require the two arms M2 compares (practised loop and fresh loop) to each be in the band on at least 3 shared rungs, on dev.
Cheapest test: the dev ladder itself, which the plan already runs before the holdout.

**H1-b. WEAKENS: on graph, the plain arm may be unable to do the job at any number of examples.** Suggested.
Hop distance at 14 nodes needs up to about 12 rounds of spreading; the practised plain net has one pass. M1 and M2b then mostly
measure "can express BFS", not "learns from fewer examples". The ruler has the same confound on mazes and accepts it, but H1's
roll-up sentence (`PASSMARKS.md:35-39`) will say "shown on further kinds". Fix: add a per-kind validity row, "plain's k = 16,384
accuracy"; if it is below 90 the plain comparison is labelled "expressivity", and M2 (vs the fresh loop) is the row that carries
the claim. Cheapest test: plain and loop at k = 16,384 on dev.

**H1-c. NIT:** the marks were calibrated after the maze numbers were known (`PASSMARKS.md:50`, disclosed). Fine; do not call the
maze reproduction "evidence".

**H1-d. NIT (untested):** the torch part has never run. `scripts/claude_dir_h1_bench.py:47-55` replaces `B.exact` on the sealed harness
module. Any module that imported `exact` by name keeps the old checker and would score graph and rank answers as maze answers
(all zeros). V3 would then fail loudly, so it is an INCONCLUSIVE, not a silent error.

Recount, H1 (shown): the marks arithmetic reproduces the published maze numbers I checked: F_eq 51.00 / 51.29 (loop), 33.79 / 33.58 (plain),
20.67 / 21.50 (fresh loop), 22.46 / 25.00 (fresh plain); M1 = 17.21 / 17.71, M2 = 30.33 / 29.79 (`PASSMARKS.md:50`, recomputed from
`eq-runs`). Collapsed rung (30 points below both neighbours): only `loop-fresh-s1` at k = 1,024 (0 of 300) and k = 16,384 (18 of 300).

### 3.5 H2 numbers pool (`artifacts/claude-dir-h2-numbers-20260928/`)

**H2-a. WEAKENS: the change moves repeats and target variety together, so a PASS cannot name the cause.** `PASSMARKS.md:7-11, 14-16`.
The idea is stated as "stop showing the same items so often" (69.6 draws per pair instead of 2,410 per hand, recounted:
2,560,000 draws / 36,782 = 69.6; / 1,062 = 2,410). But the new pool also gives every hand 24-odd targets, and target 24 falls
from 100% to 2.9% of the practice (L31). A pass could be "targets forced real arithmetic". Also the pool uses the whole hand space:
1,519 hands + 300 held-out + one hand left over (presumably 1,1,1,1, which reaches at most 4, so no target from 5 to 40) = 1,820 = C(16,4) (shown for the total, inferred for the leftover), so the held-out
300 stay the only unseen hands (good) but P_other (L48) is on **seen hands with unseen targets**.
Fix: word a PASS as "a much larger (hand, target) pool fixes it", not "fewer repeats". Cheapest test to split them (untested):
the old target-24 pool with 1/35 of the numbers4 draws (same 69.6 draws per hand); if it still memorises or underfits, repeats alone
are not the lever.

**H2-b. WEAKENS: P_other has no stated floor.** The WRONG branch "too little target 24" (L80-82) uses P_other >= 30, but the search-free
floor of 7.5 (L61) is for target 24. Easy targets (a sum of the four numbers) have a much higher no-search floor. Fix: compute
the code-only floor on the 300 dev pairs before any run (`claude_dir_h2_pool.py selftest` needs no torch).

**H2-c. NIT:** practice exactness between 0.5 and 0.9 is in neither WRONG branch (L76-79); it lands in PARTIAL (L87-88), as intended.
Say so.

**H2-d. NIT:** replication seeds 15 and 16 (L37-39) "cannot overturn a primary WRONG": correct and good.

Recount, H2 (shown): pool 37,082 pairs, 1,062 old, minus 300 dev = 36,782; old nets held-out numbers4 = 1,1,0,1 / 1,0,1,3 / 2,2,3,1 from
`tests.json` of `claude-rsn358u-20260927` and `claude-rsn358u2-20260928` (12 nets, total 16 of 3,600, mean 1.33), matching L39-41;
diagnosis: 1,820 multisets, 1,362 solvable at 24, 300 test hands (`claude-numbers-diag-20260928/DIAGNOSIS.md:23`).

### 3.6 H3 settle gate (`artifacts/claude-dir-h3-design-20260928/`)

**H3-a. BLOCKS (the word): code and marks disagree** (X2). Fix the code (`claude_dir_h3_report.py:41-42`) to the marks' "every".

**H3-b. WEAKENS: weight decay drags the gate bias off its start, so the "dead gate" test misreads.** `scripts/claude_dir_h3_net.py:104`
puts AdamW with decay 0.1 on **all** parameters, including `gate_state.bias` (start 4.0, L69) and the gate weights. With the ruler's
schedule (lr 1e-3, warm-up 200, cosine over 12,000) the decay alone multiplies an unused weight by exp(-0.59) = 0.55, so the bias
goes 4.00 to about 2.2 and the gate from 0.982 to about 0.90 (shown, my arithmetic on the schedule); another 2,048 adaptation
updates at decay 0.1 take it to about 0.86. `PASSMARKS.md:64-66` calls a gate dead only if the mean is above 0.98 or below 0.05,
so a gate that learned nothing but drifted to 0.9 is read as alive. Fix (before practice, nothing has run): exempt `gate_state`
and `gate_surprise` from decay (two parameter groups), and define "dead" by spread: the standard deviation of g over cells and rounds
below 0.02.

**H3-c. WEAKENS: no damping control.** `h + g*(prop - h)` (`claude_dir_h3_net.py:71-80`) with g near a constant is under-relaxation, the textbook
cure for an iteration that keeps overshooting (the loop's cap hits and collapsed rungs are the symptom, `DESIGN.md:76-77`). A +10 result could
come from plain damping with no per-cell "settle" logic. Fix: one extra arm "constant g = 0.9" (same code, no gate weights)
through the same ladder, seeds 0 and 1. Cheapest test: its dev ladder only (about 3 hours per the design's own estimate, `DESIGN.md:122`).

**H3-d. NIT (untested):** the code has never run (`PASSMARKS.md:3, 41`); `selftest` checks that the loop part starts from the loop's random
numbers, not that the gated net equals the loop at start (it does not: g = 0.982 at start).

**H3-e. NIT:** size mark 5 cannot fail (+258 weights = +0.016%); the design's own odds of clearing +10 in both seeds are "a few percent to one in ten"
(`DESIGN.md:118`). A cheap test, but do not expect an answer to the mechanism from it.

Recount, H3 (shown): 1,645,984 - 1,645,726 = 258 weights (256 + 1 + 1); the sparse test's numbers +3.88 / -6.25 are recounted from
`claude-sparse-20260928/race-holdout.json`; fresh sparse F_eq 14.38 / 8.79.

### 3.7 H6 sleep length (`artifacts/claude-dir-h6-sleeplen-20260928/`)

**H6-a. WEAKENS: the test cannot tell "moved too far" from "memorised the 300 puzzles".** From the slp-358n3 raw files (recounted, 400 items):
day_grids after night 3: N = 293, 279, 284, 184; S = 366, 361, 353, 353; L (seeds 13, 14 only) = 290, 267. So L minus N is
-3 and -12 (L is at the no-night level), while S minus N is +73 and +82; L minus S = -76 and -94 (matches `DESIGN.md:18`).
L's day_sums is 388 and 391, above S (381, 388), so the night learned sums and not grids. Two readings: (i) the 6,000 steps at 3e-5 move
the grid weights too far; (ii) each of the 300 day grids is seen about 1,280 times and the net memorises them. B (lr 1.5e-6) rescues under
(i) but may also rescue under a net that simply does not learn (the file says so at `PASSMARKS.md:46-48`, but cannot separate it).
Fix (report-only, no training cost beyond the run): in every L and B night, also score day_grids on fresh puzzles at steps 300, 1,000,
2,000, 6,000 and score the night's own 300 day grids. Peak-then-decay means "too far"; own-puzzles near 300 with fresh flat means
"memorised"; both low means "not learning".

**H6-b. NIT:** the "SD about 20" behind the +40 / -40 bars (`DESIGN.md:18`) has no source I can find: S varies 353 to 366 across four seeds
(SD about 6), N varies 184 to 293 because seed 16's base is low. Only two L runs existed before this test. The bars are not unreasonable, but "two wobbles" is a guess. M0 (3 of 4 seeds) needs L to lose on at least one of seeds 15 or 16, and seed 16's base (184) leaves the
most room to gain.

**H6-c. WEAKENS: no carry-over row** (`design/v3/30-modes/ben-goals-2026-09-26.md:22`: sleep tests "add carry-over rows: skill on a kind
never practised"). The tests are day sizes and old-skill sizes of the same two kinds. Fix: score one code-made kind the nights never train on
(H1's rank or graph panel is code-made and would do) on the morning net for every arm. No training cost.

**H6-d. NIT:** the bf16-autocast GPU path (`claude_slp358n3_nights.py` train step) differs from the CPU one, so absolute numbers change with hardware;
the plan re-runs N, S and L in the same code on the same card, which is the right control (`PASSMARKS.md:19-20`).

Recount, H6 (shown): L minus S = -76 / -94; S minus N = +73 / +82; L minus N = -3 / -12 (day_grids of 400, seeds 13 / 14); B and L sharing every draw is
enforced by `plan_identical_L_B` (`scripts/claude_dir_h6_sleeplen.py:108, 128`).

---------------------------------------------------------------------------------------------------------------

## 4. What can still be fixed before a first score

| Item | Needs | When |
|---|---|---|
| X1 gate noise (addendum + 3 sleep draws) | addendum; harness run with checkpoint saving | patch: before dev score; relnet: before dev score; H3: before practice |
| X2 one reading of "breaking a gate" | addendum + 3-line edit each in relnet and H3 reports | any time before holdout |
| X3 F_few as second row | addendum | any time before holdout |
| P1 max of the two controls | addendum | before holdout |
| P2 writes-off run | 1 small plug-in + 2 dev ladders | before holdout |
| R1 GPU addendum | Director + Ben ($4 cap) | before the first relnet maze score |
| H1-a V3 on the compared arms | edit to `claude_dir_h1_marks.py:71-74` and PASSMARKS | before the first H1 run |
| H3-b decay exemption, H3-c constant-gate arm | edit to `claude_dir_h3_net.py:104` | before H3 practice |
| H6-a mid-night curve, H6-c carry-over panel | edit to the H6 script | before the H6 job |

The patch PASSMARKS say "no mark changes after this file is committed" (`PASSMARKS.md:3-4`); the race rule is "no change after a design sees any dev or
holdout maze score" (`RACE-PASSMARKS.md:13`). No maze score of the patch, relnet or H3 exists, so an addendum that only adds a required row or
tightens a wording is allowed by the second rule; whether it is allowed by the first is the Director's call. I did not edit any of these files.

---------------------------------------------------------------------------------------------------------------

## 5. Recount table (three or more numbers per test, from raw files, all match the sealed pages)

| Test | Number | Raw source | Value |
|---|---|---|---|
| Ruler (all race tests) | practised loop F_eq, holdout | `eq-runs/loop-s{0,1}-pre/holdout.json` | 51.00 / 51.29 |
| | practised plain F_eq | `plain-s{0,1}-pre` | 33.79 / 33.58 |
| | loop old-kind after k=16,384 sleep, sums4 | `loop-s{0,1}-pre/adapt.json` | 76 / 83 of 200 |
| Patch | stored numbers | `runs/patch-s0/source.json` | 1,652,767 (+0.428%) |
| | guard, sums4 and grids5 | `runs/*/source.json` | 200 / 200 all four nets |
| | write-time cost | `DESIGN.md:86-87` | 4.7 s vs 3.1 s per maze batch |
| Distill | R128 / D128 / W128 s0 k64 sums4 | `sleeps/*.json` | 155.3 / 160.0 / 179.0 |
| | D128 - R128, sums4 / grids5 (12 draws) | `sleeps/*.json` | +4.5 / +9.75 |
| | files present | `sleeps/` | 60 |
| Relnet | weights | `PASSMARKS-C.md:10-11` | 1,644,198 (-0.093%) |
| | maze batch ratio | `timing-t1.json`, `TIMING-ESTIMATE.md` | 41.3 / 3.42 = 12.08 |
| | practice at 1 thread | same | 12,000 x 3.18 s = 10.6 h |
| H1 | maze F_eq of four arms | `eq-runs/*` | 51.00 / 33.79 / 20.67 / 22.46 (seed 0) |
| | M1 on mazes | recomputed | +17.21 / +17.71 |
| | collapsed rungs | recomputed | 2 rungs, `loop-fresh-s1` only |
| H2 | pool pairs | pure Python per `PASSMARKS.md:23-31` | 37,082 / 36,782 |
| | draws per pair | 2,560,000 / 36,782 | 69.6 (old 2,410) |
| | old nets numbers4 | `tests.json` x 2 runs | 12 nets, 16 of 3,600 |
| H3 | added weights | 1,645,984 - 1,645,726 | 258 |
| | sparse F_eq vs loop | `claude-sparse-20260928/race-holdout.json` | +3.88 / -6.25 |
| | fresh sparse | same | 14.38 / 8.79 |
| H6 | L - S, day_grids (400) | `claude-slp358n3-20260927/runs/s13, s14` | -76 / -94 |
| | S - N | same | +73 / +82 |
| | N day_grids, four seeds | `runs/s13..s16` | 293, 279, 284, 184 |

---------------------------------------------------------------------------------------------------------------

## 6. What I could not test, and risks in this review

- **No torch here.** I did not run any net, the H1 kind self-test, the H3 self-test, the H6 script, or any practice or ladder.
  Anything about how a net behaves (P4's size, H3-b's gate values in a trained net, H6-a's mechanism) is suggested or untested.
- **The noise estimate (X1) is small-sample.** It comes from 4 cells x 3 draws of one arm on rebuilt nets, and treats sums and grids noise as
  independent and normal. It excludes net-to-net differences, so it is a lower bound. Treat "24% / 6% / 58% / 94%" as the right order of
  magnitude, not exact. The cheap 3-draw pilot in X1 settles it.
- **Practised weights** for patch and relnet are local to other machines (not in the repo); I read their `source.json` records, not the nets.
- **I did not run the report scripts** on fake data (X2's test); I read the code lines and the marks text side by side.
- **Not judged:** the goals page's ordering of Ben's goals, the small card experiments, and the village model; I kept them out of every claim.
- Two of my calls are judgement, not measurement: rating X2 and H3-a as BLOCKS (they change the verdict word, not the numbers), and rating
  R1 as BLOCKS (it is a feasibility and rules issue, not a flaw in the marks).
