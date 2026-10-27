# Patch race on the equal-practice ruler: practice recipe and adapter design

Written 2026-09-28 16:05 UTC (`date -u`), before any practice run of this test and before any maze score
of the patch. Governing marks: PASSMARKS.md in this folder. Ruler: artifacts/claude-fewex-20260927
(ADDENDUM-3, ADDENDUM-4, RACE-PASSMARKS.md, RACE-ADDENDUM-1.md; EQ-DEV-GATE.json = PASS). Its harness,
scripts/claude_fewex_eq_bench.py, is used unedited. The old patch run (artifacts/claude-patch-20260927)
and its budget-v2/ stay sealed and unrun.

## What changed from the failed six-kind run (the one change)
Practice goes back to **sums and grids only**, with the ruler's qualified recipe. The patch itself is
unchanged: the sealed core scripts/claude_patch_net.py arm `patch` (two width-256 blocks with MLP 896,
rank 8, the writer, the gate, the bounds). Stored numbers 1,652,767 = 1,648,671 parameters + 4,096 A/B
patch coefficients; the ruler loop has 1,645,726 (+0.43%). New source nets are trained from scratch; no
six-kind checkpoint is used.

## Practice (scripts/claude_patch_eq_practice.py), both arms, logical seeds 0 and 1
**Phase 1, the ruler's qualified recipe (ADDENDUM-3, as claude_fewex_source_qualify.main).**
12,000 batches of 64 from `claude_fewex_data.source_batch` (half sums of 1-4 digits, half 4x4/5x5 Latin
grids with the legend), source RNG `7000000+seed`, torch seed `seed`, AdamW lr 1e-3, betas (0.9, 0.95),
decay 0.1, 200-step warm-up then cosine, clip 1.0, 1-16 rounds with gradient through the last
1-min(6, rounds), stop loss 0.5 x BCE, round RNG `9000+seed`. The patch stays zero (as sealed).

**Phase 2, the sealed 2,000 episodes (claude-patch-20260927/EPISODE-RECIPE.md), sums and grids only.**
Fresh AdamW with the same settings and its own 200-step warm-up and cosine over 2,000. Each episode picks an
order (A, B) of the two kinds at random; supports A, A, B, B (one puzzle each); then 8 B queries and 8 A
queries; all 20 inputs differ. Objective: B-query loss + A-query loss (retention coefficient 1), each
with the answer loss and the 0.5 stop loss on the sampled rounds.
- **Patch:** a write after each support (random 1-16 rounds, the writer on the final state); the patch is
  detached before the third write, so the last two writes are trained through the query losses; the patch
  is carried, detached, into the next episode and never reset. The patch left after episode 2,000 is the
  practised net's stored patch.
- **Loop with episodes:** functional SGD, lr 0.01, on each support; the first two steps' history is
  detached (identity derivative kept); the last two are differentiated (second order); restart from the
  current outer weights each episode. Net: the ruler's loop, built from claude_patch_net `loop` (same
  parameter names and shapes; explicit attention so second derivatives exist). Its checkpoint loads
  strictly into claude_fewex_net `loop` (selftest.json: equal predictions over 48 rounds).
- Both arms use episode data RNG `7500000+seed` and episode round RNG `9500000+seed`, and draw six round
  schedules per episode in the same order, so they see identical episodes and schedules (selftest.json).
- Episode puzzles come from the ruler's own generators (sums 1-4 digits; grids 4x4/5x5 with legend; one size
  per draw, as sealed) and never repeat an input of the ruler's source panels (SOURCE_SEED old panels,
  +1 replay, +100 source dev, +300 guard). The old run used the six-kind generator file; with two kinds I
  use the ruler's generators so practice, episodes, guard and replay share one puzzle format.

**Then, as the ruler:** fixed depth from 8/16/32/48 on source dev `SOURCE_SEED+100`; guard on
`SOURCE_SEED+300` (200 four-digit sums, 200 5x5 grids); the harness's one-step fp32 gradient check. For the
patch the check's loss writes two supports differentiably and scores the rest as queries, so the writer
is included. Report only: the learned-stop guard counts after phase 1, before the episodes.

## Adapter on the ruler (scripts/claude_patch_eq_plugin.py)
- Harness arm `loop`. The A/B patch lives in two buffers, so every harness checkpoint carries it and the
  holdout scores exactly what was trained. Nothing reads a puzzle kind; Learners know only their order.
- **Each maze batch:** first one write, then the harness loop's own four ordinary updates (3 free + 2
  gradient rounds, carried state, no stop loss, lr 1e-3, 50-update warm-up). A rung is 512 writes and
  2,048 updates; the harness refuses anything else.
- **The write (a choice made now):** every puzzle in the batch runs with the current patch to its own
  learned stop (from round 3, cap 48; the old adapter's rule); the writer turns each puzzle's
  correct-minus-predicted feedback into a proposal (the sealed formula); the batch's proposals are
  averaged and blended once: `A = clamp(0.9 A + 0.1 mean_proposal)`, same for B. One write per batch keeps
  the TM's 512-writes rung; averaging keeps the writer's per-puzzle inputs as in practice. No gradient.
- **Sleep:** the harness's 512 updates with replay (4 sums, 4 grids, 8 branch mazes), the patch held fixed,
  no writes; after update 512 the patch is zeroed, so sleep scores and the sleep checkpoint have no patch.
- **Fresh patch** (scripts/claude_patch_eq_fresh.py, `--init fresh`): the same net and random init under
  the harness seed `900000+seed`, never written; its Learner zeroes the patch and freezes writer, rank
  slots and gate, and makes only the ordinary updates. It is bit-identical to the harness's own learner on
  the same net (selftest.json).
- **Loop with episodes** runs through the ruler's default plug-in (claude_fewex_net and the harness's own
  learner), exactly like the baseline loop, from this test's loop-with-episodes checkpoint.
- **Report-only fast path** (scripts/claude_patch_eq_fastpath.py): at k = 1, 4, 16, 64, a clean copy of the
  practised patch, ordinary weights frozen, only the rung's 512 writes, then the 9x9 **dev** panel.

## Commands (fp32 CPU, no autocast, same device for every arm)
```
python -B scripts/claude_patch_eq_practice.py --arm {patch,loop_ep} --seed {0,1} --out artifacts/claude-patch-eq-20260928/runs/{patch,loop_ep}-s{seed}
python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_patch_eq_plugin --arm loop --seed S --init pre   --source .../runs/patch-sS   --out .../eq-runs/patch-sS
python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_patch_eq_fresh  --arm loop --seed S --init fresh --source .../runs/patch-sS   --out .../eq-runs/fresh-sS
python -B scripts/claude_fewex_eq_bench.py adapt                                 --arm loop --seed S --init pre   --source .../runs/loop_ep-sS --out .../eq-runs/loopep-sS
python -B scripts/claude_patch_eq_fastpath.py --seed S --source .../runs/patch-sS --out .../fastpath-dev-sS.json
python -B scripts/claude_patch_eq_report.py dev      # dev tables only
python -B scripts/claude_fewex_eq_bench.py holdout ... (same plug-in, arm, seed, init, out as adapt), once
python -B scripts/claude_patch_eq_report.py holdout  # marks and verdict
```
The fresh arm reads only the fixed depth from runs/patch-sS (as the sparse test's fresh arm did).

## Compute
This chat's machine: 4 CPU cores, no GPU, $0. Measured before any run, one thread: a practice batch
0.89 s; an episode 0.25 s (patch) and 0.45 s (loop with episodes); a maze batch about 4.7 s for the patch
with its write against 3.1 s for the loop. Estimate (untested): practice about 3.5 hours with the four nets
in parallel; dev ladders about 5-8 hours; holdout under 1 hour.
