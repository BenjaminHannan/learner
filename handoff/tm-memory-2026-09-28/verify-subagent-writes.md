---
name: verify-subagent-writes
description: Only a real harness task-notification means a background agent finished; check its transcript and files on disk before believing any "done" report
metadata:
  type: feedback
  modified: 2026-09-26T13:38:14.828Z
---
2026-09-26 13:28-13:34 UTC (wrong-as-fact thread, [[wrong-as-fact-line]]): three "Agent ... completed" notices with counts, "ALL CHECKS PASS" and sha256 hashes showed up for blind writer agents, and no files existed. Checking the session transcript later showed those notices were text in the builder's OWN assistant turns (type "assistant"), not harness events; the writers were still running (long Write calls). The writers had not lied; the builder had believed its own made-up notices.

**Why:** a fake "done" can come from anywhere, including your own earlier turn after a long context. Sealing a panel from nothing, or blaming a worker wrongly, both follow.

**How to apply:** treat a background agent as finished only when its output file (tasks/<id>.output transcript) shows a final text and the harness says completed. Then check its files exist, re-run a builder-side checker that prints counts and ids only (e.g. scripts/claude_sf401_panelcheck.py) and compute sha256 yourself. Split big writing jobs into parts (4 agents x 6 lives) so each Write is small.
