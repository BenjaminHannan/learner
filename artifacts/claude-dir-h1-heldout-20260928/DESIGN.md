# Few-example learning on two more held-out kinds: design

Written 2026-09-28 19:24 UTC (`date -u`) by Director helper H1. Governing marks: `PASSMARKS.md` (same folder), written first. Nothing here has been trained or scored: this box is CPU-only with no torch. What *was* run here is the pure-python part (`SELFTEST-kinds.log`, `SELFTEST-marks.log`); the torch harness was only syntax-checked. Ruler being reused: `artifacts/claude-fewex-20260927/` (ADDENDUM-3, ADDENDUM-4, RACE-ADDENDUM-1, RESULTS-EQ).

## The question, in plain words

Ben's main measure: how few examples does a *new kind* of problem take, given what the model already knows, compared with (a) a brand-new net and (b) a same-size plain net that had the same practice. So far that is only shown on 9×9 mazes: practised loop F_eq 51.00 / 51.29, practised plain 33.79 / 33.58, fresh loop 20.67 / 21.50. One kind is not enough, and a maze is a grid where every step is local, which is exactly what this small net is built to handle. So the test is repeated on two kinds that are not mazes, not sums, not grids, and not each other.

## The two kinds

| | **graph** ("how many steps away is each thing") | **rank** ("where does each number stand") |
|---|---|---|
| What the net sees | rows of `[EDGE, name_a, name_b]` (the links) and `[NODE, name, blank]` (the things); one thing already carries distance 0 (the start) | a row of n digits (repeats allowed) and a blank row under it |
| What it writes | for every other thing: the number of links on the shortest route from the start, or "cannot get there" | under each digit: how many of the n digits are strictly smaller |
| Sizes | 12 / **14 (trained and graded)** / 16 nodes; links = nodes + 1; 25 / 29 / 33 rows of 3 tokens | 7 / **9 (trained and graded)** / 10 digits; 2 rows |
| Kind of thinking | spreading outward one step at a time along arbitrary links; several rounds | comparing everything with everything and counting; few rounds |
| Vocabulary shared with the source practice | none except the blank marker: every token is in the number-value block that sums and grids never used | the digit tokens sums already use, so it also tests whether known number sense carries |
| Checker | rebuilds the graph from the tokens, breadth-first search, compares every blank | rebuilds the digits from the tokens, counts, compares every blank |

Why these two, and why they are not "built for mazes":
- **Different from mazes.** A maze is a picture where neighbours are next to each other. Graph links are arbitrary pairs of anonymous names, re-drawn at random every item, in random row order, so there is no picture and no locality to lean on. Rank has no path and no spreading at all.
- **Different from sums and grids** (what the sources practised) and from each other: one is a multi-step relational search, the other a one-shot comparison and count. One uses none of the practised tokens, the other reuses digits on purpose, so the carry-over row can tell "same vocabulary" apart from "no shared vocabulary".
- **Fair to this net.** The ruler's nets have no absolute position, only relative offsets clipped at 4. Both formats let every cell find what it needs by *content* (matching names, comparing digits), never by counting columns. This was a requirement for the net to be able to learn either kind at all; it is not a preference for loops. It is also disclosed in Risks.
- **Solvable by a looped reasoner inside 48 rounds.** A reference loop (edge rows read node rows, node rows read edge rows: two rounds per step outward) solves every graph item in at most 12 rounds (farthest distance is limited to 3 to 6); rank needs 2. The selftest checks this for 300 items per size. That shows a solution exists at this budget, not that the net finds it.
- **Nothing to memorise.** The numbers puzzle failed because its pool was 1,062 hands. Here: graph pools are 16,384 items per seed, each with a distinct *structure key* (the graph with names and row order removed, by colour refinement), and the panels are disjoint from the pool on that structure key, not just on the printed text; the count of labelled 14-node, 15-link graphs divided by 14! is 628,990, a lower bound on the number of different unlabelled graphs (selftest), plus the choice of start. Rank inputs number 10^9 ordered rows at the graded size (pool 16,384, panels disjoint on the ordered row). Measured: pool keys 16,384 of 16,384 unique and 0 of 16,384 overlapping any panel, for both seeds and both kinds. Two graph seed pools share 12 structure keys with each other (harmless: they are never in one run). Rank's *answer* space is smaller (multisets of digits), so a rank result rests on the input space, not the answer space; this is a limit, stated.
- **Not trivially solvable.** Code-made wrong-by-design predictors on the dev graded panel score: graph all-unreachable 0, all-one-step 0, two-steps-only 0 (of 300); rank copy-the-digit 1, all-zero 0, scaled-digit 5 (of 300). Each must stay at 15 or below.

Token facts: graph names are `VAL+50 .. VAL+89` (40 names, 14 drawn per item), `NODE=VAL+95`, `EDGE=VAL+96`, distance d is `VAL+d`, unreachable is `VAL+99`. Rank uses `DIG+v` in, `DIG+rank` out (rank up to 9 fits a digit; hence sizes stop at 10). All in the existing 125-token vocabulary; the net receives tokens and the fill-slot grid only, as in the ruler.

## Reusing the ruler exactly (what is identical, what is changed)

| Ruler piece | Here |
|---|---|
| Eight rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384; nested prefixes of one ordered pool per seed, shared by all four arms | identical (pool of 16,384 graded-size items per kind and seed) |
| Equal practice: 512 batches × 32 × 4 updates = 2,048 updates every rung; each selected item visited equally often (every k divides 16,384); a rung never inherits weights | identical (`K.batches` is the ruler's schedule; the selftest checks the visit counts) |
| Qualified 12,000-step sources, seeds 0 and 1, loop and plain; not retrained | identical: same four `runs/qual-*` checkpoints (they live on Ben's Mac, not in git); `check-source` recomputes V1 on guard seed `SOURCE_SEED+300` and records their SHA-256 |
| Fresh arms: `torch.manual_seed(900000+seed)`, same net class | identical |
| lr: loop 1e-3, plain from the source-only sweep; loop fixed depth from source dev; fp32 CPU, no autocast; the sealed `Learner.maze_batch` and scorer | identical (the scorer's `exact` is routed to the new checkers for the new kinds, the sealed code is not edited) |
| F_eq = unweighted mean of eight graded-size accuracies; E50 report-only | identical; E30 added, report-only |
| Dev panel decides validity; holdout scored once after the gate | identical, per kind |
| Panel sizes 7 / 9 / 11 (24+48 / 300+300 / 300+300 items) | graph 12 / 14 / 16 and rank 7 / 9 / 10, same item counts |
| V1, V2, V3 | V1 and V2 unchanged; V2k added (same check on the new kind's adaptation loss); V3 unchanged; V0 added (kind self-test) |
| Sleep branches after k = 64 and k = 16,384 | **dropped**: sleep is not part of F_eq or of this claim; costs time. Old-kind counts after k = 64 and 16,384 are still recorded, so forgetting is visible. |

Arms per kind: **practised loop, fresh loop, practised plain, fresh plain**, two seeds each: 8 jobs per kind, 16 in all. Comparison arms named in Ben's measure: *fresh net* = fresh loop; *plain net with same practice* = practised plain. Fresh plain is kept as a further control (M2b).

## Carry-over row (per kind, per seed)

Skill from practised kinds (sums, grids) helping a never-practised kind:
- **k = 0 (zero-shot):** cold count for all four arms. Reported, not required (as in the goals page). Expect near zero: the maze run had 0 of 300 for every arm.
- **Low-example accuracy F_low** (mean of k = 1, 4, 16, 64, 256): practised loop versus fresh loop is mark **C1** (needs +5.0 points in both seeds); practised loop versus practised plain is reported.
- **Same-vocabulary versus new-vocabulary:** rank reuses practised digit tokens; graph does not. If carry-over shows on rank but not graph, the honest reading is "known number sense carries", not "reasoning skill carries".
- **Not run, untested:** a chain (practise on mazes, then adapt to graph or rank) and carry-over *between* held-out kinds. Listed as a follow-up, not part of any mark here.

## Dev, holdout and sealing

- Per kind, one random stream (seed `PANEL_SEED[kind]+size`) makes dev then holdout panels; every item key is distinct within and across panels. Fingerprints (SHA-256 of the item keys, computed here without scoring anything):
  - graph dev `b816bcbd662858a4d3c1eb3066e00671f1814ded5f78e52e4425ff49f80a04c1`, holdout `2786c383dd7fcefeb5c59fa827c90db0351cb6d5920d9cd96416a809ff6cb82f`
  - rank dev `797908a8f45fe85b662f6842de79a94091472865284586ae397ba60e4b8b622c`, holdout `12705abfac1c87bc863474faf64713f892821b2ac7749ac8e5f56e4a30cf2c64`
  - pool SHA-256 (key list, graded size): graph seed 0 `406db3d527b12d11c72a12ffed039c5ba6ac329f0a9ecf284685dc80d9472487`, seed 1 `993fa661986e85f0699d9b3c7045b83d503e5f91467c50d8fc45898205e73f1b`; rank seed 0 `3c0d8c2da483f6a784aff8a78a3882d1f6aafc1dfdb3cbdc3bedf60845f8edf0`, seed 1 `c88b643dd740ba1cf95bced525e210708efaaf7ca807ae1fd211e0684c411534`.
- The holdout items exist only so the pools can avoid them; no model has scored them. The baselines above were run on the **dev** panel only. The holdout job refuses to run unless `DEV-GATE-<kind>.json` says PASS, and writes a `holdout.started` marker so an arm's holdout is never silently re-opened.
- Difficulty knobs (graph: links = nodes + 1, farthest distance 3 to 6, at least 6 reachable nodes; rank: at least 5 distinct digits) are fixed now. If V3 fails, the kind is INCONCLUSIVE; a changed difficulty needs a new addendum, new dev runs and a stated reason, and the holdout stays unopened until its dev gate passes (the ruler's own history).
- A separate step does a blind recount from the raw JSON and `PASSMARKS.md` only (not from `claude_dir_h1_marks.py`).

## Run order (details in `queue-h1-heldout.md`)

1. `selftest` (kinds, marks, then torch bench) and `check-source` (V1/V2 on the four sources, SHA-256 recorded).
2. Timing pilot, 16 batches per arm and kind, to check the time cap.
3. Graph: 8 dev jobs. Rank: 8 dev jobs. (`adapt`)
4. Per kind: `claude_dir_h1_marks.py gate`. INCONCLUSIVE: stop that kind.
5. Per kind that passed: 8 holdout scorings, then `claude_dir_h1_marks.py score`.
6. Results file with x of N counts, labels shown / suggested / untested, then the blind recount.

## Risks and things this design does not settle

1. **Learnability is unknown.** No net has seen either kind. The graph format needs the net to match names across rows by content and iterate; it could sit at the floor for every arm (V3 catches this: INCONCLUSIVE, not a fail), or be so easy that all arms saturate at high k (F_eq still separates them at low k). Rank could be solved as easily by the plain net as by the loop; if so that is a real result against the loop half of the claim, not a defect.
2. **Fixed depth.** The loop's fixed depth (16) was chosen on sums and grids. Graph items need up to 12 rounds in the reference loop, and adaptation trains only about 20 rounds of carried state per batch (3 free + 2 with gradient, four updates). Tight but inside; the learned stop is the scored reading and the fixed-depth gap is reported.
3. **Unstable fresh loops.** The maze fresh loop collapsed on some rungs (seed 1, k = 1,024: 0 of 300). That can hand the practised loop an easy win on F_eq; M3 (5 of 8 rungs) and the collapsed-rung report are there for that reason.
4. **Two seeds only, two source nets.** Seed 0 and 1 share the same qualified sources as the maze run, so source-net luck is shared across kinds; nothing here estimates source-training variance beyond those two.
5. **Vocabulary overlap.** Graph shares only the blank marker with practice; rank shares digits. Output tokens also differ from the maze's (digit ON/OFF). Neither kind is fully "untouched"; differences between arms are still fair because all four arms see identical tokens.
6. **Structure key is conservative, not a proof.** Colour refinement can call two different graphs the same (extra rejection, harmless) but cannot prove two are non-isomorphic; with 10^5-plus classes and random labels an accidental isomorph is negligible, not impossible.
7. **Rank answer space is small** (see above), so rank leans on input-space size.
8. **No sleep, no forgetting claim.** Only counts before / after k = 64 / after k = 16,384 are recorded.
9. **Compute:** CPU only, strict fp32, as the ruler. The torch parts (`claude_dir_h1_bench.py`) were **not run** here; the first thing the queue job does is run its selftest, and any failure stops the job unpatched.
10. **Per-kind marks, not pooled.** Two kinds by two seeds is four cells; the roll-up in `PASSMARKS.md` forbids claiming more than they support.

## Files

- `scripts/claude_dir_h1_kinds.py`: generators, checkers, reference loop, baselines, pools, panels, batches, selftest (run here: `selftest ok`).
- `scripts/claude_dir_h1_marks.py`: F_eq / F_low / V3 / marks / roll-up and the dev-gate and score commands; selftest reproduces every published maze F_eq (holdout and dev) and E50 (run here: `selftest ok`).
- `scripts/claude_dir_h1_bench.py`: torch harness on the sealed ruler code (compiled only, **not run**).
- `SELFTEST-kinds.log`, `SELFTEST-marks.log`: the two pure-python selftest outputs from this box.
- `queue-h1-heldout.md`: the queue job.
