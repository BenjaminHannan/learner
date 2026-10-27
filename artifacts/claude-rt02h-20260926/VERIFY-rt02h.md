# VERIFY rt-02h: registered FAIL on H1 (2026-09-26 17:17 UTC)

Owner: Plain-English puzzles thread. The code seal (cbed59867) was committed before the run. Each step ran once on
this container's CPU (fp32), 16:49-17:15 UTC, at $0. The run files and score are in ee8136e68. A separate blind agent
recounted with its own code, without importing claude_rt02h.py and printing integers only. Every count and every
mark agrees with score/rt02h_score.json, and every panel id appears exactly once in both run files.

| Row | Test | Result | Bar | |
|---|---|---|---|---|
| H1 | puzzles read exactly | 86 of 100 (rules D: 100) | >= 85 AND >= D - 2 = 98 | FAIL |
| H2 | lookalikes fired | 2 of 100 (rules D: 10, rt-02e: 4) | <= 2 | pass |
| H3 | puzzles fired with the wrong reading | 0 | <= 2 | pass |
| H4 | general items reaching the head | 0 of 300 | 0 | pass |

**rt-02h is a registered FAIL, and it stays a FAIL.**

## What it shows (counts from the panel; no panel text read or quoted)
- Shown: the learned check fires on far fewer lookalikes than the rules, 2 of 100 against 10. The head said yes to 7
  of the 85 lookalikes with 4-5 numbers, and the exact-number check on the 1B's copy turned down 5 of those 7.
- Shown: all 14 missed puzzles came back with no reading, and none was read wrongly. One of the 10 blind wordings
  (wording 5) was rejected every time, 0 of 10. The other nine wordings read 86 of 90. Recognition is narrow: the head
  learned from the 1B's own drafts in 6 prompt styles and does not reach every new way of asking.
- Shown: on this panel's 10 blind wordings, the rules read all 100 puzzles, so H1's "D - 2" bar was 98.
- Untested: whether broader training wording closes the gap without raising false fires.

## Brain-first next step (Ben 16:05: "How does the human brain do this?")
A person learns to recognise "someone wants me to solve this" from years of hearing many people ask in many
different ways, not from 6 templates. The single change that matches this is breadth: train the same head with the
same features and the same cut rule on far more varied requests and everyday messages. Those would come from GLM 5.3
Flash on the Mac (allowed since Ben's 16:39 "Use GLM") and the 1B's own drafts, with code labels, and the test would be
a fresh blind panel. The rt-02g panel is now used. Under the Redirect, sum puzzles in chat are not in 0.2d, so this
waits behind the learned grid reader owed to 358b3.
