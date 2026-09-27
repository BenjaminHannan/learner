# relnet practice gate: pass marks (fixed before any practice result)

Written 2026-09-27 21:01 UTC (committed c53442a71), while the first two practice runs were between steps 250 and 500 of
6,000 and no score existed.
Source: the task prompt ("It must reach 95% on 200 fresh 4-digit sums and on 200 fresh 5x5 grids, and be within 3
points of the loop on each"). Runs: scripts/claude_relnet_practice.py, seeds 0 and 1, lr 1e-3 (the recipe's).

Scored on the **gate** panel (seed 6279901, 200 four-digit sums + 200 5x5 grids, never used for any choice), with
the learned stop and the 48-round cap:
- **G1 (source guard):** the relation net gets at least 190 of 200 on sums and at least 190 of 200 on grids, in
  each seed.
- **G2 (race gate):** on each kind, the relation net is at most 6 of 200 (3 points) below the loop with the same
  seed.
- **Verdict:** PASS if G1 and G2 hold in both seeds. Otherwise FAIL, and not being able to reach the guard is
  reported as a finding.
- **Allowed repair (disclosed if used):** if G1 fails at lr 1e-3, a sweep of lr 5e-4 and 2e-3, chosen on the
  **dev** panel (seed 6270703) only. The chosen lr is then run on both seeds and scored on the gate panel once.
  The loop keeps lr 1e-3, its recipe's value.
- **Report-only:**
  - stop failure: learned-stop score more than 4 of 200 (2 points) below the best fixed depth, with the depth
    picked on dev;
  - mean rounds and cap hits;
  - training minutes.

## Addendum, 2026-09-27 21:19 UTC (before any practice score existed; no mark changed)
Ben wants the gate faster, so it may run on a rented vast.ai GPU in a new session. The handoff is
artifacts/claude-relnet-20260927/HANDOFF-gpu-practice.md. **Registered result:** the GPU runs, if they finish
(`--device cuda`, strict fp32, the same script, seeds, recipe and panels). The CPU runs in the first session
(compiled, started 21:09 UTC) are reported alongside as a replication, not picked by score. If the GPU runs fail or
are not made, the CPU runs are the registered result.
