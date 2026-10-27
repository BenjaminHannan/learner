---
name: rsn-358u-pass
description: 2026-09-27 18:20 UTC: rsn-358u PASS, the loop reasoner keeps its lead over plain without being told the puzzle kind (sums6 +144.50, grids6 +41.50)
metadata:
  type: project
  modified: 2026-09-27T18:18:35.948Z
---
**rsn-358u PASS.** Result: artifacts/claude-rsn358u-20260927/RESULTS.md at main 56a1d3a74. All marks were met: V0, V1 poison, and G0-G3.

- **What changed from 358i3:** one change. Every item gets the same env id, so the net must read the puzzle kind from its tokens (Ben 11:34 09-27: no task labels).
- **Setup:** loop 2 x d512 vs plain 8 x d256, seeds 13-16. All 8 runs trained at once on one vast 5090 (torch 2.11).
- **Gaps, loop minus plain:** sums6 +144.50, grids6 +41.50, sums8 +220.25, grids7 +36.75. Numbers stay 0-3 on both nets.
- **Loop scores (the base levels slp-358n3 starts from):** sums8 274, sums10 238, grids7 184 (of 300).
- **Weights:** not yet on the Mac. The copy-back truncated loop-s13, so instance 52964920 was STOPPED. The held re-copy job is handoff/held/rent358u-4-recopy.md.

**Why:** these are the kind-blind nets that slp-358n3, the build's sleep gate H-B, trains at night ([[sleep-trains-reasoner-only]]).

**How to apply:**
- Cite 358u, not 358i3, for "no task label" claims.
- slp-358n3 (sealed a81c4aa69, kit sleep358nv, jobs rent358n3-*) waits for the re-copy.
- Related: [[rsn-358i3-pass]].
