---
name: question-failures-critically
description: Ben 16:51 UTC 09-26: keep tests going while he's away; when a test fails, the Thread manager questions the owning thread critically, the way Ben questions Claude
metadata:
  type: feedback
  modified: 2026-09-26T16:51:36.002Z
---
Ben, 16:51 UTC 09-26 (cmsg_01FuvegZXjMmeUzStiEFVnEW1bAdnbrmFyePHxWg4HmUdu), going away for about 1.5 h: "Just keep having these tests go. When something doesn't work, ask questions critically to the threads working on the problems just as I did with you".

His own questions show the style:
- "didn't I say it could use the 8 workers? Why not do that"
- "can we just stack a ton of layers?"
- "maybe it's something with how we train the models?"
- "why not 50 layers with smaller sizes?"
- "explain where the 12 comes from"
They are plain, they challenge assumptions, they ask "why not the obvious thing", and they ask for the mechanism behind a number.

**Why:** he wants the threads to face the hard questions without him having to ask them.

**How to apply:** after each FAIL or INCONCLUSIVE result, send the owning thread 3 to 5 sharp questions before it plans a next test:
- What exactly failed, and at what step?
- What assumption did the test rest on, and was that assumption itself checked?
- Why not the obvious or simplest fix?
- Could the training recipe, rather than the idea, be the cause?
- How does the brain do it?
- What cheap test would tell the explanations apart?

Don't accept a retry that only nudges a number. Log the questions and the answers in the round log. Also keep the tests moving, with no pauses while he's away. Related: [[thread-manager-line]], [[own-your-problem]].
