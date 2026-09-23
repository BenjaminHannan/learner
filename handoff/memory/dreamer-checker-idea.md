---
name: dreamer-checker-idea
description: "2026-09-21 Ben's idea: a part that hallucinates on purpose to generate ideas, checked by another part; parked as a later milestone"
metadata:
  type: project
---

Ben proposed (2026-09-21) a model that deliberately "hallucinates" candidate ideas and has another part check them. I told him it matches generate-and-verify (AlphaGeometry, FunSearch), works only when checking is more reliable than generating, and fits our design because the notebook + lookup reasoner is an exact checker: dreamer proposes links/rules, checker verifies against taught facts, survivors are labelled "inferred, not taught".

**Why:** it's Ben's own direction for making the assistant produce ideas, not just recall; he knows it needs a bigger model.
**How to apply:** parked, not started — sits after the talker ([[talker-route-b]]) and new names ([[exp21-newnames-result]]) on the [[teachable-roadmap-fable-review]] path. A cheap Mac toy version exists: propose rules over the notebook, measure true rules found vs false ones passed. Limits to keep stating: checker only knows the notebook (consistent ≠ true in the world). If Ben asks to start it, send the design to a Fable reviewer ([[ask-fable-max-subagent]]).
