---
name: ask-fable-max-subagent
description: "2026-09-20 Ben — design questions/rulings that used to go to Astra via copy-box now go to a Fable subagent (Agent tool, model \"fable\", maximum thoroughness)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T22:11:16.749Z
---

From 2026-09-20 Ben said: "From now on, ask a fable max subagent." Questions I would have handed to Astra in a copy box (rulings, next-experiment design, diagnosis) go to a subagent spawned with the Agent tool, model "fable", told to reason as thoroughly as possible (the tool has no effort knob, so say it in the prompt).

**Why:** Ben was the relay for every Astra round-trip; this removes him from the loop and lets design questions run in parallel with experiments (see [[parallelize-when-possible]]).
**How to apply:** give the reviewer a fully self-contained prompt (as in [[handoff-copy-box-format]]), have it write its rulings to a new clearly-labelled file (never under Astra's name, never editing Astra's files), record in any freeze manifest that the ruling came from the Fable reviewer under Ben's instruction, and still report the outcome to Ben in plain terms. Implementation still goes to Opus subagents unless Ben says otherwise. Ben can still relay to Astra if he chooses ([[outside-review-option]]).
