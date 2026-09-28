---
name: rsn-299-think
description: rsn-299 think-then-answer = FAIL +4/60; rsn-299b 5-sample vote = FAIL +10/60 vs +12 but wrong 29->10; rsn line stopped for Sept
metadata:
  type: project
---
rsn-299 (reasoning thread, 2026-09-24, assigned by the month-end rebalance 330r item 4). Design design/v3/30-modes/299-think-then-answer.md; verdict artifacts/claude-rsn299-20260924/VERIFY-director.md; blind thinkpanel299 (60 items, Opus key audit 0/60).

- Plain MiniCPM5-1B 28/60, calculator arm 32/60 (+4 vs bar +12) = FAIL. 0 arithmetic errors; wrong 27 vs 29. TIME 1 to 6; the other categories are flat. The 24 shared misses are setup errors; neither arm ever says "not sure".
- Dev path: a special <<expr>> format hurt the 1B's planning (tie 14/28). An identical prompt with the calculator filling each "=" gave 18 vs 13 on dev, then +4 on the blind panel.
- The plain MiniCPM5-1B is on BensPC only, not the Mac; the cloud can't reach Hugging Face. Short dev checks ran on BensPC daytime (about 5 min each).
- Join layer, unused: scripts/claude_think299_agent.py install_think299(loop, model) routes 0/194 DEV-bank turns and 55/60 panel questions.

**Why:** for a 1B, arithmetic isn't the bottleneck; setting up the right sum is.
**How to apply:** don't sell "exact calculator" as the reasoning win. The next lever is checking the setup (sampling plus a vote, or a re-read). It is not in 0.1 under the 330r rule. See [[rsn-298-branching]].

## rsn-299b = registered FAIL (verified 13:25 UTC 2026-09-24, main 10f6e8918)
- 5 sampled calculator runs + 3-of-5 vote, else "not sure". Fresh blind panel: plain 28/60, vote 38/60 (+10 vs bar +12). 0 arith errors; wrong 10 vs 29; "not sure" on 5/6 missing-fact items (plain 0/6); 16/60 no majority.
- A right answer was among the 5 samples on 48/60: the bottleneck is picking, not generating.
- The rsn line STOPS for September; the reasoning row reports FAIL. Month-end (13:17) is still joining install_think299b into 330c for safety, labelled "FAILED its bar, joined for safety" (order 333 -> think299b -> 338 -> 339). Nothing more for the rsn thread.
