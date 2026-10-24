# Sleep-1L addendum 2 (2026-10-24 ~08:30Z, before any real run)
Sleep-B (branch claude/project-thread-cqc4bi, RESULTS-sleepB.md) found that closed-book sleep made a 2B model worse at using
retrieved notes (diary score 66 vs 84.6 for the base model). Sleep-1L adds one measurement with no mark and no change to the arms:
after training, S1, S2 and S2T are also scored with all 120 facts in context (`<test>_with_notes`). This is compared with the IC arm
(base model with the same notes). A drop of more than 5 points versus IC would mean the same damage is happening on LFM2.5, and
the next sleep test should add open-book rehearsal.
