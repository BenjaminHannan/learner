---
name: builders-muse-no-paste
description: Ben's 2026-09-23 rule: builder/subagent work goes to Muse Spark 1.3 on his opencode Go plan, launched without him pasting; cloud can't reach opencode.ai or BensPC
metadata:
  type: feedback
  modified: 2026-09-23T01:35:40.943Z
---
Non-thread subagent work = Muse Spark 1.3 (opencode-go/muse-spark-1.3-contributor) on Ben's opencode Go subscription, not Claude subagents. Ben (2026-09-23 01:35 UTC): "you shouldn't have me use the gui, you should just call it" — he does not want to paste launch boxes.

**Why:** Ben wants builders run automatically.
**How to apply:** Cloud session cannot call them directly: network policy returns 403 for opencode.ai (checked 01:36 UTC), and experiments need BensPC GPU via ssh from the Mac. Proposed fix (awaiting Ben's yes at 01:37): a one-time Mac watcher that polls a GitHub queue folder and runs handoff/kit/mimo/rungo4.sh, pushing replies back. See [[director-role]].
