# Test D pass marks: the sparse loop (a mixture of experts in each loop block)

Written 2026-09-28 01:40 UTC (`date -u`), before any practice result of this design and before any maze dev or
holdout score of this design exists. No mark changes after this file is committed.

## The design (fixed now)
The race's loop exactly (scripts/claude_fewex_net.py: two shared width-256 blocks, eight heads, the same attention,
the input re-added every round, learned stop, 48-round cap). The one change: each block's feed-forward layer is 8
experts (256 -> 127 -> 256, GELU) with a bias-free learned router on the cell's hidden state that picks the top 2
per cell per round; the two outputs are mixed by a softmax over the two chosen router logits (Mixtral style). The
router gets no kind label, no round number and no hand-written rule. Nothing is frozen or grown. One Switch/Mixtral
load-balancing loss (8 x sum over experts of routing-slot share x mean router probability) at coefficient 0.01 is
added in practice, in maze adaptation and in sleep. It is never tuned. Plug-in: scripts/claude_sparse_net.py.

Stored weights 1,645,198 (loop 1,645,726; -0.03%). Active per cell per round: 860,314 (the 6 unchosen experts of
each block, 12 x 65,407, left out); the loop's is 1,645,726.

Everything else is the harness's, unchanged: ADDENDUM-3's qualified practice (12,000 batches of 64, guard seed
SOURCE_SEED+300), fixed depth chosen on source dev, the maze recipe, sleep, panels, seeds 0 and 1, fp32 on CPU,
scoring. The learner is the baseline learner plus the 0.01 load-balancing term (with the term at 0 it leaves
bit-identical weights; selftest.json).

## Source guard (before any maze run)
Each seed's practised sparse loop gets at least 190 of 200 on the guard's 4-digit sums and at least 190 of 200 on
its 5x5 grids (PASSMARKS.md V1), and every 2-D weight matrix, including every expert and both routers, gets a
nonzero gradient on a sums or a grids batch (V2). If either fails in either seed: report it and stop.

## Test D (applies only after the few-example baseline has passed V1-V3 on main)
**Common gates for each design, in both seeds:** before maze adaptation, at least 95% on each old kind and within three points of the source-trained loop on sums and grids separately; `F_all` at least five points above the source-trained plain model and at least five points above the design's own fresh copy; after both 64-example and 64k sleep branches, each old kind within three points of the loop's corresponding old-kind score. All persistent coefficients count toward the 1.65M-weight budget (within 2% of the loop); raw example memory and inference rounds are disclosed. Learned stopping has the 48-round cap and the same source-selected fixed-depth check. Reaching 50% after 64 examples is report-only.

**Plus:** `F_all` at least 10 points above the loop in both seeds.

**Proved wrong:** `F_all` no higher than the loop in both seeds (a tie counts as no higher), or a maze gain only by
breaking an old-kind gate. Either rejects this design at this budget.

**Verdict words:** PASS if every gate above holds in both seeds. REJECTED if the proved-wrong condition holds.
Otherwise NOT PROMOTED, with the failing gates named.

### How the numbers are read (fixed now, so no choice is left for later)
- `F_all`: PROTOCOL.md's, from the harness's holdout.json: the mean over the nine positive rungs (k = 1, 4, 16, 64,
  256, 1,024, 4,096, 16,384, 65,536) of 100 x right / 300 on the 9x9 holdout, learned stop. Each seed is judged
  alone. Differences are in percentage points.
- "The loop" and "the source-trained plain model" are the few-example baseline's own `loop`/`pre` and `plain`/`pre`
  runs with the same seed, from their published adapt.json and holdout.json. The loop is not retrained here.
  "The design's own fresh copy" is this plug-in run with `--init fresh` (the harness's seed 900000+seed).
- "Before maze adaptation" is the harness's `old.before` record (200 sums4, 200 grids5): at least 190 of 200 each,
  and not more than 6 of 200 below the loop's `old.before` on each kind. After sleep: `sleep.64.old` and
  `sleep.64k.old`, each kind not more than 6 of 200 below the loop's same record. Being above the loop always
  passes.
- Fixed-depth check: learned-stop score more than 2 points below the source-selected fixed depth is a stop failure
  (PROTOCOL.md); it is reported for every rung.
- Order: dev branches (seeds 0 and 1, `pre` and `fresh`) first, with no change of any kind after a dev score is
  seen; then the holdout once. If the baseline reports INCONCLUSIVE, this test is INCONCLUSIVE and the holdout is
  not opened.

## Report only (the paper's mechanism; no pass mark)
For practised and maze-adapted weights (source guard sums and grids; 9x9 dev mazes at k = 0, 64 and 65,536 and
after the 64k sleep), per block: for each pair of consecutive rounds, the share of cells whose two chosen experts
differ from the previous round (none, one or both), also averaged over rounds 2-8 and 9-48; expert use (share of
routing slots and of cell-rounds); and every expert chosen by under 1% of cell-rounds
(scripts/claude_sparse_routes.py; it reads expert choices only and scores nothing). Also reported: the 7x7 and
11x11 panels, the k=64 50% line, `F_few - cold`, mean rounds, cap hits, both sleep `D` values by kind, training
time, optimizer updates, raw example memory, stored and active weights.
