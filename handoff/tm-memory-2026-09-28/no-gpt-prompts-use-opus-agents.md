---
name: no-gpt-prompts-use-opus-agents
description: GPT-6 Pro prompts: banned by Ben 02:51 UTC, RE-ALLOWED 09:45 UTC 2026-09-23 (many standalone prompts, hardest problems, full context)
metadata:
  type: feedback
  modified: 2026-09-23T09:52:46.950Z
---
Ben (2026-09-23 02:51 UTC): "No more gpt prompts. You should just research it with a subagent on opus 5.5 max".
Ben (2026-09-23 09:45-09:47 UTC) reversed it: "I can give gpt 6 pro more prompts now... give me a ton of prompts", "They should be the hardest problems... Anything that's an issue that has to resolved at some point", "make sure it gives the entire context of the project since it's a chat not agentic session".

**How to apply:** GPT-6 Pro prompts are allowed again. Format that Ben asked for: one file, one prompt per hard problem, each a code block starting with the same full project-context block (GPT can't see the repo), hardest first. Batch 2 (18 prompts) is at reviews/gpt6pro-2026-09-23/batch2-18-prompts.md and /mnt/project-files/research-2026-09-23/gpt6pro-prompts-batch2.md. Verify every claim in the answers against code and full papers before acting. Opus subagents are still fine for research; every subagent prompt must start with: "Never call WebFetch. Use WebSearch, and download papers with curl + pdftotext."
