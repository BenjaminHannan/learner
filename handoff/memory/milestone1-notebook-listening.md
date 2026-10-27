---
name: milestone1-notebook-listening
description: 2026-09-22 notebook contract + LISTENING built as plain software; 30/30 lifecycle, 7/7 mutations caught, 33-turn conversation passes
metadata:
  type: project
---

Milestone 1 of the agent build ([[three-modes-goal]], [[outside-review-28-adjudication]]) exists: scripts/fable_notebook_contract.py (append-only hash-chained log, stable IDs + aliases, source tags, supersede, idempotent events, discrete statuses, torn-tail recovery) and scripts/fable_listening_m1.py (structured-line input, template replies, clarifying questions with pending state). Notes: design/v3/30-modes/36-milestone1-notebook-listening-fable.md.

**Why:** outside review said write the contract as software before any model touches it.
**How to apply:** new modes/models must talk to the notebook only through this API; don't add an English parser until Ben's 30 natural turns have been hand-mapped (pass mark 27/30). Still waiting on Ben for those turns.
