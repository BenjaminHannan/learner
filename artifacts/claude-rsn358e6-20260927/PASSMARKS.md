# rsn-358e6 marks, SEALED 2026-09-27 02:55:07 UTC (sleep research thread)

The marks are exactly those in PASSMARKS-draft.md in this folder. Both files are sealed together in SEAL-code.sha256.txt. The Thread manager reviewed and cleared them at 02:54 UTC and asked for the two lines below.

1. **What a PASS shows.** A PASS shows that a larger trainable share (882,640, 53%, vs 352,944, 21%) lets the frozen-expert net learn new kinds. It does not separate "attention trains" from "more weights train", and the report will say so.
2. **REPRO conditions.** REPRO holds only if the run uses this same container and the same torch version (2.14.0+cu130) as rsn-358e4. If either differs, the run is INCONCLUSIVE and is not compared.

Run: CPU, 1 thread, seeds 3-8, after rsn-358e4 ends; the Director orders the batches. A run note goes in run/RUN-NOTE.md at each start.
