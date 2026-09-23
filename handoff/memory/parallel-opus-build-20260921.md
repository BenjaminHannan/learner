---
name: parallel-opus-build-20260921
description: "2026-09-21 rulings — commit to borrowed-encoder ears (drop custom ears for now); one Opus medium agent per remaining problem (thought format, reasoner-on-notebook, wiring, live sleep, mouth, modes/demo); mouth = same borrowed-weights approach as ears, not Qwen"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T00:41:49.915Z
---

Ben (2026-09-21): "if the new idea with ears is better, just commit to that. Don't worry about a custom one right now. can you have one opus medium agent work on each of those problems?" Approved items 2–7 of my remaining-work list; on the mouth: "why qwen? Shouldn't it be the same thing as what we did for ears?" → mouth = small open-weight decoder with borrowed weights + our head/format, fine-tuned frames→English; Qwen only ever a placeholder.

**Why:** speed to a talkable, reading, remembering agent; custom from-scratch language parts are deferred, not cancelled.

**How to apply:** Ears rung 2 runs arm C only (rung-1 tape/BiGRU numbers stay as the baseline). Builds go to Opus (medium) agents in parallel, one per problem, each additive with its own file prefix and design-doc number (47 ears, 48 brief, 49 thought format, 50 reasoner-on-notebook, 51 wiring, 52 live sleep, 53 mouth, 54 modes+demo). This overrides [[subagents-gpt-xhigh]] for builds; GPT xhigh stays for research scouts. Related: [[borrowed-ears-weights-ok]].
