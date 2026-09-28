# Sleep that matches the loop's own earlier answers, round by round: PASS MARKS

Written 2026-09-28 15:53 UTC (`date -u`), before any sleep of this test has run and before any rebuilt net
exists. Ruler: `artifacts/claude-fewex-20260927` (RESULTS-EQ.md; EQ-DEV-GATE.json = PASS). Harness:
`scripts/claude_fewex_eq_bench.py` and `scripts/claude_fewex_bench.py`, imported, not edited. Code:
`scripts/claude_fewex_distill_sleep.py`. Only the practised loop (`loop-s{0,1}-pre`) is used. Nothing here
touches the ruler's one-time maze holdout; all maze scores below are on the ruler's **dev** panels.

## Start points: the saved nets are missing, so they are rebuilt first

`k0.pt`, `k64.pt` and `k16384.pt` are not in this checkout, and neither are the ruler's qualified source nets
(`runs/qual-loop-s{0,1}/source.pt`); checkpoints were kept local to the Mac that ran the ruler. So:

1. **Source nets.** Re-run the unchanged `claude_fewex_source_qualify.py --arm loop --seed {0,1} --steps 12000
   --threads 2` (the qualified recipe of ADDENDUM-3, same seeds) into `rebuild/qual-loop-s{seed}/`.
2. **Rungs.** `claude_fewex_distill_sleep.py rebuild` calls the harness's own functions in `adapt_job`'s order
   (`EQ.identity_source`, `EQ.make_pool`, `EQ.batches`, `B.Learner.maze_batch`, `B.maze_scores`,
   `B.Learner.sleep(pool[:k], seed + k, replay)`, `B.save_stage`) for k = 64 and k = 16,384 only, 1 thread
   each. Skipping the other rungs does not change these two: every rung starts from a fresh copy of the source
   net, its batch order comes from its own `random.Random(9272700 + seed + k)`, and no torch random numbers
   are drawn. This saves about three hours of CPU; it is a disclosed deviation from "re-run the ladder".
3. **Check.** Each rebuild record compares, field by field, k0's dev maze and old scores, rung k's dev maze
   and old scores, and the harness sleep's old and dev maze scores with the ruler's `adapt.json`, and says
   whether each is **exactly** equal. The ruler ran on a different machine (Apple CPU) and possibly a different
   torch build, so exact equality is not expected (suggested). Whether or not it is exact, every arm below
   uses the rebuilt nets, the teacher is the rebuilt `k0.pt`, and the re-run R128 is the control.

## Arms (every sleep: 512 updates, 4 stored sums + 4 stored grids + 8 branch mazes per update)

Everything except the named change is the harness's `Learner.sleep`: same optimizer (AdamW 1e-3, wd 0.1,
betas .9/.95, 50-step warm-up, clip 1), same random draws of puzzles and rounds (`rr` total rounds from 1 to 16,
the last `grad` of them, 1 to min(rr, 6), trained with gradient), same mazes (`pool[:k]`, nothing more stored).
The self-test shows the code's mode R equals the harness sleep bit for bit (`selftest.json`).

Let `CE_s`, `CE_g`, `CE_m` be the harness's per-kind losses (true-answer cross-entropy, mean over the trained
rounds). The harness's step loss is `.25 CE_s + .25 CE_g + .5 CE_m`.

| Arm | Store per old kind | Step loss |
|---|---:|---|
| R128 (control, today's sleep) | 128 | `.25 CE_s + .25 CE_g + .5 CE_m` |
| D128 | 128 | `.25 (CE_s + 1.0 KL_s) + .25 (CE_g + 1.0 KL_g) + .5 CE_m` |
| W128 | 128 | `.25 (2 CE_s) + .25 (2 CE_g) + .5 CE_m` |
| R16 | first 16 | as R128 |
| D16 | first 16 | as D128 |

**The teacher term, fixed now.** `KL_x` = for the same 4 stored puzzles of kind x in that step, the frozen
teacher (rebuilt `k0.pt`, the net before the day's maze practice) runs the same puzzle from a zero state for the
same `rr` rounds, with no gradient. For each of the `grad` rounds the student is trained on, take KL(teacher ‖
student) of the answer-cell distributions at temperature 1, averaged over all answer cells of the 4 puzzles
(the same pooling as the harness's cross-entropy), then average over those `grad` rounds. Weight 1.0, not tuned.

**Reading of "added loss", fixed now.** The KL is added inside each old kind's loss, before the unchanged
.25/.25/.5 weights. W128 doubles the same two losses. So D128 and W128 add exactly the same weight (.25 per
old kind) on the same puzzles; they differ only in whether the extra term is the teacher's answers or a
second copy of the true answers. The mazes' part is identical in all arms.

**Draws.** Draw 0 uses the harness's own sleep seed `seed + k`; draws 1 and 2 use `seed + k + 101` and
`seed + k + 202`. One draw fixes the puzzle, round and maze sequence, and is shared by all five arms.

**Runs.** 5 arms × 2 branches (after k = 64, after k = 16,384) × 2 seeds × 3 draws = 60 sleeps, fp32 CPU,
1 thread each, 4 at a time. Memory disclosure: the D arms hold one extra frozen copy of the net (1,645,726
weights) during sleep only; no maze example and no teacher output is stored.

## Marks

A **cell** is one seed × branch (4 cells). A cell's score is the mean over its 3 draws of the count right on the
ruler's fixed old panel (`D.old_panels()`: 200 sums4, 200 grids5) at the learned stop (`right` in `B.score`,
fixed depth 16 only for the report-only fixed-depth count).

- **Validity.** R128 draw 0 must reproduce the ruler's recorded sleep scores (`adapt.json` → `sleep` → `old`
  right counts, both kinds, both branches, both seeds) exactly. If not, report the differences and use the
  re-run R128 as the control (the marks below already do). Also report whether R128 draw 0 equals the rebuild
  record's own harness sleep exactly (same machine, same code path; a determinism check).
- **M1** (each old kind separately): mean over the 4 cells of (D128 − R128) ≥ 20 of 200, **and** D128 > R128
  strictly in at least 3 of the 4 cells.
- **M1b** (each kind): mean over the 4 cells of (D128 − W128) ≥ 10 of 200.
- **M2**: in every one of the 4 cells, D128's 9×9 dev maze count after sleep (mean over 3 draws, of 300) is at
  most 6 below R128's.
- **PASS** = M1 and M1b on both kinds, and M2.
- **"Helps only as extra weight"** = M1 holds on both kinds but M1b fails on either kind.
- **Proved wrong** = mean over the 4 cells of (D128 − R128) < 5 of 200 on **both** kinds. Then matching its old
  self adds nothing to replay with true answers, at this size.
- Anything else (for example M1 on one kind only, or M1 and M1b with M2 failing) is reported as **not passed,
  not proved wrong**, naming each mark that failed.
- **Smaller store (own verdict).** D16 passes if mean over the 4 cells of (D16 − R16) ≥ 20 of 200 and D16 > R16
  in at least 3 of 4 cells, on each kind. Also report whether D16's cell score is at least R128's − 6 on each
  kind in at least 3 of 4 cells ("a store 8 times smaller plus the teacher matches today's sleep").

## Report only (no mark)

- Spread across the 3 draws (min and max) for every arm and cell.
- The teacher's own scores (rebuilt `k0.pt`) on the fixed and fresh old panels.
- Mean KL(teacher ‖ student) before and after sleep, on all 128 + 128 stored puzzles, per round 1–16 and
  averaged, for every arm (including R and W, where it is not trained on).
- Rounds used: mean learned-stop rounds on the old panels and the dev mazes, and the mean trained rounds
  (`rr`, `grad`) per kind during sleep.
- The 7×7 (of 24) and 11×11 (of 300) dev maze panels.
- A fresh old-kind panel for every arm: 200 sums4 + 200 grids5 from `random.Random(9233200)`
  (`D.SOURCE_SEED + 500`), skipping any puzzle whose tokens equal one in the 128 + 128 store or the fixed
  panel (self-test: 0 skipped, 0 overlap, 400 distinct).

## Process

- Nothing is tuned. A job that crashes is re-run unchanged, and the crash is reported.
- RESULTS.md reports every mark with counts "x of 200" / "x of 300" and labels claims shown / suggested /
  untested. A separate subagent recounts every mark blind from the raw JSON (`sleeps/*.json`) and this file.
- $0, no rentals, fp32 CPU.
