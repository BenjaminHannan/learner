---
name: proactive-literature-scouting
description: "Ben wants Claude to find relevant recent research (like Anthropic's 2026 J-space work) on its own during design, not wait for him to mention it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e4cbfe4b-0edd-4974-bba0-c4ce5deb664a
  modified: 2026-09-18T20:52:08.729Z
---

When Ben mentioned Anthropic's J-space (July 2026 global-workspace paper) himself, he said: "Things like J-space I want you to be able to figure out yourself. I don't want to draw on my pretty limited knowledge once in a while to solve things."

**Why:** Much relevant work postdates the model's training cutoff; Ben knows he can't be the source of it and wants the design grounded in the latest findings by default.

**How to apply:** When designing any Premonition component, search for 2025-2026 research on that component (frontier-lab blogs, transformer-circuits.pub, arXiv) before or alongside proposing a design, and say what was found. Research sweeps go to subagents/workflows per [[ben-delegation-preference]] and [[workflows-research-only]]. He especially likes surprising biology-to-mechanism ideas like "consolidation pressure" (see [[human-learning-redesign]]).
