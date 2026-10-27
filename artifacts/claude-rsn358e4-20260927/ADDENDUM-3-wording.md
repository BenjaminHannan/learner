# rsn-358e4 addendum 3: how the verdict will be worded (written 2026-09-27 02:48:50 UTC, before seeds 5-8 are read; no mark changes)

**Why:** the Thread manager, 02:46 UTC. In seed 4 the new router group got 0% of the sums cells, so that seed never tried the new-expert idea for sums (DIAG-new-group-share.md). Seeds 3-4 are the only 358e4 results read so far. I read them at 02:44 UTC and sent them at 02:44:55 UTC. Seeds 5-8 have not been read.

**Marks:** unchanged. V, PASS and proved wrong stay exactly as in ADDENDUM-1.md and ADDENDUM-2.md.

**A seed "tested the routing"** if, after phase B, the new group (experts 4-7) got at least 5% of the sums4 cells in at least one block, AND, after phase C, the new group (experts 8-11) got at least 5% of the maze7 cells in at least one block. These are read from expert_share in result.json. The count of seeds that tested the routing (of 6) is reported next to the verdict.

**Wording, fixed now:**
- If proved wrong fires: "Proved wrong for this freeze-and-grow recipe (zero-initialised new router rows, top-1 routing, old rows frozen, 4 narrow new experts per phase): at equal size with full replay it keeps and learns less than the dense loop. N of 6 seeds tested the routing." Then exactly one of:
  - if N >= 4: "Where the new group did get the new kind, it still learned little, which points to the small trainable share (352,944 of 1,654,446) rather than routing alone (suggested)";
  - if N <= 3: "Most seeds never sent the new kind to the new experts, so this says little about separate experts themselves."
  Either way the report will not say that separate experts, or a mixture of experts, are wrong in general.
- If FAIL or PASS: the same N-of-6 line is added.
- The architecture question still goes to Ben through the Thread manager, as addendum 1 says.
