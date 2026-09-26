# 0.2d gates, ADDENDUM-26: sleep line, fair row A, DEV health gate. Written 2026-09-26 17:47 UTC, before any code or run

These are the Thread manager's three points from 17:46 UTC, all accepted.

1. **Sleep line.** ADDENDUM-24's sleep line ("night pool with dl-6's settings") now reads: the sleep recipe is whichever
   one passes H-B (dl-7b or dl-8); none has passed yet.
2. **Row A fairness.** Our build's reasoner receives the grid from the disclosed code reader (read_latin). Every rival
   therefore runs in two arms, with the same model, prompt recipe, caps and scorer:
   - (i) raw: the plain-English message only;
   - (ii) grid-given: the same message plus the same code-read grid, prepended in plain text.
   Both arms are reported. The "reasoner beats a same-size model" claim is made **only against arm (ii)**, which has the same
   input as ours. A win against arm (i) is reported only, because the reader does part of the work. Benchmarks, which owns the rival runner, is asked to add arm (ii).
3. **DEV health gate D0**, run before any panel. scripts/claude_e2e02d.py runs on DEV chats only (readable practice
   chats; never a TEST-ONLY panel or bank). Marks, fixed now, all integer counts:
   - D0.1: every user turn gets a non-empty reply (count = turns);
   - D0.2: 0 crashes or tracebacks;
   - D0.3: at least 1 fact saved on every chat that teaches one;
   - D0.4: the W input is used on every turn, and the number of turns where the chat did not fit and the store was used instead is reported;
   - D0.5: the reasoner is called on every grid turn, and the number of calls and of grids read is reported;
   - D0.6: one night of sleep completes without error.
   If D0 fails, no row runs. The counts are sealed in D0's own VERIFY before the rows are registered.
