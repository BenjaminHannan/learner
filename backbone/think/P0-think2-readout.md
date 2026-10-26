# P0 readout from Think-2's logs (2026-10-26, no new compute)

PREREG-think2.md Addendum C says a Think-2 fail runs PR #131's checks before looped thinking is dropped.
This note reads the first of them, P0, from what Think-2 already logged (backbone/results/think2/*/result_*.json).
Readings that need the checkpoint (forced-gate wiring test, refiner drift, bridge probe) are still to run;
tj's adapter and think_block.pt are on the Mac at ~/learner-ops/think2/ckpt/tj_s0/.

## Think-2 verdict (seed 0, 8,675 validation rows)

| arm | S(4) | vs max(aplus 70.26, tc 71.99) | swap4 cost | gates-off | L4 - L1 |
|---|---|---|---|---|---|
| tj | 70.73 | -1.26 [-1.91, -0.60] | +0.09 | 70.73 | +0.07 |
| tf | 71.82 | -0.17 [-0.86, +0.46] | +0.53 | 72.44 | +0.05 |

Both arms FAIL P1 and trigger wrong-if. tc (the same loss with the block shut) beats aplus by 1.73.

## §3.5 routing rows that the logs already answer

| # | reading | tj | tf | rule fires? |
|---|---|---|---|---|
| 2 | mean \|tanh a\| at the end | 0.051 | 0.123 | tj yes (< 0.1), tf no |
| 4 | swap lesion | 0.09 cost: unused | 0.53: not shown | - |
| 5 | notes across stories (cos_across, proxy for row 5) | 0.99997 | 0.966 | tj: notes are nearly the same for every story |
| 6 | per-lap change (step_rms falls 0.071 -> 0.068; L4 - L1) | +0.07 | +0.05 | laps add nothing in both |
| - | refiner grad norm vs LoRA grad norm (last step) | 0.0016 vs 3.5 | 0.0060 vs 3.7 | the block gets ~1/1000 of the gradient |

Extra readings:
- tf's blind pass (answer from notes + question, no story, first 2,000 rows) scores 36.05; the same rows score 71.15
  with the story. No "notes zeroed" blind baseline was logged, so how much of the 36 comes from the notes is not shown.
- tf with gates off is 0.62 points better than with them on: once the gates open, the notes slightly hurt.
- Dev-set swap cost in tf was 6.3 points at step 250 (while the blind schedule ran) and 0.4 at step 1,250: the
  model used the notes while it was forced to, then stopped.

## Routing (fixed by PR #131 §3.5)

Row 2 fires for tj, so P2a (gate start 0.3) runs before P2b. Remaining order: wiring test and drift on the tj
checkpoint -> T (toy plumbing check) -> P1 (written steps + sham) -> P2a -> P2b, then the give-up rule.
Chain order for P1/P2b: Step 0 found the evidence lines in file order, not chain order (backbone/think3/STEP0-data-check.md).
