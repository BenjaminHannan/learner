---
name: ben-delegation-preference
description: "Ben wants the main session to minimise its own token usage and push research/audit/drafting work to subagents, keeping only the level-above synthesis and decision for itself"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d3ee76bc-6878-4e63-b8cf-0076c8b06e66
  modified: 2026-09-18T04:48:53.173Z
---

For large research-and-design tasks on beautiful-model, Ben wants as much as possible routed through subagents (GPT xhigh via the bridge, or Opus subagents when that fails), with the main session doing only the judgement that the agents cannot: choosing a stance, catching their errors, and writing the final decision.

**Why:** Stated explicitly on 2026-09-17 ("minimize the usage you do ... your job should just be to think a level above what they can"), and reaffirmed with "you can use as many opus subagents as you want".

**How to apply:** Fan out scaffold audits, literature verification, memo extraction, spec drafting and adversarial review to background agents; read only the sections needed to synthesise; deliver one decision with a fallback rather than a survey. See [[gpt-bridge-serial-only]].

**Update 2026-09-18:** Ben: "Just use opus medium subagents from now on yourself" — stop routing build/research through the GPT bridge (/gpt); use Opus subagents (Agent tool, model "opus"). The Agent tool can't set reasoning effort per call; workflow agent() calls can (effort: 'medium').

**2026-09-19 (reconfirmed):** Ben said "use opus on medium for work". Run implementation/engineering work through Opus subagents at medium effort (Workflow `agent(..., {model:'opus', effort:'medium'})` — the plain Agent tool cannot set effort). The main session scopes, reviews results and decides. Small read-only probes can stay inline.

2026-09-20: Ben repeated "have the opus agent on medium". The Agent tool has no effort parameter; I created W/.claude/agents/opus-medium.md (model: opus, effort: medium — the effort key is undocumented, so unverified). Use subagent_type "opus-medium" if the session accepts it; otherwise model "opus" plus an explicit "work at medium effort, be economical" line in the prompt.
