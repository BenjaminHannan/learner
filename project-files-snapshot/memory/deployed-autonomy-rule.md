---
name: deployed-autonomy-rule
description: Ben KEY RULE 2:45 PM ET 10-07 - everything we do must be doable by the model autonomously while deployed (no researcher or test-designer knowledge at runtime)
metadata:
  type: feedback
  modified: 2026-10-07T18:48:28.474Z
---

Ben (18:45 UTC 10-07, project chat): "remember this as a key rule: everything that you do should be able to be done by the model autonomously while it's deployed".
Builds on his 12:01 PM ET rule: everything is learned; hand-written code lives only inside outside tools.

**Why:** the model must work on its own for real users; anything a researcher picks per task (input ranges from the test generator, temperatures tuned on dev answers, format rules of a test) won't exist when deployed.
**How to apply:** every sleep/learning step may use only what the model saw (its own questions, tries, notes) plus fixed design constants that are the same every night. Search/executor are fine as tools the sleep calls itself. Tuning on dev answers to set a runtime value (e.g. the night's temperature) fails the rule; let the model pick from signals it can check without answers. Audit each recipe against this and report non-compliant numbers separately. Related: [[no-hardcoding]], [[fast-sleep]].
