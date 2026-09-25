# rsn-351b: fairness twin for rsn-351 (fixed before any run; 2026-09-25)

Ben's standing goal (00:04 UTC 09-25): make the 3x model beat the 1x "as much as possible", with
genuine gains only. Fair tuning rule: every learning-rate choice given to the 3x is given to the 1x too.

**One change from 296:** plain 30M arm with lr 1e-4 instead of 3e-4 (`--lr 1e-4`, existing flag), same
generator, steps, batches, reward, seeds 1 and 2, eval. Runner: scripts/claude_rsn296_run.py.

Report-only marks (this run exists to give the 1x the same lr options as the 3x):
- W1: dev-final checked right (1200 generated items, seed 777) for each seed. **The learning rate for
  each size is chosen on dev only** (higher mean dev over both seeds; ties go to 3e-4), never on a panel.
- W2: panel296 v2 and panel294 v3 totals and categories (reported, not used for choosing).
- W3: invented (checked) ≤ 2 on each panel.

The size comparison that counts is made later on a FRESH blind panel written after the recipe is
frozen (design/v3/30-modes/352-fair-size-plan.md).
