---
name: gpt-bridge-serial-only
description: The claude-web (ChatGPT web) bridge cannot run calls concurrently and blocks local file tools in headless mode; use Opus subagents when it times out
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d3ee76bc-6878-4e63-b8cf-0076c8b06e66
  modified: 2026-09-18T04:48:47.180Z
---

Launching several `claude-web xhigh -p` calls at once breaks the single ChatGPT tab (page.goto ERR_ABORTED, "stopped responding", "superseded" 502s), and even a serial retry can hit "browser stage timed out" until the tab recovers. Headless `-p` mode also blocks Read/Glob/Bash for the GPT side, so any source it must see has to be inlined into the prompt. Opus subagents via the Agent tool run concurrently without these problems.

**Why:** Ben asked for research work to be routed through GPT xhigh agents; on 2026-09-17 four concurrent calls all failed and a serial chain then timed out. Ben then said: if GPT times out, use Opus subagents, as many as needed.

**How to apply:** Run GPT bridge calls one at a time with file contents inlined; if the bridge 502s twice, switch to Opus subagents (general-purpose, model opus, run_in_background) and say so. See [[ben-delegation-preference]].

2026-09-18 (building): the bridge only starts if an arm64 node is first on PATH — run `PATH="/opt/homebrew/bin:$PATH" claude-web xhigh ...` (/usr/local/bin/node is x86 and fails with "Bad CPU type"). xhigh works (GPT-5.6 Sol) despite proAvailable=false. With tools allowed, a build task either 502'd ("ChatGPT stopped responding", ~20 turns in) or spent all 15 turns reading without editing. For GPT build jobs: inline the exact code excerpts and ask for a patch, keep each task to one small change; fall back to an Opus subagent after two failures.
