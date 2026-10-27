---
name: ben-runs-mimo-agents
description: "2026-09-21 — Ben runs his own \"MiMo 2.6 Flash\" agents on build prompts I write; I hand him self-contained prompts, then verify each agent's RESULTS.md (seal, re-score, claims vs numbers)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T00:45:36.670Z
---

Ben asked "Give me prompts to give my own thing for it" and then "I have mimo 2.6 flash agents that can do it" — he wants to run builds on his own MiMo 2.6 Flash agents rather than my Opus subagents. I stopped the one Opus agent I had launched.

**Why:** saves his Claude usage; he has cheaper agents available.

**Update 2026-09-21 (later):** Ben: "you should use it for agents now" — I launch MiMo agents myself through the /mimo recipe ([[mimo-skill]]), one `opencode run` at a time, background, then verify. No Opus subagents unless asked.

**How to apply:** For parallel build work, write one self-contained prompt per problem (copy box each), pointing at the worktree and the shared brief `design/v3/30-modes/48-parallel-build-brief-20260921.md`. Don't launch Opus agents for builds unless asked. When a MiMo agent finishes, Ben sends me its final message / RESULTS.md; I verify seal, re-run scoring, check claims ≤ evidence (flash-class agents over-claim). The seven prompts (ears 47, thought 49, reasoner 50, wiring 51, live sleep 52, mouth 53, modes/demo 54) were given 2026-09-21. Related: [[parallel-opus-build-20260921]], [[handoff-copy-box-format]].
