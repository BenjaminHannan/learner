# ADDENDUM-1 to PASSMARKS.md (H3 settle-gate loop): review fixes X1, X2/H3-a, X3, H3-b, H3-c

Written 2026-09-28 20:59 UTC (`date -u`) by Director helper H10, on the Director's decisions, from the adversarial review
`artifacts/claude-dir-h8-review-20260928/REVIEW.md` (items X1, X2, X3, H3-a, H3-b, H3-c). New file. PASSMARKS.md, DESIGN.md, the v1 plug-in
`scripts/claude_dir_h3_net.py` and the v1 queue files are not edited. PASSMARKS.md line 5 says "No mark changes after this file is committed": this
addendum changes marks, so it is the Director's call (REVIEW.md section 4); it is committed **before any maze score, source guard or practice of
this design exists**, which is the race rule (RACE-PASSMARKS.md: no change after a design sees a dev or holdout maze score).

**Order (checked 20:59 UTC):** written before any maze score of this test was seen. On origin/main (commit d0a10db78) this folder holds only DESIGN.md,
PASSMARKS.md and the four v1 queue files. On origin/builder-outbox it also holds the v1 first-run files `selftest.json`, `selftest.log`,
`harness-selftest.log` (job 1, torch on the Mac): they contain a 200-step practice smoke (loss, mean gate 0.966 after 200 steps) and CPU timings,
and I read them; they are not a maze score, a source-guard score or a mark input, and nothing below depends on them except the timing sentence in
the queue files. No `runs/`, `eq-runs/`, `dev-table.json`, `holdout-table.json` or `source.json` exists on either branch.

## (a) X2 / H3-a: one meaning of "a maze gain made only by breaking an old-kind gate" (supersedes the code, confirms the text)
PASSMARKS.md lines 54-55 already say "in **every** seed where H3's `F_eq` is above the loop, at least one of marks 3-4 fails". The v1 report script
`scripts/claude_dir_h3_report.py:41-42` says `any(...)`. **The text stands; the v1 report script is not used for the holdout verdict.**
The verdict is computed by the new `scripts/claude_dir_h3_report_add1.py`, a copy of the v1 script whose only differences are the rows of this
addendum. Fixed wording: REJECTED-by-breaking needs at least one seed where H3's `F_eq` is above the loop **and every such gaining seed** breaks a
judged old-kind gate (mark 3 or a judged mark 4). "No higher than the loop in both seeds (a tie counts as no higher)" is unchanged.
- Shown (selftest, pure python, `python3 scripts/claude_dir_h3_report_add1.py selftest` prints "selftest ok"): with two fake seeds, one that gains and
  breaks a sleep gate and one that gains and passes everything, the v1 expression `any(...)` gives REJECTED and the add1 verdict gives NOT PROMOTED.
  Both gaining seeds breaking gives REJECTED; a clean double win gives PASS.

## (b) X1: the old-kind sleep gates on the mean of three sleep draws (supersedes PASSMARKS.md line 47, mark 4)
Sealed line: after the k=64 sleep and the k=16,384 sleep, each old kind no more than 6 of 200 below the loop's same (single) record.
- The measured noise (REVIEW.md X1, shown from the distill run's raw sleeps; the review's own caveat: small sample, a lower bound): one sleep draw of
  the same net moves an old-kind count by about 14 of 200 on sums4 and about 5 on grids5, more than the 6-count margin.
- **New rule.** For each seed, branch (k = 64, k = 16,384) and kind (sums4, grids5): take 3 sleep draws of the H3 arm and 3 sleep draws of the loop
  (counts of 200). The gate passes when `mean(H3) >= mean(loop) - max(6, 2 x SE)`, with `SE = sqrt(var_H3/3 + var_loop/3)` and `var` the sample variance
  (n - 1) of that side's 3 draws (2 degrees of freedom each, so SE is itself noisy; the floor of 6 keeps the sealed margin). All four (branch, kind) cells
  must pass in a seed for mark 4 to hold there. Being above the loop always passes, as before. Implemented and selftested in `draw_gate` (report_add1).
- **Mark 3 (old kinds before maze adaptation) is unchanged**: it scores one fixed net on one fixed panel, with no sleep draw.
- **Draws.** Draw 0 is the harness's own recorded sleep (`seed + k`); draws 1 and 2 use the offsets +101 and +202 (the distill script's `DRAW_OFFSETS`).
  Input file, one per seed: `artifacts/claude-dir-h3-design-20260928/sleep-draws/sleep-draws-s{seed}.json` =
  `{"seed": s, "h3": {"64": {"sums4": [a,b,c], "grids5": [a,b,c]}, "16384": {...}}, "loop": {"64": {...}, "16384": {...}}}`, integer counts of 200; the
  report refuses anything but exactly 3 draws.
- **Plan for producing the draws (not code; the driver is not written here because it needs torch to test):**
  1. Checkpoints: H3 v2 `k64.pt` and `k16384.pt` from `eq-runs/h3-pre-s{seed}` (job queue-h3-3-dev-v2, kept in `$HOME/premonition-h3v2`), and the loop's
     `k64.pt` and `k16384.pt` from the baseline `eq-runs/loop-s{seed}-pre` if they still exist on the machine that ran the baseline.
  2. Driver: a small new script, `scripts/claude_dir_h3_sleepdraws.py`, that copies the `sleep` path of `scripts/claude_fewex_distill_sleep.py`
     (`sleep(...)` in mode R, which that run's selftest showed equals the harness sleep bit for bit), sets `B.N` to the arm's plug-in, loads the stage
     checkpoint, builds the same support pool `pool[:k]`, the same replay store and the same old panels the harness used, runs draws 0, 1, 2 with sleep seed
     `seed + k + offset`, and writes one JSON per (arm, seed, branch, draw). Draw 0 must equal the harness's recorded sleep in adapt.json exactly (same code,
     checkpoint and thread count); if any count differs, the draws for that seed are void and mark 4 falls to "skipped" there.
  3. Cost: 16 new sleeps (2 arms x 2 seeds x 2 branches x 2 new draws) at about 5 minutes each on one CPU thread (distill RESULTS.md: about 255 s per R
     sleep; H3's practice step is 2 to 4 percent slower than the loop's in the v1 selftest), about 80 core-minutes, about 20 minutes on four cores. Untested.
  4. If the loop's baseline checkpoints are gone, rebuild the loop's two branches with the same harness command (`--plugin claude_fewex_net --init pre`)
     from its qualified source, take all 3 loop draws from the rebuild, and say so in RESULTS: the distill run showed a rebuild is not the ruler's net
     (its draw 0 differed from the recorded sleep). Never mix rebuilt loop draws with the ruler's single recorded number.
- **"Sleeps skipped" makes mark 4 report-only.** If a seed's sleep-draw file is missing (the Director commits `SLEEPS-SKIPPED.txt` to say so on purpose),
  mark 4 is reported and cannot fail, cannot make a gain "breaking", and a run that meets every other row is worded **"PASS (sleep gates not judged)"**,
  never plain "PASS".

## (c) X3: a second required verdict row, F_few (supersedes the verdict sentence, PASSMARKS.md lines 43 and 58)
**F_few**, the mean over k = 1, 4, 16 and 64 of 100 x right / 300 on the 9x9 holdout (learned stop), **at least +5.0 over the loop's F_few in both seeds.**
Required for PASS like mark 1. It does not enter the REJECTED conditions. Numbers to beat, recounted from `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/holdout.json`
(loop right answers of 300 at k = 1, 4, 16, 64: seed 0 = 1, 0, 28, 137; seed 1 = 1, 0, 3, 190):

| seed | loop F_few | H3 needs F_few at least |
|---:|---:|---:|
| 0 | 13.83 | 18.83 |
| 1 | 16.17 | 21.17 |

Why (REVIEW.md X3; recounted here from the loop's holdout counts: 86.4 and 84.2 percent): F_eq comes mostly from the rungs k >= 256, so a real few-example gain (k <= 64) can read NOT PROMOTED, and Ben's goals page names
"how few examples a new kind takes" as the main measure. The +5.0 margin equals mark 2's. PASS therefore needs marks 1 to 5 **and** this row, in both seeds.

## (d) H3-b: weight decay must not move the gate (supersedes the plug-in named in PASSMARKS.md line 5, and the dead-gate line 65)
- **Plug-in v2:** `scripts/claude_dir_h3_net_v2.py` replaces `claude_dir_h3_net.py` for every scored run of this design (v1 is never scored; no practice has
  started). Differences from v1, all listed in its docstring: the three gate tensors (`gate_state.weight`, `gate_state.bias`, `gate_surprise`) get weight
  decay 0 in two AdamW parameter groups, every other parameter keeps 0.1; `gate_stats` also reports `std_all`.
- **Two places, not one (a deviation from the Director's "2-line change" wording, made because the arithmetic below needs it):** practice (`Practice`) and the
  harness's adaptation and sleep (`Learner`, which decays every parameter at 0.1). v2 therefore also defines a `Learner`, a subclass of the harness Learner
  with the same two groups; all its other settings, updates and sleep are the harness's. The selftest `learner_v2` replaces v1's `learner` check, which asserted
  that the plug-in has no Learner.
- **Why (shown, arithmetic):** an unused weight under decay 0.1 with the practice schedule (lr 1e-3, warm-up 200, cosine over 12,000) is multiplied by
  exp(-0.590) = 0.554 (sum of lr x 0.1 = 0.5901): the gate bias 4.0 goes to about 2.22 and the gate from 0.982 to about 0.90. Each adaptation rung (fresh
  Learner, 2,048 updates, lr 1e-3, warm-up 50) multiplies it by exp(-0.202) = 0.817 again. So a gate that learned nothing would still read about 0.86 to 0.90.
- **Dead gate (supersedes PASSMARKS.md line 65):** a gate is **dead** at a checkpoint when the standard deviation of g over puzzles, rounds and cells is
  below **0.02** on **all three** sets (source sums4, source grids5, dev mazes 9x9) of `scripts/claude_dir_h3_gate_report_v2.py`. The old "mean above 0.98 or
  below 0.05" is still printed as `mean_extreme`, report only. A dead gate at the k = 64 or the k = 16,384 checkpoint of `h3-pre` in either seed means H3 is
  read as the loop with a constant damping, and a PASS may not use the settle-gate mechanism sentence (see (e)).
- Stored weights are unchanged (1,645,984, +0.016% over the loop): mark 5 is unchanged.

## (e) H3-c: the constant-g = 0.9 damping control (adds one arm; report and wording only)
- **Arm:** `scripts/claude_dir_h3_net_v2_const.py`, the v2 plug-in with `Net.CONST_G = 0.9` (a thin plug-in in the style of `claude_patch_eq_fresh.py`): a round is
  `h_new = h + 0.9 (prop - h)` for every cell and round, no gate tensors, 1,645,726 stored weights (the loop's). Same source practice (12,000 steps, seeds 0 and 1,
  `claude_dir_h3_practice_v2.py --plugin claude_dir_h3_net_v2_const`), same ladder (`--init pre`, both seeds, dev and one holdout pass), same harness Learner.
- **Use:** it never changes the verdict word (PASS, REJECTED, NOT PROMOTED are decided by marks 1 to 5, F_few and (a)-(c)). It decides only which sentence a
  PASS may carry (`mechanism_sentence` in report_add1, selftested):
  - **"the per-cell settle gate beats plain damping (constant g = 0.9) by at least 5 F_eq points in both seeds"** only if H3 F_eq is at least the control's F_eq
    + 5.0 in both seeds **and** the gate is not dead (d) at both checkpoints in both seeds and all four dead-gate files exist;
  - otherwise **"mechanism not separated from damping"** (or, with a dead gate, "read as the loop with a constant damping").
- Result that would prove the mechanism story wrong: a PASS in which the control is within 5 F_eq points of H3 in either seed.

## (f) Queue files
New files, all `STATUS: HELD`, replacing the v1 jobs 2 to 4 (which never ran; do not run both): `queue-h3-2-practice-v2.md` (runs the v2 selftest first, then practises
H3 v2 and the control, both seeds), `queue-h3-3-dev-v2.md` (six dev ladders, the add1 dev table, gate reports at k = 64 and k = 16,384), `queue-h3-4-holdout-v2.md`
(six holdout passes, waits for the three-draw sleep files or `SLEEPS-SKIPPED.txt`, then the add1 verdict). The v1 job 1 (selftest of v1) already ran and printed "selftest": "ok"
on the Mac (origin/builder-outbox); its result says nothing about v2, which has its own selftest, `scripts/claude_dir_h3_selftest_v2.py`, as step 0 of job 2-v2.

## Not changed
Marks 1, 2, 3, 5 and their thresholds (+10 over the loop: 61.00 and 61.29; +5 over plain and over fresh H3; old kinds before adaptation at least 190 of 200 and within 6 of the loop;
size within 2%), the ruler, the loop and plain baselines (not retrained), the seeds, the source guard and its gradient check, the one-holdout-pass rule, the "never pooled seeds" rule, and
everything reported-only.

## What I could not test
This box has no torch. `claude_dir_h3_net_v2.py`, `_v2_const.py`, `claude_dir_h3_practice_v2.py`, `claude_dir_h3_gate_report_v2.py` and `claude_dir_h3_selftest_v2.py` were checked with
`python3 -m py_compile` only: **untested**. Run here and passing: the report script's selftest, and one end-to-end run of `claude_dir_h3_report_add1.py` on fake harness JSON in a scratch folder
(dev and holdout splits, with and without sleep draws, control and gate files). The three-draw driver is a plan. The v2 selftest is step 0 of the practice job with a stop rule; if it fails,
nothing is practised and the Director decides.
