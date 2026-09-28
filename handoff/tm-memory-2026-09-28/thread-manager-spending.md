---
name: thread-manager-spending
description: Ben 18:54 UTC 09-26: every spend needs Ben's yes on a plan + ELI5 artifact (what it buys, goal, this run's cost, expected cost until fixed); $30 pool; GLM via opencode
metadata:
  type: feedback
  modified: 2026-09-26T18:49:30.063Z
---
Ben's money messages on 09-26, in order:
- 18:39:52: "you can choose to spend money"
- 18:42:25: "I lied you're out of money. You can only spend what's left on the vast and rest has to be on benspc"
- 18:47:31 (cmsg_01FuvegZXjMmeUzStiEFVnEWPjV99TXfE8wX2RKj8kDaF3): "I lied. You have $30 more compute. But you can use him 5.3 flash from my opencode subscription". "him" is read as GLM.

The newest message wins.

**Rentals.** Since 18:47 the rental pool is $30. The Director counts every rental cost against it, including what the two rentals already running (dl-7b, k1f) spend after 18:47. There is no refill beyond it, so never ask Ben for a top-up.

**GLM teacher.** It goes through the opencode subscription on Ben's Mac (the opencode-go provider, already used for Muse agents) instead of OpenRouter. The Director sets up the route, and nobody reads or prints the opencode config or keys. OpenRouter itself ran out of funds at about 18:30. lis320-full-mac stopped on HTTP 402 at 298 of 6,000 rows (outbox b1895b05c). Ben tapped "Keep GLM" at 18:50 on the card, so GLM work continues through opencode. Switching an experiment's teacher route after sealing needs an addendum written first.

**PLAN FIRST (Ben 18:54:40 UTC, cmsg_01FuvegZXjMmeUzStiEFVnEW1jDRbenpQ6jRoT2L9TumxN):** "before people spend money, they have to give me a plan for what the money will do. They should have the eli5 artifact for me when they do so, and what they hope to accomplish. THey should also include in the artifact what they expect to pay after this run before they succeed with fixing their problems". This ends the Thread manager's own spending approval.

Every rental now needs:
- an ELI5 artifact from the owner, following [[ben-eli5-style]], that shows what the money buys, the goal and its pass mark, the cap for this run, and the expected total spend after this run until the problem is fixed (labelled as a guess);
- the Thread manager to check its numbers against the repo and the Director's figures;
- a card to Ben with the link;
- Ben's own yes on that card. The Director releases nothing without it.

Rentals launched before 18:54 (k1f, dl7b, 358t3, mu405) finish under their caps. GLM on the opencode subscription is not per-run money, so it needs no plan.

**Why:** money is limited, and Ben wants to see what each dollar buys. Reasoning gets it first.

**How to apply:**
- Every new rental needs Ben's yes on a plan artifact (above). Keep the cap at no more than $4 per job.
- Order: the next build's gates first (reasoner, reader, sleep), then reasoning, then the rest.
- Use BensPC and CPU when they aren't much slower.
- Take the Director's first-hand pool figure before approving.
- Report every spend and the pool left in the next batch to Ben.
- Ben asked at 18:49 "how are you spending so much money daily? It's $17". The answer: 14 threads x $2 lines (about 30 rentals), the sleep extras, and the reader depot at about $2.70 a day. Keep the depot only while a job needs it.
- Architecture changes and new model downloads still need Ben's own yes.

Related: [[thread-manager-line]], [[check-validity-before-spend]], [[question-failures-critically]].
