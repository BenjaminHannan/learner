---
name: web-trust-and-reading-requests
description: 2026-09-22 Ben — per-fact approval of web findings is "stupid" at scale; model must judge what is real itself; wants Markdown input and a "read this web page then answer questions" demo
metadata:
  type: feedback
---

Ben, 22 Sep 2026:
- Approving every web finding does not scale ("learn all about doors" -> 1,000 pages). The system should work out which findings are real by itself; Ben only sees the doubtful ones.
- The model should take Markdown-formatted input ("industry standard").
- Cool test he wants: give it a link, it takes in the page, then he asks questions about the page.
- He doubts token count matters much if the model can reason; he cares about beating same-size models on reasoning/puzzles, not general knowledge.
- He asked for a one-off H100 run training a ~50M plain transformer (useful as the same-size baseline and first chat-able thing), rental up to ~$5.

**How to apply:** replace "Ben approves each fact" with a written automatic trust policy (quote re-verified on the fetched page, >=2 independent domains agree, no conflict with taught facts, never personal facts) writing a lower-priority answering source; only conflicts/uncorroborated items queue for Ben. Include Markdown in all ears/talker training data. Build page-reading as link -> fetch -> extract facts -> notebook -> Q&A (placeholder model as reader first). See [[milestone2-thinking-websearch]], [[placeholder-english-ok]], [[benchmark-goal]].
