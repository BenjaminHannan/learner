---
name: director-role-and-rules
description: Premonition Director thread (started 2026-09-28): role, finish line, helper rules, files to resume from
metadata:
  type: project
---

Thread Claude acts as Director for Ben's Premonition (repo BenjaminHannan/learner, commit to main, no PRs). Resume from handoff/director-roadmap.md (finish line + status) and handoff/director-board.md (helpers). Shared helper rules: handoff/director-briefs/rules.md.
Helpers = Agent-tool subagents, model sonnet, max 4 at once, told not to run git (Director commits), no hearthbot calls.
**Why:** Ben wants autonomous progress, results reported one message each, few status pings (usage matters).
**How to apply:** this box is CPU-only, no torch; training goes via handoff/queue/ (Mac watcher, BensPC). Only Ben approves architecture changes, new model downloads, data-rule changes, replacing reasoner with plain net. Ben alone declares the project finished.
