---
name: nudge-means-status-not-reply
description: Coordinator 14:50 UTC 09-26: the harness "user hasn't heard from you" nudge is answered with update_status, not a reply, when Ben is away and nothing needs him
metadata:
  type: feedback
  modified: 2026-09-26T14:50:13.590Z
---
The Sleep research thread answered a harness "say in a few words what you're doing" nudge with a reply saying "nothing needed". The coordinator flagged it (14:50 UTC 09-26): 6+ replies since Ben last wrote, and every reply notifies him.

**Why:** Ben reads notifications; progress-only replies bury real results.
**How to apply:** if Ben hasn't written since my last 2 replies, put progress in update_status (it satisfies the nudge without notifying). Reply only with a result, a blocker, or a decision only he can make. See [[own-your-problem]].
