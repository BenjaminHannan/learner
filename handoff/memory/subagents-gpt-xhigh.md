---
name: subagents-gpt-xhigh
description: "2026-09-21 Ben — tone down Claude usage; ALL subagent work goes to GPT xhigh agents (claude-web bridge), not Opus/Fable subagents"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-21T02:51:53.521Z
---

All delegated work (builds, audits, design reviews, research) goes to GPT xhigh via the bridge: `PATH="/opt/homebrew/bin:$PATH" claude-web xhigh -p "$(cat task.md)" --max-turns 12 --allowedTools "..." < /dev/null`. No Opus or Fable subagents unless Ben says otherwise. Supersedes the Opus-medium rule in [[gpt-bridge-serial-only]] and the Fable-reviewer rule in [[ask-fable-max-subagent]].

**Why:** Ben asked on 2026-09-21 to tone down usage; Claude subagents were burning 100–250k tokens each.

**How to apply:** one GPT call at a time (bridge is serial); inline the needed code/file excerpts; keep each task to one small bounded change; read-only tools unless it must edit. Keep my own main-session work lean too ([[minimize-usage]]): no re-audits or extra arms unless they change a decision. If the bridge is down (launcher not running on 127.0.0.1:17841) or 502s twice, tell Ben and wait/ask rather than silently falling back to Claude subagents.

**22 Sep 2026 update (Ben approved the split):** GPT xhigh for research, literature, design critique and first drafts of standalone scripts (it cannot run code or see the repo, so I always run and check its code). Opus agents allowed for audits/debugging that must run against repo files, but prefer doing those inline. Fable max subagent only when Ben asks.

**2026-09-21 update (Ben):** the bridge works again (verified). Use GPT web xhigh whenever possible; Codex subagents are usable too. Ben is happy for GPT to run as a long-lived research agent, and for more than one to run at once (two parallel calls launched 2026-09-21 as a concurrency test — check they both returned before relying on parallel use).

**Concurrency test result (2026-09-21):** two claude-web calls launched at the same moment BOTH failed with 502 ("ChatGPT stopped responding"). The bridge is still serial: run GPT tasks one after another in a single background shell loop.
