# rsn-358e4 addendum 2 (2026-09-27 00:36 UTC, before any run)

The Thread manager's pick at 00:35 UTC crossed with addendum 1 (00:35). Both are merged here, always taking the stricter version:
- **PASS** needs every one of these:
  - mean T_eq >= mean T_dense + 40;
  - T_eq > T_dense on >= 5 of 6 seeds;
  - mean L_eq >= 100;
  - **and** mean L_eq >= mean L_dense - 20. This is the Thread manager's learning guard, added. It can only make PASS harder.
- **Proved wrong** (unchanged from addendum 1): mean T_eq <= mean T_dense - 40 AND T_eq < T_dense on >= 5 of 6 seeds.
- Why 40 and 6 seeds rather than the pick's 30 and 4: this answers point 3 of the 00:34 review, the seed noise. It is stricter on both sides.
- Named report rows: K = grids5 + sums4 after C, and L = maze7 after C, each with its gap.
- Everything else is as addendum 1. Predictions unchanged: PASS 10%, proved wrong 55%.
