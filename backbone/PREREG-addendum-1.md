# Stage 1 addendum 1 (written 2026-10-23 23:20Z, before these runs report)

Generalization probes from the generalization thread (generalize.probes @21b4d92b7, seed 101, 500 fresh train-
distribution visits each): P0 switches nothing; Pword switches only the narrator/question/rule wording to the
validation split's templates. v1 FULL (their RESULTS.md): P0 82.7, Pword 50.6, validation 45.6.

Runs: arm A at 418 steps (Vast, claude-bb-probes); arm A2 (2B) at 418 steps (Vast, claude-bb-a2b); arm B at 418
steps with seed 1 (BensPC, via the PC-runner thread). All are also scored on P0 and Pword.

Marks:
- W1 borrowed reader fixes wording: arm A Pword >= 65.0 (v1 + about 15) AND arm A (P0 - Pword) <= half of v1's
  32.1-point drop (i.e. <= 16.0). Wrong if A's P0 - Pword drop >= 25 points.
- P4 (unchanged): A2 validation >= A validation + 3.0, now at equal steps (418 vs 418).
- Seed check: |B seed 1 - B seed 0| on validation, reported as the noise floor for P3. No pass mark.
