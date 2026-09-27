# Independent saved-checkpoint recount

**Shown: VERIFIER PASS, 337 recorded checks, zero mismatches.** This verifies
saved-artifact consistency and same-device reproducibility. It does not change
scientific thresholds or stand in for project reviewer sign-off.

| Run | Grids before sums | Latest model's grids after sums | Routed grids after sums | Sums after practice | Original classification |
| --- | ---: | ---: | ---: | ---: | --- |
| R1 seed 29 | 174 | 0 | 174 | 200 | R1 INCONCLUSIVE |
| R1 seed 30 | 197 | 0 | 197 | 200 | R1 INCONCLUSIVE (aggregate) |
| R2 seed 31 | 200 | 0 | 200 | 200 | R2 PASS |
| R2 seed 32 | 200 | 0 | 200 | 200 | R2 PASS |

The verifier independently computed every item's own-stop, fixed16, any48 and
stop-round values without using the experiment's score or itemwise helpers.
It loaded all eight checkpoints, checked metadata, tensor keys/shapes/dtypes,
state hashes, file byte counts, parameter counts and canonical source versions,
then checked reloads and alternating typed routes. All routed grid losses were
zero. Latest-model grid losses were 174, 197, 200 and 200; gains were zero.

Evidence: [recount.json](recount-fab44d9d17e5/recount.json) contains the individual
booleans, per-item arrays, source/file hashes and all comparisons.
[RUN-NOTE](recount-fab44d9d17e5/RUN-NOTE.md) records the launch. Marks and code were
committed and pushed at `fab44d9d17e5ae3882cdef663b69f38b3265236a` before execution.
The run used MPS, Torch 2.14.0, PID 18369, MacBook-Pro, began at
2026-09-27 04:40:53 UTC and took 21.7 seconds.

**Suggested:** the saved models and reporting code form a reproducible reference
for this scoped mechanism. **Untested:** arbitrary task classification, other
software/device settings, unsaved historical in-memory states, fixed-total-size
continual learning, or 1B retention. Returning the same immutable old checkpoint
is expected to preserve its function; the empirical comparison is against the
newest model on the same training trajectory.

For a fresh reviewer recount, use the same Torch version and an MPS-capable Mac.
Run from the repository root, supplying the full current HEAD commit that
contains byte-identical verifier marks:

```sh
python -B artifacts/codex-retention-20260927/verify/recount.py --passmarks-sha <full-current-HEAD-commit>
```

The command refuses missing or incomplete inputs, source/weight differences,
and an existing `recount-<commit-prefix>` output directory. The final delivery
commit differs from the original recount registration commit, so its output
directory is fresh in a new checkout. Earlier results are never overwritten.
No training, downloads or external machines are required.
