# rsn-358i2 pass marks (fixed before any run; sleep research thread, 2026-09-26 17:06 UTC)

**Question:** is the autocast weight cache what made 358i's loop learn slowly on rentals and lose on grids?
**One change** vs 358i's loop arm: bf16 autocast with cache_enabled=False (scripts/claude_rsn358i2_run.py docstring). This is a bug repair, not a design change. Plain never runs no-grad rounds, so it is unaffected, and plain for grading is 358i's own runs/plain-s{1..4}/tests.json (on main).
The marks are the Thread manager's audit Test A (/mnt/project-files/thread-manager/loop-training-audit-2026-09-26.md), fixed there at 16:59 UTC before any fix existed. They are adopted unchanged, plus validity mark V0.
Evidence so far: artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md (SHOWN on CPU; CUDA not yet checked).

## Stage 0, on the rental, before any training
1. Print torch.__version__.
2. Run `python -B scripts/claude_stage0_autocast_grad.py`.
3. If the loop line with free=3 and cache=True shows 0/12 on the rental's CUDA, the mechanism is **proved wrong** on the rental. Stop and train nothing. The fallback is the audit's: 358i loop, seeds 1-2, unchanged, on BensPC, needing Ben's yes.

## Stage 1 marks (loop arm, seeds 1-4, 60,000 steps; 358i's sealed tests, once per checkpoint)
- **V0 validity:** steps_block_nograd = 0 in every train_summary.json. Otherwise the fix did not take, and the result is INCONCLUSIVE.
- **M1 learning speed** (train-log dev, not the test files): dev grids5 at step 10,000 >= 100/200 on >= 3 of 4 seeds.
  - 358i loop: 0/1/2/1.
  - 358a loop (BensPC): 176/163.
  - 358i plain: 160-174.
- **M2:** 4-seed mean of loop - plain on grids5 >= -10. 358i: -77.5.
- **M3:** 4-seed mean of loop - plain on grids6 >= -10. 358i: -83.
- **Suspect confirmed** = V0, M1, M2 and M3.
- **Proved wrong:** dev grids5 at step 10,000 <= 20/200 on >= 3 of 4 seeds, AND the 4-seed mean of loop - plain on grids5 <= -50.
- Anything between is PARTIAL, reported as such with no rescue.
- **Report only:**
  - sums6/8/10/12, grids7, numbers;
  - loop at fixed rounds;
  - seed 4;
  - the 358t-style G0-G3 against plain, for reading beside 358i;
  - torch/CUDA/GPU, and the grad-norm table.

## What each outcome means for registered verdicts
358d, 358i and 358x stay registered as they are and are never rewritten. If the suspect is confirmed, each gets an addendum saying "possibly hit by the autocast cache bug: loop trained on a torch 2.8 rental".
- Rental use is SHOWN for 358i (5090), 358d and 358x. The torch version is recorded nowhere, only in the rent kit.
- Next after a confirmation: 358t reruns with the fix (loop-trm, loop8), then the 358y sweep, all using this autocast.

**Prediction:** suspect confirmed 60%. On CPU the 2.8 bug removes the layers' gradient on about 85% of steps. That fits the 7x slowdown, but the rental's CUDA path and torch version are not yet seen.

**Cost:** 4 loop runs at once on one RTX 5090. 358d's 4 loops took 35 min, and 358i's took 75 min alongside 4 plains. With Stage 0 and evals, about 1.0-1.5 h at about $0.49/h, so $0.50-0.75. Cap: $0.90.
