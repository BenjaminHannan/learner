---
name: workflows-research-only
description: "Ben wants the Workflow tool (multi-agent orchestration) used only for research tasks, never for code audits, compatibility checks, or implementation"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: daf7c42e-d7f3-43b9-ae1e-ebd0fe3a6e26
  modified: 2026-09-18T11:19:55.127Z
---

Use dynamic workflows only for research (literature, design investigation, open questions). Do code audits, compatibility checks, test writing, and implementation inline with targeted probes, even when ultracode is on.

**Why:** On 2026-09-18 Ben questioned a five-agent transformer compatibility audit ("why would you need a five part compatibility audit") and said: "From now on, only use dynamic workflows for research." A single probe had already found the real bug, so the fan-out was token cost without matching value.

**How to apply:** For verification in beautiful-model, write a small probe script and run it directly. Save Workflow for research-shaped questions. This narrows [[ben-delegation-preference]]: research still goes to agents, but engineering checks stay inline.
