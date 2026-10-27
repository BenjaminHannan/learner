# rsn-358e: caveat for moe-grow-eq, stated before anyone runs it (2026-09-26 21:20 UTC)

This adds to ADDENDUM-3-size.md (3), which stays sealed and unchanged. It follows the Thread manager's review at 21:21 UTC.
- In phase A only 4 of the 12 experts can be routed to, each 4d/12 = 85 wide. So the MLP weights a phase-A cell can use are a third of moe's, and the routable MLP total in phase A is a third of the dense control's.
- Expected in advance: its after-A grids5 will likely be below moe-grow's 187 / 188. A lower after-A number is not a surprise and not a finding. The after-A dev score is a report row, and V (grids5 >= 120 after A) still applies.
- When 358e and any follow-up report forgetting, the trainable weight count in phase B goes beside it: dense trains all 1,646,750; moe-grow trains 1,054,728. "Forgot less" and "learned less" are both read against that count.
